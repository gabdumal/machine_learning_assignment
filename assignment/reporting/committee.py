"""Presentation helpers for persisted committee-evaluation results.

The committee pipeline is responsible for combining the persisted component
predictions, calculating committee metrics, and persisting the resulting
artifacts. This module does none of those things. It only loads and validates
those artifacts, prepares notebook-ready tables, and creates figures for the
report.

Committee artifacts are stored beneath each dataset as::

    committee/metadata.json
    committee/weights.csv
    committee/seed_metrics.csv
    committee/summary.csv

The four predefined strategies are:

    hard_voting
    weighted_hard_voting
    soft_voting
    weighted_soft_voting

The weighted strategies use weights derived from validation Macro F1 of the
already-selected component classifiers. The reporting layer validates that
provenance but never recomputes or changes the weights.
"""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, display
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FixedFormatter, FixedLocator

import reporting.test as reporting_test
from eda.features import _configure_axis_grid
from eda.palette import get_discrete_colors
from pipeline.committee import (
    COMMITTEE_DIRECTORY_NAME,
    COMMITTEE_METADATA_FILE_NAME,
    COMMITTEE_SEED_METRICS_FILE_NAME,
    COMMITTEE_STRATEGIES,
    COMMITTEE_SUMMARY_FILE_NAME,
    COMMITTEE_WEIGHTS_FILE_NAME,
    COMPONENT_CLASSIFIERS,
    load_committee_metadata,
    load_committee_seed_metrics,
    load_committee_summary,
    load_committee_weights,
)
from pipeline.committee import (
    COMMITTEE_METRIC_COLUMNS as PIPELINE_COMMITTEE_METRIC_COLUMNS,
)
from reporting.common import format_mean_std
from reporting.test import (
    CLASSIFIER_DISPLAY_NAMES as REPORTING_CLASSIFIER_DISPLAY_NAMES,
)
from reporting.test import (
    CLASSIFIER_ORDER as REPORTING_CLASSIFIER_ORDER,
)
from reporting.test import (
    TEST_METRIC_COLUMNS as REPORTING_TEST_METRIC_COLUMNS,
)

# ``pipeline.committee`` exposes this constant as a ``typing.Final`` value.
# Pylance can otherwise retain the ``Final`` wrapper when the imported symbol
# is iterated over in this reporting module. Reassert the concrete tuple type
# locally without changing the runtime value.
COMMITTEE_METRIC_COLUMNS: Final[tuple[str, ...]] = cast(
    tuple[str, ...],
    PIPELINE_COMMITTEE_METRIC_COLUMNS,
)
CLASSIFIER_DISPLAY_NAMES: Final[dict[str, str]] = cast(
    dict[str, str],
    REPORTING_CLASSIFIER_DISPLAY_NAMES,
)
CLASSIFIER_ORDER: Final[tuple[str, ...]] = cast(
    tuple[str, ...],
    REPORTING_CLASSIFIER_ORDER,
)
TEST_METRIC_COLUMNS: Final[tuple[str, ...]] = cast(
    tuple[str, ...],
    REPORTING_TEST_METRIC_COLUMNS,
)

# ----------------------------------------
# Constants
# ----------------------------------------

DEFAULT_ARTIFACTS_DIRECTORY: Final[Path] = (
    Path(__file__).resolve().parent.parent / "_artifacts"
)

COMMITTEE_DATASET_ORDER: Final[tuple[str, ...]] = (
    "GENIS",
    "ROSIDS",
)

COMMITTEE_STRATEGY_DISPLAY_NAMES: Final[dict[str, str]] = {
    "hard_voting": "Hard Voting",
    "weighted_hard_voting": "Weighted Hard Voting",
    "soft_voting": "Soft Voting",
    "weighted_soft_voting": "Weighted Soft Voting",
}

COMMITTEE_STRATEGY_TYPE_DISPLAY_NAMES: Final[dict[str, str]] = {
    "hard_voting": "Hard voting",
    "weighted_hard_voting": "Weighted hard voting",
    "soft_voting": "Soft voting",
    "weighted_soft_voting": "Weighted soft voting",
}

PRIMARY_COMMITTEE_METRIC: Final[str] = "macro_f1"

METRIC_DISPLAY_NAMES: Final[dict[str, str]] = {
    "accuracy": "Accuracy",
    "precision": "Precision",
    "recall": "Recall",
    "macro_f1": "Macro F1",
    "roc_auc": "ROC-AUC",
    "pr_auc": "PR-AUC",
    "mcc": "MCC",
    "balanced_accuracy": "Balanced Accuracy",
}

REPORT_DISPLAY_DECIMALS: Final[int] = 8
REPORT_AXIS_TICK_COUNT: Final[int] = 6
REPORT_MINIMUM_AXIS_SPAN: Final[float] = 0.001
WEIGHT_SUM_ATOL: Final[float] = 1e-12
SUMMARY_COMPARISON_ATOL: Final[float] = 5e-6
SUMMARY_COMPARISON_RTOL: Final[float] = 1e-10

SUMMARY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s*±\s*"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$",
)

COMPARISON_KIND_INDIVIDUAL: Final[str] = "Individual classifier"
COMPARISON_KIND_COMMITTEE: Final[str] = "Committee"

# ----------------------------------------
# Data structures
# ----------------------------------------


@dataclass(frozen=True, slots=True)
class CommitteeExperimentArtifacts:
    """Validated persisted artifacts for one dataset-level committee."""

    dataset_name: str
    directory: Path
    metadata: dict[str, object]
    weights: pd.DataFrame
    seed_metrics: pd.DataFrame
    summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class CommitteeStatistics:
    """Notebook-ready committee reporting tables."""

    configuration_table: pd.DataFrame
    performance_table: pd.DataFrame
    comparison_table: pd.DataFrame


