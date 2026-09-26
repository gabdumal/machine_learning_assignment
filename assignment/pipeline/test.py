"""Final evaluation of persisted models on frozen test sets.

This module does not train or tune models. It loads the seed-specific final
models already persisted by the validation phase, evaluates them on the
existing transformed test partitions, and persists test-evaluation results.

Run from the project root, for example:

    python -m pipeline.test
    python -m pipeline.test --dataset genis
    python -m pipeline.test --dataset rosids --classifier xgboost
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize

from definitions import SEEDS
from pipeline.common import (
    ARTIFACT_ROOT,
    ARTIFACT_SCHEMA_VERSION,
    FittedClassificationModel,
    load_experiment_metadata,
    load_final_models,
)
from pipeline.genis import GENIS_X_TEST, GENIS_Y_TEST
from pipeline.rosids import ROSIDS_X_TEST, ROSIDS_Y_TEST

# ----------------------------------------
# Constants
# ----------------------------------------

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

CLASSIFIER_NAMES: Final[tuple[str, ...]] = (
    "decision_tree",
    "random_forest",
    "xgboost",
)

# Numeric CSV artifacts use one project-wide precision convention.
TEST_FLOAT_FORMAT: Final[str] = "%.12g"

# ``test_summary.csv`` stores human-readable ``mean ± std`` strings. The
# numeric values embedded in those strings use the same 12-significant-digit
# convention as the numeric CSV artifacts. The reporting layer performs
# final display rounding.
TEST_SUMMARY_FLOAT_FORMAT: Final[str] = ".12g"

# XGBoost may expose float32 probabilities. Their row sums can therefore
# differ from exactly 1.0 by a few float32 ulps. This tolerance validates
# the probability distribution without rejecting valid model output solely
# because of single-precision rounding.
PROBABILITY_SUM_ATOL: Final[float] = 1e-6

DATASET_CONFIGURATIONS: Final[dict[str, tuple[str, pd.DataFrame, pd.Series]]] = {
    "genis": (
        "GENIS",
        GENIS_X_TEST,
        GENIS_Y_TEST,
    ),
    "rosids": (
        "ROSIDS",
        ROSIDS_X_TEST,
        ROSIDS_Y_TEST,
    ),
}


# ----------------------------------------
# Metric helpers
# ----------------------------------------


def _encode_target_labels(
    *,
    target: pd.Series,
    classes: Sequence[str],
) -> np.ndarray:
    """Encode labels using the persisted model class order."""
    class_to_index = {str(label): index for index, label in enumerate(classes)}

    encoded: list[int] = []
    unknown_labels: set[str] = set()

    for label in target:
        normalized_label = str(label)
        class_index = class_to_index.get(normalized_label)

        if class_index is None:
            unknown_labels.add(normalized_label)
        else:
            encoded.append(class_index)

    if unknown_labels:
        raise ValueError(
            "The test target contains labels that are absent from the "
            f"persisted model classes: {sorted(unknown_labels)!r}.",
        )

    return np.asarray(
        encoded,
        dtype=np.int64,
    )


def _calculate_roc_auc(
    *,
    encoded_target: np.ndarray,
    probabilities: np.ndarray,
) -> float:
    """Calculate macro ROC-AUC using the validation convention."""
    class_count = probabilities.shape[1]

    if class_count == 2:
        return float(
            roc_auc_score(
                encoded_target,
                probabilities[:, 1],
            ),
        )

    return float(
        roc_auc_score(
            encoded_target,
            probabilities,
            multi_class="ovr",
            average="macro",
            labels=np.arange(class_count),
        ),
    )


def _calculate_pr_auc(
    *,
    encoded_target: np.ndarray,
    probabilities: np.ndarray,
) -> float:
    """Calculate macro PR-AUC using the validation convention."""
    class_count = probabilities.shape[1]

    if class_count == 2:
        return float(
            average_precision_score(
                encoded_target,
                probabilities[:, 1],
            ),
        )

    binary_targets = label_binarize(
        encoded_target,
        classes=np.arange(class_count),
    )

    return float(
        average_precision_score(
            binary_targets,
            probabilities,
            average="macro",
        ),
    )


def _calculate_test_metrics(
    *,
    actual_labels: np.ndarray,
    predicted_labels: np.ndarray,
    encoded_target: np.ndarray,
    probabilities: np.ndarray,
) -> dict[str, float]:
    """Calculate all scalar metrics used during validation."""
    metrics = {
        "accuracy": accuracy_score(
            actual_labels,
            predicted_labels,
        ),
        "precision": precision_score(
            actual_labels,
            predicted_labels,
            average="macro",
            zero_division=0,
        ),
        "recall": recall_score(
            actual_labels,
            predicted_labels,
            average="macro",
            zero_division=0,
        ),
        "macro_f1": f1_score(
            actual_labels,
            predicted_labels,
            average="macro",
            zero_division=0,
        ),
        "roc_auc": _calculate_roc_auc(
            encoded_target=encoded_target,
            probabilities=probabilities,
        ),
        "pr_auc": _calculate_pr_auc(
            encoded_target=encoded_target,
            probabilities=probabilities,
        ),
        "mcc": matthews_corrcoef(
            actual_labels,
            predicted_labels,
        ),
        "balanced_accuracy": balanced_accuracy_score(
            actual_labels,
            predicted_labels,
        ),
    }

    result = {name: float(value) for name, value in metrics.items()}

    missing_metrics = set(TEST_METRIC_COLUMNS) - set(result)
    if missing_metrics:
        raise RuntimeError(
            f"Test metrics were not calculated: {sorted(missing_metrics)!r}.",
        )

    return result


def _build_per_class_metrics(
    *,
    actual_labels: np.ndarray,
    predicted_labels: np.ndarray,
    classes: Sequence[str],
    seed: int,
    configuration_id: str,
    classifier_name: str,
) -> pd.DataFrame:
    """Build a per-class precision/recall/F1 table."""
    precision, recall, f1, support = precision_recall_fscore_support(
        actual_labels,
        predicted_labels,
        labels=list(classes),
        zero_division=0,
    )

    return pd.DataFrame(
        {
            "seed": np.full(
                len(classes),
                seed,
                dtype=np.int64,
            ),
            "configuration_id": np.full(
                len(classes),
                configuration_id,
                dtype=object,
            ),
            "classifier": np.full(
                len(classes),
                classifier_name,
                dtype=object,
            ),
            "class": list(classes),
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        },
    )


# ----------------------------------------
# Artifact checks
# ----------------------------------------


def _get_metadata_feature_labels(
    *,
    metadata: dict[str, object],
    key: str,
) -> tuple[str, ...]:
    """Return a validated feature-label tuple from experiment metadata."""
    value = metadata.get(key)

    if value is None:
        return ()

    if not isinstance(value, (list, tuple)):
        raise TypeError(
            f"Experiment metadata field {key!r} must be a list or tuple.",
        )

    if not all(isinstance(label, str) for label in value):
        raise ValueError(
            f"Experiment metadata field {key!r} must contain only strings.",
        )

    return tuple(value)


def _validate_experiment_artifacts(
    *,
    artifact_directory: Path,
    dataset_name: str,
    classifier_name: str,
    models: dict[int, FittedClassificationModel],
) -> dict[str, object]:
    """Verify that persisted models belong to the requested experiment."""
    metadata = load_experiment_metadata(
        artifact_directory,
    )

    metadata_schema_version = metadata.get("schema_version")
    if metadata_schema_version != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported experiment artifact schema: "
            f"expected {ARTIFACT_SCHEMA_VERSION!r}, "
            f"found {metadata_schema_version!r}.",
        )

    if metadata.get("status") != "complete":
        raise ValueError(
            f"Experiment artifacts at '{artifact_directory}' are not "
            "marked as complete.",
        )

    if metadata.get("dataset_name") != dataset_name:
        raise ValueError(
            f"Expected dataset '{dataset_name}', but metadata contains "
            f"{metadata.get('dataset_name')!r}.",
        )

    if metadata.get("classifier_name") != classifier_name:
        raise ValueError(
            f"Expected classifier '{classifier_name}', but metadata contains "
            f"{metadata.get('classifier_name')!r}.",
        )

    selected_configuration = metadata.get(
        "selected_configuration",
    )
    if not isinstance(selected_configuration, dict):
        raise TypeError(
            "Experiment metadata does not contain a valid "
            "'selected_configuration' object.",
        )

    selected_configuration_id = selected_configuration.get(
        "configuration_id",
    )
    if not isinstance(selected_configuration_id, str):
        raise TypeError(
            "Selected configuration does not contain a valid 'configuration_id'.",
        )

    metadata_seeds = metadata.get(
        "cross_validation_seeds",
    )
    if metadata_seeds is None:
        expected_seeds = tuple(int(seed) for seed in SEEDS)
    else:
        if not isinstance(metadata_seeds, (list, tuple)):
            raise TypeError(
                "Experiment metadata field 'cross_validation_seeds' must "
                "be a list or tuple.",
            )
        expected_seeds = tuple(int(seed) for seed in metadata_seeds)

    if not expected_seeds:
        raise ValueError(
            "The experiment metadata does not contain any validation seeds.",
        )

    if len(expected_seeds) != len(set(expected_seeds)):
        raise ValueError(
            "Experiment metadata contains duplicate validation seeds.",
        )

    expected_seed_set = set(expected_seeds)
    actual_seed_set = set(models)

    missing_seeds = expected_seed_set - actual_seed_set
    unexpected_seeds = actual_seed_set - expected_seed_set

    if missing_seeds:
        raise FileNotFoundError(
            f"Missing final models for seeds: {sorted(missing_seeds)!r}.",
        )

    if unexpected_seeds:
        raise ValueError(
            "Found persisted model seeds that are not part of this "
            f"experiment: {sorted(unexpected_seeds)!r}.",
        )

    reference_classes: tuple[str, ...] | None = None

    for seed, model in models.items():
        if model.seed != seed:
            raise ValueError(
                f"Persisted model seed mismatch: filename seed={seed}, "
                f"model seed={model.seed}.",
            )

        if model.configuration_id != selected_configuration_id:
            raise ValueError(
                f"Seed {seed} model uses configuration "
                f"{model.configuration_id!r}, but metadata selects "
                f"{selected_configuration_id!r}.",
            )

        model_classes = tuple(str(label) for label in model.classes)
        if not model_classes:
            raise ValueError(
                f"Persisted model for seed {seed} contains no target classes.",
            )

        if len(set(model_classes)) != len(model_classes):
            raise ValueError(
                f"Persisted model for seed {seed} contains duplicate target classes.",
            )

        if reference_classes is None:
            reference_classes = model_classes
        elif model_classes != reference_classes:
            raise ValueError(
                "Persisted final models do not use the same target-class order: "
                f"seed {seed} has {model_classes!r}, expected "
                f"{reference_classes!r}.",
            )

    return metadata


# ----------------------------------------
# One saved model
# ----------------------------------------


def _evaluate_seed(
    *,
    model: FittedClassificationModel,
    classifier_name: str,
    test_features: pd.DataFrame,
    test_target: pd.Series,
) -> tuple[dict[str, float], pd.DataFrame, np.ndarray]:
    """Evaluate one already-fitted seed-specific model."""
    actual_labels = np.asarray(
        test_target.astype(str),
        dtype=object,
    )

    predicted_labels = np.asarray(
        model.predict(test_features).astype(str),
        dtype=object,
    )

    probabilities = np.asarray(
        model.predict_proba(test_features),
        dtype=float,
    )

    if len(predicted_labels) != len(actual_labels):
        raise ValueError(
            "Prediction count does not match test-target count: "
            f"{len(predicted_labels)} != {len(actual_labels)}.",
        )

    if probabilities.ndim != 2:
        raise ValueError(
            "Persisted classifier probabilities must be a 2D array.",
        )

    if probabilities.shape[0] != len(actual_labels):
        raise ValueError(
            "Probability row count does not match test-target count: "
            f"{probabilities.shape[0]} != {len(actual_labels)}.",
        )

    if probabilities.shape[1] != len(model.classes):
        raise ValueError(
            "Probability column count does not match persisted model "
            f"classes: {probabilities.shape[1]} != {len(model.classes)}.",
        )

    if not np.isfinite(probabilities).all():
        raise ValueError(
            "Persisted classifier probabilities contain non-finite values.",
        )

    if (probabilities < 0.0).any() or (probabilities > 1.0).any():
        raise ValueError(
            "Persisted classifier probabilities must be within [0, 1].",
        )

    probability_sums = probabilities.sum(
        axis=1,
    )
    maximum_probability_sum_deviation = float(
        np.max(
            np.abs(probability_sums - 1.0),
        ),
    )
    if maximum_probability_sum_deviation > PROBABILITY_SUM_ATOL:
        raise ValueError(
            "Persisted classifier probability rows do not sum to 1 within "
            f"the allowed numerical tolerance of {PROBABILITY_SUM_ATOL:g}; "
            f"maximum observed deviation was "
            f"{maximum_probability_sum_deviation:.3g}.",
        )

    encoded_target = _encode_target_labels(
        target=pd.Series(actual_labels),
        classes=model.classes,
    )

    expected_class_indices = set(range(len(model.classes)))
    present_class_indices = set(np.unique(encoded_target))

    if present_class_indices != expected_class_indices:
        raise ValueError(
            "The frozen test partition does not contain every persisted "
            "target class; ROC-AUC/PR-AUC cannot be calculated using "
            "the same multiclass convention as validation.",
        )

    metrics = _calculate_test_metrics(
        actual_labels=actual_labels,
        predicted_labels=predicted_labels,
        encoded_target=encoded_target,
        probabilities=probabilities,
    )

    per_class = _build_per_class_metrics(
        actual_labels=actual_labels,
        predicted_labels=predicted_labels,
        classes=model.classes,
        seed=model.seed,
        configuration_id=model.configuration_id,
        classifier_name=classifier_name,
    )

    return metrics, per_class, predicted_labels


# ----------------------------------------
# Persistence
# ----------------------------------------


def _write_json(
    path: Path,
    payload: object,
) -> None:
    """Atomically write JSON metadata."""
    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp",
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(
        path,
    )


def _write_dataframe_csv(
    data_frame: pd.DataFrame,
    path: Path,
    *,
    index: bool = False,
) -> None:
    """Atomically write a DataFrame using the project's numeric precision."""
    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp",
    )

    data_frame.to_csv(
        temporary_path,
        index=index,
        float_format=TEST_FLOAT_FORMAT,
    )

    temporary_path.replace(
        path,
    )


