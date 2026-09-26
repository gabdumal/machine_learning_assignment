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
    committee/diversity_seed_metrics.csv
    committee/diversity_summary.csv
    committee/correction_seed_metrics.csv
    committee/correction_summary.csv

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
from eda.palette import CONTINUOUS_PALETTE, get_discrete_colors
from pipeline.committee import (
    COMMITTEE_ARTIFACT_SCHEMA_VERSION,
    COMMITTEE_CLASSIFIER_PAIRS,
    COMMITTEE_CORRECTION_SEED_METRICS_FILE_NAME,
    COMMITTEE_CORRECTION_SUMMARY_FILE_NAME,
    COMMITTEE_DIRECTORY_NAME,
    COMMITTEE_DIVERSITY_SEED_METRICS_FILE_NAME,
    COMMITTEE_DIVERSITY_SUMMARY_FILE_NAME,
    COMMITTEE_METADATA_FILE_NAME,
    COMMITTEE_SEED_METRICS_FILE_NAME,
    COMMITTEE_STRATEGIES,
    COMMITTEE_SUMMARY_FILE_NAME,
    COMMITTEE_WEIGHTS_FILE_NAME,
    COMPONENT_CLASSIFIERS,
    CORRECTION_COUNT_COLUMNS,
    CORRECTION_RATE_COLUMNS,
    DIVERSITY_METRIC_COLUMNS,
    load_committee_correction_seed_metrics,
    load_committee_correction_summary,
    load_committee_diversity_seed_metrics,
    load_committee_diversity_summary,
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
    diversity_seed_metrics: pd.DataFrame
    diversity_summary: pd.DataFrame
    correction_seed_metrics: pd.DataFrame
    correction_summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class CommitteeStatistics:
    """Notebook-ready committee reporting tables."""

    configuration_table: pd.DataFrame
    performance_table: pd.DataFrame
    comparison_table: pd.DataFrame
    diversity_table: pd.DataFrame
    correction_table: pd.DataFrame


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
    if metadata.get("schema_version") != COMMITTEE_ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            "Committee metadata uses an unsupported artifact schema version: "
            f"{metadata.get('schema_version')!r} != "
            f"{COMMITTEE_ARTIFACT_SCHEMA_VERSION!r}."
        )

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


def _validate_seed_sequence(
    frame: pd.DataFrame,
    *,
    expected_seeds: Sequence[int],
    key_columns: Sequence[str],
    table_name: str,
) -> pd.DataFrame:
    """Validate and normalize persisted seed identifiers."""
    normalized = frame.copy()
    seed_values = pd.to_numeric(
        normalized["seed"],
        errors="coerce",
    ).to_numpy(dtype=float)
    if not np.all(np.isfinite(seed_values)) or not np.all(
        seed_values == np.floor(seed_values),
    ):
        raise ValueError(f"{table_name} contains invalid seed values.")

    normalized["seed"] = seed_values.astype(np.int64)
    expected = tuple(sorted(int(seed) for seed in expected_seeds))
    actual = tuple(sorted(int(seed) for seed in normalized["seed"].unique()))
    if actual != expected:
        raise ValueError(f"{table_name} uses seeds {actual!r}; expected {expected!r}.")

    if normalized[list(key_columns)].duplicated().any():
        raise ValueError(
            f"{table_name} contains duplicate rows for keys {tuple(key_columns)!r}."
        )

    return normalized


def _validate_rate_metrics(
    frame: pd.DataFrame,
    *,
    metric_columns: Sequence[str],
    table_name: str,
) -> None:
    """Validate finite rate metrics in the closed interval [0, 1]."""
    for metric in metric_columns:
        values = _validate_numeric_column(
            frame,
            metric,
            table_name=table_name,
        )
        if np.any(values < 0.0) or np.any(values > 1.0):
            raise ValueError(
                f"{table_name} metric {metric!r} contains values outside [0, 1]."
            )