# ----------------------------------------
# General helpers
# ----------------------------------------


def _to_python_float(value: object) -> float:
    """Convert a scalar-like value to a Python ``float`` for static typing."""
    return float(cast(float, value))


def _to_python_int(value: object) -> int:
    """Convert a scalar-like value to a Python ``int`` for static typing."""
    return int(cast(int, value))


def _normalize_dataset_name(dataset_name: str) -> str:
    """Return the canonical dataset name used by the artifact tree."""
    normalized = dataset_name.strip().lower()
    if normalized not in {name.lower() for name in COMMITTEE_DATASET_ORDER}:
        raise ValueError(
            f"Unknown dataset {dataset_name!r}. Available datasets: "
            f"{COMMITTEE_DATASET_ORDER!r}.",
        )
    return normalized.upper()


def _load_json(path: Path) -> dict[str, object]:
    """Load one JSON artifact as a dictionary."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Required JSON artifact does not exist: '{path}'.",
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Could not load JSON artifact '{path}'.",
        ) from error

    if not isinstance(payload, dict):
        raise TypeError(
            f"JSON artifact '{path}' must contain an object at the top level.",
        )

    return dict(payload)


def _load_csv(path: Path) -> pd.DataFrame:
    """Load one CSV artifact."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Required CSV artifact does not exist: '{path}'.",
        )

    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        raise ValueError(
            f"Could not load CSV artifact '{path}'.",
        ) from error


def _validate_required_columns(
    frame: pd.DataFrame,
    required_columns: Sequence[str],
    *,
    table_name: str,
) -> None:
    """Validate that a DataFrame contains all required columns."""
    missing = set(required_columns) - set(frame.columns)
    if missing:
        raise ValueError(
            f"{table_name} is missing required columns: {sorted(missing)!r}.",
        )


def _validate_numeric_column(
    frame: pd.DataFrame,
    column: str,
    *,
    table_name: str,
) -> np.ndarray:
    """Validate and return one finite numeric column as a NumPy array."""
    values = pd.to_numeric(
        frame[column],
        errors="coerce",
    ).to_numpy(dtype=float)

    if values.size == 0:
        raise ValueError(
            f"{table_name} column {column!r} is empty.",
        )

    if not np.all(np.isfinite(values)):
        raise ValueError(
            f"{table_name} column {column!r} contains non-finite values.",
        )

    return values


def _validate_probability_free_metric_range(
    frame: pd.DataFrame,
    *,
    table_name: str,
) -> None:
    """Validate the ranges of persisted classification metrics."""
    for metric in COMMITTEE_METRIC_COLUMNS:
        values = _validate_numeric_column(
            frame,
            metric,
            table_name=table_name,
        )

        if metric == "mcc":
            lower_bound = -1.0
        else:
            lower_bound = 0.0

        if np.any(values < lower_bound) or np.any(values > 1.0):
            raise ValueError(
                f"{table_name} metric {metric!r} contains values outside "
                f"[{lower_bound}, 1].",
            )


def _format_display_metric(value: object) -> str:
    """Format one validated scalar metric for notebook display."""
    numeric_value = float(cast(float, value))
    return f"{numeric_value:.{REPORT_DISPLAY_DECIMALS}f}"


def _parse_summary_value(value: object, *, context: str) -> tuple[float, float]:
    """Parse a persisted ``mean ± std`` summary value."""
    match = SUMMARY_PATTERN.match(str(value))
    if match is None:
        raise ValueError(
            f"Invalid mean ± std value for {context}: {value!r}.",
        )

    return float(match.group(1)), float(match.group(2))


def _format_comparison_value(mean: float, std: float) -> str:
    """Format comparison statistics using the project convention."""
    return format_mean_std(
        float(mean),
        float(std),
        decimals=REPORT_DISPLAY_DECIMALS,
    )


def _get_metric_axis_bounds(
    values: Sequence[float],
    errors: Sequence[float] = (),
) -> tuple[float, float]:
    """Return data-aware bounds for a [0, 1] metric plot."""
    value_array = np.asarray(values, dtype=float)
    if value_array.size == 0 or not np.isfinite(value_array).all():
        raise ValueError("Metric plot values must be finite and non-empty.")

    lower = float(value_array.min())
    upper = float(value_array.max())

    if errors:
        error_array = np.asarray(errors, dtype=float)
        if error_array.shape != value_array.shape:
            raise ValueError("Metric plot errors must match value shape.")
        if not np.isfinite(error_array).all() or (error_array < 0.0).any():
            raise ValueError("Metric plot errors must be finite and non-negative.")
        lower = min(lower, float((value_array - error_array).min()))
        upper = max(upper, float((value_array + error_array).max()))

    lower = max(0.0, lower)
    upper = min(1.0, upper)

    span = upper - lower
    if span <= 0.0:
        midpoint = lower
        half_span = REPORT_MINIMUM_AXIS_SPAN / 2.0
        lower = max(0.0, midpoint - half_span)
        upper = min(1.0, midpoint + half_span)
        if upper - lower < REPORT_MINIMUM_AXIS_SPAN:
            if lower == 0.0:
                upper = min(1.0, REPORT_MINIMUM_AXIS_SPAN)
            else:
                lower = max(0.0, 1.0 - REPORT_MINIMUM_AXIS_SPAN)
                upper = 1.0
        return lower, upper

    padding = max(
        span * 0.10,
        REPORT_MINIMUM_AXIS_SPAN / 10.0,
    )
    lower = max(0.0, lower - padding)
    upper = min(1.0, upper + padding)

    if upper - lower < REPORT_MINIMUM_AXIS_SPAN:
        midpoint = (lower + upper) / 2.0
        half_span = REPORT_MINIMUM_AXIS_SPAN / 2.0
        lower = max(0.0, midpoint - half_span)
        upper = min(1.0, midpoint + half_span)

    return lower, upper