def _build_summary_row(
    *,
    dataset_name: str,
    classifier_name: str,
    seed_results: pd.DataFrame,
) -> dict[str, object]:
    """Build a report-friendly mean ± std summary row."""
    row: dict[str, object] = {
        "dataset": dataset_name,
        "classifier": classifier_name,
        "seed_count": len(seed_results),
    }

    for metric in TEST_METRIC_COLUMNS:
        mean = float(seed_results[metric].mean())

        if len(seed_results) > 1:
            std = float(seed_results[metric].std(ddof=1))
        else:
            std = 0.0

        row[metric] = (
            f"{mean:{TEST_SUMMARY_FLOAT_FORMAT}} ± {std:{TEST_SUMMARY_FLOAT_FORMAT}}"
        )

    return row


def _persist_test_artifacts(
    *,
    artifact_directory: Path,
    dataset_name: str,
    classifier_name: str,
    seed_results: pd.DataFrame,
    per_class_results: pd.DataFrame,
    test_row_count: int,
    confusion_matrices: dict[
        int,
        tuple[pd.DataFrame, pd.DataFrame],
    ],
    summary_row: dict[str, object],
) -> None:
    """Persist final test results beneath the model experiment directory."""
    evaluation_directory = artifact_directory / "test_evaluation"
    evaluation_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    _write_dataframe_csv(
        seed_results,
        evaluation_directory / "test_seed_metrics.csv",
    )

    _write_dataframe_csv(
        per_class_results,
        evaluation_directory / "test_per_class_metrics.csv",
    )

    # This file intentionally stores presentation strings (mean ± std), not
    # numeric metric columns. It still goes through the same CSV writer so the
    # project has one serialization path and one numeric precision convention.
    _write_dataframe_csv(
        pd.DataFrame([summary_row]),
        evaluation_directory / "test_summary.csv",
    )

    for seed, (raw_matrix, normalized_matrix) in confusion_matrices.items():
        _write_dataframe_csv(
            raw_matrix,
            evaluation_directory / f"confusion_matrix_seed_{seed}.csv",
            index=True,
        )
        _write_dataframe_csv(
            normalized_matrix,
            evaluation_directory / f"confusion_matrix_normalized_seed_{seed}.csv",
            index=True,
        )

    metadata = {
        "dataset_name": dataset_name,
        "classifier_name": classifier_name,
        "evaluation_type": "frozen_test_set",
        "test_row_count": int(test_row_count),
        "seed_count": len(seed_results),
        "seeds": [int(seed) for seed in sorted(seed_results["seed"].unique())],
        "configuration_ids": sorted(
            str(configuration_id)
            for configuration_id in seed_results["configuration_id"].unique()
        ),
        "metrics": TEST_METRIC_COLUMNS,
        "numeric_csv_float_format": TEST_FLOAT_FORMAT,
        "summary_float_format": TEST_SUMMARY_FLOAT_FORMAT,
        "summary": summary_row,
    }

    _write_json(
        evaluation_directory / "test_evaluation_metadata.json",
        metadata,
    )