def _validate_non_negative_count_metrics(
    frame: pd.DataFrame,
    *,
    metric_columns: Sequence[str],
    test_row_counts: np.ndarray,
    table_name: str,
) -> None:
    """Validate persisted non-negative integer counts against test size."""
    for metric in metric_columns:
        values = _validate_numeric_column(
            frame,
            metric,
            table_name=table_name,
        )
        if not np.all(values == np.floor(values)):
            raise ValueError(
                f"{table_name} metric {metric!r} must contain integer counts."
            )
        if np.any(values < 0.0) or np.any(values > test_row_counts):
            raise ValueError(
                f"{table_name} metric {metric!r} contains counts outside the "
                "valid test-row range."
            )


def _validate_diversity_seed_metrics(
    diversity_seed_metrics: pd.DataFrame,
    *,
    metadata: Mapping[str, object],
) -> None:
    """Validate persisted per-seed pairwise diversity statistics."""
    _validate_required_columns(
        diversity_seed_metrics,
        (
            "dataset",
            "seed",
            "test_row_count",
            "classifier_a",
            "classifier_b",
            *DIVERSITY_METRIC_COLUMNS,
        ),
        table_name="committee diversity seed metrics",
    )
    if diversity_seed_metrics.empty:
        raise ValueError("Committee diversity seed metrics are empty.")

    expected_dataset = str(metadata["dataset_name"])
    recorded_datasets = {
        str(value) for value in diversity_seed_metrics["dataset"].unique()
    }
    if recorded_datasets != {expected_dataset}:
        raise ValueError(
            "Committee diversity seed metrics contain unexpected dataset values: "
            f"{sorted(recorded_datasets)!r}."
        )

    classifier_pairs = tuple(
        (
            str(row["classifier_a"]),
            str(row["classifier_b"]),
        )
        for _, row in diversity_seed_metrics.iterrows()
    )
    expected_pairs = tuple(
        (str(classifier_a), str(classifier_b))
        for classifier_a, classifier_b in COMMITTEE_CLASSIFIER_PAIRS
    )
    if set(classifier_pairs) != set(expected_pairs):
        raise ValueError(
            "Committee diversity seed metrics do not contain exactly the expected "
            f"classifier pairs: {sorted(set(classifier_pairs))!r}."
        )

    test_row_counts = _validate_numeric_column(
        diversity_seed_metrics,
        "test_row_count",
        table_name="committee diversity seed metrics",
    )
    if not np.all(test_row_counts == np.floor(test_row_counts)) or np.any(
        test_row_counts <= 0.0,
    ):
        raise ValueError(
            "Committee diversity test_row_count values must be positive integers."
        )

    metadata_seeds = metadata.get("seeds")
    if not isinstance(metadata_seeds, (list, tuple)):
        raise TypeError("Committee metadata does not contain a valid seed sequence.")

    normalized = _validate_seed_sequence(
        diversity_seed_metrics,
        expected_seeds=tuple(int(value) for value in metadata_seeds),
        key_columns=("classifier_a", "classifier_b", "seed"),
        table_name="Committee diversity seed metrics",
    )

    pair_counts = normalized.groupby(
        ["classifier_a", "classifier_b"],
        sort=False,
    )["seed"].nunique()
    expected_seed_count = len(tuple(int(value) for value in metadata_seeds))
    if not np.all(pair_counts.to_numpy(dtype=int) == expected_seed_count):
        raise ValueError(
            "Committee diversity seed metrics do not contain every expected "
            "seed for each classifier pair."
        )

    _validate_rate_metrics(
        normalized,
        metric_columns=DIVERSITY_METRIC_COLUMNS,
        table_name="Committee diversity seed metrics",
    )


