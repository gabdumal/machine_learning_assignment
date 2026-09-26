"""Evaluate committees composed from the persisted final classifiers.

This module is deliberately a composition/evaluation layer. It does not fit
models, tune hyperparameters, preprocess data, rebalance classes, or select a
committee strategy using the frozen test labels.

For each dataset, the committee is formed independently for each persisted
seed:

    Decision Tree(seed) + Random Forest(seed) + XGBoost(seed)

Four predefined aggregation strategies are evaluated:

* hard voting;
* weighted hard voting;
* soft voting;
* weighted soft voting.

Weights are fixed per dataset and are derived exclusively from validation
Macro F1 for the already-selected configuration of each classifier:

    weight_i = validation_macro_f1_i / sum(validation_macro_f1_j)

The persisted test predictions provide the component outputs. The persisted
``actual_class`` column is read only after those outputs have been combined,
and is used only for final metric calculation.
"""

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize

from pipeline.common import (
    ARTIFACT_ROOT,
    load_experiment_metadata,
    load_test_predictions,
    load_validation_seed_results,
)

# ----------------------------------------
# Constants
# ----------------------------------------

COMMITTEE_DIRECTORY_NAME: Final[str] = "committee"

COMMITTEE_METADATA_FILE_NAME: Final[str] = "metadata.json"
COMMITTEE_WEIGHTS_FILE_NAME: Final[str] = "weights.csv"
COMMITTEE_SEED_METRICS_FILE_NAME: Final[str] = "seed_metrics.csv"
COMMITTEE_SUMMARY_FILE_NAME: Final[str] = "summary.csv"

COMPONENT_CLASSIFIERS: Final[tuple[str, ...]] = (
    "decision_tree",
    "random_forest",
    "xgboost",
)

COMMITTEE_STRATEGIES: Final[tuple[str, ...]] = (
    "hard_voting",
    "weighted_hard_voting",
    "soft_voting",
    "weighted_soft_voting",
)

COMMITTEE_METRIC_COLUMNS: Final[tuple[str, ...]] = (
    "accuracy",
    "precision",
    "recall",
    "macro_f1",
    "roc_auc",
    "pr_auc",
    "mcc",
    "balanced_accuracy",
)

WEIGHT_METRIC: Final[str] = "macro_f1"

REQUIRED_TEST_PREDICTION_COLUMNS: Final[tuple[str, ...]] = (
    "seed",
    "row_index",
    "actual_class",
    "predicted_class",
)

PROBABILITY_COLUMN_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^probability_(\d+)_(.*)$",
)

NUMERIC_CSV_FLOAT_FORMAT: Final[str] = "%.12g"
SUMMARY_DECIMALS: Final[int] = 5
PROBABILITY_SUM_ATOL: Final[float] = 1e-6


# ----------------------------------------
# Data structures
# ----------------------------------------


@dataclass(frozen=True, slots=True)
class CommitteeExperimentPaths:
    """Paths belonging to one dataset-level committee experiment."""

    root: Path
    metadata: Path
    weights: Path
    seed_metrics: Path
    summary: Path

    @classmethod
    def from_root(
        cls,
        root: Path,
    ) -> CommitteeExperimentPaths:  # noqa: F821
        """Create all committee-artifact paths beneath ``root``."""
        return cls(
            root=root,
            metadata=root / COMMITTEE_METADATA_FILE_NAME,
            weights=root / COMMITTEE_WEIGHTS_FILE_NAME,
            seed_metrics=root / COMMITTEE_SEED_METRICS_FILE_NAME,
            summary=root / COMMITTEE_SUMMARY_FILE_NAME,
        )

    def ensure_directory(self) -> None:
        """Create the committee artifact directory."""
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )


@dataclass(frozen=True, slots=True)
class CommitteeExperimentResult:
    """Persisted outputs from one dataset-level committee experiment."""

    dataset_name: str
    artifact_paths: CommitteeExperimentPaths
    metadata: dict[str, object]
    weights: pd.DataFrame
    seed_metrics: pd.DataFrame
    summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class _ComponentPredictions:
    """Aligned persisted predictions for one component classifier."""

    classifier: str
    seeds: tuple[int, ...]
    classes: tuple[str, ...]
    rows_by_seed: Mapping[int, pd.DataFrame]


# ----------------------------------------
# General helpers
# ----------------------------------------


def _to_python_int(value: object) -> int:
    """Convert an integer-like scalar to a Python ``int``."""
    return int(
        cast(int, value),
    )


def _normalize_dataset_name(dataset_name: str) -> str:
    """Return the canonical dataset name used by experiment artifacts."""
    normalized = dataset_name.strip().lower()

    if not normalized:
        raise ValueError("Dataset name must not be empty.")

    if normalized not in {"genis", "rosids"}:
        raise ValueError(
            f"Unknown dataset {dataset_name!r}. Available datasets: GENIS, ROSIDS.",
        )

    return normalized.upper()