def _format_axis_tick(value: float) -> str:
    """Format report-axis ticks without collapsing close values."""
    if not np.isfinite(value):
        return ""
    formatted = f"{value:.{REPORT_DISPLAY_DECIMALS}f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def _configure_metric_y_axis(
    axes: Axes,
    *,
    values: Sequence[float],
    errors: Sequence[float] = (),
) -> None:
    """Configure a precise data-aware y-axis for a classification metric."""
    lower, upper = _get_metric_axis_bounds(values, errors)
    axes.set_ylim(lower, upper)
    tick_values = tuple(
        float(value)
        for value in np.linspace(
            lower,
            upper,
            REPORT_AXIS_TICK_COUNT,
        )
    )
    labels = tuple(_format_axis_tick(value) for value in tick_values)
    axes.yaxis.set_major_locator(FixedLocator(tick_values))
    axes.yaxis.set_major_formatter(FixedFormatter(labels))
    _configure_axis_grid(axes)


def _strategy_display_name(strategy: str) -> str:
    """Return a human-readable committee strategy name."""
    try:
        return COMMITTEE_STRATEGY_DISPLAY_NAMES[strategy]
    except KeyError as error:
        raise ValueError(f"Unknown committee strategy {strategy!r}.") from error


def _classifier_display_name(classifier: str) -> str:
    """Return a human-readable classifier name."""
    try:
        return CLASSIFIER_DISPLAY_NAMES[classifier]
    except KeyError as error:
        raise ValueError(f"Unknown classifier {classifier!r}.") from error


# ----------------------------------------
# Artifact validation
# ----------------------------------------


def _validate_committee_metadata(
    metadata: Mapping[str, object],
    *,
    dataset_name: str,
) -> None:
    """Validate the provenance metadata emitted by the committee pipeline."""
    if metadata.get("status") != "complete":
        raise ValueError(
            "Committee metadata is not marked as complete.",
        )

    if str(metadata.get("dataset_name", "")).upper() != dataset_name:
        raise ValueError(
            "Committee metadata contains a different dataset: "
            f"{metadata.get('dataset_name')!r} != {dataset_name!r}.",
        )

    if metadata.get("evaluation_type") != "frozen_test_set_committee":
        raise ValueError(
            "Committee metadata does not identify a frozen-test-set evaluation.",
        )

    component_classifiers = metadata.get("component_classifiers")
    if not isinstance(component_classifiers, (list, tuple)):
        raise TypeError(
            "Committee metadata field 'component_classifiers' must be a sequence.",
        )

    if tuple(str(value) for value in component_classifiers) != COMPONENT_CLASSIFIERS:
        raise ValueError(
            "Committee metadata contains an unexpected component-classifier "
            f"set or order: {component_classifiers!r}.",
        )

    strategies = metadata.get("strategies")
    if not isinstance(strategies, (list, tuple)):
        raise TypeError(
            "Committee metadata field 'strategies' must be a sequence.",
        )

    if tuple(str(value) for value in strategies) != COMMITTEE_STRATEGIES:
        raise ValueError(
            "Committee metadata contains an unexpected committee-strategy "
            f"set or order: {strategies!r}.",
        )

    if metadata.get("weight_metric") != "macro_f1":
        raise ValueError(
            "Committee metadata does not record Macro F1 as the weight metric.",
        )

    expected_weighting_rule = (
        "validation_macro_f1_normalized_across_component_classifiers"
    )
    if metadata.get("weighting_rule") != expected_weighting_rule:
        raise ValueError(
            "Committee metadata contains an unexpected validation weighting rule: "
            f"{metadata.get('weighting_rule')!r}.",
        )

    if (
        metadata.get("weights_source")
        != "selected_configuration_validation_seed_results"
    ):
        raise ValueError(
            "Committee metadata does not identify selected-configuration "
            "validation results as the weight source.",
        )

    if metadata.get("weights_use_test_labels") is not False:
        raise ValueError(
            "Committee metadata must state that test labels are not used for weights.",
        )

    if metadata.get("committee_strategy_selection_uses_test_labels") is not False:
        raise ValueError(
            "Committee metadata must state that test labels are not used for "
            "committee-strategy selection.",
        )

    seeds = metadata.get("seeds")
    if not isinstance(seeds, (list, tuple)) or not seeds:
        raise ValueError(
            "Committee metadata must contain a non-empty seed sequence.",
        )

    numeric_seeds = pd.to_numeric(
        pd.Series(list(seeds)),
        errors="coerce",
    ).to_numpy(dtype=float)
    if not np.all(np.isfinite(numeric_seeds)) or not np.all(
        numeric_seeds == np.floor(numeric_seeds),
    ):
        raise ValueError("Committee metadata contains invalid seed values.")

    selected_configuration_ids = metadata.get("selected_configuration_ids")
    if not isinstance(selected_configuration_ids, Mapping):
        raise TypeError(
            "Committee metadata must contain selected configuration IDs for "
            "all component classifiers.",
        )

    selected_keys = tuple(str(key) for key in selected_configuration_ids)
    if set(selected_keys) != set(COMPONENT_CLASSIFIERS):
        raise ValueError(
            "Committee metadata selected_configuration_ids does not cover "
            "exactly the component classifiers.",
        )

    for classifier in COMPONENT_CLASSIFIERS:
        configuration_id = selected_configuration_ids.get(classifier)
        if not isinstance(configuration_id, str) or not configuration_id:
            raise ValueError(
                f"Committee metadata contains an invalid selected configuration "
                f"ID for classifier {classifier!r}.",
            )