def _validate_mean_std_summary(
    summary: pd.DataFrame,
    *,
    group_columns: Sequence[str],
    group_values: Sequence[tuple[str, ...]],
    metric_columns: Sequence[str],
    seed_metrics: pd.DataFrame,
    table_name: str,
    context_column_names: Sequence[str],
) -> None:
    """Validate a persisted summary of per-seed statistics."""
    _validate_required_columns(
        summary,
        (*group_columns, "seed_count", *metric_columns),
        table_name=table_name,
    )
    if summary.empty:
        raise ValueError(f"{table_name} is empty.")

    expected_groups = set(group_values)
    actual_groups = {
        tuple(str(row[column]) for column in group_columns)
        for _, row in summary.iterrows()
    }
    if actual_groups != expected_groups:
        raise ValueError(
            f"{table_name} does not contain exactly the expected groups: "
            f"{sorted(actual_groups)!r}."
        )

    if len(summary) != len(expected_groups):
        raise ValueError(f"{table_name} contains duplicate group rows.")

    seed_counts = _validate_numeric_column(
        summary,
        "seed_count",
        table_name=table_name,
    )
    if not np.all(seed_counts == np.floor(seed_counts)) or np.any(seed_counts <= 0.0):
        raise ValueError(f"{table_name} contains invalid seed counts.")

    for group in group_values:
        summary_mask = np.ones(len(summary), dtype=bool)
        seed_mask = np.ones(len(seed_metrics), dtype=bool)
        for column, value in zip(group_columns, group, strict=True):
            summary_mask &= summary[column].astype(str).to_numpy() == value
            seed_mask &= seed_metrics[column].astype(str).to_numpy() == value

        summary_positions = np.flatnonzero(summary_mask)
        if len(summary_positions) != 1:
            raise ValueError(
                f"{table_name} does not contain exactly one row for group {group!r}."
            )
        summary_position = int(summary_positions[0])

        group_frame = seed_metrics.loc[seed_mask]
        if group_frame.empty:
            raise ValueError(
                f"{table_name} group {group!r} has no corresponding seed metrics."
            )

        if int(seed_counts[summary_position]) != len(group_frame):
            raise ValueError(
                f"{table_name} seed_count for group {group!r} does not match "
                "the persisted seed metrics."
            )

        for metric in metric_columns:
            values = group_frame[metric].to_numpy(dtype=float)
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            stored_mean, stored_std = _parse_summary_value(
                summary.iloc[summary_position][metric],
                context=(f"{context_column_names!r}={group!r}, metric={metric!r}"),
            )
            if not np.isclose(
                mean,
                stored_mean,
                atol=SUMMARY_COMPARISON_ATOL,
                rtol=SUMMARY_COMPARISON_RTOL,
            ) or not np.isclose(
                std,
                stored_std,
                atol=SUMMARY_COMPARISON_ATOL,
                rtol=SUMMARY_COMPARISON_RTOL,
            ):
                raise ValueError(
                    f"{table_name} summary for group {group!r}/{metric!r} "
                    "does not match the persisted seed metrics."
                )


def _validate_diversity_summary(
    diversity_summary: pd.DataFrame,
    *,
    diversity_seed_metrics: pd.DataFrame,
) -> None:
    """Validate persisted pairwise diversity summaries."""
    classifier_pairs = tuple(
        (classifier_a, classifier_b)
        for classifier_a, classifier_b in COMMITTEE_CLASSIFIER_PAIRS
    )
    _validate_mean_std_summary(
        diversity_summary,
        group_columns=("classifier_a", "classifier_b"),
        group_values=classifier_pairs,
        metric_columns=DIVERSITY_METRIC_COLUMNS,
        seed_metrics=diversity_seed_metrics,
        table_name="committee diversity summary",
        context_column_names=("classifier_a", "classifier_b"),
    )
    means = diversity_summary.copy()
    for metric in DIVERSITY_METRIC_COLUMNS:
        means[metric] = means[metric].map(
            lambda value, metric=metric: _parse_summary_value(
                value,
                context=f"committee diversity summary/{metric}",
            )[0]
        )
    _validate_rate_metrics(
        means,
        metric_columns=DIVERSITY_METRIC_COLUMNS,
        table_name="committee diversity summary means",
    )