# ----------------------------------------
# Public execution API
# ----------------------------------------


def run_classifier_test(
    *,
    dataset_key: str,
    classifier_name: str,
) -> pd.DataFrame:
    """Evaluate the persisted final models for one dataset/classifier.

    No fitting, hyperparameter search, or model selection occurs here.
    """
    normalized_dataset_key = dataset_key.lower()
    normalized_classifier_name = classifier_name.lower()

    try:
        dataset_name, test_features, test_target = DATASET_CONFIGURATIONS[
            normalized_dataset_key
        ]
    except KeyError as error:
        available = ", ".join(
            sorted(DATASET_CONFIGURATIONS),
        )
        raise ValueError(
            f"Unknown dataset {dataset_key!r}. Available datasets: {available}.",
        ) from error

    if normalized_classifier_name not in CLASSIFIER_NAMES:
        available = ", ".join(CLASSIFIER_NAMES)
        raise ValueError(
            f"Unknown classifier {classifier_name!r}. "
            f"Available classifiers: {available}.",
        )

    artifact_directory = (
        ARTIFACT_ROOT / normalized_dataset_key / normalized_classifier_name
    )

    models = load_final_models(
        artifact_directory,
    )

    if not models:
        raise FileNotFoundError(
            f"No persisted final models were found for '{artifact_directory}'.",
        )

    metadata = _validate_experiment_artifacts(
        artifact_directory=artifact_directory,
        dataset_name=dataset_name,
        classifier_name=normalized_classifier_name,
        models=models,
    )

    if len(test_features) != len(test_target):
        raise ValueError(
            "The transformed test features and target have different row "
            f"counts: {len(test_features)} != {len(test_target)}.",
        )

    expected_test_row_count = metadata.get("test_row_count")
    if expected_test_row_count is not None:
        if not isinstance(expected_test_row_count, int):
            raise ValueError(
                "Experiment metadata field 'test_row_count' must be an integer.",
            )

        if len(test_features) != expected_test_row_count:
            raise ValueError(
                "The loaded frozen test partition has "
                f"{len(test_features)} rows, but the persisted experiment "
                f"metadata records {expected_test_row_count} test rows.",
            )

    numerical_features = _get_metadata_feature_labels(
        metadata=metadata,
        key="numerical_features",
    )
    categorical_features = _get_metadata_feature_labels(
        metadata=metadata,
        key="categorical_features",
    )
    expected_features = numerical_features + categorical_features

    if len(expected_features) != len(set(expected_features)):
        raise ValueError(
            "Experiment metadata contains duplicate predictor feature names.",
        )

    if test_features.columns.duplicated().any():
        duplicated_columns = tuple(
            str(column)
            for column in test_features.columns[test_features.columns.duplicated()]
        )
        raise ValueError(
            "The transformed test DataFrame contains duplicate column names: "
            f"{duplicated_columns!r}.",
        )

    missing_features = set(expected_features) - set(test_features.columns)
    if missing_features:
        raise ValueError(
            "The transformed test DataFrame is missing predictor features "
            f"required by the persisted experiment: {sorted(missing_features)!r}.",
        )

    seed_rows: list[dict[str, object]] = []
    per_class_frames: list[pd.DataFrame] = []
    confusion_matrices: dict[
        int,
        tuple[pd.DataFrame, pd.DataFrame],
    ] = {}

    for seed, model in models.items():
        print(
            f"{dataset_name} / {normalized_classifier_name} — "
            f"test evaluation for seed {seed}",
        )

        metrics, per_class, predictions = _evaluate_seed(
            model=model,
            classifier_name=normalized_classifier_name,
            test_features=test_features,
            test_target=test_target,
        )

        seed_rows.append(
            {
                "dataset": dataset_name,
                "classifier": normalized_classifier_name,
                "seed": int(seed),
                "configuration_id": model.configuration_id,
                **metrics,
            },
        )

        per_class_frames.append(
            per_class,
        )

        actual_labels = np.asarray(
            test_target.astype(str),
            dtype=object,
        )

        raw_values = confusion_matrix(
            actual_labels,
            predictions,
            labels=list(model.classes),
        )

        normalized_values = confusion_matrix(
            actual_labels,
            predictions,
            labels=list(model.classes),
            normalize="true",
        )

        confusion_matrices[seed] = (
            pd.DataFrame(
                raw_values,
                index=pd.Index(
                    model.classes,
                    name="actual",
                ),
                columns=pd.Index(
                    model.classes,
                    name="predicted",
                ),
            ),
            pd.DataFrame(
                normalized_values,
                index=pd.Index(
                    model.classes,
                    name="actual",
                ),
                columns=pd.Index(
                    model.classes,
                    name="predicted",
                ),
            ),
        )

    seed_results = pd.DataFrame(
        seed_rows,
    ).sort_values(
        "seed",
        ignore_index=True,
    )

    per_class_results = pd.concat(
        per_class_frames,
        ignore_index=True,
    ).sort_values(
        ["seed", "class"],
        ignore_index=True,
    )

    summary_row = _build_summary_row(
        dataset_name=dataset_name,
        classifier_name=normalized_classifier_name,
        seed_results=seed_results,
    )

    _persist_test_artifacts(
        artifact_directory=artifact_directory,
        dataset_name=dataset_name,
        classifier_name=normalized_classifier_name,
        seed_results=seed_results,
        per_class_results=per_class_results,
        test_row_count=len(test_features),
        confusion_matrices=confusion_matrices,
        summary_row=summary_row,
    )

    return pd.DataFrame(
        [summary_row],
    )