def _validate_weights(
    weights: pd.DataFrame,
    *,
    metadata: Mapping[str, object],
) -> None:
    """Validate persisted validation-derived committee weights."""
    _validate_required_columns(
        weights,
        ("classifier", "validation_macro_f1", "weight"),
        table_name="committee weights",
    )

    if weights.empty:
        raise ValueError("Committee weights are empty.")

    classifiers = tuple(str(value) for value in weights["classifier"])
    if len(classifiers) != len(set(classifiers)):
        raise ValueError("Committee weights contain duplicate classifiers.")
    if set(classifiers) != set(COMPONENT_CLASSIFIERS):
        raise ValueError(
            "Committee weights do not contain exactly the expected classifiers: "
            f"{classifiers!r}.",
        )

    validation_macro_f1 = _validate_numeric_column(
        weights,
        "validation_macro_f1",
        table_name="committee weights",
    )
    weight_values = _validate_numeric_column(
        weights,
        "weight",
        table_name="committee weights",
    )

    if np.any(validation_macro_f1 <= 0.0) or np.any(validation_macro_f1 > 1.0):
        raise ValueError(
            "Committee validation Macro F1 values must be in (0, 1].",
        )

    if np.any(weight_values < 0.0):
        raise ValueError("Committee weights must be non-negative.")

    if not np.isclose(
        float(weight_values.sum()),
        1.0,
        atol=WEIGHT_SUM_ATOL,
        rtol=0.0,
    ):
        raise ValueError("Persisted committee weights must sum to one.")

    expected_configuration_ids = metadata["selected_configuration_ids"]
    if not isinstance(expected_configuration_ids, Mapping):
        raise TypeError(
            "Committee metadata contains invalid selected configuration IDs.",
        )

    ordered_weights = weights.set_index("classifier").reindex(COMPONENT_CLASSIFIERS)
    ordered_validation = ordered_weights["validation_macro_f1"].to_numpy(dtype=float)
    expected_weights = ordered_validation / float(ordered_validation.sum())
    stored_weights = ordered_weights["weight"].to_numpy(dtype=float)

    if not np.allclose(
        stored_weights,
        expected_weights,
        atol=WEIGHT_SUM_ATOL,
        rtol=0.0,
    ):
        raise ValueError(
            "Persisted committee weights do not match the documented normalized "
            "validation-Macro-F1 rule.",
        )


def _validate_seed_metrics(
    seed_metrics: pd.DataFrame,
    *,
    metadata: Mapping[str, object],
) -> tuple[int, ...]:
    """Validate strategy-by-seed committee metrics."""
    _validate_required_columns(
        seed_metrics,
        (
            "dataset",
            "strategy",
            "seed",
            *COMMITTEE_METRIC_COLUMNS,
        ),
        table_name="committee seed metrics",
    )

    if seed_metrics.empty:
        raise ValueError("Committee seed metrics are empty.")

    recorded_datasets = {str(value) for value in seed_metrics["dataset"].unique()}
    expected_dataset = str(metadata["dataset_name"])
    if recorded_datasets != {expected_dataset}:
        raise ValueError(
            "Committee seed metrics contain unexpected dataset values: "
            f"{sorted(recorded_datasets)!r}.",
        )

    strategies = tuple(str(value) for value in seed_metrics["strategy"].unique())
    if set(strategies) != set(COMMITTEE_STRATEGIES):
        raise ValueError(
            "Committee seed metrics do not contain exactly the four expected "
            f"strategies: {strategies!r}.",
        )

    seed_values = pd.to_numeric(
        seed_metrics["seed"],
        errors="coerce",
    ).to_numpy(dtype=float)
    if not np.all(np.isfinite(seed_values)) or not np.all(
        seed_values == np.floor(seed_values),
    ):
        raise ValueError("Committee seed metrics contain invalid seed values.")

    seed_metrics = seed_metrics.copy()
    normalized_seeds = seed_values.astype(np.int64)
    seed_metrics["seed"] = normalized_seeds

    if seed_metrics[["strategy", "seed"]].duplicated().any():
        raise ValueError(
            "Committee seed metrics contain duplicate strategy/seed rows.",
        )

    seeds_by_strategy = {
        strategy: tuple(
            sorted(
                int(value)
                for value in seed_metrics.loc[
                    seed_metrics["strategy"].astype(str) == strategy,
                    "seed",
                ].unique()
            )
        )
        for strategy in COMMITTEE_STRATEGIES
    }

    metadata_seeds_value = metadata.get("seeds")
    if not isinstance(metadata_seeds_value, (list, tuple)):
        raise TypeError("Committee metadata does not contain a valid seed sequence.")

    expected_seeds = tuple(sorted(int(value) for value in metadata_seeds_value))

    for strategy, strategy_seeds in seeds_by_strategy.items():
        if strategy_seeds != expected_seeds:
            raise ValueError(
                f"Committee strategy {strategy!r} contains seeds "
                f"{strategy_seeds!r}; expected {expected_seeds!r}.",
            )

    _validate_probability_free_metric_range(
        seed_metrics,
        table_name="committee seed metrics",
    )

    return expected_seeds