def _validate_correction_seed_metrics(
    correction_seed_metrics: pd.DataFrame,
    *,
    metadata: Mapping[str, object],
) -> None:
    """Validate persisted per-seed committee correction statistics."""
    _validate_required_columns(
        correction_seed_metrics,
        (
            "dataset",
            "strategy",
            "seed",
            "test_row_count",
            *CORRECTION_COUNT_COLUMNS,
            *CORRECTION_RATE_COLUMNS,
        ),
        table_name="committee correction seed metrics",
    )
    if correction_seed_metrics.empty:
        raise ValueError("Committee correction seed metrics are empty.")

    expected_dataset = str(metadata["dataset_name"])
    recorded_datasets = {
        str(value) for value in correction_seed_metrics["dataset"].unique()
    }
    if recorded_datasets != {expected_dataset}:
        raise ValueError(
            "Committee correction seed metrics contain unexpected dataset values: "
            f"{sorted(recorded_datasets)!r}."
        )

    metadata_seeds = metadata.get("seeds")
    if not isinstance(metadata_seeds, (list, tuple)):
        raise TypeError("Committee metadata does not contain a valid seed sequence.")

    normalized = _validate_seed_sequence(
        correction_seed_metrics,
        expected_seeds=tuple(int(value) for value in metadata_seeds),
        key_columns=("strategy", "seed"),
        table_name="Committee correction seed metrics",
    )

    strategies = {str(value) for value in normalized["strategy"].unique()}
    if strategies != set(COMMITTEE_STRATEGIES):
        raise ValueError(
            "Committee correction seed metrics do not contain exactly the "
            f"expected strategies: {sorted(strategies)!r}."
        )

    expected_seeds = tuple(sorted(int(value) for value in metadata_seeds))
    for strategy in COMMITTEE_STRATEGIES:
        strategy_seeds = tuple(
            sorted(
                int(value)
                for value in normalized.loc[
                    normalized["strategy"].astype(str) == strategy,
                    "seed",
                ].unique()
            )
        )
        if strategy_seeds != expected_seeds:
            raise ValueError(
                f"Committee correction strategy {strategy!r} uses seeds "
                f"{strategy_seeds!r}; expected {expected_seeds!r}."
            )

    test_row_counts = _validate_numeric_column(
        normalized,
        "test_row_count",
        table_name="committee correction seed metrics",
    )
    if not np.all(test_row_counts == np.floor(test_row_counts)) or np.any(
        test_row_counts <= 0.0,
    ):
        raise ValueError(
            "Committee correction test_row_count values must be positive integers."
        )

    _validate_non_negative_count_metrics(
        normalized,
        metric_columns=CORRECTION_COUNT_COLUMNS,
        test_row_counts=test_row_counts,
        table_name="Committee correction seed metrics",
    )
    _validate_rate_metrics(
        normalized,
        metric_columns=CORRECTION_RATE_COLUMNS,
        table_name="Committee correction seed metrics",
    )


