"""Presentation helpers for persisted final test-evaluation results.

The test pipeline is responsible for loading the persisted final models,
running predictions, calculating test metrics, and persisting evaluation
artifacts. This module does none of those things. It only loads those
artifacts, validates them, formats report tables, and creates notebook-ready
figures.

The persisted test artifacts are stored beneath each dataset/classifier
experiment as::

    test_evaluation/test_seed_metrics.csv
    test_evaluation/test_per_class_metrics.csv
    test_evaluation/test_summary.csv
    test_evaluation/test_evaluation_metadata.json
    test_evaluation/inference_timing.csv
    test_evaluation/inference_timing_metadata.json
    test_evaluation/confusion_matrix_seed_<seed>.csv
    test_evaluation/confusion_matrix_normalized_seed_<seed>.csv
    training_timing.csv
    training_timing_metadata.json
    feature_importances/seed_<seed>.csv

Validation artifacts are optionally loaded for the selected configuration so
that validation-versus-test comparisons can be displayed without rerunning
any experiment.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import HTML, display
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.ticker import FixedFormatter, FixedLocator

import pipeline.test as pipeline_test
from eda.features import _configure_axis_grid
from eda.palette import (
    CONTINUOUS_PALETTE,
    get_discrete_colors,
)
from pipeline.common import (
    TRAINING_TIMING_CLOCK,
    TRAINING_TIMING_OPERATION,
    TRAINING_TIMING_SCHEMA_VERSION,
    TRAINING_TIMING_SCOPE,
    load_feature_importances,
    load_training_timing,
    load_training_timing_metadata,
)
from reporting.common import REPORT_DISPLAY_DECIMALS, format_mean_std

# ----------------------------------------
# Constants
# ----------------------------------------

DEFAULT_ARTIFACTS_DIRECTORY: Final[Path] = (
    Path(__file__).resolve().parent.parent / "_artifacts"
)

TEST_EVALUATION_DIRECTORY_NAME: Final[str] = "test_evaluation"

TEST_SEED_METRICS_FILE_NAME: Final[str] = "test_seed_metrics.csv"
TEST_PER_CLASS_METRICS_FILE_NAME: Final[str] = "test_per_class_metrics.csv"
TEST_SUMMARY_FILE_NAME: Final[str] = "test_summary.csv"
TEST_METADATA_FILE_NAME: Final[str] = "test_evaluation_metadata.json"
EXPERIMENT_METADATA_FILE_NAME: Final[str] = "metadata.json"
FEATURE_IMPORTANCE_DIRECTORY_NAME: Final[str] = "feature_importances"

VALIDATION_SEED_RESULTS_FILE_NAME: Final[str] = "validation_seeds.csv"

TEST_METRIC_COLUMNS: Final[tuple[str, ...]] = (
    "accuracy",
    "precision",
    "recall",
    "macro_f1",
    "roc_auc",
    "pr_auc",
    "mcc",
    "balanced_accuracy",
)

PRIMARY_TEST_METRIC: Final[str] = "macro_f1"

CONFIGURATION_ID_COLUMN: Final[str] = "configuration_id"
DATASET_COLUMN: Final[str] = "dataset"
CLASSIFIER_COLUMN: Final[str] = "classifier"
SEED_COLUMN: Final[str] = "seed"
CLASS_COLUMN: Final[str] = "class"

CLASSIFIER_ORDER: Final[tuple[str, ...]] = (
    "decision_tree",
    "random_forest",
    "xgboost",
)

DATASET_ORDER: Final[tuple[str, ...]] = (
    "GENIS",
    "ROSIDS",
)

CLASSIFIER_DISPLAY_NAMES: Final[dict[str, str]] = {
    "decision_tree": "Decision Tree",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

DEFAULT_FIGURE_SIZE: Final[tuple[float, float]] = (10.0, 6.0)
DEFAULT_CONFUSION_MATRIX_FIGURE_SIZE: Final[tuple[float, float]] = (10.5, 7.0)

REPORT_AXIS_TICK_COUNT: Final[int] = 6
REPORT_MINIMUM_AXIS_SPAN: Final[float] = 0.001

NORMALIZED_CONFUSION_MATRIX_MIN_SPAN: Final[float] = 0.05

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

REPORT_TEXT_LUMINANCE_THRESHOLD: Final[float] = 0.6

FEATURE_IMPORTANCE_LEVEL_COLUMN: Final[str] = "importance_level"
TRANSFORMED_FEATURE_COLUMN: Final[str] = "transformed_feature"
ORIGINAL_FEATURE_COLUMN: Final[str] = "original_feature"
IMPORTANCE_COLUMN: Final[str] = "importance"

DEFAULT_FEATURE_IMPORTANCE_TOP_N: Final[int] = 15

# Timing artifacts are persisted separately from predictive metrics. Training
# timing lives at the dataset/classifier experiment root, while frozen-test
# inference timing lives beneath ``test_evaluation``.
TRAINING_TIMING_FILE_NAME: Final[str] = "training_timing.csv"
TRAINING_TIMING_METADATA_FILE_NAME: Final[str] = "training_timing_metadata.json"
INFERENCE_TIMING_FILE_NAME: Final[str] = cast(
    str,
    pipeline_test.INFERENCE_TIMING_FILE_NAME,
)
INFERENCE_TIMING_METADATA_FILE_NAME: Final[str] = cast(
    str,
    pipeline_test.INFERENCE_TIMING_METADATA_FILE_NAME,
)
TRAINING_TIMING_COLUMNS: Final[tuple[str, ...]] = (
    DATASET_COLUMN,
    CLASSIFIER_COLUMN,
    SEED_COLUMN,
    CONFIGURATION_ID_COLUMN,
    "training_time_seconds",
    "training_row_count",
)
INFERENCE_TIMING_COLUMNS: Final[tuple[str, ...]] = cast(
    tuple[str, ...],
    pipeline_test.INFERENCE_TIMING_COLUMNS,
)

# ----------------------------------------
# Data structures
# ----------------------------------------


@dataclass(frozen=True, slots=True)
class TestExperimentArtifacts:
    """Paths and metadata for one persisted test evaluation."""

    dataset_name: str
    classifier_name: str
    directory: Path
    metadata: dict[str, object]
    seed_metrics: pd.DataFrame
    per_class_metrics: pd.DataFrame
    summary: pd.DataFrame
    training_timing: pd.DataFrame
    inference_timing: pd.DataFrame
    training_timing_metadata: dict[str, object]
    inference_timing_metadata: dict[str, object]
    confusion_matrices: dict[int, pd.DataFrame]
    normalized_confusion_matrices: dict[int, pd.DataFrame]


@dataclass(frozen=True, slots=True)
class TestStatistics:
    """Notebook-ready final-test reporting tables."""

    summary_table: pd.DataFrame
    seed_metrics_table: pd.DataFrame
    per_class_metrics_table: pd.DataFrame
    selected_configuration_table: pd.DataFrame
    timing_table: pd.DataFrame
    validation_vs_test_table: pd.DataFrame | None


# ----------------------------------------
# Loading
# ----------------------------------------


def load_test_experiment_artifacts(
    *,
    dataset_name: str,
    classifier_name: str,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> TestExperimentArtifacts:
    """Load one dataset/classifier test-evaluation artifact set.

    Args:
        dataset_name: Dataset identifier, e.g. ``GENIS`` or ``ROSIDS``.
        classifier_name: Classifier directory name.
        artifacts_directory: Root project ``_artifacts`` directory.

    Returns:
        Loaded test-evaluation artifacts.
    """
    normalized_dataset = dataset_name.lower()
    normalized_classifier = classifier_name.lower()

    experiment_directory = (
        artifacts_directory.expanduser().resolve()
        / normalized_dataset
        / normalized_classifier
    )
    evaluation_directory = experiment_directory / TEST_EVALUATION_DIRECTORY_NAME

    if not evaluation_directory.is_dir():
        raise FileNotFoundError(
            f"Test-evaluation artifact directory does not exist: "
            f"'{evaluation_directory}'.",
        )

    test_metadata = _load_json(
        evaluation_directory / TEST_METADATA_FILE_NAME,
    )
    experiment_metadata = _load_json(
        experiment_directory / EXPERIMENT_METADATA_FILE_NAME,
    )

    selected_configuration = experiment_metadata.get(
        "selected_configuration",
    )
    if not isinstance(selected_configuration, dict):
        raise TypeError(
            "Experiment metadata does not contain a valid "
            "selected_configuration object.",
        )

    metadata = dict(test_metadata)
    metadata["selected_configuration"] = selected_configuration
    metadata["training_row_count"] = experiment_metadata.get("training_row_count")

    seed_metrics = _load_csv(
        evaluation_directory / TEST_SEED_METRICS_FILE_NAME,
    )
    per_class_metrics = _load_csv(
        evaluation_directory / TEST_PER_CLASS_METRICS_FILE_NAME,
    )
    # The per-class test artifact is written per dataset/classifier directory
    # and therefore does not need to duplicate the classifier in the pipeline
    # artifact itself. Add it here so the reporting tables have a uniform
    # classifier key across seed-level and per-class data.
    if CLASSIFIER_COLUMN not in per_class_metrics.columns:
        per_class_metrics.insert(
            0,
            CLASSIFIER_COLUMN,
            normalized_classifier,
        )
    summary = _load_csv(
        evaluation_directory / TEST_SUMMARY_FILE_NAME,
    )

    training_timing = load_training_timing(
        experiment_directory,
    )
    training_timing_metadata = load_training_timing_metadata(
        experiment_directory,
    )
    inference_timing = pipeline_test.load_inference_timing(
        experiment_directory,
    )
    inference_timing_metadata = pipeline_test.load_inference_timing_metadata(
        experiment_directory,
    )

    _validate_test_seed_metrics(seed_metrics)
    _validate_per_class_metrics(per_class_metrics)
    _validate_summary(summary)

    _validate_training_timing_metadata(
        metadata=training_timing_metadata,
        dataset_name=dataset_name,
        classifier_name=normalized_classifier,
        configuration_id=str(selected_configuration["configuration_id"]),
        expected_seeds=tuple(
            int(seed)
            for seed in pd.to_numeric(
                seed_metrics[SEED_COLUMN],
                errors="raise",
            )
        ),
        training_row_count=_get_required_experiment_training_row_count(
            experiment_metadata,
        ),
    )
    _validate_inference_timing_metadata(
        metadata=inference_timing_metadata,
        dataset_name=dataset_name,
        classifier_name=normalized_classifier,
        expected_configuration_ids=(str(selected_configuration["configuration_id"]),),
        expected_seeds=tuple(
            int(seed)
            for seed in pd.to_numeric(
                seed_metrics[SEED_COLUMN],
                errors="raise",
            )
        ),
        test_row_count=_get_required_test_row_count(test_metadata),
    )
    _validate_inference_timing_frame(
        timing_data=inference_timing,
        dataset_name=dataset_name,
        classifier_name=normalized_classifier,
        expected_configuration_ids=(str(selected_configuration["configuration_id"]),),
        expected_seeds=tuple(
            int(seed)
            for seed in pd.to_numeric(
                seed_metrics[SEED_COLUMN],
                errors="raise",
            )
        ),
        test_row_count=_get_required_test_row_count(test_metadata),
    )

    confusion_matrices = _load_confusion_matrices(
        evaluation_directory,
        normalized_prefix="confusion_matrix_seed_",
    )
    normalized_confusion_matrices = _load_confusion_matrices(
        evaluation_directory,
        normalized_prefix="confusion_matrix_normalized_seed_",
    )

    _validate_confusion_matrices(
        matrices=confusion_matrices,
        seed_metrics=seed_metrics,
        normalized=False,
    )
    _validate_confusion_matrices(
        matrices=normalized_confusion_matrices,
        seed_metrics=seed_metrics,
        normalized=True,
    )
    _validate_confusion_matrix_pairs(
        raw_matrices=confusion_matrices,
        normalized_matrices=normalized_confusion_matrices,
    )

    _validate_identity(
        metadata=metadata,
        dataset_name=dataset_name,
        classifier_name=normalized_classifier,
        seed_metrics=seed_metrics,
        per_class_metrics=per_class_metrics,
        summary=summary,
    )

    return TestExperimentArtifacts(
        dataset_name=str(dataset_name),
        classifier_name=normalized_classifier,
        directory=experiment_directory,
        metadata=metadata,
        seed_metrics=seed_metrics,
        per_class_metrics=per_class_metrics,
        summary=summary,
        training_timing=training_timing,
        inference_timing=inference_timing,
        training_timing_metadata=training_timing_metadata,
        inference_timing_metadata=inference_timing_metadata,
        confusion_matrices=confusion_matrices,
        normalized_confusion_matrices=normalized_confusion_matrices,
    )


def load_all_test_experiment_artifacts(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> tuple[TestExperimentArtifacts, ...]:
    """Load all configured dataset/classifier test evaluations."""
    artifacts: list[TestExperimentArtifacts] = []

    for dataset_name in DATASET_ORDER:
        for classifier_name in CLASSIFIER_ORDER:
            artifacts.append(
                load_test_experiment_artifacts(
                    dataset_name=dataset_name,
                    classifier_name=classifier_name,
                    artifacts_directory=artifacts_directory,
                ),
            )

    return tuple(artifacts)


# ----------------------------------------
# Feature-importance loading and aggregation
# ----------------------------------------


def _validate_feature_importance_artifact(
    table: pd.DataFrame,
    *,
    classifier_name: str,
) -> tuple[int, ...]:
    """Validate one classifier's persisted feature-importance artifact."""
    required_columns = {
        SEED_COLUMN,
        CONFIGURATION_ID_COLUMN,
        FEATURE_IMPORTANCE_LEVEL_COLUMN,
        TRANSFORMED_FEATURE_COLUMN,
        ORIGINAL_FEATURE_COLUMN,
        IMPORTANCE_COLUMN,
    }

    missing_columns = required_columns - set(table.columns)
    if missing_columns:
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            f"is missing columns: {sorted(missing_columns)!r}.",
        )

    if table.empty:
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} is empty.",
        )

    frame = table.copy()

    frame[SEED_COLUMN] = pd.to_numeric(
        frame[SEED_COLUMN],
        errors="raise",
    ).astype(int)
    frame[CONFIGURATION_ID_COLUMN] = frame[CONFIGURATION_ID_COLUMN].astype(str)
    frame[FEATURE_IMPORTANCE_LEVEL_COLUMN] = frame[
        FEATURE_IMPORTANCE_LEVEL_COLUMN
    ].astype(str)
    frame[ORIGINAL_FEATURE_COLUMN] = frame[ORIGINAL_FEATURE_COLUMN].astype("string")
    frame[IMPORTANCE_COLUMN] = pd.to_numeric(
        frame[IMPORTANCE_COLUMN],
        errors="raise",
    ).astype(float)

    importance_values = frame[IMPORTANCE_COLUMN].to_numpy(dtype=float)
    if not np.isfinite(importance_values).all():
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "contains non-finite importance values.",
        )

    if (importance_values < 0.0).any():
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "contains negative importance values.",
        )

    configuration_ids = set(frame[CONFIGURATION_ID_COLUMN])
    if len(configuration_ids) != 1:
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "must contain exactly one configuration ID.",
        )

    original_frame = frame[
        frame[FEATURE_IMPORTANCE_LEVEL_COLUMN] == "original_feature"
    ].copy()

    if original_frame.empty:
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "contains no original-feature rows.",
        )

    if original_frame[ORIGINAL_FEATURE_COLUMN].isna().any():
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "contains missing original feature names.",
        )

    if original_frame[[SEED_COLUMN, ORIGINAL_FEATURE_COLUMN]].duplicated().any():
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "contains duplicate seed/original-feature rows.",
        )

    seeds = tuple(
        sorted(int(seed) for seed in original_frame[SEED_COLUMN].unique()),
    )

    if not seeds:
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "contains no seeds.",
        )

    seed_counts = original_frame.groupby(ORIGINAL_FEATURE_COLUMN)[SEED_COLUMN].nunique()

    if not (seed_counts == len(seeds)).all():
        incomplete_features = sorted(
            str(feature) for feature in seed_counts[seed_counts != len(seeds)].index
        )
        raise ValueError(
            f"Feature-importance data for classifier {classifier_name!r} "
            "does not contain every seed for every original feature: "
            f"{incomplete_features!r}.",
        )

    return seeds