def run_dataset_test(
    dataset_key: str,
) -> pd.DataFrame:
    """Evaluate all three classifiers for one dataset."""
    summaries = [
        run_classifier_test(
            dataset_key=dataset_key,
            classifier_name=classifier_name,
        )
        for classifier_name in CLASSIFIER_NAMES
    ]

    return pd.concat(
        summaries,
        ignore_index=True,
    )


def run_all_tests() -> pd.DataFrame:
    """Evaluate all dataset/classifier combinations."""
    summaries = [
        run_dataset_test(dataset_key) for dataset_key in DATASET_CONFIGURATIONS
    ]

    result = pd.concat(
        summaries,
        ignore_index=True,
    )

    evaluation_directory = ARTIFACT_ROOT / "test_evaluation"
    evaluation_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # The table contains presentation strings for the metric columns, but use
    # the same CSV-writing helper for a single project-wide serialization path.
    _write_dataframe_csv(
        result,
        evaluation_directory / "test_summary_all.csv",
    )

    return result


# ----------------------------------------
# Command-line interface
# ----------------------------------------


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate persisted final models on their frozen test partitions."
        ),
    )

    parser.add_argument(
        "--dataset",
        choices=tuple(DATASET_CONFIGURATIONS),
        default=None,
        help="Evaluate one dataset; omit to evaluate both.",
    )

    parser.add_argument(
        "--classifier",
        choices=CLASSIFIER_NAMES,
        default=None,
        help=(
            "Evaluate one classifier. Requires --dataset; omit to "
            "evaluate all classifiers for the selected dataset."
        ),
    )

    return parser


def main() -> None:
    """Run the requested final test evaluation."""
    parser = _build_argument_parser()
    arguments = parser.parse_args()

    if arguments.classifier is not None and arguments.dataset is None:
        parser.error("--classifier requires --dataset.")

    if arguments.dataset is None:
        summary = run_all_tests()
    elif arguments.classifier is None:
        summary = run_dataset_test(
            arguments.dataset,
        )
    else:
        summary = run_classifier_test(
            dataset_key=arguments.dataset,
            classifier_name=arguments.classifier,
        )

    print()
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