def _validate_correction_summary(
    correction_summary: pd.DataFrame,
    *,
    correction_seed_metrics: pd.DataFrame,
) -> None:
    """Validate persisted committee correction summaries."""
    _validate_mean_std_summary(
        correction_summary,
        group_columns=("strategy",),
        group_values=tuple((strategy,) for strategy in COMMITTEE_STRATEGIES),
        metric_columns=(*CORRECTION_COUNT_COLUMNS, *CORRECTION_RATE_COLUMNS),
        seed_metrics=correction_seed_metrics,
        table_name="committee correction summary",
        context_column_names=("strategy",),
    )

    means = correction_summary.copy()
    for metric in CORRECTION_RATE_COLUMNS:
        means[metric] = [
            _parse_summary_value(
                value,
                context=f"committee correction summary/{metric}",
            )[0]
            for value in means[metric]
        ]
    _validate_rate_metrics(
        means,
        metric_columns=CORRECTION_RATE_COLUMNS,
        table_name="committee correction summary means",
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

    diversity_seed_metrics = load_committee_diversity_seed_metrics(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    _validate_diversity_seed_metrics(
        diversity_seed_metrics,
        metadata=metadata,
    )

    diversity_summary = load_committee_diversity_summary(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    _validate_diversity_summary(
        diversity_summary,
        diversity_seed_metrics=diversity_seed_metrics,
    )

    correction_seed_metrics = load_committee_correction_seed_metrics(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    _validate_correction_seed_metrics(
        correction_seed_metrics,
        metadata=metadata,
    )

    correction_summary = load_committee_correction_summary(
        dataset_name=canonical_dataset,
        artifacts_directory=artifacts_directory,
    )
    _validate_correction_summary(
        correction_summary,
        correction_seed_metrics=correction_seed_metrics,
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
        committee_directory / COMMITTEE_DIVERSITY_SEED_METRICS_FILE_NAME,
        committee_directory / COMMITTEE_DIVERSITY_SUMMARY_FILE_NAME,
        committee_directory / COMMITTEE_CORRECTION_SEED_METRICS_FILE_NAME,
        committee_directory / COMMITTEE_CORRECTION_SUMMARY_FILE_NAME,
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
        diversity_seed_metrics=diversity_seed_metrics,
        diversity_summary=diversity_summary,
        correction_seed_metrics=correction_seed_metrics,
        correction_summary=correction_summary,
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


def _prepare_diversity_table(
    artifacts: CommitteeExperimentArtifacts,
) -> pd.DataFrame:
    """Prepare the persisted pairwise diversity summary for notebook display."""
    rows: list[dict[str, object]] = []
    for _, row in artifacts.diversity_summary.iterrows():
        classifier_a = str(row["classifier_a"])
        classifier_b = str(row["classifier_b"])
        rows.append(
            {
                "Classifier A": _classifier_display_name(classifier_a),
                "Classifier B": _classifier_display_name(classifier_b),
                "Prediction disagreement": str(row["prediction_disagreement"]),
                "Double Fault": str(row["double_fault"]),
                "Error-set Jaccard overlap": str(row["error_set_jaccard"]),
            },
        )

    return pd.DataFrame(rows)


def _prepare_correction_table(
    artifacts: CommitteeExperimentArtifacts,
) -> pd.DataFrame:
    """Prepare persisted committee correction statistics for notebook display."""
    rows: list[dict[str, object]] = []
    for _, row in artifacts.correction_summary.iterrows():
        strategy = str(row["strategy"])
        rows.append(
            {
                "Strategy": _strategy_display_name(strategy),
                "Corrected (all components wrong)": str(row["corrected_count"]),
                "Incorrect (all components correct)": str(
                    row["incorrect_while_all_components_correct_count"]
                ),
                "Correct (≥1 component wrong)": str(
                    row["correct_while_component_wrong_count"]
                ),
            },
        )

    return pd.DataFrame(rows)


def compile_committee_diversity_table(
    artifacts: CommitteeExperimentArtifacts,
) -> pd.DataFrame:
    """Build the notebook-ready pairwise diversity table."""
    return _prepare_diversity_table(artifacts)


def compile_committee_correction_table(
    artifacts: CommitteeExperimentArtifacts,
) -> pd.DataFrame:
    """Build the notebook-ready committee correction table."""
    return _prepare_correction_table(artifacts)


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
        diversity_table=_prepare_diversity_table(artifacts),
        correction_table=_prepare_correction_table(artifacts),
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


def plot_committee_prediction_disagreement_heatmap(
    diversity_table: pd.DataFrame,
    *,
    title: str | None = None,
) -> Figure:
    """Plot the mean persisted prediction-disagreement rate as a heatmap."""
    required_columns = (
        "Classifier A",
        "Classifier B",
        "Prediction disagreement",
    )
    _validate_required_columns(
        diversity_table,
        required_columns,
        table_name="committee diversity table",
    )
    if diversity_table.empty:
        raise ValueError("Committee diversity table is empty.")

    expected_labels = tuple(
        _classifier_display_name(classifier) for classifier in CLASSIFIER_ORDER
    )
    matrix = np.full(
        (len(expected_labels), len(expected_labels)),
        np.nan,
        dtype=float,
    )
    label_to_index = {label: index for index, label in enumerate(expected_labels)}

    for _, row in diversity_table.iterrows():
        classifier_a = str(row["Classifier A"])
        classifier_b = str(row["Classifier B"])
        if classifier_a not in label_to_index or classifier_b not in label_to_index:
            raise ValueError(
                "Committee diversity table contains an unexpected classifier pair."
            )
        mean, std = _parse_summary_value(
            row["Prediction disagreement"],
            context=f"pair=({classifier_a}, {classifier_b})",
        )
        if not 0.0 <= mean <= 1.0 or std < 0.0 or not np.isfinite(std):
            raise ValueError(
                "Prediction-disagreement summary values must be finite and in "
                "the interval [0, 1]."
            )
        index_a = label_to_index[classifier_a]
        index_b = label_to_index[classifier_b]
        if np.isfinite(matrix[index_a, index_b]):
            raise ValueError("Committee diversity table contains duplicate pairs.")
        matrix[index_a, index_b] = mean
        matrix[index_b, index_a] = mean

    if np.isnan(matrix[np.triu_indices_from(matrix, k=1)]).any():
        raise ValueError("Committee diversity table is missing a classifier pair.")

    figure, axes = plt.subplots(figsize=(7.5, 6.5))
    image = axes.imshow(
        matrix,
        vmin=0.0,
        vmax=1.0,
        cmap=CONTINUOUS_PALETTE,
    )
    figure.colorbar(
        image,
        ax=axes,
        label="Prediction disagreement",
    )

    axes.set_xticks(
        np.arange(len(expected_labels)),
        expected_labels,
        rotation=30,
        ha="right",
    )
    axes.set_yticks(
        np.arange(len(expected_labels)),
        expected_labels,
    )
    axes.set_xlabel("Classifier")
    axes.set_ylabel("Classifier")
    axes.set_title(title or "Prediction disagreement between classifiers")

    for index in range(len(expected_labels)):
        axes.text(
            index,
            index,
            "—",
            ha="center",
            va="center",
        )

    for row_index in range(len(expected_labels)):
        for column_index in range(row_index + 1, len(expected_labels)):
            axes.text(
                column_index,
                row_index,
                f"{matrix[row_index, column_index]:.4f}",
                ha="center",
                va="center",
            )
            axes.text(
                row_index,
                column_index,
                f"{matrix[row_index, column_index]:.4f}",
                ha="center",
                va="center",
            )

    axes.set_aspect("equal")
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
    show_diversity: bool = False,
    show_correction: bool = False,
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

    if show_diversity:
        _display_section(
            title="Pairwise model diversity and complementarity",
            table=statistics.diversity_table,
        )

    if show_correction:
        _display_section(
            title="Committee correction behavior",
            table=statistics.correction_table,
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
        display_committee_statistics(
            statistics,
            show_diversity=True,
            show_correction=True,
        )


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
    "compile_committee_correction_table",
    "compile_committee_diversity_table",
    "compile_committee_statistics",
    "display_all_committee_statistics",
    "display_committee_statistics",
    "load_all_committee_experiment_artifacts",
    "load_committee_experiment_artifacts",
    "plot_committee_prediction_disagreement_heatmap",
    "plot_committee_primary_metric",
]