def _write_json(
    path: Path,
    payload: object,
) -> None:
    """Write JSON metadata with deterministic key ordering."""
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _validate_required_columns(
    frame: pd.DataFrame,
    required_columns: Sequence[str],
    *,
    table_name: str,
) -> None:
    """Validate that a DataFrame contains every required column."""
    missing = set(required_columns) - set(frame.columns)
    if missing:
        raise ValueError(
            f"{table_name} is missing required columns: {sorted(missing)!r}.",
        )


def _validate_probability_columns(
    frame: pd.DataFrame,
    *,
    classifier: str,
) -> tuple[str, ...]:
    """Validate and return probability columns in persisted class order."""
    indexed_columns: dict[int, str] = {}

    for column in frame.columns:
        match = PROBABILITY_COLUMN_PATTERN.match(str(column))
        if match is None:
            continue

        class_index = int(match.group(1))
        if class_index in indexed_columns:
            raise ValueError(
                f"Classifier {classifier!r} contains duplicate probability "
                f"columns for class index {class_index}.",
            )

        indexed_columns[class_index] = str(column)

    if not indexed_columns:
        raise ValueError(
            f"Persisted predictions for classifier {classifier!r} contain "
            "no probability columns.",
        )

    expected_indices = set(range(len(indexed_columns)))
    actual_indices = set(indexed_columns)

    if actual_indices != expected_indices:
        raise ValueError(
            f"Probability class indices for classifier {classifier!r} are not "
            f"contiguous from zero: {sorted(actual_indices)!r}.",
        )

    ordered_columns = tuple(
        indexed_columns[index] for index in range(len(indexed_columns))
    )

    return ordered_columns


def _probability_class_labels(
    probability_columns: Sequence[str],
) -> tuple[str, ...]:
    """Extract the persisted class label associated with each probability."""
    labels: list[str] = []

    for column in probability_columns:
        match = PROBABILITY_COLUMN_PATTERN.match(column)
        if match is None:
            raise ValueError(
                f"Invalid persisted probability column name: {column!r}.",
            )

        labels.append(match.group(2))

    if any(not label for label in labels):
        raise ValueError(
            "Persisted probability columns must contain non-empty class labels.",
        )

    if len(set(labels)) != len(labels):
        raise ValueError(
            f"Persisted probability columns contain duplicate class labels: "
            f"{labels!r}.",
        )

    return tuple(labels)


def _validate_test_prediction_frame(
    frame: pd.DataFrame,
    *,
    classifier: str,
) -> tuple[int, ...]:
    """Validate one concatenated persisted prediction table."""
    _validate_required_columns(
        frame,
        REQUIRED_TEST_PREDICTION_COLUMNS,
        table_name=f"test predictions for {classifier}",
    )

    probability_columns = _validate_probability_columns(
        frame,
        classifier=classifier,
    )

    if frame.empty:
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} are empty.",
        )

    seeds = pd.to_numeric(
        frame["seed"],
        errors="raise",
    )
    if seeds.isna().any():
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "missing seeds.",
        )

    if not np.all(
        np.isfinite(
            seeds.to_numpy(dtype=float),
        ),
    ):
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "non-finite seeds.",
        )

    seed_values = seeds.to_numpy(dtype=float)
    if not np.all(seed_values == np.floor(seed_values)):
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "non-integer seed values.",
        )

    row_indices = pd.to_numeric(
        frame["row_index"],
        errors="raise",
    )
    if row_indices.isna().any():
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "missing row indices.",
        )

    row_index_values = row_indices.to_numpy(dtype=float)
    if not np.all(np.isfinite(row_index_values)):
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "non-finite row indices.",
        )
    if not np.all(row_index_values == np.floor(row_index_values)):
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "non-integer row indices.",
        )

    frame["seed"] = seed_values.astype(np.int64)
    frame["row_index"] = row_index_values.astype(np.int64)

    if frame[["seed", "row_index"]].duplicated().any():
        duplicate_rows = frame.loc[
            frame[["seed", "row_index"]].duplicated(keep=False),
            ["seed", "row_index"],
        ]
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "duplicate (seed, row_index) keys. Example duplicates: "
            f"{duplicate_rows.head().to_dict(orient='records')!r}.",
        )

    if frame["actual_class"].isna().any():
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "missing actual classes.",
        )
    if frame["predicted_class"].isna().any():
        raise ValueError(
            f"Persisted test predictions for classifier {classifier!r} contain "
            "missing predicted classes.",
        )

    frame["actual_class"] = frame["actual_class"].astype(str)
    frame["predicted_class"] = frame["predicted_class"].astype(str)

    probabilities = frame.loc[:, probability_columns].to_numpy(
        dtype=float,
    )

    if not np.all(np.isfinite(probabilities)):
        raise ValueError(
            f"Persisted probabilities for classifier {classifier!r} contain "
            "non-finite values.",
        )

    if np.any(probabilities < -PROBABILITY_SUM_ATOL):
        raise ValueError(
            f"Persisted probabilities for classifier {classifier!r} contain "
            "negative values.",
        )

    probability_sums = probabilities.sum(axis=1)
    if not np.allclose(
        probability_sums,
        1.0,
        atol=PROBABILITY_SUM_ATOL,
        rtol=0.0,
    ):
        raise ValueError(
            f"Persisted probabilities for classifier {classifier!r} do not "
            "sum to one within the allowed tolerance.",
        )

    return tuple(
        sorted(_to_python_int(seed) for seed in frame["seed"].unique()),
    )