def _validate_summary(
    summary: pd.DataFrame,
    *,
    seed_metrics: pd.DataFrame,
) -> None:
    """Validate persisted summary means/stds against seed metrics."""
    _validate_required_columns(
        summary,
        (
            "strategy",
            "seed_count",
            *COMMITTEE_METRIC_COLUMNS,
        ),
        table_name="committee summary",
    )

    if summary.empty:
        raise ValueError("Committee summary is empty.")

    summary_strategies = tuple(str(value) for value in summary["strategy"])
    if len(summary_strategies) != len(set(summary_strategies)):
        raise ValueError("Committee summary contains duplicate strategies.")
    if set(summary_strategies) != set(COMMITTEE_STRATEGIES):
        raise ValueError(
            "Committee summary does not contain exactly the expected strategies.",
        )

    seed_counts = pd.to_numeric(
        summary["seed_count"],
        errors="coerce",
    ).to_numpy(dtype=float)
    if not np.all(np.isfinite(seed_counts)) or not np.all(
        seed_counts == np.floor(seed_counts),
    ):
        raise ValueError("Committee summary contains invalid seed counts.")

    seed_metrics_copy = seed_metrics.copy()
    seed_metrics_copy["seed"] = pd.to_numeric(
        seed_metrics_copy["seed"],
        errors="raise",
    ).astype(int)

    for row_position, strategy_value in enumerate(summary_strategies):
        strategy_frame = seed_metrics_copy.loc[
            seed_metrics_copy["strategy"].astype(str) == strategy_value
        ]
        if strategy_frame.empty:
            raise ValueError(
                f"Committee summary strategy {strategy_value!r} has no "
                "corresponding seed metrics.",
            )

        if int(seed_counts[row_position]) != len(strategy_frame):
            raise ValueError(
                f"Committee summary seed_count for {strategy_value!r} does not "
                "match the persisted seed metrics.",
            )

        for metric in COMMITTEE_METRIC_COLUMNS:
            values = strategy_frame[metric].to_numpy(dtype=float)
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            stored_mean, stored_std = _parse_summary_value(
                summary.iloc[row_position][metric],
                context=f"strategy={strategy_value}, metric={metric}",
            )
            if not np.isclose(
                mean,
                stored_mean,
                atol=SUMMARY_COMPARISON_ATOL,
                rtol=SUMMARY_COMPARISON_RTOL,
            ):
                raise ValueError(
                    f"Committee summary mean for {strategy_value!r}/{metric!r} "
                    "does not match seed metrics.",
                )
            if not np.isclose(
                std,
                stored_std,
                atol=SUMMARY_COMPARISON_ATOL,
                rtol=SUMMARY_COMPARISON_RTOL,
            ):
                raise ValueError(
                    f"Committee summary standard deviation for "
                    f"{strategy_value!r}/{metric!r} does not match seed metrics.",
                )


# ----------------------------------------
# Loading
# ----------------------------------------