def load_dataset_feature_importances(
    *,
    dataset_name: str,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> dict[str, pd.DataFrame]:
    """Load persisted feature importances for every classifier in one dataset."""
    normalized_dataset = dataset_name.upper()

    if normalized_dataset not in DATASET_ORDER:
        raise ValueError(
            f"Unknown dataset {dataset_name!r}. Available datasets: {DATASET_ORDER!r}.",
        )

    dataset_artifact_directory = (
        artifacts_directory.expanduser().resolve() / normalized_dataset.lower()
    )

    result: dict[str, pd.DataFrame] = {}

    for classifier_name in CLASSIFIER_ORDER:
        experiment_directory = dataset_artifact_directory / classifier_name

        feature_importance_directory = (
            experiment_directory / FEATURE_IMPORTANCE_DIRECTORY_NAME
        )

        if not feature_importance_directory.is_dir():
            raise FileNotFoundError(
                "Feature-importance artifact directory does not exist: "
                f"'{feature_importance_directory}'.",
            )

        frame = load_feature_importances(
            experiment_directory,
        )

        _validate_feature_importance_artifact(
            frame,
            classifier_name=classifier_name,
        )

        result[classifier_name] = frame

    return result


def _aggregate_feature_importances(
    frame: pd.DataFrame,
    *,
    classifier_name: str,
) -> pd.DataFrame:
    """Aggregate one classifier's original-feature importance over seeds."""
    working_frame = frame[
        frame[FEATURE_IMPORTANCE_LEVEL_COLUMN].astype(str) == "original_feature"
    ].copy()

    working_frame[ORIGINAL_FEATURE_COLUMN] = working_frame[
        ORIGINAL_FEATURE_COLUMN
    ].astype(str)

    grouped = working_frame.groupby(
        ORIGINAL_FEATURE_COLUMN,
        as_index=False,
    ).agg(
        mean_importance=(IMPORTANCE_COLUMN, "mean"),
        std_importance=(IMPORTANCE_COLUMN, "std"),
        seed_count=(SEED_COLUMN, "nunique"),
    )

    grouped["std_importance"] = grouped["std_importance"].fillna(0.0)
    grouped[CLASSIFIER_COLUMN] = classifier_name

    return grouped[
        [
            CLASSIFIER_COLUMN,
            ORIGINAL_FEATURE_COLUMN,
            "mean_importance",
            "std_importance",
            "seed_count",
        ]
    ]


def compile_dataset_feature_importances(
    *,
    dataset_name: str,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> pd.DataFrame:
    """Compile seed-aggregated feature importances for one dataset."""
    feature_importance_frames = load_dataset_feature_importances(
        dataset_name=dataset_name,
        artifacts_directory=artifacts_directory,
    )

    aggregated_frames: list[pd.DataFrame] = []
    reference_seeds: tuple[int, ...] | None = None
    reference_features: set[str] | None = None

    for classifier_name in CLASSIFIER_ORDER:
        frame = feature_importance_frames[classifier_name]

        seeds = _validate_feature_importance_artifact(
            frame,
            classifier_name=classifier_name,
        )

        if reference_seeds is None:
            reference_seeds = seeds
        elif seeds != reference_seeds:
            raise ValueError(
                "Feature-importance artifacts for the classifiers in dataset "
                f"{dataset_name!r} do not use the same seeds: "
                f"{classifier_name!r} has {seeds!r}, expected {reference_seeds!r}.",
            )

        aggregated_frame = _aggregate_feature_importances(
            frame,
            classifier_name=classifier_name,
        )

        feature_set = set(
            aggregated_frame[ORIGINAL_FEATURE_COLUMN].astype(str),
        )

        if reference_features is None:
            reference_features = feature_set
        elif feature_set != reference_features:
            missing_features = sorted(
                reference_features - feature_set,
            )
            unexpected_features = sorted(
                feature_set - reference_features,
            )
            raise ValueError(
                "Feature-importance artifacts for the classifiers in dataset "
                f"{dataset_name!r} do not contain the same original features "
                f"for classifier {classifier_name!r}. Missing: "
                f"{missing_features!r}; unexpected: {unexpected_features!r}."
            )

        aggregated_frames.append(
            aggregated_frame,
        )

    result = pd.concat(
        aggregated_frames,
        ignore_index=True,
    )

    result = result.sort_values(
        [CLASSIFIER_COLUMN, ORIGINAL_FEATURE_COLUMN],
        key=lambda values: (
            pd.Categorical(
                values,
                categories=list(CLASSIFIER_ORDER),
                ordered=True,
            )
            if values.name == CLASSIFIER_COLUMN
            else values
        ),
        ignore_index=True,
    )

    return result


def _get_feature_importance_order(
    feature_importances: pd.DataFrame,
    *,
    top_n: int | None,
) -> list[str]:
    """Return features ordered by their largest mean importance."""
    required_columns = {
        CLASSIFIER_COLUMN,
        ORIGINAL_FEATURE_COLUMN,
        "mean_importance",
        "std_importance",
    }

    missing_columns = required_columns - set(feature_importances.columns)
    if missing_columns:
        raise ValueError(
            f"Feature-importance data is missing columns: {sorted(missing_columns)!r}.",
        )

    if top_n is not None and top_n < 1:
        raise ValueError("top_n must be at least 1 or None.")

    frame = feature_importances.copy()

    frame["mean_importance"] = pd.to_numeric(
        frame["mean_importance"],
        errors="raise",
    ).astype(float)
    frame["std_importance"] = pd.to_numeric(
        frame["std_importance"],
        errors="raise",
    ).astype(float)

    if not np.isfinite(
        frame[["mean_importance", "std_importance"]].to_numpy(dtype=float)
    ).all():
        raise ValueError(
            "Feature-importance means and standard deviations must be finite.",
        )

    if (frame["mean_importance"] < 0.0).any() or (frame["std_importance"] < 0.0).any():
        raise ValueError(
            "Feature-importance means and standard deviations must be non-negative.",
        )

    feature_order = (
        frame.groupby(ORIGINAL_FEATURE_COLUMN)["mean_importance"]
        .max()
        .sort_values(ascending=False, kind="stable")
        .index.astype(str)
        .tolist()
    )

    if top_n is not None:
        feature_order = feature_order[:top_n]

    return feature_order


def prepare_dataset_feature_importance_table(
    feature_importances: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare an aggregated feature-importance table for notebook display."""
    feature_order = _get_feature_importance_order(
        feature_importances,
        top_n=None,
    )

    frame = feature_importances.copy()

    frame[CLASSIFIER_COLUMN] = frame[CLASSIFIER_COLUMN].map(
        _normalize_classifier_name,
    )
    frame[ORIGINAL_FEATURE_COLUMN] = frame[ORIGINAL_FEATURE_COLUMN].astype(str)

    mean_matrix = frame.pivot(
        index=ORIGINAL_FEATURE_COLUMN,
        columns=CLASSIFIER_COLUMN,
        values="mean_importance",
    ).reindex(
        index=feature_order,
        columns=CLASSIFIER_ORDER,
    )

    std_matrix = frame.pivot(
        index=ORIGINAL_FEATURE_COLUMN,
        columns=CLASSIFIER_COLUMN,
        values="std_importance",
    ).reindex(
        index=feature_order,
        columns=CLASSIFIER_ORDER,
    )

    rows: list[dict[str, object]] = []

    for feature_name in feature_order:
        row: dict[str, object] = {
            "Feature": feature_name,
        }

        for classifier_name in CLASSIFIER_ORDER:
            mean = mean_matrix.loc[feature_name, classifier_name]
            std = std_matrix.loc[feature_name, classifier_name]

            if pd.isna(mean) or pd.isna(std):
                row[_classifier_display_name(classifier_name)] = "—"
            else:
                row[_classifier_display_name(classifier_name)] = (
                    f"{_to_python_float(mean):.{REPORT_DISPLAY_DECIMALS}f} ± "
                    f"{_to_python_float(std):.{REPORT_DISPLAY_DECIMALS}f}"
                )

        rows.append(row)

    return pd.DataFrame(rows)


def plot_dataset_feature_importances(
    feature_importances: pd.DataFrame,
    *,
    title: str | None = None,
    top_n: int = DEFAULT_FEATURE_IMPORTANCE_TOP_N,
) -> Figure:
    """Plot top aggregated original-feature importances by classifier."""
    feature_order = _get_feature_importance_order(
        feature_importances,
        top_n=top_n,
    )

    if not feature_order:
        raise ValueError("Feature-importance data contains no features to plot.")

    frame = feature_importances.copy()
    frame[CLASSIFIER_COLUMN] = frame[CLASSIFIER_COLUMN].map(
        _normalize_classifier_name,
    )
    frame[ORIGINAL_FEATURE_COLUMN] = frame[ORIGINAL_FEATURE_COLUMN].astype(str)

    colors = get_discrete_colors(
        len(CLASSIFIER_ORDER),
    )

    figure_height = max(
        DEFAULT_FIGURE_SIZE[1],
        0.38 * len(feature_order) + 2.5,
    )

    figure, axes = plt.subplots(
        figsize=(
            DEFAULT_FIGURE_SIZE[0],
            figure_height,
        ),
    )

    positions = np.arange(
        len(feature_order),
        dtype=float,
    )

    bar_height = 0.8 / len(CLASSIFIER_ORDER)
    offsets = (
        np.arange(
            len(CLASSIFIER_ORDER),
            dtype=float,
        )
        - (len(CLASSIFIER_ORDER) - 1) / 2.0
    ) * bar_height

    for classifier_index, classifier_name in enumerate(CLASSIFIER_ORDER):
        classifier_frame = frame[frame[CLASSIFIER_COLUMN] == classifier_name].set_index(
            ORIGINAL_FEATURE_COLUMN
        )

        means = np.asarray(
            [
                _to_python_float(classifier_frame.loc[feature, "mean_importance"])
                for feature in feature_order
            ],
            dtype=float,
        )
        errors = np.asarray(
            [
                _to_python_float(classifier_frame.loc[feature, "std_importance"])
                for feature in feature_order
            ],
            dtype=float,
        )

        axes.barh(
            positions + offsets[classifier_index],
            means,
            height=bar_height,
            xerr=errors,
            capsize=3,
            color=colors[classifier_index],
            label=_classifier_display_name(classifier_name),
        )

    axes.set_yticks(
        positions,
        feature_order,
    )
    axes.invert_yaxis()
    axes.set_xlabel("Mean feature importance")
    axes.set_ylabel("Original feature")
    axes.set_title(
        title or "Feature importance by classifier",
    )
    axes.legend()

    figure.tight_layout()
    return figure


def plot_dataset_feature_importance_heatmap(
    feature_importances: pd.DataFrame,
    *,
    title: str | None = None,
    top_n: int = DEFAULT_FEATURE_IMPORTANCE_TOP_N,
) -> Figure:
    """Plot top aggregated original-feature importances as a heatmap."""
    feature_order = _get_feature_importance_order(
        feature_importances,
        top_n=top_n,
    )

    if not feature_order:
        raise ValueError("Feature-importance data contains no features to plot.")

    frame = feature_importances.copy()
    frame[CLASSIFIER_COLUMN] = frame[CLASSIFIER_COLUMN].map(
        _normalize_classifier_name,
    )
    frame[ORIGINAL_FEATURE_COLUMN] = frame[ORIGINAL_FEATURE_COLUMN].astype(str)

    matrix = frame.pivot(
        index=ORIGINAL_FEATURE_COLUMN,
        columns=CLASSIFIER_COLUMN,
        values="mean_importance",
    ).reindex(
        index=feature_order,
        columns=CLASSIFIER_ORDER,
    )

    values = matrix.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(
            "Feature-importance heatmap values must be finite.",
        )

    maximum_value = _to_python_float(values.max())
    if maximum_value <= 0.0:
        maximum_value = 1.0

    normalization = Normalize(
        vmin=0.0,
        vmax=maximum_value,
    )

    figure_height = max(
        DEFAULT_FIGURE_SIZE[1],
        0.38 * len(feature_order) + 2.5,
    )

    figure, axes = plt.subplots(
        figsize=(
            DEFAULT_FIGURE_SIZE[0],
            figure_height,
        ),
    )

    sns.heatmap(
        matrix,
        ax=axes,
        cmap=CONTINUOUS_PALETTE,
        vmin=0.0,
        vmax=maximum_value,
        annot=False,
        cbar=True,
        cbar_kws={
            "label": "Mean feature importance",
        },
        square=False,
        xticklabels=[
            _classifier_display_name(classifier_name)
            for classifier_name in CLASSIFIER_ORDER
        ],
        yticklabels=feature_order,
    )

    axes.set_xlabel("Classifier")
    axes.set_ylabel("Original feature")
    axes.set_title(
        title or "Feature importance by classifier",
    )

    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix.iat[
                row_index,
                column_index,
            ]

            if pd.notna(value):
                numeric_value = _to_python_float(value)

                normalized_value = normalization(
                    np.asarray(
                        [numeric_value],
                        dtype=float,
                    ),
                )

                cell_color = CONTINUOUS_PALETTE(
                    normalized_value,
                )[0]

                luminance = (
                    0.2126 * _to_python_float(cell_color[0])
                    + 0.7152 * _to_python_float(cell_color[1])
                    + 0.0722 * _to_python_float(cell_color[2])
                )

                text_color = (
                    "white" if luminance < REPORT_TEXT_LUMINANCE_THRESHOLD else "black"
                )

                axes.text(
                    column_index + 0.5,
                    row_index + 0.5,
                    f"{numeric_value:.{REPORT_DISPLAY_DECIMALS}f}",
                    ha="center",
                    va="center",
                    color=text_color,
                )

    figure.tight_layout()
    return figure


# ----------------------------------------
# Compilation
# ----------------------------------------


def compile_test_statistics(
    *,
    artifacts: TestExperimentArtifacts,
    include_validation_comparison: bool = True,
) -> TestStatistics:
    """Prepare one experiment's test artifacts for notebook display."""
    summary_table = _prepare_summary_table(
        artifacts.summary,
        artifacts.seed_metrics,
    )
    seed_metrics_table = _prepare_seed_metrics_table(
        artifacts.seed_metrics,
    )
    per_class_metrics_table = _prepare_per_class_metrics_table(
        artifacts.per_class_metrics,
    )
    selected_configuration_table = _prepare_selected_configuration_table(
        artifacts.metadata,
    )
    timing_table = _prepare_timing_table(
        training_timing=artifacts.training_timing,
        inference_timing=artifacts.inference_timing,
    )

    validation_vs_test_table: pd.DataFrame | None = None

    if include_validation_comparison:
        validation_vs_test_table = _build_validation_vs_test_table(
            artifacts,
        )

    return TestStatistics(
        summary_table=summary_table,
        seed_metrics_table=seed_metrics_table,
        per_class_metrics_table=per_class_metrics_table,
        selected_configuration_table=selected_configuration_table,
        timing_table=timing_table,
        validation_vs_test_table=validation_vs_test_table,
    )


def compile_all_test_statistics(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
    include_validation_comparison: bool = True,
) -> tuple[TestStatistics, ...]:
    """Compile all configured dataset/classifier test evaluations."""
    return tuple(
        compile_test_statistics(
            artifacts=artifacts,
            include_validation_comparison=include_validation_comparison,
        )
        for artifacts in load_all_test_experiment_artifacts(
            artifacts_directory=artifacts_directory,
        )
    )


def compile_all_test_summary_table(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> pd.DataFrame:
    """Build one combined summary table for every experiment."""
    rows: list[dict[str, object]] = []

    for artifacts in load_all_test_experiment_artifacts(
        artifacts_directory=artifacts_directory,
    ):
        statistics = compile_test_statistics(
            artifacts=artifacts,
            include_validation_comparison=False,
        )
        for record in statistics.summary_table.to_dict(orient="records"):
            normalized_record: dict[str, object] = {
                str(key): value for key, value in record.items()
            }
            rows.append(normalized_record)

    return pd.DataFrame(rows)


def compile_all_test_timing_table(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
) -> pd.DataFrame:
    """Build one combined timing table for every experiment."""
    rows: list[dict[str, object]] = []

    for artifacts in load_all_test_experiment_artifacts(
        artifacts_directory=artifacts_directory,
    ):
        statistics = compile_test_statistics(
            artifacts=artifacts,
            include_validation_comparison=False,
        )
        for record in statistics.timing_table.to_dict(orient="records"):
            rows.append({str(key): value for key, value in record.items()})

    return pd.DataFrame(rows)


# ----------------------------------------
# Public display functions
# ----------------------------------------


def display_test_statistics(
    statistics: TestStatistics,
    *,
    show_summary: bool = True,
    show_configuration: bool = True,
    show_seed_metrics: bool = True,
    show_per_class_metrics: bool = True,
    show_timing: bool = True,
    show_validation_comparison: bool = True,
) -> None:
    """Display the main test-result tables in a notebook."""
    if show_summary:
        _display_section(
            title="Final test metrics",
            table=statistics.summary_table,
        )

    if show_configuration:
        _display_section(
            title="Selected configuration",
            table=statistics.selected_configuration_table,
        )

    if show_seed_metrics:
        _display_section(
            title="Test metrics by seed",
            table=statistics.seed_metrics_table,
        )

    if show_per_class_metrics:
        _display_section(
            title="Test per-class metrics",
            table=statistics.per_class_metrics_table,
        )

    if show_timing:
        _display_section(
            title="Computational timing",
            table=statistics.timing_table,
        )

    if show_validation_comparison and statistics.validation_vs_test_table is not None:
        _display_section(
            title="Validation versus test",
            table=statistics.validation_vs_test_table,
        )


def display_test_confusion_matrices(
    artifacts: TestExperimentArtifacts,
    *,
    normalized: bool = True,
    seed: int | None = None,
) -> None:
    """Display persisted confusion matrices as heatmaps.

    Args:
        artifacts: Loaded test artifacts for one experiment.
        normalized: Display normalized true-class rates when true.
        seed: Optional seed. When omitted, display every persisted seed.
    """
    matrices = (
        artifacts.normalized_confusion_matrices
        if normalized
        else artifacts.confusion_matrices
    )

    seeds = (seed,) if seed is not None else tuple(sorted(matrices))

    for matrix_seed in seeds:
        try:
            matrix = matrices[matrix_seed]
        except KeyError as error:
            raise ValueError(
                f"No {'normalized ' if normalized else ''}confusion matrix "
                f"was persisted for seed {matrix_seed}.",
            ) from error

        figure = plot_confusion_matrix(
            matrix=matrix,
            title=(
                f"{artifacts.dataset_name} — "
                f"{_classifier_display_name(artifacts.classifier_name)} — "
                f"seed {matrix_seed}"
            ),
            normalized=normalized,
        )
        display(figure)
        plt.close(figure)


def display_all_test_confusion_matrices(
    *,
    artifacts_directory: Path = DEFAULT_ARTIFACTS_DIRECTORY,
    normalized: bool = True,
) -> None:
    """Display confusion matrices for all dataset/classifier experiments."""
    for artifacts in load_all_test_experiment_artifacts(
        artifacts_directory=artifacts_directory,
    ):
        display_test_confusion_matrices(
            artifacts,
            normalized=normalized,
        )


# ----------------------------------------
# Display formatting helpers
# ----------------------------------------


def _to_python_float(value: object) -> float:
    """Convert a numeric scalar to a Python float for static type checking."""
    return float(cast(float, value))


def _format_report_axis_tick(value: float) -> str:
    """Format report metric-axis ticks without collapsing values near 1."""
    if not np.isfinite(value):
        return ""

    formatted_value = f"{value:.{REPORT_DISPLAY_DECIMALS}f}"
    if "." in formatted_value:
        formatted_value = formatted_value.rstrip("0").rstrip(".")

    return formatted_value


def _configure_report_axis_ticks(
    axes: Axes,
    tick_values: Sequence[float],
) -> None:
    """Apply high-precision fixed tick labels to a report axis."""
    labels = tuple(
        _format_report_axis_tick(_to_python_float(value)) for value in tick_values
    )
    axes.yaxis.set_major_locator(FixedLocator(tick_values))
    axes.yaxis.set_major_formatter(FixedFormatter(labels))


def _get_metric_axis_bounds(
    values: Sequence[float],
    errors: Sequence[float] = (),
) -> tuple[float, float]:
    """Return data-aware bounds for classification metric plots."""
    value_array = np.asarray(values, dtype=float)
    if value_array.size == 0 or not np.isfinite(value_array).all():
        raise ValueError("Metric plot values must be finite and non-empty.")

    lower = _to_python_float(value_array.min())
    upper = _to_python_float(value_array.max())

    if len(errors) > 0:
        error_array = np.asarray(errors, dtype=float)
        if error_array.shape != value_array.shape:
            raise ValueError("Metric plot errors must match value shape.")
        if not np.isfinite(error_array).all() or (error_array < 0.0).any():
            raise ValueError("Metric plot errors must be finite and non-negative.")
        lower = min(lower, _to_python_float((value_array - error_array).min()))
        upper = max(upper, _to_python_float((value_array + error_array).max()))

    lower = max(0.0, lower)
    upper = min(1.0, upper)

    span = upper - lower
    minimum_span = REPORT_MINIMUM_AXIS_SPAN
    if span <= 0.0:
        center = lower
        lower = max(0.0, center - minimum_span / 2.0)
        upper = min(1.0, center + minimum_span / 2.0)
        if upper - lower < minimum_span:
            if lower == 0.0:
                upper = min(1.0, minimum_span)
            else:
                lower = max(0.0, 1.0 - minimum_span)
                upper = 1.0
        return lower, upper

    padding = max(span * 0.10, minimum_span / 10.0)
    lower = max(0.0, lower - padding)
    upper = min(1.0, upper + padding)

    if upper - lower < minimum_span:
        midpoint = (lower + upper) / 2.0
        lower = max(0.0, midpoint - minimum_span / 2.0)
        upper = min(1.0, midpoint + minimum_span / 2.0)

    return lower, upper


def _configure_metric_y_axis(
    axes: Axes,
    *,
    values: Sequence[float],
    errors: Sequence[float] = (),
) -> None:
    """Configure a precise, data-aware Y axis for a [0, 1] metric."""
    lower, upper = _get_metric_axis_bounds(
        values,
        errors,
    )
    axes.set_ylim(lower, upper)
    tick_values = tuple(
        _to_python_float(value)
        for value in np.linspace(
            lower,
            upper,
            REPORT_AXIS_TICK_COUNT,
        )
    )
    _configure_report_axis_ticks(
        axes,
        tick_values,
    )
    _configure_axis_grid(axes)


# ----------------------------------------
# Figures
# ----------------------------------------


def plot_metric_comparison(
    data_frame: pd.DataFrame,
    *,
    metric: str,
    title: str | None = None,
) -> Figure:
    """Plot validation versus test for one metric across classifiers.

    ``data_frame`` must contain the columns ``classifier``,
    ``validation_mean``, ``validation_std``, ``test_mean`` and ``test_std``.
    """
    if metric not in TEST_METRIC_COLUMNS:
        raise ValueError(
            f"Unknown metric {metric!r}. Available metrics: {TEST_METRIC_COLUMNS!r}.",
        )

    required_columns = {
        CLASSIFIER_COLUMN,
        "validation_mean",
        "validation_std",
        "test_mean",
        "test_std",
    }
    missing_columns = required_columns - set(data_frame.columns)
    if missing_columns:
        raise ValueError(
            f"Metric comparison data is missing columns: {sorted(missing_columns)!r}.",
        )

    frame = data_frame.copy()
    _validate_metric_frame(
        frame,
        columns=(
            "validation_mean",
            "validation_std",
            "test_mean",
            "test_std",
        ),
        table_name="metric_comparison",
    )

    frame[CLASSIFIER_COLUMN] = frame[CLASSIFIER_COLUMN].map(
        _normalize_classifier_name,
    )
    frame["classifier_display"] = frame[CLASSIFIER_COLUMN].map(
        _classifier_display_name,
    )
    frame = frame.sort_values(
        by=CLASSIFIER_COLUMN,
        key=lambda values: pd.Categorical(
            values,
            categories=list(CLASSIFIER_ORDER),
            ordered=True,
        ),
        ignore_index=True,
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    positions = np.arange(
        len(frame),
        dtype=float,
    )

    validation_color, test_color = get_discrete_colors(
        2,
    )

    validation_values = frame["validation_mean"].to_numpy(dtype=float)
    validation_errors = frame["validation_std"].to_numpy(dtype=float)
    test_values = frame["test_mean"].to_numpy(dtype=float)
    test_errors = frame["test_std"].to_numpy(dtype=float)

    offset = 0.16

    axes.errorbar(
        positions - offset,
        validation_values,
        yerr=validation_errors,
        fmt="o",
        capsize=4,
        color=validation_color,
        label="Validation",
    )
    axes.errorbar(
        positions + offset,
        test_values,
        yerr=test_errors,
        fmt="o",
        capsize=4,
        color=test_color,
        label="Test",
    )

    axes.set_xticks(
        positions,
        frame["classifier_display"].tolist(),
    )

    axes.set_title(
        title or f"Validation versus test — {METRIC_DISPLAY_NAMES[metric]}",
    )
    axes.set_ylabel(
        METRIC_DISPLAY_NAMES[metric],
    )
    axes.set_xlabel("Classifier")
    _configure_metric_y_axis(
        axes,
        values=(
            *validation_values.tolist(),
            *test_values.tolist(),
        ),
        errors=(
            *validation_errors.tolist(),
            *test_errors.tolist(),
        ),
    )
    axes.legend()

    figure.tight_layout()
    return figure


def plot_test_seed_metric(
    seed_metrics: pd.DataFrame,
    *,
    metric: str = PRIMARY_TEST_METRIC,
    title: str | None = None,
) -> Figure:
    """Plot one test metric by seed for all classifiers in one experiment."""
    if metric not in TEST_METRIC_COLUMNS:
        raise ValueError(
            f"Unknown metric {metric!r}. Available metrics: {TEST_METRIC_COLUMNS!r}.",
        )

    required_columns = {
        CLASSIFIER_COLUMN,
        SEED_COLUMN,
        metric,
    }
    missing_columns = required_columns - set(seed_metrics.columns)
    if missing_columns:
        raise ValueError(
            f"Seed metric data is missing columns: {sorted(missing_columns)!r}.",
        )

    frame = seed_metrics.copy()

    frame[CLASSIFIER_COLUMN] = frame[CLASSIFIER_COLUMN].map(
        _normalize_classifier_name,
    )

    frame[SEED_COLUMN] = pd.to_numeric(
        frame[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    frame[metric] = pd.to_numeric(
        frame[metric],
        errors="raise",
    ).astype(float)

    _validate_metric_frame(
        frame,
        columns=(metric,),
        table_name="seed_metrics",
    )

    colors = get_discrete_colors(
        len(CLASSIFIER_ORDER),
    )

    seed_values = tuple(
        sorted(
            frame[SEED_COLUMN].unique(),
        ),
    )

    seed_positions = np.arange(
        len(seed_values),
        dtype=float,
    )

    bar_width = 0.8 / len(CLASSIFIER_ORDER)

    offsets = (
        np.arange(
            len(CLASSIFIER_ORDER),
            dtype=float,
        )
        - (len(CLASSIFIER_ORDER) - 1) / 2.0
    ) * bar_width

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    for classifier_index, classifier_name in enumerate(CLASSIFIER_ORDER):
        classifier_frame = frame[frame[CLASSIFIER_COLUMN] == classifier_name][
            [SEED_COLUMN, metric]
        ].copy()

        if classifier_frame.empty:
            raise ValueError(
                f"No test metrics were found for classifier {classifier_name!r}.",
            )

        if classifier_frame[SEED_COLUMN].duplicated().any():
            raise ValueError(
                f"Test seed metrics contain duplicate seeds for classifier "
                f"{classifier_name!r}.",
            )

        seed_to_value = dict(
            zip(
                classifier_frame[SEED_COLUMN].to_numpy(dtype=int),
                classifier_frame[metric].to_numpy(dtype=float),
                strict=True,
            ),
        )

        values: list[float] = []

        for seed in seed_values:
            try:
                value = seed_to_value[seed]
            except KeyError as error:
                raise ValueError(
                    f"Missing seed {seed} for classifier {classifier_name!r}.",
                ) from error

            values.append(value)

        axes.bar(
            seed_positions + offsets[classifier_index],
            values,
            width=bar_width,
            color=colors[classifier_index],
            label=_classifier_display_name(classifier_name),
        )

    axes.set_xticks(
        seed_positions,
        [str(seed) for seed in seed_values],
    )

    axes.set_xlabel("Seed")
    axes.set_ylabel(
        METRIC_DISPLAY_NAMES[metric],
    )

    axes.set_title(
        title or f"Test {METRIC_DISPLAY_NAMES[metric]} by seed",
    )

    _configure_metric_y_axis(
        axes,
        values=tuple(
            _to_python_float(value) for value in frame[metric].to_numpy(dtype=float)
        ),
    )

    axes.legend()

    figure.tight_layout()
    return figure


def plot_per_class_metric_heatmap(
    per_class_metrics: pd.DataFrame,
    *,
    metric: str = "f1",
    title: str | None = None,
    aggregate_seeds: bool = True,
) -> Figure:
    """Plot a classifier-by-class heatmap for a per-class metric."""
    allowed_metrics = {"precision", "recall", "f1"}

    if metric not in allowed_metrics:
        raise ValueError(
            f"Unknown per-class metric {metric!r}. Available metrics: "
            f"{sorted(allowed_metrics)!r}.",
        )

    required_columns = {
        CLASSIFIER_COLUMN,
        CLASS_COLUMN,
        SEED_COLUMN,
        metric,
    }

    missing_columns = required_columns - set(per_class_metrics.columns)

    if missing_columns:
        raise ValueError(
            f"Per-class metric data is missing columns: {sorted(missing_columns)!r}.",
        )

    frame = per_class_metrics.copy()

    frame[CLASSIFIER_COLUMN] = frame[CLASSIFIER_COLUMN].map(
        _normalize_classifier_name,
    )

    frame[metric] = pd.to_numeric(
        frame[metric],
        errors="raise",
    ).astype(float)

    frame[SEED_COLUMN] = pd.to_numeric(
        frame[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    frame[CLASSIFIER_COLUMN] = frame[CLASSIFIER_COLUMN].astype(str)
    frame[CLASS_COLUMN] = frame[CLASS_COLUMN].astype(str)

    _validate_metric_frame(
        frame,
        columns=(metric,),
        table_name="per_class_metrics",
    )

    if aggregate_seeds:
        frame = frame.groupby(
            [CLASSIFIER_COLUMN, CLASS_COLUMN],
            as_index=False,
        )[metric].mean()
    else:
        raise ValueError(
            "aggregate_seeds=False is intentionally unsupported for the "
            "classifier-by-class summary heatmap. Use seed-level tables "
            "for individual seeds.",
        )

    classifier_values = [
        classifier
        for classifier in CLASSIFIER_ORDER
        if classifier in set(frame[CLASSIFIER_COLUMN])
    ]

    class_values = frame[CLASS_COLUMN].drop_duplicates().tolist()

    matrix = frame.pivot(
        index=CLASSIFIER_COLUMN,
        columns=CLASS_COLUMN,
        values=metric,
    ).reindex(
        index=classifier_values,
        columns=class_values,
    )

    values = matrix.to_numpy(dtype=float)

    if values.size == 0:
        raise ValueError(
            "Per-class metric heatmap contains no values.",
        )

    finite_values = values[np.isfinite(values)]

    if finite_values.size == 0:
        raise ValueError(
            "Per-class metric heatmap contains no finite values.",
        )

    if (finite_values < 0.0).any() or (finite_values > 1.0).any():
        raise ValueError(
            "Per-class metric heatmap values must be within [0, 1].",
        )

    minimum_observed_value = _to_python_float(finite_values.min())
    maximum_observed_value = _to_python_float(finite_values.max())

    span = maximum_observed_value - minimum_observed_value

    if span <= 0.0:
        lower = max(
            0.0,
            minimum_observed_value - REPORT_MINIMUM_AXIS_SPAN / 2.0,
        )

        upper = min(
            1.0,
            maximum_observed_value + REPORT_MINIMUM_AXIS_SPAN / 2.0,
        )

        if upper - lower < REPORT_MINIMUM_AXIS_SPAN:
            if lower == 0.0:
                upper = min(
                    1.0,
                    REPORT_MINIMUM_AXIS_SPAN,
                )
            else:
                lower = max(
                    0.0,
                    1.0 - REPORT_MINIMUM_AXIS_SPAN,
                )
                upper = 1.0
    else:
        padding = max(
            span * 0.10,
            REPORT_MINIMUM_AXIS_SPAN / 10.0,
        )

        lower = max(
            0.0,
            minimum_observed_value - padding,
        )

        upper = min(
            1.0,
            maximum_observed_value + padding,
        )

        if upper - lower < REPORT_MINIMUM_AXIS_SPAN:
            midpoint = (lower + upper) / 2.0

            lower = max(
                0.0,
                midpoint - REPORT_MINIMUM_AXIS_SPAN / 2.0,
            )

            upper = min(
                1.0,
                midpoint + REPORT_MINIMUM_AXIS_SPAN / 2.0,
            )

    normalization = Normalize(
        vmin=lower,
        vmax=upper,
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    sns.heatmap(
        matrix,
        ax=axes,
        cmap=CONTINUOUS_PALETTE,
        vmin=lower,
        vmax=upper,
        annot=False,
        cbar=True,
        cbar_kws={
            "label": METRIC_DISPLAY_NAMES.get(
                metric,
                metric.title(),
            ),
        },
        square=False,
    )

    axes.set_xticks(
        np.arange(len(class_values)) + 0.5,
        class_values,
    )

    axes.set_yticks(
        np.arange(len(classifier_values)) + 0.5,
        [_classifier_display_name(value) for value in classifier_values],
    )

    axes.set_xlabel("Class")
    axes.set_ylabel("Classifier")
    axes.set_title(
        title or f"Test per-class {metric.upper()}",
    )

    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix.iat[
                row_index,
                column_index,
            ]

            if pd.notna(value):
                numeric_value = _to_python_float(value)

                normalized_value = normalization(
                    np.asarray(
                        [numeric_value],
                        dtype=float,
                    ),
                )

                cell_color = CONTINUOUS_PALETTE(
                    normalized_value,
                )[0]

                luminance = (
                    0.2126 * _to_python_float(cell_color[0])
                    + 0.7152 * _to_python_float(cell_color[1])
                    + 0.0722 * _to_python_float(cell_color[2])
                )

                text_color = (
                    "white" if luminance < REPORT_TEXT_LUMINANCE_THRESHOLD else "black"
                )

                axes.text(
                    column_index + 0.5,
                    row_index + 0.5,
                    f"{numeric_value:.{REPORT_DISPLAY_DECIMALS}f}",
                    ha="center",
                    va="center",
                    color=text_color,
                )

    figure.tight_layout()
    return figure


def plot_confusion_matrix(
    matrix: pd.DataFrame,
    *,
    title: str,
    normalized: bool,
) -> Figure:
    """Plot one persisted confusion matrix."""
    if matrix.empty:
        raise ValueError("Confusion matrix is empty.")

    values = matrix.to_numpy(dtype=float)

    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError(
            "Confusion matrix must be a non-empty square matrix.",
        )

    if normalized:
        if ((values < 0.0) | (values > 1.0)).any():
            raise ValueError(
                "Normalized confusion-matrix values must be within [0, 1].",
            )

        value_format = f".{REPORT_DISPLAY_DECIMALS}f"
        maximum_value = 1.0
        colorbar_label = "Rate"

        diagonal_values = np.diag(values)

        if not np.isfinite(diagonal_values).all():
            raise ValueError(
                "Normalized confusion-matrix diagonal values must be finite.",
            )

        minimum_diagonal_value = _to_python_float(
            diagonal_values.min(),
        )
        maximum_diagonal_value = _to_python_float(
            diagonal_values.max(),
        )

        diagonal_span = maximum_diagonal_value - minimum_diagonal_value

        minimum_padding = REPORT_MINIMUM_AXIS_SPAN / 2.0

        padding = max(
            diagonal_span * 0.10,
            minimum_padding,
        )

        minimum_value = max(
            0.0,
            minimum_diagonal_value - padding,
        )

        if minimum_value >= maximum_value:
            minimum_value = max(
                0.0,
                maximum_value - REPORT_MINIMUM_AXIS_SPAN,
            )

    else:
        if (values < 0.0).any():
            raise ValueError(
                "Confusion-matrix counts must not be negative.",
            )

        value_format = ".0f"
        minimum_value = 0.0

        maximum_value = _to_python_float(values.max()) if values.size else 1.0

        maximum_value = max(
            maximum_value,
            1.0,
        )

        colorbar_label = "Count"

    normalization = Normalize(
        vmin=minimum_value,
        vmax=maximum_value,
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_CONFUSION_MATRIX_FIGURE_SIZE,
    )

    sns.heatmap(
        matrix,
        ax=axes,
        cmap=CONTINUOUS_PALETTE,
        vmin=minimum_value,
        vmax=maximum_value,
        annot=False,
        cbar=True,
        cbar_kws={
            "label": colorbar_label,
        },
        square=False,
        xticklabels=[str(label) for label in matrix.columns],
        yticklabels=[str(label) for label in matrix.index],
    )

    axes.set_xlabel("Predicted class")
    axes.set_ylabel("Actual class")
    axes.set_title(title)

    axes.tick_params(
        axis="x",
        rotation=45,
    )

    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            cell_value = values[
                row_index,
                column_index,
            ]

            normalized_value = normalization(
                np.asarray(
                    [cell_value],
                    dtype=float,
                ),
            )

            cell_color = CONTINUOUS_PALETTE(
                normalized_value,
            )[0]

            luminance = (
                0.2126 * _to_python_float(cell_color[0])
                + 0.7152 * _to_python_float(cell_color[1])
                + 0.0722 * _to_python_float(cell_color[2])
            )

            text_color = (
                "white" if luminance < REPORT_TEXT_LUMINANCE_THRESHOLD else "black"
            )

            axes.text(
                column_index + 0.5,
                row_index + 0.5,
                format(
                    cell_value,
                    value_format,
                ),
                ha="center",
                va="center",
                color=text_color,
            )

    figure.tight_layout()
    return figure


# ----------------------------------------
# Table preparation
# ----------------------------------------


def _prepare_summary_table(
    summary: pd.DataFrame,
    seed_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare the main report-friendly test summary table."""
    frame = summary.copy()

    _validate_required_columns(
        frame,
        {
            DATASET_COLUMN,
            CLASSIFIER_COLUMN,
            "seed_count",
            *TEST_METRIC_COLUMNS,
        },
        table_name="summary",
    )

    result: dict[str, object] = {
        "Dataset": str(frame.iloc[0][DATASET_COLUMN]),
        "Classifier": _classifier_display_name(
            str(frame.iloc[0][CLASSIFIER_COLUMN]),
        ),
        "Seeds": int(frame.iloc[0]["seed_count"]),
    }

    seed_frame = seed_metrics.copy()
    for metric in TEST_METRIC_COLUMNS:
        values = pd.to_numeric(
            seed_frame[metric],
            errors="raise",
        ).to_numpy(dtype=float)
        mean = _to_python_float(np.mean(values))
        std = _to_python_float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        result[METRIC_DISPLAY_NAMES[metric]] = format_mean_std(
            mean,
            std,
        )

        stored_mean, stored_std = _parse_mean_std_string(
            str(frame.iloc[0][metric]),
        )
        if not np.isclose(mean, stored_mean, rtol=1e-10, atol=1e-12):
            raise ValueError(
                f"Summary artifact for {metric!r} does not match the "
                "seed-level test metrics.",
            )
        if not np.isclose(std, stored_std, rtol=1e-10, atol=1e-12):
            raise ValueError(
                f"Summary standard deviation for {metric!r} does not "
                "match the seed-level test metrics.",
            )

    return pd.DataFrame([result])


def _format_display_metric_value(value: object) -> str:
    """Format one validated numeric metric for notebook display."""
    numeric_value = cast(float, value)
    return f"{numeric_value:.{REPORT_DISPLAY_DECIMALS}f}"


def _prepare_seed_metrics_table(
    table: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare numeric per-seed test metrics for display."""
    result = table.copy()
    _validate_test_seed_metrics(result)

    result[SEED_COLUMN] = pd.to_numeric(
        result[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    result[CLASSIFIER_COLUMN] = result[CLASSIFIER_COLUMN].map(
        _classifier_display_name,
    )

    for metric in TEST_METRIC_COLUMNS:
        result[metric] = pd.to_numeric(
            result[metric],
            errors="raise",
        ).astype(float)

    display_columns = [
        "dataset",
        "classifier",
        "seed",
        CONFIGURATION_ID_COLUMN,
        *TEST_METRIC_COLUMNS,
    ]
    display_result = result[display_columns].copy()
    display_result = display_result.rename(
        columns={
            DATASET_COLUMN: "Dataset",
            CLASSIFIER_COLUMN: "Classifier",
            SEED_COLUMN: "Seed",
            CONFIGURATION_ID_COLUMN: "Configuration ID",
            **{metric: METRIC_DISPLAY_NAMES[metric] for metric in TEST_METRIC_COLUMNS},
        },
    )

    for metric_name in METRIC_DISPLAY_NAMES.values():
        if metric_name in display_result.columns:
            display_result[metric_name] = display_result[metric_name].map(
                _format_display_metric_value,
            )

    return display_result.reset_index(drop=True)


def _prepare_per_class_metrics_table(
    table: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare per-class metrics as mean ± std across test seeds."""
    result = table.copy()
    _validate_per_class_metrics(result)

    numeric_columns = [
        "precision",
        "recall",
        "f1",
        "support",
    ]
    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="raise",
        ).astype(float)

    rows: list[dict[str, object]] = []

    for (classifier_name, class_name), group in result.groupby(
        [CLASSIFIER_COLUMN, CLASS_COLUMN],
        sort=False,
    ):
        support_values = group["support"].to_numpy(dtype=float)
        if not np.allclose(
            support_values,
            support_values[0],
        ):
            raise ValueError(
                f"Test support for class {class_name!r} differs across seeds "
                f"for classifier {classifier_name!r}.",
            )

        row: dict[str, object] = {
            "Classifier": _classifier_display_name(
                str(classifier_name),
            ),
            "Class": str(class_name),
            "Support": round(_to_python_float(support_values[0])),
        }

        for metric in ("precision", "recall", "f1"):
            values = group[metric].to_numpy(dtype=float)
            mean = _to_python_float(np.mean(values))
            std = _to_python_float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            row[METRIC_DISPLAY_NAMES.get(metric, metric.title())] = format_mean_std(
                mean,
                std,
            )

        rows.append(row)

    return pd.DataFrame(rows).reset_index(drop=True)


def _prepare_timing_table(
    *,
    training_timing: pd.DataFrame,
    inference_timing: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare mean ± std computational timing across persisted seeds."""
    training = training_timing.copy()
    inference = inference_timing.copy()

    _validate_training_timing_columns(
        training,
    )
    _validate_inference_timing_columns(
        inference,
    )

    training[SEED_COLUMN] = pd.to_numeric(
        training[SEED_COLUMN],
        errors="raise",
    ).astype(int)
    inference[SEED_COLUMN] = pd.to_numeric(
        inference[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    training_seeds = tuple(
        sorted(int(seed) for seed in training[SEED_COLUMN].to_numpy(dtype=int))
    )
    inference_seeds = tuple(
        sorted(int(seed) for seed in inference[SEED_COLUMN].to_numpy(dtype=int))
    )

    if training_seeds != inference_seeds:
        raise ValueError(
            "Training and inference timing artifacts do not use the same seeds.",
        )

    dataset_values = {str(value) for value in training[DATASET_COLUMN]}
    classifier_values = {str(value) for value in training[CLASSIFIER_COLUMN]}

    if len(dataset_values) != 1 or len(classifier_values) != 1:
        raise ValueError(
            "Timing artifacts must belong to exactly one dataset and classifier.",
        )

    def summarize(
        frame: pd.DataFrame,
        column: str,
    ) -> str:
        values = pd.to_numeric(
            frame[column],
            errors="raise",
        ).to_numpy(dtype=float)
        mean = _to_python_float(np.mean(values))
        std = _to_python_float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        return format_mean_std(
            mean,
            std,
        )

    row: dict[str, object] = {
        "Dataset": next(iter(dataset_values)),
        "Classifier": _classifier_display_name(
            next(iter(classifier_values)),
        ),
        "Seeds": len(training_seeds),
        "Training time (s)": summarize(
            training,
            "training_time_seconds",
        ),
        "Prediction time (s)": summarize(
            inference,
            "prediction_time_seconds",
        ),
        "Probability time (s)": summarize(
            inference,
            "probability_time_seconds",
        ),
        "Inference time (s)": summarize(
            inference,
            "inference_time_seconds",
        ),
        "Inference / 100 samples (s)": summarize(
            inference,
            "inference_time_per_100_samples",
        ),
    }

    return pd.DataFrame([row])


def _prepare_selected_configuration_table(
    metadata: Mapping[str, object],
) -> pd.DataFrame:
    """Prepare the selected-configuration metadata for display."""
    selected_configuration = metadata.get("selected_configuration")

    if not isinstance(selected_configuration, dict):
        raise TypeError(
            "Test metadata does not contain a valid selected_configuration object.",
        )

    configuration_id = selected_configuration.get("configuration_id")
    parameters = selected_configuration.get("parameters")

    if not isinstance(configuration_id, str):
        raise TypeError(
            "Selected configuration metadata must contain a string configuration_id.",
        )
    if not isinstance(parameters, dict):
        raise TypeError(
            "Selected configuration metadata must contain a parameters mapping.",
        )

    row: dict[str, object] = {
        "Configuration ID": configuration_id,
    }

    for name, value in parameters.items():
        display_name = str(name).replace("classifier__", "")
        row[display_name] = value

    return pd.DataFrame([row])


def _build_validation_vs_test_table(
    artifacts: TestExperimentArtifacts,
) -> pd.DataFrame | None:
    """Build selected-configuration validation-versus-test metrics."""
    selected_configuration = artifacts.metadata.get(
        "selected_configuration",
    )
    if not isinstance(selected_configuration, dict):
        raise TypeError(
            "Test metadata is missing selected_configuration.",
        )

    configuration_id = selected_configuration.get("configuration_id")
    if not isinstance(configuration_id, str):
        raise TypeError(
            "Selected configuration metadata is missing configuration_id.",
        )

    validation_path = artifacts.directory / VALIDATION_SEED_RESULTS_FILE_NAME
    if not validation_path.is_file():
        return None

    validation = pd.read_csv(validation_path)

    required_columns = {
        CONFIGURATION_ID_COLUMN,
        SEED_COLUMN,
        *{f"mean_{metric}" for metric in TEST_METRIC_COLUMNS},
    }
    missing_columns = required_columns - set(validation.columns)
    if missing_columns:
        raise ValueError(
            "Validation seed results are missing columns required for the "
            f"validation-versus-test comparison: {sorted(missing_columns)!r}.",
        )

    selected_validation = validation[
        validation[CONFIGURATION_ID_COLUMN].astype(str) == configuration_id
    ].copy()

    if selected_validation.empty:
        raise ValueError(
            f"Selected configuration {configuration_id!r} was not found "
            "in validation seed results.",
        )

    selected_validation[SEED_COLUMN] = pd.to_numeric(
        selected_validation[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    test_seed_metrics = artifacts.seed_metrics.copy()
    test_seed_metrics[SEED_COLUMN] = pd.to_numeric(
        test_seed_metrics[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    merged = selected_validation.merge(
        test_seed_metrics,
        on=SEED_COLUMN,
        how="inner",
        suffixes=("_validation", "_test"),
        validate="one_to_one",
    )

    if len(merged) != len(selected_validation):
        raise ValueError(
            "Validation and test seed results do not contain the same seeds "
            "for the selected configuration.",
        )

    rows: list[dict[str, object]] = []

    for metric in TEST_METRIC_COLUMNS:
        validation_values = pd.to_numeric(
            merged[f"mean_{metric}"],
            errors="raise",
        ).to_numpy(dtype=float)
        test_values = pd.to_numeric(
            merged[metric],
            errors="raise",
        ).to_numpy(dtype=float)

        validation_mean = _to_python_float(np.mean(validation_values))
        validation_std = (
            _to_python_float(np.std(validation_values, ddof=1))
            if len(validation_values) > 1
            else 0.0
        )
        test_mean = _to_python_float(np.mean(test_values))
        test_std = (
            _to_python_float(np.std(test_values, ddof=1))
            if len(test_values) > 1
            else 0.0
        )

        rows.append(
            {
                "Metric": METRIC_DISPLAY_NAMES[metric],
                "validation_mean": validation_mean,
                "validation_std": validation_std,
                "test_mean": test_mean,
                "test_std": test_std,
                "Validation": format_mean_std(
                    validation_mean,
                    validation_std,
                ),
                "Test": format_mean_std(
                    test_mean,
                    test_std,
                ),
                "Test − validation": test_mean - validation_mean,
            },
        )

    return pd.DataFrame(rows)


# ----------------------------------------
# Artifact validation
# ----------------------------------------


def _get_required_experiment_training_row_count(
    metadata: Mapping[str, object],
) -> int:
    """Return and validate the full-training row count from experiment metadata."""
    value = metadata.get("training_row_count")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(
            "Experiment metadata must contain a positive integer 'training_row_count'.",
        )
    return value


def _get_required_test_row_count(
    metadata: Mapping[str, object],
) -> int:
    """Return and validate the frozen-test row count from test metadata."""
    value = metadata.get("test_row_count")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(
            "Test metadata must contain a positive integer 'test_row_count'.",
        )
    return value


def _validate_training_timing_columns(table: pd.DataFrame) -> None:
    """Validate the structural columns of the training-timing artifact."""
    _validate_required_columns(
        table,
        set(TRAINING_TIMING_COLUMNS),
        table_name="training_timing",
    )

    if table.empty:
        raise ValueError("training_timing is empty.")

    for column in ("training_time_seconds",):
        values = pd.to_numeric(
            table[column],
            errors="coerce",
        ).to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values <= 0.0).any():
            raise ValueError(
                f"training_timing.{column} contains non-positive or non-finite values.",
            )

    row_counts = pd.to_numeric(
        table["training_row_count"],
        errors="coerce",
    ).to_numpy(dtype=float)
    if (
        not np.isfinite(row_counts).all()
        or (row_counts < 1.0).any()
        or not np.allclose(
            row_counts,
            np.round(row_counts),
            rtol=0.0,
            atol=0.0,
        )
    ):
        raise ValueError(
            "training_timing.training_row_count must contain positive integer counts.",
        )


def _validate_inference_timing_columns(table: pd.DataFrame) -> None:
    """Validate the structural and arithmetic invariants of inference timing."""
    _validate_required_columns(
        table,
        set(INFERENCE_TIMING_COLUMNS),
        table_name="inference_timing",
    )

    if table.empty:
        raise ValueError("inference_timing is empty.")

    for column in (
        "prediction_time_seconds",
        "probability_time_seconds",
        "inference_time_seconds",
        "inference_time_per_100_samples",
    ):
        values = pd.to_numeric(
            table[column],
            errors="coerce",
        ).to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values <= 0.0).any():
            raise ValueError(
                f"inference_timing.{column} contains non-positive "
                "or non-finite values.",
            )

    prediction_times = pd.to_numeric(
        table["prediction_time_seconds"],
        errors="raise",
    ).to_numpy(dtype=float)
    probability_times = pd.to_numeric(
        table["probability_time_seconds"],
        errors="raise",
    ).to_numpy(dtype=float)
    total_times = pd.to_numeric(
        table["inference_time_seconds"],
        errors="raise",
    ).to_numpy(dtype=float)

    if not np.allclose(
        prediction_times + probability_times,
        total_times,
        rtol=1e-10,
        atol=1e-12,
    ):
        raise ValueError(
            "inference_timing total does not equal prediction plus probability time.",
        )

    row_counts = pd.to_numeric(
        table["test_row_count"],
        errors="raise",
    ).to_numpy(dtype=float)
    persisted_per_100 = pd.to_numeric(
        table["inference_time_per_100_samples"],
        errors="raise",
    ).to_numpy(dtype=float)

    if (
        not np.isfinite(row_counts).all()
        or (row_counts < 1.0).any()
        or not np.allclose(
            row_counts,
            np.round(row_counts),
            rtol=0.0,
            atol=0.0,
        )
    ):
        raise ValueError(
            "inference_timing.test_row_count must contain positive integer counts.",
        )

    expected_per_100 = total_times / row_counts * 100.0
    if not np.allclose(
        expected_per_100,
        persisted_per_100,
        rtol=1e-10,
        atol=1e-12,
    ):
        raise ValueError(
            "inference_timing per-100-sample values are inconsistent "
            "with total inference time.",
        )


def _validate_training_timing_metadata(
    *,
    metadata: Mapping[str, object],
    dataset_name: str,
    classifier_name: str,
    configuration_id: str,
    expected_seeds: Sequence[int],
    training_row_count: int,
) -> None:
    """Validate provenance metadata for final-model training timing."""
    expected_fields = {
        "schema_version": TRAINING_TIMING_SCHEMA_VERSION,
        "dataset_name": dataset_name,
        "classifier_name": classifier_name,
        "configuration_id": configuration_id,
        "operation": TRAINING_TIMING_OPERATION,
        "clock": TRAINING_TIMING_CLOCK,
        "scope": TRAINING_TIMING_SCOPE,
        "timing_file": TRAINING_TIMING_FILE_NAME,
        "training_row_count": training_row_count,
        "seed_count": len(tuple(expected_seeds)),
    }

    for key, expected_value in expected_fields.items():
        if metadata.get(key) != expected_value:
            raise ValueError(
                f"Training-timing metadata field {key!r} does not match "
                f"the expected experiment value {expected_value!r}.",
            )

    metadata_seeds = metadata.get("seeds")
    if _parse_integer_sequence(
        metadata_seeds,
        field_name="training_timing.seeds",
    ) != tuple(sorted(int(seed) for seed in expected_seeds)):
        raise ValueError(
            "Training-timing metadata seeds do not match the test experiment.",
        )


def _validate_inference_timing_metadata(
    *,
    metadata: Mapping[str, object],
    dataset_name: str,
    classifier_name: str,
    expected_configuration_ids: Sequence[str],
    expected_seeds: Sequence[int],
    test_row_count: int,
) -> None:
    """Validate provenance metadata for frozen-test inference timing."""
    expected_configuration_set = {str(value) for value in expected_configuration_ids}
    expected_seed_tuple = tuple(sorted(int(seed) for seed in expected_seeds))

    expected_fields = {
        "schema_version": pipeline_test.INFERENCE_TIMING_SCHEMA_VERSION,
        "dataset_name": dataset_name,
        "classifier_name": classifier_name,
        "evaluation_type": "frozen_test_set",
        "operation": pipeline_test.INFERENCE_TIMING_OPERATION,
        "clock": pipeline_test.INFERENCE_TIMING_CLOCK,
        "scope": pipeline_test.INFERENCE_TIMING_SCOPE,
        "timing_file": INFERENCE_TIMING_FILE_NAME,
        "test_row_count": test_row_count,
        "seed_count": len(expected_seed_tuple),
        "metric_calculation_included": False,
        "model_loading_included": False,
        "artifact_writing_included": False,
        "inference_time_definition": "prediction_time_seconds + probability_time_seconds",
    }

    for key, expected_value in expected_fields.items():
        if metadata.get(key) != expected_value:
            raise ValueError(
                f"Inference-timing metadata field {key!r} does not match "
                f"the expected experiment value {expected_value!r}.",
            )

    metadata_configuration_ids = _parse_string_set(
        metadata.get("configuration_ids"),
        field_name="inference_timing.configuration_ids",
    )
    if metadata_configuration_ids != expected_configuration_set:
        raise ValueError(
            "Inference-timing metadata configuration IDs do not match "
            "the selected experiment configuration.",
        )

    metadata_seeds = _parse_integer_sequence(
        metadata.get("seeds"),
        field_name="inference_timing.seeds",
    )
    if metadata_seeds != expected_seed_tuple:
        raise ValueError(
            "Inference-timing metadata seeds do not match the test experiment.",
        )


def _validate_inference_timing_frame(
    *,
    timing_data: pd.DataFrame,
    dataset_name: str,
    classifier_name: str,
    expected_configuration_ids: Sequence[str],
    expected_seeds: Sequence[int],
    test_row_count: int,
) -> None:
    """Validate the persisted frozen-test inference timings against the experiment."""
    _validate_inference_timing_columns(
        timing_data,
    )

    if set(str(value) for value in timing_data[DATASET_COLUMN]) != {dataset_name}:
        raise ValueError(
            "Inference-timing artifact contains an unexpected dataset.",
        )

    if set(str(value) for value in timing_data[CLASSIFIER_COLUMN]) != {classifier_name}:
        raise ValueError(
            "Inference-timing artifact contains an unexpected classifier.",
        )

    configuration_ids = {str(value) for value in timing_data[CONFIGURATION_ID_COLUMN]}
    if configuration_ids != {str(value) for value in expected_configuration_ids}:
        raise ValueError(
            "Inference-timing artifact contains unexpected configuration IDs.",
        )

    seed_values = pd.to_numeric(
        timing_data[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    if seed_values.duplicated().any():
        raise ValueError(
            "Inference-timing artifact contains duplicate seed rows.",
        )

    expected_seed_set = {int(seed) for seed in expected_seeds}
    if set(int(seed) for seed in seed_values) != expected_seed_set:
        raise ValueError(
            "Inference-timing artifact seeds do not match the test experiment.",
        )

    test_row_counts = pd.to_numeric(
        timing_data["test_row_count"],
        errors="raise",
    ).astype(int)
    if set(int(value) for value in test_row_counts) != {int(test_row_count)}:
        raise ValueError(
            "Inference-timing artifact contains an unexpected test row count.",
        )


def _validate_test_seed_metrics(table: pd.DataFrame) -> None:
    _validate_required_columns(
        table,
        {
            DATASET_COLUMN,
            CLASSIFIER_COLUMN,
            SEED_COLUMN,
            CONFIGURATION_ID_COLUMN,
            *TEST_METRIC_COLUMNS,
        },
        table_name="test_seed_metrics",
    )

    if table.empty:
        raise ValueError("test_seed_metrics is empty.")

    if (
        table[[DATASET_COLUMN, CLASSIFIER_COLUMN, CONFIGURATION_ID_COLUMN]]
        .isna()
        .any()
        .any()
    ):
        raise ValueError(
            "test_seed_metrics contains missing dataset, classifier, or "
            "configuration identifiers.",
        )

    normalized_seeds = pd.to_numeric(
        table[SEED_COLUMN],
        errors="coerce",
    )
    if normalized_seeds.isna().any():
        raise ValueError("test_seed_metrics contains invalid seed values.")
    if normalized_seeds.duplicated().any():
        raise ValueError("test_seed_metrics contains duplicate seed rows.")

    for metric in TEST_METRIC_COLUMNS:
        _validate_numeric_metric_column(
            table,
            metric,
            table_name="test_seed_metrics",
        )


def _validate_per_class_metrics(table: pd.DataFrame) -> None:
    _validate_required_columns(
        table,
        {
            SEED_COLUMN,
            CONFIGURATION_ID_COLUMN,
            CLASS_COLUMN,
            "precision",
            "recall",
            "f1",
            "support",
            CLASSIFIER_COLUMN,
        },
        table_name="test_per_class_metrics",
    )

    if table.empty:
        raise ValueError("test_per_class_metrics is empty.")

    if (
        table[
            [
                CLASSIFIER_COLUMN,
                CONFIGURATION_ID_COLUMN,
                CLASS_COLUMN,
            ]
        ]
        .isna()
        .any()
        .any()
    ):
        raise ValueError(
            "test_per_class_metrics contains missing classifier, configuration, "
            "or class identifiers.",
        )

    if table[[SEED_COLUMN, CLASS_COLUMN]].duplicated().any():
        raise ValueError(
            "test_per_class_metrics contains duplicate seed/class rows.",
        )

    normalized_support = pd.to_numeric(
        table["support"],
        errors="coerce",
    )
    if normalized_support.isna().any():
        raise ValueError(
            "test_per_class_metrics.support contains non-numeric values.",
        )

    support_array = normalized_support.to_numpy(dtype=float)
    if not np.allclose(support_array, np.round(support_array)):
        raise ValueError(
            "test_per_class_metrics.support must contain integer counts.",
        )

    for metric in ("precision", "recall", "f1"):
        _validate_numeric_metric_column(
            table,
            metric,
            table_name="test_per_class_metrics",
        )

    support = pd.to_numeric(
        table["support"],
        errors="coerce",
    ).to_numpy(dtype=float)
    if not np.isfinite(support).all() or (support < 0.0).any():
        raise ValueError(
            "test_per_class_metrics.support contains invalid values.",
        )


def _validate_summary(table: pd.DataFrame) -> None:
    _validate_required_columns(
        table,
        {
            DATASET_COLUMN,
            CLASSIFIER_COLUMN,
            "seed_count",
            *TEST_METRIC_COLUMNS,
        },
        table_name="test_summary",
    )

    if len(table) != 1:
        raise ValueError(
            "test_summary must contain exactly one row.",
        )

    seed_count = pd.to_numeric(
        table.iloc[0]["seed_count"],
        errors="coerce",
    )
    if (
        pd.isna(seed_count)
        or _to_python_float(seed_count) < 1.0
        or _to_python_float(seed_count) % 1.0 != 0.0
    ):
        raise ValueError(
            "test_summary.seed_count must be a positive integer.",
        )

    for metric in TEST_METRIC_COLUMNS:
        _parse_mean_std_string(
            str(table.iloc[0][metric]),
        )


def _validate_confusion_matrices(
    *,
    matrices: Mapping[int, pd.DataFrame],
    seed_metrics: pd.DataFrame,
    normalized: bool,
) -> None:
    expected_seeds = {
        int(seed)
        for seed in pd.to_numeric(
            seed_metrics[SEED_COLUMN],
            errors="raise",
        )
    }

    if set(matrices) != expected_seeds:
        raise ValueError(
            f"{'Normalized ' if normalized else ''}confusion matrices do not "
            "match the seed metrics artifact seeds.",
        )

    for seed, matrix in matrices.items():
        if matrix.empty:
            raise ValueError(
                f"Confusion matrix for seed {seed} is empty.",
            )
        values = matrix.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(
                f"Confusion matrix for seed {seed} contains non-finite values.",
            )

        if values.ndim != 2 or values.shape[0] != values.shape[1]:
            raise ValueError(
                f"Confusion matrix for seed {seed} must be square.",
            )

        if list(matrix.index.astype(str)) != list(matrix.columns.astype(str)):
            raise ValueError(
                f"Confusion matrix for seed {seed} must use the same class "
                "labels for rows and columns in the same order.",
            )

        if len(set(matrix.index.astype(str))) != len(matrix.index):
            raise ValueError(
                f"Confusion matrix for seed {seed} contains duplicate class labels.",
            )

        if normalized:
            if ((values < 0.0) | (values > 1.0)).any():
                raise ValueError(
                    f"Normalized confusion matrix for seed {seed} contains "
                    "values outside [0, 1].",
                )
        else:
            if (values < 0.0).any():
                raise ValueError(
                    f"Confusion matrix for seed {seed} contains negative counts.",
                )
            if not np.allclose(values, np.round(values), rtol=0.0, atol=0.0):
                raise ValueError(
                    f"Confusion matrix for seed {seed} must contain integer counts.",
                )


def _validate_confusion_matrix_pairs(
    *,
    raw_matrices: Mapping[int, pd.DataFrame],
    normalized_matrices: Mapping[int, pd.DataFrame],
) -> None:
    """Ensure raw and normalized matrices describe the same class order."""
    if set(raw_matrices) != set(normalized_matrices):
        raise ValueError(
            "Raw and normalized confusion-matrix artifacts do not contain "
            "the same seeds.",
        )

    for seed in raw_matrices:
        raw = raw_matrices[seed]
        normalized = normalized_matrices[seed]
        raw_index = tuple(str(value) for value in raw.index)
        normalized_index = tuple(str(value) for value in normalized.index)

        if raw_index != normalized_index:
            raise ValueError(
                f"Raw and normalized confusion matrices for seed {seed} "
                "do not use the same class order.",
            )


def _parse_integer_sequence(
    value: object,
    *,
    field_name: str,
) -> tuple[int, ...]:
    """Validate and normalize a metadata sequence of integer values."""
    if not isinstance(value, (list, tuple)):
        raise TypeError(
            f"Test metadata field {field_name!r} must be a list or tuple.",
        )

    normalized_values: list[int] = []

    for item in value:
        if isinstance(item, bool):
            raise TypeError(
                f"Test metadata field {field_name!r} contains an invalid "
                "boolean value.",
            )

        if isinstance(item, int):
            normalized_values.append(item)
            continue

        if isinstance(item, str):
            try:
                normalized_values.append(int(item))
            except ValueError as error:
                raise ValueError(
                    f"Test metadata field {field_name!r} contains a non-integer "
                    f"value: {item!r}."
                ) from error
            continue

        raise ValueError(
            f"Test metadata field {field_name!r} contains an unsupported "
            f"value: {item!r}.",
        )

    return tuple(sorted(normalized_values))


def _parse_string_set(
    value: object,
    *,
    field_name: str,
) -> set[str]:
    """Validate and normalize a metadata sequence of string identifiers."""
    if not isinstance(value, (list, tuple)):
        raise TypeError(
            f"Test metadata field {field_name!r} must be a list or tuple.",
        )

    if not all(isinstance(item, str) for item in value):
        raise ValueError(
            f"Test metadata field {field_name!r} must contain only strings.",
        )

    return set(value)


def _validate_identity(
    *,
    metadata: Mapping[str, object],
    dataset_name: str,
    classifier_name: str,
    seed_metrics: pd.DataFrame,
    per_class_metrics: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    if metadata.get("dataset_name") != dataset_name:
        raise ValueError(
            "Test-evaluation metadata dataset does not match the artifact path."
        )

    if metadata.get("classifier_name") != classifier_name:
        raise ValueError(
            "Test-evaluation metadata classifier does not match the artifact path."
        )

    if metadata.get("evaluation_type") != "frozen_test_set":
        raise ValueError(
            "Test-evaluation metadata does not identify a frozen test-set evaluation.",
        )

    if summary.iloc[0][DATASET_COLUMN] != dataset_name:
        raise ValueError(
            "Test summary dataset does not match the requested dataset.",
        )

    if summary.iloc[0][CLASSIFIER_COLUMN] != classifier_name:
        raise ValueError(
            "Test summary classifier does not match the requested classifier.",
        )

    artifact_seed_values = pd.to_numeric(
        seed_metrics[SEED_COLUMN],
        errors="raise",
    ).astype(int)
    if artifact_seed_values.duplicated().any():
        raise ValueError(
            "test_seed_metrics contains duplicate seed rows.",
        )

    artifact_seeds = tuple(sorted(int(seed) for seed in artifact_seed_values))

    metadata_seeds_raw = metadata.get("seeds")
    if metadata_seeds_raw is not None:
        metadata_seeds = _parse_integer_sequence(
            metadata_seeds_raw,
            field_name="seeds",
        )
        if metadata_seeds != artifact_seeds:
            raise ValueError(
                "Test metadata seeds do not match the test seed-metrics artifact.",
            )

    metadata_seed_count = metadata.get("seed_count")
    if metadata_seed_count is not None:
        if isinstance(metadata_seed_count, bool) or not isinstance(
            metadata_seed_count, int
        ):
            raise ValueError(
                "Test metadata field 'seed_count' must be an integer.",
            )
        if metadata_seed_count != len(artifact_seeds):
            raise ValueError(
                "Test metadata seed_count does not match the test seed-metrics "
                "artifact.",
            )

    metadata_test_row_count = metadata.get("test_row_count")
    if metadata_test_row_count is not None:
        if not isinstance(metadata_test_row_count, int):
            raise ValueError(
                "Test metadata field 'test_row_count' must be an integer.",
            )
        if metadata_test_row_count < 1:
            raise ValueError(
                "Test metadata field 'test_row_count' must be positive.",
            )

    configuration_ids = {str(value) for value in seed_metrics[CONFIGURATION_ID_COLUMN]}
    if len(configuration_ids) != 1:
        raise ValueError(
            "test_seed_metrics must contain exactly one configuration ID.",
        )

    per_class_configuration_ids = {
        str(value) for value in per_class_metrics[CONFIGURATION_ID_COLUMN]
    }
    if per_class_configuration_ids != configuration_ids:
        raise ValueError(
            "test_per_class_metrics configuration ID does not match test_seed_metrics.",
        )

    per_class_classifier_values = {
        str(value) for value in per_class_metrics[CLASSIFIER_COLUMN]
    }
    if per_class_classifier_values != {classifier_name}:
        raise ValueError(
            "test_per_class_metrics classifier does not match the requested "
            "classifier.",
        )

    per_class_seed_values = pd.to_numeric(
        per_class_metrics[SEED_COLUMN],
        errors="raise",
    ).astype(int)
    if set(per_class_seed_values) != set(artifact_seeds):
        raise ValueError(
            "test_per_class_metrics seeds do not match test_seed_metrics.",
        )

    metadata_configuration_ids_raw = metadata.get("configuration_ids")
    if metadata_configuration_ids_raw is not None:
        metadata_configuration_ids = _parse_string_set(
            metadata_configuration_ids_raw,
            field_name="configuration_ids",
        )
        if metadata_configuration_ids != configuration_ids:
            raise ValueError(
                "Test metadata configuration_ids do not match the test "
                "seed-metrics artifact.",
            )

    selected_configuration = metadata.get("selected_configuration")
    if not isinstance(selected_configuration, dict):
        raise TypeError(
            "Experiment metadata does not contain a valid "
            "selected_configuration object.",
        )

    selected_configuration_id = selected_configuration.get("configuration_id")
    if not isinstance(selected_configuration_id, str):
        raise TypeError(
            "Selected configuration metadata must contain a string configuration_id.",
        )

    if selected_configuration_id not in configuration_ids:
        raise ValueError(
            "Selected configuration ID does not match the test seed-metrics "
            "configuration ID.",
        )


# ----------------------------------------
# Low-level helpers
# ----------------------------------------


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required JSON artifact does not exist: '{path}'.",
        )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
        )
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Could not load JSON artifact '{path}'.",
        ) from error

    if not isinstance(value, dict):
        raise TypeError(
            f"JSON artifact '{path}' must contain an object.",
        )

    return dict(value)


def _load_csv(path: Path) -> pd.DataFrame:
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


def _load_confusion_matrices(
    directory: Path,
    *,
    normalized_prefix: str,
) -> dict[int, pd.DataFrame]:
    matrices: dict[int, pd.DataFrame] = {}

    for path in sorted(directory.glob(f"{normalized_prefix}*.csv")):
        seed_text = path.stem.removeprefix(normalized_prefix)
        if not seed_text.isdigit():
            raise ValueError(
                f"Invalid confusion-matrix artifact filename: '{path.name}'.",
            )
        matrices[int(seed_text)] = pd.read_csv(
            path,
            index_col=0,
        )

    return dict(sorted(matrices.items()))


def _validate_required_columns(
    table: pd.DataFrame,
    required_columns: set[str],
    *,
    table_name: str,
) -> None:
    missing_columns = required_columns - set(table.columns)
    if missing_columns:
        raise ValueError(
            f"{table_name} is missing required columns: {sorted(missing_columns)!r}.",
        )


def _validate_numeric_metric_column(
    table: pd.DataFrame,
    column: str,
    *,
    table_name: str,
) -> None:
    values = pd.to_numeric(
        table[column],
        errors="coerce",
    ).to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(
            f"{table_name}.{column} contains non-finite or non-numeric values.",
        )

    if column == "mcc":
        if ((values < -1.0) | (values > 1.0)).any():
            raise ValueError(
                f"{table_name}.{column} values must be within [-1, 1].",
            )
    elif ((values < 0.0) | (values > 1.0)).any():
        raise ValueError(
            f"{table_name}.{column} values must be within [0, 1].",
        )


def _validate_metric_frame(
    table: pd.DataFrame,
    *,
    columns: Sequence[str],
    table_name: str,
) -> None:
    for column in columns:
        if column not in table:
            raise ValueError(
                f"{table_name} is missing metric column {column!r}.",
            )
        _validate_numeric_metric_column(
            table,
            column,
            table_name=table_name,
        )


def _parse_mean_std_string(value: str) -> tuple[float, float]:
    parts = value.split(" ± ")
    if len(parts) != 2:
        raise ValueError(
            f"Expected a 'mean ± std' value, got {value!r}.",
        )

    try:
        mean = _to_python_float(parts[0])
        std = _to_python_float(parts[1])
    except ValueError as error:
        raise ValueError(
            f"Invalid mean ± std value: {value!r}.",
        ) from error

    if not np.isfinite(mean) or not np.isfinite(std):
        raise ValueError(
            f"Mean ± std value must be finite: {value!r}.",
        )

    if std < 0.0:
        raise ValueError(
            f"Standard deviation must not be negative: {value!r}.",
        )

    return mean, std


def _classifier_display_name(classifier_name: str) -> str:
    return CLASSIFIER_DISPLAY_NAMES.get(
        classifier_name,
        classifier_name.replace("_", " ").title(),
    )


def _normalize_classifier_name(classifier_name: object) -> str:
    """Normalize a classifier key or display label to its canonical key."""
    value = str(classifier_name).strip()

    if value in CLASSIFIER_DISPLAY_NAMES:
        return value

    normalized_display = value.casefold()
    for key, display_name in CLASSIFIER_DISPLAY_NAMES.items():
        if normalized_display == display_name.casefold():
            return key

    return value.casefold().replace(" ", "_")


def _display_section(
    *,
    title: str,
    table: pd.DataFrame,
) -> None:
    display(
        HTML(
            f"<h3>{title}</h3>",
        ),
    )
    display(table)


__all__ = [
    "CLASSIFIER_DISPLAY_NAMES",
    "CLASSIFIER_ORDER",
    "DATASET_ORDER",
    "DEFAULT_ARTIFACTS_DIRECTORY",
    "DEFAULT_FEATURE_IMPORTANCE_TOP_N",
    "METRIC_DISPLAY_NAMES",
    "PRIMARY_TEST_METRIC",
    "REPORT_DISPLAY_DECIMALS",
    "TEST_METRIC_COLUMNS",
    "TestExperimentArtifacts",
    "TestStatistics",
    "compile_all_test_statistics",
    "compile_all_test_summary_table",
    "compile_all_test_timing_table",
    "compile_dataset_feature_importances",
    "compile_test_statistics",
    "display_all_test_confusion_matrices",
    "display_test_confusion_matrices",
    "display_test_statistics",
    "load_all_test_experiment_artifacts",
    "load_dataset_feature_importances",
    "load_test_experiment_artifacts",
    "plot_confusion_matrix",
    "plot_dataset_feature_importance_heatmap",
    "plot_dataset_feature_importances",
    "plot_metric_comparison",
    "plot_per_class_metric_heatmap",
    "plot_test_seed_metric",
    "prepare_dataset_feature_importance_table",
]