def _split_predictions_by_seed(
    frame: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    """Return independent seed-level views sorted by row index."""
    result: dict[int, pd.DataFrame] = {}

    for seed, seed_frame in frame.groupby(
        "seed",
        sort=True,
    ):
        result[_to_python_int(seed)] = seed_frame.sort_values(
            "row_index",
            ignore_index=True,
        ).reset_index(drop=True)

    return result


def _load_component_predictions(
    *,
    dataset_directory: Path,
    dataset_name: str,
    classifier: str,
) -> _ComponentPredictions:
    """Load and validate persisted test predictions for one classifier."""
    artifact_directory = dataset_directory / classifier

    metadata = load_experiment_metadata(
        artifact_directory,
    )
    _validate_component_experiment_metadata(
        metadata,
        dataset_name=dataset_name,
        classifier=classifier,
    )

    frame = load_test_predictions(
        artifact_directory,
    ).copy()

    seeds = _validate_test_prediction_frame(
        frame,
        classifier=classifier,
    )
    probability_columns = _validate_probability_columns(
        frame,
        classifier=classifier,
    )
    classes = _probability_class_labels(
        probability_columns,
    )

    for seed, seed_frame in _split_predictions_by_seed(frame).items():
        seed_probabilities = seed_frame.loc[:, probability_columns].to_numpy(
            dtype=float,
        )
        probability_sums = seed_probabilities.sum(axis=1)
        if not np.allclose(
            probability_sums,
            1.0,
            atol=PROBABILITY_SUM_ATOL,
            rtol=0.0,
        ):
            raise ValueError(
                f"Persisted probabilities for classifier {classifier!r}, "
                f"seed {seed}, do not sum to one within tolerance.",
            )

    return _ComponentPredictions(
        classifier=classifier,
        seeds=seeds,
        classes=classes,
        rows_by_seed=_split_predictions_by_seed(frame),
    )


def _validate_component_compatibility(
    components: Mapping[str, _ComponentPredictions],
) -> tuple[int, ...]:
    """Validate common seed, class, row-key, and target alignment."""
    reference_classifier = COMPONENT_CLASSIFIERS[0]
    reference = components[reference_classifier]

    for classifier in COMPONENT_CLASSIFIERS[1:]:
        component = components[classifier]

        if component.seeds != reference.seeds:
            raise ValueError(
                "Persisted classifier predictions do not use the same seeds: "
                f"{reference_classifier}={reference.seeds!r}, "
                f"{classifier}={component.seeds!r}.",
            )

        if component.classes != reference.classes:
            raise ValueError(
                "Persisted classifier predictions do not use the same target "
                "class order: "
                f"{reference_classifier}={reference.classes!r}, "
                f"{classifier}={component.classes!r}.",
            )

    for seed in reference.seeds:
        reference_frame = reference.rows_by_seed[seed]
        reference_keys = reference_frame[["seed", "row_index"]].to_numpy()
        reference_actual = reference_frame["actual_class"].to_numpy(dtype=object)

        for classifier in COMPONENT_CLASSIFIERS[1:]:
            component_frame = components[classifier].rows_by_seed[seed]
            component_keys = component_frame[["seed", "row_index"]].to_numpy()

            if not np.array_equal(
                reference_keys,
                component_keys,
            ):
                raise ValueError(
                    "Persisted classifier predictions do not align on "
                    f"(seed, row_index) for seed {seed}: "
                    f"{reference_classifier} vs {classifier}.",
                )

            actual_classes = component_frame["actual_class"].to_numpy(dtype=object)
            if not np.array_equal(
                reference_actual,
                actual_classes,
            ):
                raise ValueError(
                    "Persisted classifier predictions disagree on actual test "
                    f"labels for seed {seed}: {reference_classifier} vs {classifier}.",
                )

    return reference.seeds


# ----------------------------------------
# Validation-derived weights
# ----------------------------------------


def _validate_component_experiment_metadata(
    metadata: Mapping[str, object],
    *,
    dataset_name: str,
    classifier: str,
) -> None:
    """Validate metadata identity before consuming a component artifact set."""
    recorded_dataset = metadata.get("dataset_name")
    if (
        recorded_dataset is not None
        and str(recorded_dataset).upper() != dataset_name.upper()
    ):
        raise ValueError(
            f"Experiment metadata for classifier {classifier!r} records dataset "
            f"{recorded_dataset!r}, expected {dataset_name!r}."
        )

    recorded_classifier = metadata.get("classifier_name")
    if (
        recorded_classifier is not None
        and str(recorded_classifier).lower() != classifier.lower()
    ):
        raise ValueError(
            f"Experiment metadata records classifier {recorded_classifier!r}, "
            f"expected {classifier!r}."
        )

    status = metadata.get("status")
    if status != "complete":
        raise ValueError(
            f"Experiment metadata for classifier {classifier!r} is not marked "
            f"complete: status={status!r}."
        )


def _selected_configuration_id(
    metadata: Mapping[str, object],
    *,
    classifier: str,
) -> str:
    """Extract the selected validation configuration identifier."""
    selected_configuration = metadata.get("selected_configuration")

    if not isinstance(selected_configuration, Mapping):
        raise TypeError(
            f"Experiment metadata for classifier {classifier!r} does not "
            "contain a valid selected_configuration object.",
        )

    configuration_id = selected_configuration.get("configuration_id")
    if not isinstance(configuration_id, str) or not configuration_id:
        raise ValueError(
            f"Experiment metadata for classifier {classifier!r} does not "
            "contain a valid selected configuration_id.",
        )

    return configuration_id


def _validation_macro_f1(
    *,
    artifact_directory: Path,
    classifier: str,
    expected_seeds: Sequence[int],
) -> tuple[str, tuple[int, ...], float]:
    """Read selected-configuration validation Macro F1 and average seeds."""
    metadata = load_experiment_metadata(
        artifact_directory,
    )
    configuration_id = _selected_configuration_id(
        metadata,
        classifier=classifier,
    )

    validation_metric = metadata.get("validation_metric")
    if validation_metric != WEIGHT_METRIC:
        raise ValueError(
            f"Experiment metadata for classifier {classifier!r} records "
            f"validation_metric={validation_metric!r}; committee weights require "
            f"{WEIGHT_METRIC!r}."
        )

    validation_seed_results = load_validation_seed_results(
        artifact_directory,
    )

    _validate_required_columns(
        validation_seed_results,
        (
            "configuration_id",
            "seed",
            "mean_macro_f1",
        ),
        table_name=f"validation results for {classifier}",
    )

    configuration_rows = validation_seed_results.loc[
        validation_seed_results["configuration_id"].astype(str) == configuration_id
    ].copy()

    if configuration_rows.empty:
        raise ValueError(
            f"Validation results for classifier {classifier!r} do not contain "
            f"the selected configuration {configuration_id!r}.",
        )

    validation_seeds = tuple(
        sorted(
            _to_python_int(seed)
            for seed in pd.to_numeric(
                configuration_rows["seed"],
                errors="raise",
            ).unique()
        )
    )

    expected_seed_tuple = tuple(
        sorted(int(seed) for seed in expected_seeds),
    )

    if validation_seeds != expected_seed_tuple:
        raise ValueError(
            f"Validation seeds for classifier {classifier!r} do not match "
            f"the persisted test seeds: validation={validation_seeds!r}, "
            f"test={expected_seed_tuple!r}.",
        )

    if configuration_rows["seed"].duplicated().any():
        raise ValueError(
            f"Validation results for classifier {classifier!r} contain "
            "duplicate selected-configuration seed rows.",
        )

    validation_values = pd.to_numeric(
        configuration_rows["mean_macro_f1"],
        errors="raise",
    ).to_numpy(dtype=float)

    if not np.all(np.isfinite(validation_values)):
        raise ValueError(
            f"Validation Macro F1 for classifier {classifier!r} contains "
            "non-finite values.",
        )

    if np.any(validation_values < 0.0) or np.any(validation_values > 1.0):
        raise ValueError(
            f"Validation Macro F1 for classifier {classifier!r} contains "
            "values outside [0, 1].",
        )

    mean_macro_f1 = float(np.mean(validation_values))

    if mean_macro_f1 <= 0.0:
        raise ValueError(
            f"Validation Macro F1 for classifier {classifier!r} is not "
            "positive, so validation-derived committee weights cannot be "
            "constructed.",
        )

    return configuration_id, validation_seeds, mean_macro_f1


def _build_validation_weights(
    *,
    dataset_directory: Path,
    test_seeds: Sequence[int],
) -> pd.DataFrame:
    """Build one fixed validation-derived weight vector for the dataset."""
    rows: list[dict[str, object]] = []

    for classifier in COMPONENT_CLASSIFIERS:
        configuration_id, _, mean_macro_f1 = _validation_macro_f1(
            artifact_directory=dataset_directory / classifier,
            classifier=classifier,
            expected_seeds=test_seeds,
        )
        del configuration_id

        rows.append(
            {
                "classifier": classifier,
                "validation_macro_f1": mean_macro_f1,
            },
        )

    weights = pd.DataFrame(rows)
    total = float(weights["validation_macro_f1"].sum())

    if not np.isfinite(total) or total <= 0.0:
        raise ValueError(
            "Validation Macro F1 values do not produce a positive finite "
            "weight denominator.",
        )

    weights["weight"] = weights["validation_macro_f1"] / total

    weight_values = weights["weight"].to_numpy(dtype=float)
    if not np.all(np.isfinite(weight_values)) or np.any(weight_values < 0.0):
        raise ValueError(
            "Validation-derived committee weights must be finite and non-negative.",
        )

    if not np.isclose(
        float(weight_values.sum()),
        1.0,
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError(
            "Validation-derived committee weights must sum to one.",
        )

    return weights.loc[
        :,
        ["classifier", "validation_macro_f1", "weight"],
    ].copy()


# ----------------------------------------
# Committee aggregation
# ----------------------------------------


def _class_indices(
    labels: np.ndarray,
    classes: Sequence[str],
) -> np.ndarray:
    """Encode predicted string labels using the common class order."""
    class_to_index = {str(label): index for index, label in enumerate(classes)}

    encoded = np.empty(
        len(labels),
        dtype=np.int64,
    )

    unknown_labels: set[str] = set()

    for index, label in enumerate(labels.astype(str)):
        class_index = class_to_index.get(label)
        if class_index is None:
            unknown_labels.add(label)
        else:
            encoded[index] = class_index

    if unknown_labels:
        raise ValueError(
            "A persisted classifier prediction contains labels absent from "
            f"the common target classes: {sorted(unknown_labels)!r}.",
        )

    return encoded


def _select_hard_vote_class(
    vote_scores: np.ndarray,
    probability_mean: np.ndarray,
) -> np.ndarray:
    """Select hard-vote classes with probability-based deterministic ties."""
    row_count = vote_scores.shape[0]
    predictions = np.empty(
        row_count,
        dtype=np.int64,
    )

    maximum_votes = np.max(
        vote_scores,
        axis=1,
        keepdims=True,
    )
    ties = np.isclose(
        vote_scores,
        maximum_votes,
        atol=1e-12,
        rtol=0.0,
    )

    for row_index in range(row_count):
        tied_classes = np.flatnonzero(ties[row_index])

        if len(tied_classes) == 1:
            predictions[row_index] = tied_classes[0]
            continue

        tied_probabilities = probability_mean[
            row_index,
            tied_classes,
        ]
        maximum_probability = np.max(tied_probabilities)
        probability_ties = np.flatnonzero(
            np.isclose(
                tied_probabilities,
                maximum_probability,
                atol=1e-12,
                rtol=0.0,
            ),
        )

        # np.flatnonzero preserves class-order determinism. In the extremely
        # rare case where the tie-break probabilities also tie, the first
        # class in the persisted common class order wins deterministically.
        predictions[row_index] = tied_classes[probability_ties[0]]

    return predictions


def _aggregate_seed_predictions(
    *,
    components: Mapping[str, _ComponentPredictions],
    seed: int,
    classes: Sequence[str],
    weights: Mapping[str, float],
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Create predictions and class scores for every committee strategy."""
    probability_arrays: list[np.ndarray] = []
    predicted_indices: list[np.ndarray] = []

    for classifier in COMPONENT_CLASSIFIERS:
        frame = components[classifier].rows_by_seed[seed]
        probability_columns = _validate_probability_columns(
            frame,
            classifier=classifier,
        )
        probabilities = frame.loc[:, probability_columns].to_numpy(
            dtype=float,
        )
        prediction_indices = _class_indices(
            frame["predicted_class"].to_numpy(dtype=object),
            classes,
        )

        probability_arrays.append(probabilities)
        predicted_indices.append(prediction_indices)

    probability_mean = np.mean(
        np.stack(probability_arrays, axis=0),
        axis=0,
    )

    weight_array = np.asarray(
        [float(weights[classifier]) for classifier in COMPONENT_CLASSIFIERS],
        dtype=float,
    )

    weighted_probabilities = np.tensordot(
        weight_array,
        np.stack(probability_arrays, axis=0),
        axes=(0, 0),
    )

    hard_vote_counts = np.zeros(
        (len(predicted_indices[0]), len(classes)),
        dtype=float,
    )
    for classifier_predictions in predicted_indices:
        hard_vote_counts += np.eye(
            len(classes),
            dtype=float,
        )[classifier_predictions]

    hard_vote_scores = hard_vote_counts / len(COMPONENT_CLASSIFIERS)

    weighted_hard_vote_scores = np.zeros_like(hard_vote_scores)
    for classifier_index, classifier in enumerate(COMPONENT_CLASSIFIERS):
        weighted_hard_vote_scores += (
            float(
                weights[classifier],
            )
            * np.eye(
                len(classes),
                dtype=float,
            )[predicted_indices[classifier_index]]
        )

    hard_predictions = _select_hard_vote_class(
        hard_vote_scores,
        probability_mean,
    )

    weighted_hard_predictions = _select_hard_vote_class(
        weighted_hard_vote_scores,
        probability_mean,
    )

    soft_predictions = np.argmax(
        probability_mean,
        axis=1,
    ).astype(np.int64)

    weighted_soft_predictions = np.argmax(
        weighted_probabilities,
        axis=1,
    ).astype(np.int64)

    return {
        "hard_voting": (
            hard_predictions,
            hard_vote_scores,
        ),
        "weighted_hard_voting": (
            weighted_hard_predictions,
            weighted_hard_vote_scores,
        ),
        "soft_voting": (
            soft_predictions,
            probability_mean,
        ),
        "weighted_soft_voting": (
            weighted_soft_predictions,
            weighted_probabilities,
        ),
    }


# ----------------------------------------
# Metrics
# ----------------------------------------


def _calculate_roc_auc(
    *,
    encoded_target: np.ndarray,
    scores: np.ndarray,
) -> float:
    """Calculate macro ROC-AUC using the classifier pipeline convention."""
    class_count = scores.shape[1]

    if class_count == 2:
        return float(
            roc_auc_score(
                encoded_target,
                scores[:, 1],
            ),
        )

    return float(
        roc_auc_score(
            encoded_target,
            scores,
            multi_class="ovr",
            average="macro",
            labels=np.arange(class_count),
        ),
    )


def _calculate_pr_auc(
    *,
    encoded_target: np.ndarray,
    scores: np.ndarray,
) -> float:
    """Calculate macro PR-AUC using the classifier pipeline convention."""
    class_count = scores.shape[1]

    if class_count == 2:
        return float(
            average_precision_score(
                encoded_target,
                scores[:, 1],
            ),
        )

    binary_targets = label_binarize(
        encoded_target,
        classes=np.arange(class_count),
    )

    return float(
        average_precision_score(
            binary_targets,
            scores,
            average="macro",
        ),
    )


def _calculate_committee_metrics(
    *,
    actual_labels: np.ndarray,
    predicted_indices: np.ndarray,
    scores: np.ndarray,
    classes: Sequence[str],
) -> dict[str, float]:
    """Calculate the same scalar metrics used by individual classifiers."""
    class_to_index = {str(label): index for index, label in enumerate(classes)}

    encoded_target_list: list[int] = []
    unknown_labels: set[str] = set()

    for label in actual_labels.astype(str):
        class_index = class_to_index.get(label)
        if class_index is None:
            unknown_labels.add(label)
        else:
            encoded_target_list.append(class_index)

    if unknown_labels:
        raise ValueError(
            "The frozen test labels contain classes absent from the persisted "
            f"component predictions: {sorted(unknown_labels)!r}.",
        )

    encoded_target = np.asarray(
        encoded_target_list,
        dtype=np.int64,
    )

    if set(np.unique(encoded_target)) != set(range(len(classes))):
        raise ValueError(
            "The frozen test partition does not contain every persisted "
            "target class; ROC-AUC/PR-AUC cannot be calculated using the "
            "same multiclass convention as validation.",
        )

    predictions = np.asarray(
        predicted_indices,
        dtype=np.int64,
    )

    predicted_labels = np.asarray(
        [classes[index] for index in predictions],
        dtype=object,
    )
    actual_string_labels = actual_labels.astype(str)

    return {
        "accuracy": float(
            accuracy_score(
                actual_string_labels,
                predicted_labels,
            ),
        ),
        "precision": float(
            precision_score(
                actual_string_labels,
                predicted_labels,
                average="macro",
                zero_division=0,
            ),
        ),
        "recall": float(
            recall_score(
                actual_string_labels,
                predicted_labels,
                average="macro",
                zero_division=0,
            ),
        ),
        "macro_f1": float(
            f1_score(
                actual_string_labels,
                predicted_labels,
                average="macro",
                zero_division=0,
            ),
        ),
        "roc_auc": _calculate_roc_auc(
            encoded_target=encoded_target,
            scores=scores,
        ),
        "pr_auc": _calculate_pr_auc(
            encoded_target=encoded_target,
            scores=scores,
        ),
        "mcc": float(
            matthews_corrcoef(
                actual_string_labels,
                predicted_labels,
            ),
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                actual_string_labels,
                predicted_labels,
            ),
        ),
    }


# ----------------------------------------
# Persistence helpers
# ----------------------------------------


def _build_summary(
    seed_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Build one mean-plus-standard-deviation row per strategy."""
    rows: list[dict[str, object]] = []

    for strategy in COMMITTEE_STRATEGIES:
        strategy_frame = seed_metrics.loc[seed_metrics["strategy"] == strategy].copy()

        row: dict[str, object] = {
            "strategy": strategy,
            "seed_count": len(strategy_frame),
        }

        if strategy_frame.empty:
            raise ValueError(
                f"No seed-level results were found for strategy {strategy!r}.",
            )

        for metric in COMMITTEE_METRIC_COLUMNS:
            values = pd.to_numeric(
                strategy_frame[metric],
                errors="raise",
            ).to_numpy(dtype=float)
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            row[metric] = f"{mean:.{SUMMARY_DECIMALS}f} ± {std:.{SUMMARY_DECIMALS}f}"

        rows.append(row)

    return pd.DataFrame(rows)


def _build_metadata(
    *,
    dataset_name: str,
    seeds: Sequence[int],
    weights: pd.DataFrame,
    selected_configuration_ids: Mapping[str, str],
) -> dict[str, object]:
    """Build auditable committee metadata."""
    return {
        "schema_version": 1,
        "status": "complete",
        "dataset_name": dataset_name,
        "evaluation_type": "frozen_test_set_committee",
        "component_classifiers": COMPONENT_CLASSIFIERS,
        "seeds": [int(seed) for seed in seeds],
        "strategies": COMMITTEE_STRATEGIES,
        "weight_metric": WEIGHT_METRIC,
        "weighting_rule": "validation_macro_f1_normalized_across_component_classifiers",
        "weights_source": "selected_configuration_validation_seed_results",
        "selected_configuration_ids": {
            classifier: str(selected_configuration_ids[classifier])
            for classifier in COMPONENT_CLASSIFIERS
        },
        "weights_use_test_labels": False,
        "committee_strategy_selection_uses_test_labels": False,
        "test_labels_usage": "test_actual_class_is used only for final metric calculation",
        "hard_voting_tie_break": (
            "highest mean component predicted probability among tied classes; "
            "persisted class order resolves any remaining tie"
        ),
        "hard_vote_scores": "vote_count_divided_by_component_classifier_count",
        "weighted_hard_vote_scores": "validation_weighted_vote_sum",
        "soft_vote_scores": "unweighted_mean_component_probabilities",
        "weighted_soft_vote_scores": "validation_weighted_mean_component_probabilities",
        "metrics": COMMITTEE_METRIC_COLUMNS,
        "numeric_csv_float_format": NUMERIC_CSV_FLOAT_FORMAT,
        "summary_decimals": SUMMARY_DECIMALS,
        "weights": [
            {
                "classifier": str(row["classifier"]),
                "validation_macro_f1": float(row["validation_macro_f1"]),
                "weight": float(row["weight"]),
            }
            for row in weights.to_dict(orient="records")
        ],
    }


def _persist_committee_artifacts(
    *,
    paths: CommitteeExperimentPaths,
    metadata: Mapping[str, object],
    weights: pd.DataFrame,
    seed_metrics: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    """Persist all dataset-level committee artifacts."""
    paths.ensure_directory()

    weights.to_csv(
        paths.weights,
        index=False,
        float_format=NUMERIC_CSV_FLOAT_FORMAT,
    )
    seed_metrics.to_csv(
        paths.seed_metrics,
        index=False,
        float_format=NUMERIC_CSV_FLOAT_FORMAT,
    )
    summary.to_csv(
        paths.summary,
        index=False,
    )
    _write_json(
        paths.metadata,
        dict(metadata),
    )


# ----------------------------------------
# Public execution API
# ----------------------------------------


def run_dataset_committee(
    *,
    dataset_name: str,
    artifacts_directory: Path = ARTIFACT_ROOT,
) -> CommitteeExperimentResult:
    """Evaluate all predefined committee strategies for one dataset.

    The function consumes only persisted validation results and persisted test
    predictions from the three component classifiers. No model is fitted and
    no test-based selection is performed.
    """
    canonical_dataset = _normalize_dataset_name(dataset_name)
    dataset_directory = (
        artifacts_directory.expanduser().resolve() / canonical_dataset.lower()
    )

    components: dict[str, _ComponentPredictions] = {}

    for classifier in COMPONENT_CLASSIFIERS:
        components[classifier] = _load_component_predictions(
            dataset_directory=dataset_directory,
            dataset_name=canonical_dataset,
            classifier=classifier,
        )

    test_seeds = _validate_component_compatibility(
        components,
    )

    weights = _build_validation_weights(
        dataset_directory=dataset_directory,
        test_seeds=test_seeds,
    )

    weight_lookup = {
        str(row["classifier"]): float(row["weight"])
        for row in weights.to_dict(orient="records")
    }

    classes = components[COMPONENT_CLASSIFIERS[0]].classes

    seed_rows: list[dict[str, object]] = []

    for seed in test_seeds:
        reference_frame = components[COMPONENT_CLASSIFIERS[0]].rows_by_seed[seed]
        actual_labels = reference_frame["actual_class"].to_numpy(dtype=object)

        strategy_predictions = _aggregate_seed_predictions(
            components=components,
            seed=seed,
            classes=classes,
            weights=weight_lookup,
        )

        for strategy in COMMITTEE_STRATEGIES:
            predictions, scores = strategy_predictions[strategy]

            metrics = _calculate_committee_metrics(
                actual_labels=actual_labels,
                predicted_indices=predictions,
                scores=scores,
                classes=classes,
            )

            seed_rows.append(
                {
                    "dataset": canonical_dataset,
                    "strategy": strategy,
                    "seed": int(seed),
                    **metrics,
                },
            )

    seed_metrics = pd.DataFrame(seed_rows)
    seed_metrics["strategy"] = pd.Categorical(
        seed_metrics["strategy"],
        categories=COMMITTEE_STRATEGIES,
        ordered=True,
    )
    seed_metrics = seed_metrics.sort_values(
        ["strategy", "seed"],
        ignore_index=True,
    )
    seed_metrics["strategy"] = seed_metrics["strategy"].astype(str)

    summary = _build_summary(
        seed_metrics,
    )

    selected_configuration_ids = {
        classifier: _selected_configuration_id(
            load_experiment_metadata(
                dataset_directory / classifier,
            ),
            classifier=classifier,
        )
        for classifier in COMPONENT_CLASSIFIERS
    }

    metadata = _build_metadata(
        dataset_name=canonical_dataset,
        seeds=test_seeds,
        weights=weights,
        selected_configuration_ids=selected_configuration_ids,
    )

    paths = CommitteeExperimentPaths.from_root(
        dataset_directory / COMMITTEE_DIRECTORY_NAME,
    )

    _persist_committee_artifacts(
        paths=paths,
        metadata=metadata,
        weights=weights,
        seed_metrics=seed_metrics,
        summary=summary,
    )

    return CommitteeExperimentResult(
        dataset_name=canonical_dataset,
        artifact_paths=paths,
        metadata=metadata,
        weights=weights,
        seed_metrics=seed_metrics,
        summary=summary,
    )


def run_all_committee_experiments(
    *,
    artifacts_directory: Path = ARTIFACT_ROOT,
) -> dict[str, CommitteeExperimentResult]:
    """Evaluate all predefined committee strategies for GENIS and ROSIDS."""
    return {
        dataset_name: run_dataset_committee(
            dataset_name=dataset_name,
            artifacts_directory=artifacts_directory,
        )
        for dataset_name in ("GENIS", "ROSIDS")
    }


# ----------------------------------------
# Artifact loading API
# ----------------------------------------


def load_committee_metadata(
    *,
    dataset_name: str,
    artifacts_directory: Path = ARTIFACT_ROOT,
) -> dict[str, object]:
    """Load persisted committee metadata for one dataset."""
    canonical_dataset = _normalize_dataset_name(dataset_name)
    paths = CommitteeExperimentPaths.from_root(
        artifacts_directory.expanduser().resolve()
        / canonical_dataset.lower()
        / COMMITTEE_DIRECTORY_NAME,
    )

    return dict(
        json.loads(
            paths.metadata.read_text(
                encoding="utf-8",
            ),
        ),
    )


def load_committee_weights(
    *,
    dataset_name: str,
    artifacts_directory: Path = ARTIFACT_ROOT,
) -> pd.DataFrame:
    """Load persisted validation-derived committee weights."""
    canonical_dataset = _normalize_dataset_name(dataset_name)
    paths = CommitteeExperimentPaths.from_root(
        artifacts_directory.expanduser().resolve()
        / canonical_dataset.lower()
        / COMMITTEE_DIRECTORY_NAME,
    )

    return pd.read_csv(
        paths.weights,
    )


def load_committee_seed_metrics(
    *,
    dataset_name: str,
    artifacts_directory: Path = ARTIFACT_ROOT,
) -> pd.DataFrame:
    """Load persisted seed-level committee metrics."""
    canonical_dataset = _normalize_dataset_name(dataset_name)
    paths = CommitteeExperimentPaths.from_root(
        artifacts_directory.expanduser().resolve()
        / canonical_dataset.lower()
        / COMMITTEE_DIRECTORY_NAME,
    )

    return pd.read_csv(
        paths.seed_metrics,
    )


def load_committee_summary(
    *,
    dataset_name: str,
    artifacts_directory: Path = ARTIFACT_ROOT,
) -> pd.DataFrame:
    """Load persisted mean-plus-standard-deviation committee results."""
    canonical_dataset = _normalize_dataset_name(dataset_name)
    paths = CommitteeExperimentPaths.from_root(
        artifacts_directory.expanduser().resolve()
        / canonical_dataset.lower()
        / COMMITTEE_DIRECTORY_NAME,
    )

    return pd.read_csv(
        paths.summary,
    )


# ----------------------------------------
# Command-line interface
# ----------------------------------------


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for committee evaluation."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the predefined committee strategies using persisted "
            "final-model test predictions."
        ),
    )
    parser.add_argument(
        "--dataset",
        choices=("genis", "rosids"),
        help="Evaluate only the selected dataset.",
    )
    return parser


def main() -> None:
    """Run the requested committee evaluation."""
    parser = _build_argument_parser()
    arguments = parser.parse_args()

    if arguments.dataset is None:
        results = run_all_committee_experiments()

        summary = pd.concat(
            (
                result.summary.assign(
                    dataset=result.dataset_name,
                )
                for result in results.values()
            ),
            ignore_index=True,
        )
        summary = summary.loc[
            :,
            ["dataset", "strategy", "seed_count", *COMMITTEE_METRIC_COLUMNS],
        ]
    else:
        result = run_dataset_committee(
            dataset_name=arguments.dataset,
        )
        summary = result.summary.copy()
        summary.insert(
            0,
            "dataset",
            result.dataset_name,
        )

    print()
    print(
        summary.to_string(
            index=False,
        ),
    )


if __name__ == "__main__":
    main()


__all__ = [
    "COMMITTEE_DIRECTORY_NAME",
    "COMMITTEE_METRIC_COLUMNS",
    "COMMITTEE_SEED_METRICS_FILE_NAME",
    "COMMITTEE_STRATEGIES",
    "COMMITTEE_SUMMARY_FILE_NAME",
    "COMMITTEE_WEIGHTS_FILE_NAME",
    "COMPONENT_CLASSIFIERS",
    "CommitteeExperimentPaths",
    "CommitteeExperimentResult",
    "load_committee_metadata",
    "load_committee_seed_metrics",
    "load_committee_summary",
    "load_committee_weights",
    "run_all_committee_experiments",
    "run_dataset_committee",
]