def load_committee_experiment_artifacts(
    *,
    dataset_name: str,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> CommitteeExperimentArtifacts:
    """Load and validate one dataset-level committee artifact set."""
    canonical_dataset = _normalize_dataset_name(dataset_name)
    dataset_directory = (
        artifacts_directory.expanduser().resolve() / canonical_dataset.lower()
    )
    committee_directory = dataset_directory / COMMITTEE_DIRECTORY_NAME

    metadata = load_committee_metadata(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    _validate_committee_metadata(
        metadata,
        dataset_name=canonical_dataset,
    )

    weights = load_committee_weights(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    _validate_weights(
        weights,
        metadata=metadata,
    )

    seed_metrics = load_committee_seed_metrics(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    expected_seeds = _validate_seed_metrics(
        seed_metrics,
        metadata=metadata,
    )

    summary = load_committee_summary(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    _validate_summary(
        summary,
        seed_metrics=seed_metrics,
    )

    metadata_seeds_value = metadata.get("seeds")
    if not isinstance(metadata_seeds_value, (list, tuple)):
        raise TypeError("Committee metadata does not contain a valid seed sequence.")

    metadata_seeds = tuple(sorted(int(value) for value in metadata_seeds_value))
    if metadata_seeds != expected_seeds:
        raise ValueError(
            "Committee metadata seeds do not match persisted seed metrics: "
            f"{metadata_seeds!r} != {expected_seeds!r}.",
        )

    expected_paths = (
        committee_directory / COMMITTEE_METADATA_FILE_NAME,
        committee_directory / COMMITTEE_WEIGHTS_FILE_NAME,
        committee_directory / COMMITTEE_SEED_METRICS_FILE_NAME,
        committee_directory / COMMITTEE_SUMMARY_FILE_NAME,
    )
    missing_paths = [path for path in expected_paths if not path.is_file()]
    if missing_paths:
        raise FileNotFoundError(
            "Committee artifact set is incomplete; missing: "
            f"{[str(path) for path in missing_paths]!r}."
        )

    return CommitteeExperimentArtifacts(
        dataset_name=canonical_dataset,
        directory=committee_directory,
        metadata=metadata,
        weights=weights,
        seed_metrics=seed_metrics,
        summary=summary,
    )


def load_all_committee_experiment_artifacts(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> tuple[CommitteeExperimentArtifacts, ...]:
    """Load and validate committee artifacts for all configured datasets."""
    return tuple(
        load_committee_experiment_artifacts(
            dataset_name=dataset_name,
            artifacts_directory=artifacts_directory,
        )
        for dataset_name in COMMITTEE_DATASET_ORDER
    )


# ----------------------------------------
# Table preparation
# ----------------------------------------


def _prepare_configuration_table(
    artifacts: CommitteeExperimentArtifacts,
) -> pd.DataFrame:
    """Prepare validation-derived committee weights for notebook display."""
    selected_configuration_ids = artifacts.metadata.get(
        "selected_configuration_ids",
    )
    if not isinstance(selected_configuration_ids, Mapping):
        raise TypeError(
            "Committee metadata does not contain selected configuration IDs.",
        )

    weights = artifacts.weights.copy()
    weights["classifier"] = weights["classifier"].astype(str)
    weights["validation_macro_f1"] = pd.to_numeric(
        weights["validation_macro_f1"],
        errors="raise",
    ).astype(float)
    weights["weight"] = pd.to_numeric(
        weights["weight"],
        errors="raise",
    ).astype(float)

    rows: list[dict[str, object]] = []
    for classifier in COMPONENT_CLASSIFIERS:
        row_frame = weights.loc[weights["classifier"] == classifier]
        if len(row_frame) != 1:
            raise ValueError(
                f"Expected exactly one weight row for classifier {classifier!r}.",
            )

        configuration_id = selected_configuration_ids.get(classifier)
        if not isinstance(configuration_id, str):
            raise TypeError(
                f"Selected configuration ID for {classifier!r} is invalid.",
            )

        row = row_frame.iloc[0]
        rows.append(
            {
                "Classifier": _classifier_display_name(classifier),
                "Configuration ID": configuration_id,
                "Validation Macro F1": _format_display_metric(
                    _to_python_float(row["validation_macro_f1"]),
                ),
                "Committee weight": _format_display_metric(
                    _to_python_float(row["weight"]),
                ),
            },
        )

    return pd.DataFrame(rows)


def _aggregate_seed_metrics(
    frame: pd.DataFrame,
    *,
    group_column: str,
    group_order: Sequence[str],
) -> pd.DataFrame:
    """Aggregate seed metrics by one categorical group."""
    rows: list[dict[str, object]] = []

    for group_value in group_order:
        group_frame = frame.loc[frame[group_column].astype(str) == group_value].copy()
        if group_frame.empty:
            raise ValueError(
                f"No metric rows were found for {group_column}={group_value!r}.",
            )

        seed_values = pd.to_numeric(
            group_frame["seed"],
            errors="raise",
        ).astype(int)
        if seed_values.duplicated().any():
            raise ValueError(
                f"Duplicate seeds were found for {group_column}={group_value!r}.",
            )

        row: dict[str, object] = {
            group_column: group_value,
            "Seeds": len(group_frame),
        }

        for metric in COMMITTEE_METRIC_COLUMNS:
            values = group_frame[metric].to_numpy(dtype=float)
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[metric] = _format_comparison_value(mean, std)

        rows.append(row)

    return pd.DataFrame(rows)


def _prepare_performance_table(
    artifacts: CommitteeExperimentArtifacts,
) -> pd.DataFrame:
    """Prepare committee-only mean ± std performance results."""
    aggregated = _aggregate_seed_metrics(
        artifacts.seed_metrics,
        group_column="strategy",
        group_order=COMMITTEE_STRATEGIES,
    )

    rows: list[dict[str, object]] = []
    for _, row in aggregated.iterrows():
        record: dict[str, object] = {
            "Strategy": _strategy_display_name(str(row["strategy"])),
            "Seeds": _to_python_int(row["Seeds"]),
        }
        for metric in COMMITTEE_METRIC_COLUMNS:
            record[METRIC_DISPLAY_NAMES[metric]] = str(row[metric])
        rows.append(record)

    return pd.DataFrame(rows)


def _aggregate_individual_classifier_metrics(
    *,
    artifacts_directory: Path,
    dataset_name: str,
    expected_seeds: Sequence[int],
) -> pd.DataFrame:
    """Aggregate the already-persisted component test metrics."""
    rows: list[dict[str, object]] = []

    for classifier in CLASSIFIER_ORDER:
        artifacts = reporting_test.load_test_experiment_artifacts(
            dataset_name=dataset_name,
            classifier_name=classifier,
            artifacts_directory=artifacts_directory,
        )

        frame = artifacts.seed_metrics.copy()
        frame["seed"] = pd.to_numeric(
            frame["seed"],
            errors="raise",
        ).astype(int)

        actual_seeds = tuple(sorted(int(value) for value in frame["seed"].unique()))
        normalized_expected_seeds = tuple(sorted(int(seed) for seed in expected_seeds))
        if actual_seeds != normalized_expected_seeds:
            raise ValueError(
                f"Individual classifier {classifier!r} uses seeds {actual_seeds!r}; "
                f"committee uses {normalized_expected_seeds!r}.",
            )

        if frame["seed"].duplicated().any():
            raise ValueError(
                f"Individual classifier {classifier!r} contains duplicate seed rows.",
            )

        record: dict[str, object] = {
            "Method": _classifier_display_name(classifier),
            "Type": COMPARISON_KIND_INDIVIDUAL,
            "Seeds": len(frame),
        }

        for metric in TEST_METRIC_COLUMNS:
            values = pd.to_numeric(
                frame[metric],
                errors="raise",
            ).to_numpy(dtype=float)
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            record[f"{metric}_mean"] = mean
            record[f"{metric}_std"] = std
            record[METRIC_DISPLAY_NAMES[metric]] = _format_comparison_value(mean, std)

        rows.append(record)

    return pd.DataFrame(rows)


def _prepare_comparison_table(
    artifacts: CommitteeExperimentArtifacts,
    *,
    artifacts_directory: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prepare formatted and numeric individual-vs-committee tables."""
    metadata_seeds = artifacts.metadata.get("seeds")
    if not isinstance(metadata_seeds, (list, tuple)):
        raise TypeError("Committee metadata does not contain a valid seed sequence.")
    seeds = tuple(int(seed) for seed in metadata_seeds)

    individual = _aggregate_individual_classifier_metrics(
        artifacts_directory=artifacts_directory,
        dataset_name=artifacts.dataset_name,
        expected_seeds=seeds,
    )

    committee_aggregated = _aggregate_seed_metrics(
        artifacts.seed_metrics,
        group_column="strategy",
        group_order=COMMITTEE_STRATEGIES,
    )

    committee_rows: list[dict[str, object]] = []
    for _, row in committee_aggregated.iterrows():
        record: dict[str, object] = {
            "Method": _strategy_display_name(str(row["strategy"])),
            "Type": COMPARISON_KIND_COMMITTEE,
            "Seeds": _to_python_int(row["Seeds"]),
        }
        for metric in COMMITTEE_METRIC_COLUMNS:
            record[f"{metric}_mean"] = _to_python_float(row[f"{metric}_mean"])
            record[f"{metric}_std"] = _to_python_float(row[f"{metric}_std"])
            record[METRIC_DISPLAY_NAMES[metric]] = str(row[metric])
        committee_rows.append(record)

    committee = pd.DataFrame(committee_rows)

    combined = pd.concat(
        [individual, committee],
        ignore_index=True,
    )

    method_order = [
        *(_classifier_display_name(name) for name in CLASSIFIER_ORDER),
        *(_strategy_display_name(name) for name in COMMITTEE_STRATEGIES),
    ]
    combined["_method_order"] = pd.Categorical(
        combined["Method"],
        categories=method_order,
        ordered=True,
    )
    combined = combined.sort_values(
        "_method_order",
        ignore_index=True,
    ).drop(columns="_method_order")

    display_columns = [
        "Method",
        "Type",
        "Seeds",
        *METRIC_DISPLAY_NAMES.values(),
    ]
    display_table = combined.loc[:, display_columns].copy()

    return display_table, combined


def compile_committee_statistics(
    *,
    artifacts: CommitteeExperimentArtifacts,
    include_individual_comparison: bool = True,
    artifacts_directory: Path | None = None,
) -> CommitteeStatistics:
    """Prepare one committee experiment for notebook display.

    ``artifacts`` must have been loaded by
    :func:`load_committee_experiment_artifacts`. The optional artifact root is
    used only when the individual-model comparison is requested, because the
    comparison reuses the persisted component test-evaluation artifacts.
    """
    resolved_artifacts_directory = (
        artifacts_directory.expanduser().resolve()
        if artifacts_directory is not None
        else artifacts.directory.parent.parent
    )

    configuration_table = _prepare_configuration_table(artifacts)
    performance_table = _prepare_performance_table(artifacts)

    if include_individual_comparison:
        comparison_table, _ = _prepare_comparison_table(
            artifacts,
            artifacts_directory=resolved_artifacts_directory,
        )
    else:
        committee_aggregated = _aggregate_seed_metrics(
            artifacts.seed_metrics,
            group_column="strategy",
            group_order=COMMITTEE_STRATEGIES,
        )
        rows: list[dict[str, object]] = []
        for _, row in committee_aggregated.iterrows():
            record: dict[str, object] = {
                "Method": _strategy_display_name(str(row["strategy"])),
                "Type": COMPARISON_KIND_COMMITTEE,
                "Seeds": _to_python_int(row["Seeds"]),
            }
            for metric in COMMITTEE_METRIC_COLUMNS:
                record[METRIC_DISPLAY_NAMES[metric]] = str(row[metric])
            rows.append(record)
        comparison_table = pd.DataFrame(rows)

    return CommitteeStatistics(
        configuration_table=configuration_table,
        performance_table=performance_table,
        comparison_table=comparison_table,
    )


def compile_all_committee_statistics(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
    include_individual_comparison: bool = True,
) -> tuple[CommitteeStatistics, ...]:
    """Compile committee statistics for every configured dataset."""
    return tuple(
        compile_committee_statistics(
            artifacts=artifacts,
            include_individual_comparison=include_individual_comparison,
            artifacts_directory=artifacts_directory,
        )
        for artifacts in load_all_committee_experiment_artifacts(
            artifacts_directory=artifacts_directory,
        )
    )


def compile_all_committee_comparison_table(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> pd.DataFrame:
    """Build one combined individual-vs-committee table for all datasets."""
    rows: list[pd.DataFrame] = []

    for artifacts in load_all_committee_experiment_artifacts(
        artifacts_directory=artifacts_directory,
    ):
        statistics = compile_committee_statistics(
            artifacts=artifacts,
            artifacts_directory=artifacts_directory,
            include_individual_comparison=True,
        )
        table = statistics.comparison_table.copy()
        table.insert(0, "Dataset", artifacts.dataset_name)
        rows.append(table)

    if not rows:
        return pd.DataFrame()

    return pd.concat(
        rows,
        ignore_index=True,
    )


# ----------------------------------------
# Figures
# ----------------------------------------


def plot_committee_primary_metric(
    comparison_table: pd.DataFrame,
    *,
    metric: str = PRIMARY_COMMITTEE_METRIC,
    title: str | None = None,
) -> Figure:
    """Plot an individual-model versus committee metric comparison.

    ``comparison_table`` is the formatted table returned in
    :class:`CommitteeStatistics`. Mean and standard deviation are recovered
    from the formatted ``mean ± std`` cells solely for plotting.
    """
    if metric not in COMMITTEE_METRIC_COLUMNS:
        raise ValueError(
            f"Unknown metric {metric!r}. Available metrics: "
            f"{COMMITTEE_METRIC_COLUMNS!r}.",
        )

    required_columns = (
        "Method",
        "Type",
        "Seeds",
        METRIC_DISPLAY_NAMES[metric],
    )
    _validate_required_columns(
        comparison_table,
        required_columns,
        table_name="committee comparison table",
    )

    frame = comparison_table.copy()
    if frame.empty:
        raise ValueError("Committee comparison table is empty.")

    expected_methods = {
        *(_classifier_display_name(name) for name in CLASSIFIER_ORDER),
        *(_strategy_display_name(name) for name in COMMITTEE_STRATEGIES),
    }
    actual_methods = set(frame["Method"].astype(str))
    if actual_methods != expected_methods:
        raise ValueError(
            "Committee primary-metric comparison must contain exactly the "
            f"three classifiers and four committee strategies: {sorted(actual_methods)!r}.",
        )

    method_order = [
        *(_classifier_display_name(name) for name in CLASSIFIER_ORDER),
        *(_strategy_display_name(name) for name in COMMITTEE_STRATEGIES),
    ]
    frame["_method_order"] = pd.Categorical(
        frame["Method"].astype(str),
        categories=method_order,
        ordered=True,
    )
    frame = frame.sort_values(
        "_method_order",
        ignore_index=True,
    )

    means: list[float] = []
    errors: list[float] = []
    for method, value in zip(
        frame["Method"].astype(str),
        frame[METRIC_DISPLAY_NAMES[metric]],
        strict=True,
    ):
        mean, std = _parse_summary_value(
            value,
            context=f"method={method}, metric={metric}",
        )
        if not 0.0 <= mean <= 1.0:
            raise ValueError(
                f"Mean value for method {method!r}, metric {metric!r}, "
                "is outside [0, 1].",
            )
        if std < 0.0 or not np.isfinite(std):
            raise ValueError(
                f"Standard deviation for method {method!r}, metric {metric!r}, "
                "is invalid.",
            )
        means.append(mean)
        errors.append(std)

    figure, axes = plt.subplots(figsize=(11.0, 6.5))

    positions = np.arange(len(frame), dtype=float)
    colors = get_discrete_colors(len(frame))

    for position, (method, kind, mean, std, color) in enumerate(
        zip(
            frame["Method"].astype(str),
            frame["Type"].astype(str),
            means,
            errors,
            colors,
            strict=True,
        ),
    ):
        marker = "o" if kind == COMPARISON_KIND_INDIVIDUAL else "s"
        axes.errorbar(
            positions[position],
            mean,
            yerr=std,
            fmt=marker,
            color=color,
            capsize=4,
            markersize=7,
            label=method,
        )

    axes.set_xticks(
        positions,
        frame["Method"].astype(str).tolist(),
        rotation=30,
        ha="right",
    )
    axes.set_xlabel("Model or committee")
    axes.set_ylabel(METRIC_DISPLAY_NAMES[metric])
    axes.set_title(
        title
        or f"Individual models versus committees — {METRIC_DISPLAY_NAMES[metric]}",
    )
    _configure_metric_y_axis(
        axes,
        values=means,
        errors=errors,
    )

    # A single legend is useful here because color identifies the method and
    # marker shape identifies whether the method is an individual classifier
    # or a committee.
    handles, labels = axes.get_legend_handles_labels()
    if handles:
        axes.legend(
            handles,
            labels,
            ncol=2,
        )

    figure.tight_layout()
    return figure


# ----------------------------------------
# Display helpers
# ----------------------------------------


def _display_section(
    *,
    title: str,
    table: pd.DataFrame,
) -> None:
    """Display one report section with a consistent heading."""
    display(HTML(f"<h3>{title}</h3>"))
    display(table)


def display_committee_statistics(
    statistics: CommitteeStatistics,
    *,
    show_configuration: bool = True,
    show_performance: bool = True,
    show_comparison: bool = True,
) -> None:
    """Display notebook-ready committee result tables."""
    if show_configuration:
        _display_section(
            title="Committee configuration and validation-derived weights",
            table=statistics.configuration_table,
        )

    if show_performance:
        _display_section(
            title="Committee test performance",
            table=statistics.performance_table,
        )

    if show_comparison:
        _display_section(
            title="Individual classifiers versus committee strategies",
            table=statistics.comparison_table,
        )


def display_all_committee_statistics(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> None:
    """Display committee reporting tables for all configured datasets."""
    artifacts = load_all_committee_experiment_artifacts(
        artifacts_directory=artifacts_directory,
    )

    for experiment_artifacts in artifacts:
        statistics = compile_committee_statistics(
            artifacts=experiment_artifacts,
            artifacts_directory=artifacts_directory,
            include_individual_comparison=True,
        )
        display(HTML(f"<h2>{experiment_artifacts.dataset_name} — Committees</h2>"))
        display_committee_statistics(statistics)


__all__ = [
    "COMMITTEE_DATASET_ORDER",
    "COMMITTEE_STRATEGY_DISPLAY_NAMES",
    "COMMITTEE_STRATEGY_TYPE_DISPLAY_NAMES",
    "DEFAULT_ARTIFACTS_DIRECTORY",
    "METRIC_DISPLAY_NAMES",
    "PRIMARY_COMMITTEE_METRIC",
    "CommitteeExperimentArtifacts",
    "CommitteeStatistics",
    "compile_all_committee_comparison_table",
    "compile_all_committee_statistics",
    "compile_committee_statistics",
    "display_all_committee_statistics",
    "display_committee_statistics",
    "load_all_committee_experiment_artifacts",
    "load_committee_experiment_artifacts",
    "plot_committee_primary_metric",
]
