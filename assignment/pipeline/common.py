"""Reusable machine-learning experiment engine."""

import hashlib
import json
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Final, Protocol, cast

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import RandomOverSampler
from imblearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
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
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import (
    FunctionTransformer,
    LabelEncoder,
    OneHotEncoder,
    label_binarize,
)
from xgboost import XGBClassifier

from definitions import SEEDS

# ----------------------------------------
# Constants
# ----------------------------------------

FeatureLabels = tuple[str, ...]
ParameterGrid = dict[str, Sequence[Any]]

ARTIFACT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent / "_artifacts"

CV_FOLDS: Final[int] = 3

CV_SEEDS: Final[tuple[int, ...]] = tuple(int(value) for value in SEEDS)

DEFAULT_VALIDATION_WORKERS: Final[int] = 8

RANDOM_OVER_SAMPLER: Final[str] = "random_over_sampler"

ARTIFACT_SCHEMA_VERSION: Final[int] = 2


DECISION_TREE_PARAM_GRID: Final[ParameterGrid] = {
    "sampler": (
        "passthrough",
        RANDOM_OVER_SAMPLER,
    ),
    "classifier__criterion": (
        "gini",
        "entropy",
    ),
    "classifier__max_depth": (
        10,
        20,
        None,
    ),
    "classifier__min_samples_split": (
        2,
        5,
        10,
    ),
    "classifier__min_samples_leaf": (
        1,
        5,
    ),
}


RANDOM_FOREST_PARAM_GRID: Final[ParameterGrid] = {
    "sampler": (
        "passthrough",
        RANDOM_OVER_SAMPLER,
    ),
    "classifier__n_estimators": (
        100,
        200,
    ),
    "classifier__max_depth": (
        10,
        20,
        None,
    ),
    "classifier__min_samples_split": (
        2,
        5,
        10,
    ),
    "classifier__min_samples_leaf": (
        1,
        5,
    ),
}


XGBOOST_PARAM_GRID: Final[ParameterGrid] = {
    "sampler": (
        "passthrough",
        RANDOM_OVER_SAMPLER,
    ),
    "classifier__n_estimators": (
        100,
        200,
    ),
    "classifier__max_depth": (
        3,
        6,
    ),
    "classifier__learning_rate": (
        0.05,
        0.1,
    ),
    "classifier__min_child_weight": (
        1,
        5,
    ),
    "classifier__subsample": (
        0.8,
        1.0,
    ),
}


# ----------------------------------------
# Artifact paths
# ----------------------------------------


@dataclass(frozen=True, slots=True)
class ExperimentArtifactPaths:
    """Paths belonging to one dataset/classifier experiment."""

    root: Path

    validation_checkpoint: Path
    validation_folds: Path
    validation_seeds: Path
    validation_configurations: Path

    metadata: Path

    models_directory: Path
    predictions_directory: Path
    feature_importances_directory: Path

    @classmethod
    def from_root(
        cls,
        root: Path,
    ) -> ExperimentArtifactPaths:  # noqa: F821
        """Create all paths beneath one experiment directory."""
        return cls(
            root=root,
            validation_checkpoint=root / "validation_checkpoint.json",
            validation_folds=root / "validation_folds.csv",
            validation_seeds=root / "validation_seeds.csv",
            validation_configurations=root / "validation_configurations.csv",
            metadata=root / "metadata.json",
            models_directory=root / "models",
            predictions_directory=root / "test_predictions",
            feature_importances_directory=root / "feature_importances",
        )

    def ensure_directories(self) -> None:
        """Create directories required by the experiment."""
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.models_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.predictions_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.feature_importances_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def remove_validation_checkpoint(self) -> None:
        """Remove the transient validation checkpoint after completion."""
        self.validation_checkpoint.unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    """Reference to the completed experiment artifacts."""

    artifact_paths: ExperimentArtifactPaths
    selected_configuration: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FittedClassificationModel:
    """Persisted final model with original target-label decoding."""

    pipeline: Pipeline
    classes: tuple[str, ...]
    seed: int
    configuration_id: str

    @property
    def classes_(self) -> np.ndarray:
        """Expose original class labels in sklearn-like form."""
        return np.asarray(
            self.classes,
            dtype=object,
        )

    def predict(
        self,
        features: pd.DataFrame,
    ) -> np.ndarray:
        """Predict original, human-readable class labels."""
        encoded_predictions = np.asarray(
            self.pipeline.predict(features),
            dtype=int,
        )

        classes = np.asarray(
            self.classes,
            dtype=object,
        )

        return classes[encoded_predictions]

    def predict_proba(
        self,
        features: pd.DataFrame,
    ) -> np.ndarray:
        """Return class probabilities in the order of ``classes_``."""
        return np.asarray(
            self.pipeline.predict_proba(features),
            dtype=float,
        )

    def feature_importances(self) -> np.ndarray:
        """Return the classifier's feature-importance values."""
        classifier = self.pipeline.named_steps["classifier"]

        if not hasattr(classifier, "feature_importances_"):
            raise TypeError(
                "The fitted classifier does not expose feature_importances_.",
            )

        return np.asarray(
            classifier.feature_importances_,
            dtype=float,
        )

    def transformed_feature_names(self) -> tuple[str, ...]:
        """Return names of features produced by the fitted preprocessor."""
        preprocessor = self.pipeline.named_steps["preprocessor"]

        return tuple(str(name) for name in preprocessor.get_feature_names_out())


# ----------------------------------------
# Preprocessing
# ----------------------------------------


def replace_non_finite_values(
    values: np.ndarray,
) -> np.ndarray:
    """Replace positive and negative infinity with NaN."""
    numeric_values = np.asarray(
        values,
        dtype=float,
    )

    return np.where(
        np.isfinite(numeric_values),
        numeric_values,
        np.nan,
    )


def build_numeric_pipeline() -> Pipeline:
    """Build numerical preprocessing."""
    return Pipeline(
        steps=[
            (
                "replace_non_finite",
                FunctionTransformer(
                    replace_non_finite_values,
                    feature_names_out="one-to-one",
                ),
            ),
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                ),
            ),
        ],
    )


def build_categorical_pipeline() -> Pipeline:
    """Build categorical preprocessing."""
    return Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent",
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ],
    )


def build_preprocessor(
    *,
    numerical_features: FeatureLabels,
    categorical_features: FeatureLabels,
) -> ColumnTransformer:
    """Build the preprocessing transformer."""
    transformers: list[tuple[str, Pipeline, FeatureLabels]] = []

    if numerical_features:
        transformers.append(
            (
                "numerical",
                build_numeric_pipeline(),
                numerical_features,
            ),
        )

    if categorical_features:
        transformers.append(
            (
                "categorical",
                build_categorical_pipeline(),
                categorical_features,
            ),
        )

    if not transformers:
        raise ValueError(
            "At least one numerical or categorical feature is required.",
        )

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )


def build_classification_pipeline(
    *,
    numerical_features: FeatureLabels,
    categorical_features: FeatureLabels,
    classifier: ClassifierMixin,
) -> Pipeline:
    """Build the complete final-training pipeline."""
    return Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    numerical_features=numerical_features,
                    categorical_features=categorical_features,
                ),
            ),
            (
                "sampler",
                "passthrough",
            ),
            (
                "classifier",
                classifier,
            ),
        ],
    )


# ----------------------------------------
# Classifiers
# ----------------------------------------


def build_xgboost_classifier() -> XGBClassifier:
    """Build the base XGBoost classifier."""
    return XGBClassifier(
        tree_method="hist",
        n_jobs=1,
        eval_metric="mlogloss",
        verbosity=0,
    )


# ----------------------------------------
# Parameter-grid utilities
# ----------------------------------------


def expand_parameter_grid(
    parameter_grid: ParameterGrid,
) -> tuple[dict[str, Any], ...]:
    """Expand a parameter grid into deterministic configurations."""
    parameter_names = tuple(parameter_grid)

    parameter_values = tuple(parameter_grid[name] for name in parameter_names)

    configurations = tuple(
        dict(
            zip(
                parameter_names,
                values,
                strict=True,
            ),
        )
        for values in product(
            *parameter_values,
        )
    )

    return configurations


def _json_default(value: object) -> str:
    """Convert otherwise unsupported values to stable JSON strings."""
    return str(value)


def _configuration_signature(
    configuration: dict[str, Any],
) -> str:
    """Create a stable ID for a hyperparameter configuration."""
    serialized_configuration = json.dumps(
        configuration,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )

    return hashlib.sha256(
        serialized_configuration.encode("utf-8"),
    ).hexdigest()[:12]


def _attach_configuration_ids(
    configurations: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Add deterministic IDs without modifying the supplied dictionaries."""
    identified_configurations: list[dict[str, Any]] = []

    for configuration in configurations:
        identified_configurations.append(
            {
                "configuration_id": _configuration_signature(
                    configuration,
                ),
                "parameters": dict(configuration),
            },
        )

    return tuple(
        identified_configurations,
    )


def _validate_parameter_grid(
    parameter_grid: ParameterGrid,
) -> None:
    """Validate assumptions required by the experiment engine."""
    if not parameter_grid:
        raise ValueError(
            "Parameter grid must contain at least one parameter.",
        )

    if "sampler" not in parameter_grid:
        raise ValueError(
            "Parameter grid must define the 'sampler' parameter.",
        )

    sampler_options = set(
        parameter_grid["sampler"],
    )

    unknown_sampler_options = sampler_options - {
        "passthrough",
        RANDOM_OVER_SAMPLER,
    }

    if unknown_sampler_options:
        raise ValueError(
            f"Unknown sampler options: {sorted(unknown_sampler_options)!r}.",
        )

    if "classifier__random_state" in parameter_grid:
        raise ValueError(
            "classifier__random_state must not be tuned. "
            "The experiment seed controls classifier randomness.",
        )


# ----------------------------------------
# Target handling
# ----------------------------------------


def _fit_target_encoder(
    target: pd.Series,
) -> LabelEncoder:
    """Fit the target encoder using training labels only."""
    normalized_target = target.astype("string")

    if normalized_target.isna().any():
        raise ValueError(
            "Target contains missing values.",
        )

    encoder = LabelEncoder()

    encoder.fit(
        normalized_target.to_numpy(),
    )

    return encoder


def _encode_target(
    target: pd.Series,
    encoder: LabelEncoder,
) -> np.ndarray:
    """Encode a target series using an existing training encoder."""
    normalized_target = target.astype("string")

    if normalized_target.isna().any():
        raise ValueError(
            "Target contains missing values.",
        )

    try:
        return np.asarray(
            encoder.transform(
                normalized_target.to_numpy(),
            ),
            dtype=np.int64,
        )
    except ValueError as error:
        raise ValueError(
            "Target contains a class that was not present in the training target.",
        ) from error


# ----------------------------------------
# Fold preparation
# ----------------------------------------


@dataclass(frozen=True, slots=True)
class PreparedFold:
    """Preprocessed data for one CV fold."""

    X_train: np.ndarray
    y_train: np.ndarray
    X_validation: np.ndarray
    y_validation: np.ndarray


def _prepare_fold(
    *,
    features: pd.DataFrame,
    target: np.ndarray,
    train_indices: np.ndarray,
    validation_indices: np.ndarray,
    numerical_features: FeatureLabels,
    categorical_features: FeatureLabels,
) -> PreparedFold:
    """Fit preprocessing on one training fold and transform both partitions."""
    X_train = features.iloc[train_indices]
    X_validation = features.iloc[validation_indices]

    y_train = target[train_indices]
    y_validation = target[validation_indices]

    preprocessor = build_preprocessor(
        numerical_features=numerical_features,
        categorical_features=categorical_features,
    )

    transformed_X_train = np.asarray(
        preprocessor.fit_transform(
            X_train,
        ),
    )

    transformed_X_validation = np.asarray(
        preprocessor.transform(
            X_validation,
        ),
    )

    return PreparedFold(
        X_train=transformed_X_train,
        y_train=np.asarray(
            y_train,
            dtype=np.int64,
        ),
        X_validation=transformed_X_validation,
        y_validation=np.asarray(
            y_validation,
            dtype=np.int64,
        ),
    )


def _build_resampled_training_data(
    prepared_fold: PreparedFold,
    *,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Perform random over-sampling exactly once for a fold."""
    sampler = RandomOverSampler(
        random_state=seed,
    )

    resampled_data = sampler.fit_resample(
        prepared_fold.X_train,
        prepared_fold.y_train,
    )

    X_resampled = np.asarray(
        resampled_data[0],
    )

    y_resampled = np.asarray(
        resampled_data[1],
        dtype=np.int64,
    )

    return (
        X_resampled,
        y_resampled,
    )


# ----------------------------------------
# CV model evaluation
# ----------------------------------------


class ClassifierEstimator(Protocol):
    """Interface required by the validation engine."""

    def set_params(self, **params: Any) -> Any:
        """Set estimator parameters."""
        ...

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Any:
        """Fit the estimator."""
        ...

    def predict(
        self,
        X: np.ndarray,
    ) -> np.ndarray:
        """Predict class labels."""
        ...

    def predict_proba(
        self,
        X: np.ndarray,
    ) -> np.ndarray:
        """Predict class probabilities."""
        ...


VALIDATION_METRIC_COLUMNS: Final[tuple[str, ...]] = (
    "accuracy",
    "precision",
    "recall",
    "macro_f1",
    "roc_auc",
    "pr_auc",
    "mcc",
    "balanced_accuracy",
)


def _calculate_roc_auc(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> float:
    """Calculate macro ROC-AUC for binary or multiclass targets."""
    class_count = probabilities.shape[1]

    if class_count == 2:
        return float(
            roc_auc_score(
                y_true,
                probabilities[:, 1],
            ),
        )

    return float(
        roc_auc_score(
            y_true,
            probabilities,
            multi_class="ovr",
            average="macro",
            labels=np.arange(class_count),
        ),
    )


def _calculate_pr_auc(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> float:
    """Calculate macro PR-AUC for binary or multiclass targets."""
    class_count = probabilities.shape[1]

    if class_count == 2:
        return float(
            average_precision_score(
                y_true,
                probabilities[:, 1],
            ),
        )

    binary_targets = label_binarize(
        y_true,
        classes=np.arange(class_count),
    )

    return float(
        average_precision_score(
            binary_targets,
            probabilities,
            average="macro",
        ),
    )


def _calculate_validation_metrics(
    *,
    y_true: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray,
) -> dict[str, float]:
    """Calculate every scalar validation metric persisted by the engine."""
    metrics = {
        "accuracy": accuracy_score(
            y_true,
            predictions,
        ),
        "precision": precision_score(
            y_true,
            predictions,
            average="macro",
            zero_division=0,
        ),
        "recall": recall_score(
            y_true,
            predictions,
            average="macro",
            zero_division=0,
        ),
        "macro_f1": f1_score(
            y_true,
            predictions,
            average="macro",
            zero_division=0,
        ),
        "roc_auc": _calculate_roc_auc(
            y_true,
            probabilities,
        ),
        "pr_auc": _calculate_pr_auc(
            y_true,
            probabilities,
        ),
        "mcc": matthews_corrcoef(
            y_true,
            predictions,
        ),
        "balanced_accuracy": balanced_accuracy_score(
            y_true,
            predictions,
        ),
    }

    result = {name: float(value) for name, value in metrics.items()}

    missing_metrics = set(VALIDATION_METRIC_COLUMNS) - set(result)
    if missing_metrics:
        raise RuntimeError(
            f"Validation metrics were not calculated: {sorted(missing_metrics)!r}."
        )

    return result


def _fit_configuration_on_fold(
    *,
    configuration: dict[str, Any],
    classifier: BaseEstimator,
    seed: int,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    X_resampled: np.ndarray | None,
    y_resampled: np.ndarray | None,
) -> dict[str, float]:
    """Fit and score one configuration on one prepared fold."""
    classifier_estimator = cast(
        ClassifierEstimator,
        clone(classifier),
    )

    classifier_estimator.set_params(
        **{
            key.removeprefix("classifier__"): value
            for key, value in configuration.items()
            if key.startswith("classifier__")
        },
    )

    classifier_estimator.set_params(
        random_state=seed,
    )

    if configuration["sampler"] == RANDOM_OVER_SAMPLER:
        if X_resampled is None or y_resampled is None:
            raise RuntimeError(
                "Resampled training data was not prepared.",
            )

        fitting_X = X_resampled
        fitting_y = y_resampled
    else:
        fitting_X = X_train
        fitting_y = y_train

    classifier_estimator.fit(
        fitting_X,
        fitting_y,
    )

    predictions = np.asarray(
        classifier_estimator.predict(
            X_validation,
        ),
        dtype=np.int64,
    )

    probabilities = np.asarray(
        classifier_estimator.predict_proba(
            X_validation,
        ),
        dtype=float,
    )

    if probabilities.ndim != 2 or probabilities.shape[0] != len(y_validation):
        raise ValueError(
            "Classifier probabilities must be a 2D array with one row "
            "per validation observation."
        )

    return _calculate_validation_metrics(
        y_true=y_validation,
        predictions=predictions,
        probabilities=probabilities,
    )


def _evaluate_fold(
    *,
    configurations: Sequence[dict[str, Any]],
    classifier: BaseEstimator,
    seed: int,
    prepared_fold: PreparedFold,
    X_resampled: np.ndarray | None,
    y_resampled: np.ndarray | None,
    executor: ThreadPoolExecutor | None,
) -> dict[str, dict[str, float]]:
    """Evaluate every active configuration on one prepared fold."""

    def evaluate(
        identified_configuration: dict[str, Any],
    ) -> tuple[str, dict[str, float]]:
        configuration_id = str(
            identified_configuration["configuration_id"],
        )

        configuration = identified_configuration["parameters"]

        metrics = _fit_configuration_on_fold(
            configuration=configuration,
            classifier=classifier,
            seed=seed,
            X_train=prepared_fold.X_train,
            y_train=prepared_fold.y_train,
            X_validation=prepared_fold.X_validation,
            y_validation=prepared_fold.y_validation,
            X_resampled=X_resampled,
            y_resampled=y_resampled,
        )

        return configuration_id, metrics

    if executor is None:
        results = tuple(
            evaluate(
                configuration,
            )
            for configuration in configurations
        )
    else:
        results = tuple(
            executor.map(
                evaluate,
                configurations,
            ),
        )

    return {configuration_id: metrics for configuration_id, metrics in results}


# ----------------------------------------
# Validation checkpointing
# ----------------------------------------


def _load_validation_checkpoint(
    path: Path,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Load the validation checkpoint."""
    if not path.exists():
        return {}

    payload = json.loads(
        path.read_text(
            encoding="utf-8",
        ),
    )

    if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported validation checkpoint schema in '{path}'.",
        )

    return dict(
        payload.get(
            "results",
            {},
        ),
    )


def _save_validation_checkpoint(
    path: Path,
    results: dict[str, dict[str, dict[str, Any]]],
) -> None:
    """Atomically save the validation checkpoint."""
    payload = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "results": results,
    }

    _atomic_write_json(
        path,
        payload,
    )


def _update_validation_checkpoint(
    *,
    checkpoint: dict[str, dict[str, dict[str, Any]]],
    seed: int,
    seed_metrics: dict[str, list[dict[str, float]]],
    configurations: Sequence[dict[str, Any]],
) -> None:
    """Insert completed seed results and all fold metrics into the checkpoint."""
    for identified_configuration in configurations:
        configuration_id = str(
            identified_configuration["configuration_id"],
        )

        fold_metrics = tuple(
            {name: float(value) for name, value in metrics.items()}
            for metrics in seed_metrics[configuration_id]
        )

        mean_metrics = {
            metric_name: float(
                np.mean(
                    [metrics[metric_name] for metrics in fold_metrics],
                ),
            )
            for metric_name in VALIDATION_METRIC_COLUMNS
        }

        checkpoint.setdefault(
            configuration_id,
            {},
        )

        checkpoint[configuration_id][str(seed)] = {
            "fold_metrics": fold_metrics,
            "mean_metrics": mean_metrics,
        }


# ----------------------------------------
# Validation aggregation
# ----------------------------------------


def _build_validation_fold_results(
    *,
    checkpoint: dict[str, dict[str, dict[str, Any]]],
    configuration_lookup: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Build one row per configuration, seed, and fold with all metrics."""
    rows: list[dict[str, Any]] = []

    for configuration_id, seed_results in checkpoint.items():
        parameters = configuration_lookup[configuration_id]

        for seed_string, seed_result in seed_results.items():
            seed = int(seed_string)

            for fold, metrics in enumerate(
                seed_result["fold_metrics"],
                start=1,
            ):
                rows.append(
                    {
                        "configuration_id": configuration_id,
                        "seed": seed,
                        "fold": fold,
                        **{
                            metric_name: float(metrics[metric_name])
                            for metric_name in VALIDATION_METRIC_COLUMNS
                        },
                        **parameters,
                    },
                )

    return pd.DataFrame(rows)


def _build_validation_seed_results(
    *,
    checkpoint: dict[str, dict[str, dict[str, Any]]],
    configuration_lookup: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Build one row per configuration and seed with fold means for all metrics."""
    rows: list[dict[str, Any]] = []

    for configuration_id, seed_results in checkpoint.items():
        parameters = configuration_lookup[configuration_id]

        for seed_string, seed_result in seed_results.items():
            rows.append(
                {
                    "configuration_id": configuration_id,
                    "seed": int(seed_string),
                    **{
                        f"mean_{metric_name}": float(
                            seed_result["mean_metrics"][metric_name],
                        )
                        for metric_name in VALIDATION_METRIC_COLUMNS
                    },
                    **parameters,
                },
            )

    return pd.DataFrame(rows)


def _build_validation_configuration_results(
    *,
    checkpoint: dict[str, dict[str, dict[str, Any]]],
    configuration_lookup: dict[str, dict[str, Any]],
    seeds_to_report: Sequence[int],
) -> pd.DataFrame:
    """Build one row per configuration with mean/std across seed-level means."""
    rows: list[dict[str, Any]] = []

    for configuration_id, seed_results in checkpoint.items():
        row: dict[str, Any] = {
            "configuration_id": configuration_id,
            **configuration_lookup[configuration_id],
        }

        for seed in seeds_to_report:
            seed_result = seed_results.get(
                str(seed),
            )

            if seed_result is None:
                raise ValueError(
                    f"Configuration '{configuration_id}' is missing "
                    f"validation results for seed {seed}.",
                )

            row[f"seed_{seed}_macro_f1"] = float(
                seed_result["mean_metrics"]["macro_f1"],
            )

        for metric_name in VALIDATION_METRIC_COLUMNS:
            seed_values = [
                float(seed_results[str(seed)]["mean_metrics"][metric_name])
                for seed in seeds_to_report
            ]

            row[f"{metric_name}_mean"] = float(
                np.mean(seed_values),
            )
            row[f"{metric_name}_std"] = float(
                np.std(
                    seed_values,
                    ddof=1,
                )
                if len(seed_values) > 1
                else 0.0
            )

        rows.append(row)

    return pd.DataFrame(rows).sort_values(
        by=[
            "macro_f1_mean",
            "macro_f1_std",
            "configuration_id",
        ],
        ascending=[
            False,
            True,
            True,
        ],
        ignore_index=True,
    )


def select_best_configuration(
    validation_results: pd.DataFrame,
    configurations: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Select the best configuration while preserving parameter types."""
    if validation_results.empty:
        raise ValueError(
            "Validation results are empty.",
        )

    if not configurations:
        raise ValueError(
            "No configurations were provided.",
        )

    macro_f1_values = validation_results["macro_f1_mean"].to_numpy(
        dtype=float,
    )

    best_position = int(
        np.argmax(
            macro_f1_values,
        ),
    )

    configuration_ids = validation_results["configuration_id"].to_numpy(
        dtype=object,
    )

    best_configuration_id = str(
        configuration_ids[best_position],
    )

    try:
        matching_configuration = next(
            configuration
            for configuration in configurations
            if configuration["configuration_id"] == best_configuration_id
        )
    except StopIteration as error:
        raise ValueError(
            "The selected configuration ID does not exist in the "
            "original configuration definitions.",
        ) from error

    macro_f1_std_values = validation_results["macro_f1_std"].to_numpy(
        dtype=float,
    )

    selected_row = validation_results.iloc[best_position]

    metrics = {
        metric_name: {
            "mean": float(selected_row[f"{metric_name}_mean"]),
            "std": float(selected_row[f"{metric_name}_std"]),
        }
        for metric_name in VALIDATION_METRIC_COLUMNS
    }

    return {
        "configuration_id": best_configuration_id,
        "parameters": dict(
            matching_configuration["parameters"],
        ),
        "metrics": metrics,
        "macro_f1_mean": float(
            macro_f1_values[best_position],
        ),
        "macro_f1_std": float(
            macro_f1_std_values[best_position],
        ),
    }


# ----------------------------------------
# Final-model training
# ----------------------------------------


def _resolve_final_pipeline(
    *,
    base_pipeline: Pipeline,
    configuration: dict[str, Any],
    seed: int,
) -> Pipeline:
    """Create a clean final pipeline for one seed."""
    final_pipeline = clone(
        base_pipeline,
    )

    final_pipeline.set_params(
        sampler=(
            RandomOverSampler(
                random_state=seed,
            )
            if configuration["sampler"] == RANDOM_OVER_SAMPLER
            else "passthrough"
        ),
    )

    classifier_parameters = {
        key: value
        for key, value in configuration.items()
        if key.startswith("classifier__")
    }

    final_pipeline.set_params(
        **classifier_parameters,
    )

    final_pipeline.set_params(
        classifier__random_state=seed,
    )

    return final_pipeline


def _get_transformed_feature_mapping(
    preprocessor: ColumnTransformer,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return transformed feature names and their original feature labels."""
    transformed_feature_names = tuple(
        str(name) for name in preprocessor.get_feature_names_out()
    )

    original_feature_labels: list[str] = []

    for transformer_name, transformer, columns in preprocessor.transformers_:
        if transformer_name == "remainder":
            continue

        column_labels = tuple(str(column) for column in columns)

        if transformer == "drop":
            continue

        if transformer == "passthrough":
            original_feature_labels.extend(
                column_labels,
            )
            continue

        if transformer_name == "categorical":
            if not isinstance(
                transformer,
                Pipeline,
            ):
                raise TypeError(
                    "Categorical transformer is not the expected pipeline.",
                )

            encoder = transformer.named_steps["encoder"]

            categories = encoder.categories_

            for feature_label, category_values in zip(
                column_labels,
                categories,
                strict=True,
            ):
                original_feature_labels.extend(feature_label for _ in category_values)

            continue

        original_feature_labels.extend(
            column_labels,
        )

    if len(transformed_feature_names) != len(
        original_feature_labels,
    ):
        raise ValueError(
            "The number of transformed feature names does not match "
            "the original-feature mapping.",
        )

    return (
        transformed_feature_names,
        tuple(original_feature_labels),
    )


def _build_feature_importance_table(
    model: FittedClassificationModel,
) -> pd.DataFrame:
    """Create transformed- and original-feature importance data."""
    preprocessor = model.pipeline.named_steps["preprocessor"]

    (
        transformed_feature_names,
        original_feature_labels,
    ) = _get_transformed_feature_mapping(
        preprocessor,
    )

    importances = model.feature_importances()

    if len(importances) != len(transformed_feature_names):
        raise ValueError(
            "Classifier feature-importance count does not match "
            "the transformed feature count.",
        )

    transformed_rows = pd.DataFrame(
        {
            "seed": model.seed,
            "configuration_id": model.configuration_id,
            "importance_level": "transformed_feature",
            "transformed_feature": transformed_feature_names,
            "original_feature": original_feature_labels,
            "importance": importances,
        },
    )

    original_rows = (
        transformed_rows.groupby(
            [
                "seed",
                "configuration_id",
                "original_feature",
            ],
            as_index=False,
        )
        .agg(
            importance=("importance", "sum"),
        )
        .assign(
            importance_level="original_feature",
            transformed_feature=lambda frame: pd.Series(
                [None] * len(frame),
                dtype="object",
                index=frame.index,
            ),
        )
    )

    return pd.concat(
        [
            transformed_rows,
            original_rows[
                [
                    "seed",
                    "configuration_id",
                    "importance_level",
                    "transformed_feature",
                    "original_feature",
                    "importance",
                ]
            ],
        ],
        ignore_index=True,
    )


# ----------------------------------------
# Persistence helpers
# ----------------------------------------


def _atomic_write_json(
    path: Path,
    payload: object,
) -> None:
    """Atomically write a JSON file."""
    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp",
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(
        path,
    )


def _atomic_write_dataframe(
    data_frame: pd.DataFrame,
    path: Path,
) -> None:
    """Atomically write a DataFrame as CSV."""
    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp",
    )

    data_frame.to_csv(
        temporary_path,
        index=False,
        float_format="%.12g",
    )

    temporary_path.replace(
        path,
    )


def _atomic_joblib_dump(
    value: object,
    path: Path,
) -> None:
    """Atomically serialize a Python object with joblib."""
    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp",
    )

    joblib.dump(
        value,
        temporary_path,
        compress=3,
    )

    temporary_path.replace(
        path,
    )


# ----------------------------------------
# Final artifacts
# ----------------------------------------


def _save_final_model_artifacts(
    *,
    model: FittedClassificationModel,
    test_features: pd.DataFrame,
    test_target: pd.Series,
    target_encoder: LabelEncoder,
    paths: ExperimentArtifactPaths,
) -> None:
    """Save one final model, its predictions, and feature importances."""
    model_path = paths.models_directory / f"seed_{model.seed}.joblib"

    prediction_path = paths.predictions_directory / f"seed_{model.seed}.csv"

    feature_importance_path = (
        paths.feature_importances_directory / f"seed_{model.seed}.csv"
    )

    _atomic_joblib_dump(
        model,
        model_path,
    )

    predictions = model.predict(
        test_features,
    )

    probabilities = model.predict_proba(
        test_features,
    )

    encoded_actual_target = _encode_target(
        test_target,
        target_encoder,
    )

    actual_target = np.asarray(
        target_encoder.inverse_transform(
            encoded_actual_target,
        ),
        dtype=object,
    )

    prediction_data: dict[str, object] = {
        "seed": np.full(
            len(test_features),
            model.seed,
            dtype=np.int64,
        ),
        "row_index": np.asarray(
            test_features.index,
        ),
        "actual_class": actual_target,
        "predicted_class": predictions,
    }

    for class_index, class_label in enumerate(
        model.classes,
    ):
        prediction_data[f"probability_{class_index}_{class_label}"] = probabilities[
            :, class_index
        ]

    _atomic_write_dataframe(
        pd.DataFrame(
            prediction_data,
        ),
        prediction_path,
    )

    feature_importance_data = _build_feature_importance_table(
        model,
    )

    _atomic_write_dataframe(
        feature_importance_data,
        feature_importance_path,
    )


def _fit_final_models(
    *,
    base_pipeline: Pipeline,
    configuration: dict[str, Any],
    configuration_id: str,
    train_features: pd.DataFrame,
    train_target: pd.Series,
    test_features: pd.DataFrame,
    test_target: pd.Series,
    seeds_to_use: Sequence[int],
    paths: ExperimentArtifactPaths,
) -> None:
    """Fit the selected configuration on all training data for every seed."""
    target_encoder = _fit_target_encoder(
        train_target,
    )

    encoded_train_target = _encode_target(
        train_target,
        target_encoder,
    )

    encoded_test_target = _encode_target(
        test_target,
        target_encoder,
    )

    del encoded_test_target

    for seed in seeds_to_use:
        model_path = paths.models_directory / f"seed_{seed}.joblib"

        prediction_path = paths.predictions_directory / f"seed_{seed}.csv"

        feature_importance_path = (
            paths.feature_importances_directory / f"seed_{seed}.csv"
        )

        if (
            model_path.exists()
            and prediction_path.exists()
            and feature_importance_path.exists()
        ):
            continue

        final_pipeline = _resolve_final_pipeline(
            base_pipeline=base_pipeline,
            configuration=configuration,
            seed=seed,
        )

        final_pipeline.fit(
            train_features,
            encoded_train_target,
        )

        fitted_model = FittedClassificationModel(
            pipeline=final_pipeline,
            classes=tuple(str(label) for label in target_encoder.classes_),
            seed=int(seed),
            configuration_id=configuration_id,
        )

        _save_final_model_artifacts(
            model=fitted_model,
            test_features=test_features,
            test_target=test_target,
            target_encoder=target_encoder,
            paths=paths,
        )

        print(
            f"Final model completed: seed={seed}",
        )


# ----------------------------------------
# Experiment signature and metadata
# ----------------------------------------


def _build_experiment_signature(
    *,
    dataset_name: str,
    classifier_name: str,
    base_pipeline: Pipeline,
    parameter_grid: ParameterGrid,
    numerical_features: FeatureLabels,
    categorical_features: FeatureLabels,
    folds: int,
    seeds_to_use: Sequence[int],
) -> str:
    """Build an identifier for the complete experiment definition."""
    classifier = base_pipeline.named_steps["classifier"]

    payload = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "dataset_name": dataset_name,
        "classifier_name": classifier_name,
        "classifier_parameters": classifier.get_params(
            deep=False,
        ),
        "parameter_grid": parameter_grid,
        "numerical_features": numerical_features,
        "categorical_features": categorical_features,
        "folds": folds,
        "seeds": tuple(int(seed) for seed in seeds_to_use),
    }

    serialized_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )

    return hashlib.sha256(
        serialized_payload.encode("utf-8"),
    ).hexdigest()


def _save_metadata(
    *,
    paths: ExperimentArtifactPaths,
    dataset_name: str,
    classifier_name: str,
    experiment_signature: str,
    parameter_grid_size: int,
    numerical_features: FeatureLabels,
    categorical_features: FeatureLabels,
    folds: int,
    seeds_to_use: Sequence[int],
    train_row_count: int,
    test_row_count: int,
    selected_configuration: dict[str, Any],
) -> None:
    """Save final experiment metadata."""
    payload = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "status": "complete",
        "dataset_name": dataset_name,
        "classifier_name": classifier_name,
        "experiment_signature": experiment_signature,
        "validation_metric": "macro_f1",
        "validation_metrics": VALIDATION_METRIC_COLUMNS,
        "cross_validation_folds": folds,
        "cross_validation_seeds": tuple(int(seed) for seed in seeds_to_use),
        "parameter_grid_size": parameter_grid_size,
        "numerical_features": numerical_features,
        "categorical_features": categorical_features,
        "training_row_count": train_row_count,
        "test_row_count": test_row_count,
        "selected_configuration": selected_configuration,
    }

    _atomic_write_json(
        paths.metadata,
        payload,
    )


# ----------------------------------------
# Main experiment engine
# ----------------------------------------


def run_classifier_experiment(
    *,
    dataset_name: str,
    classifier_name: str,
    base_pipeline: Pipeline,
    parameter_grid: ParameterGrid,
    train_features: pd.DataFrame,
    train_target: pd.Series,
    test_features: pd.DataFrame,
    test_target: pd.Series,
    numerical_features: FeatureLabels,
    categorical_features: FeatureLabels,
    artifact_directory: Path | None = None,
    folds: int = CV_FOLDS,
    seeds_to_use: Sequence[int] = CV_SEEDS,
    max_workers: int = DEFAULT_VALIDATION_WORKERS,
) -> ExperimentResult:
    """Run, checkpoint, persist, and resume one classifier experiment.

    The expensive validation stage performs preprocessing once per
    seed/fold, reuses the transformed fold data across configurations,
    and performs random over-sampling once per seed/fold when required.

    After validation, the selected configuration is fitted on all
    training data once for every fixed seed. Those final models, test
    predictions, probabilities, and feature importances are persisted.

    The held-out test target is never used for hyperparameter selection.
    """
    if folds < 2:
        raise ValueError(
            "folds must be at least 2.",
        )

    if max_workers < 1:
        raise ValueError(
            "max_workers must be at least 1.",
        )

    seeds_to_use = tuple(int(seed) for seed in seeds_to_use)

    if not seeds_to_use:
        raise ValueError(
            "At least one validation seed is required.",
        )

    if len(train_features) != len(train_target):
        raise ValueError(
            "train_features and train_target must have the same length.",
        )

    if len(test_features) != len(test_target):
        raise ValueError(
            "test_features and test_target must have the same length.",
        )

    missing_training_features = set(
        numerical_features + categorical_features,
    ) - set(train_features.columns)

    if missing_training_features:
        raise ValueError(
            "The training DataFrame is missing predictor features: "
            f"{sorted(missing_training_features)!r}.",
        )

    missing_test_features = set(
        numerical_features + categorical_features,
    ) - set(test_features.columns)

    if missing_test_features:
        raise ValueError(
            "The test DataFrame is missing predictor features: "
            f"{sorted(missing_test_features)!r}.",
        )

    _validate_parameter_grid(
        parameter_grid,
    )

    configurations = _attach_configuration_ids(
        expand_parameter_grid(
            parameter_grid,
        ),
    )

    configuration_lookup = {
        str(configuration["configuration_id"]): configuration["parameters"]
        for configuration in configurations
    }

    if artifact_directory is None:
        artifact_directory = ARTIFACT_ROOT / dataset_name.lower() / classifier_name

    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    paths.ensure_directories()

    experiment_signature = _build_experiment_signature(
        dataset_name=dataset_name,
        classifier_name=classifier_name,
        base_pipeline=base_pipeline,
        parameter_grid=parameter_grid,
        numerical_features=numerical_features,
        categorical_features=categorical_features,
        folds=folds,
        seeds_to_use=seeds_to_use,
    )

    if paths.metadata.exists():
        existing_metadata = json.loads(
            paths.metadata.read_text(
                encoding="utf-8",
            ),
        )

        if existing_metadata.get("experiment_signature") != experiment_signature:
            raise ValueError(
                f"Existing artifacts at '{paths.root}' belong to a "
                "different experiment definition. Use a new artifact "
                "directory or remove the stale artifacts before rerunning.",
            )

        if existing_metadata.get("status") == "complete":
            # paths.remove_validation_checkpoint()
            selected_configuration = existing_metadata["selected_configuration"]

            return ExperimentResult(
                artifact_paths=paths,
                selected_configuration=selected_configuration,
            )

    checkpoint = _load_validation_checkpoint(
        paths.validation_checkpoint,
    )

    classifier = base_pipeline.named_steps["classifier"]

    encoded_target_encoder = _fit_target_encoder(
        train_target,
    )

    encoded_train_target = _encode_target(
        train_target,
        encoded_target_encoder,
    )

    stratified_splitters = {
        seed: StratifiedKFold(
            n_splits=folds,
            shuffle=True,
            random_state=seed,
        )
        for seed in seeds_to_use
    }

    executor: ThreadPoolExecutor | None = None

    if max_workers > 1:
        executor = ThreadPoolExecutor(
            max_workers=max_workers,
        )

    try:
        for seed in seeds_to_use:
            active_configurations = tuple(
                configuration
                for configuration in configurations
                if str(seed)
                not in checkpoint.get(
                    str(configuration["configuration_id"]),
                    {},
                )
            )

            if not active_configurations:
                continue

            fold_metrics: dict[str, list[dict[str, float]]] = {
                str(configuration["configuration_id"]): []
                for configuration in active_configurations
            }

            cross_validator = stratified_splitters[seed]

            for fold_number, (
                train_indices,
                validation_indices,
            ) in enumerate(
                cross_validator.split(
                    train_features,
                    encoded_train_target,
                ),
                start=1,
            ):
                print(
                    f"{dataset_name} / {classifier_name} — "
                    f"seed {seed} — fold {fold_number}/{folds}",
                )

                prepared_fold = _prepare_fold(
                    features=train_features,
                    target=encoded_train_target,
                    train_indices=np.asarray(
                        train_indices,
                        dtype=np.int64,
                    ),
                    validation_indices=np.asarray(
                        validation_indices,
                        dtype=np.int64,
                    ),
                    numerical_features=numerical_features,
                    categorical_features=categorical_features,
                )

                requires_random_over_sampling = any(
                    configuration["parameters"]["sampler"] == RANDOM_OVER_SAMPLER
                    for configuration in active_configurations
                )

                if requires_random_over_sampling:
                    X_resampled, y_resampled = _build_resampled_training_data(
                        prepared_fold,
                        seed=seed,
                    )
                else:
                    X_resampled = None
                    y_resampled = None

                fold_results = _evaluate_fold(
                    configurations=active_configurations,
                    classifier=classifier,
                    seed=seed,
                    prepared_fold=prepared_fold,
                    X_resampled=X_resampled,
                    y_resampled=y_resampled,
                    executor=executor,
                )

                for configuration_id, metrics in fold_results.items():
                    fold_metrics[configuration_id].append(
                        metrics,
                    )

            _update_validation_checkpoint(
                checkpoint=checkpoint,
                seed=seed,
                seed_metrics=fold_metrics,
                configurations=active_configurations,
            )

            _save_validation_checkpoint(
                paths.validation_checkpoint,
                checkpoint,
            )

            print(
                f"{dataset_name} / {classifier_name} — seed {seed} completed.",
            )

    finally:
        if executor is not None:
            executor.shutdown(
                wait=True,
            )

    validation_fold_results = _build_validation_fold_results(
        checkpoint=checkpoint,
        configuration_lookup=configuration_lookup,
    )

    validation_seed_results = _build_validation_seed_results(
        checkpoint=checkpoint,
        configuration_lookup=configuration_lookup,
    )

    validation_configuration_results = _build_validation_configuration_results(
        checkpoint=checkpoint,
        configuration_lookup=configuration_lookup,
        seeds_to_report=seeds_to_use,
    )

    _atomic_write_dataframe(
        validation_fold_results,
        paths.validation_folds,
    )

    _atomic_write_dataframe(
        validation_seed_results,
        paths.validation_seeds,
    )

    _atomic_write_dataframe(
        validation_configuration_results,
        paths.validation_configurations,
    )

    selected_configuration = select_best_configuration(
        validation_configuration_results,
        configurations,
    )

    print(
        f"{dataset_name} / {classifier_name} — validation completed.",
    )

    _fit_final_models(
        base_pipeline=base_pipeline,
        configuration=selected_configuration["parameters"],
        configuration_id=selected_configuration["configuration_id"],
        train_features=train_features,
        train_target=train_target,
        test_features=test_features,
        test_target=test_target,
        seeds_to_use=seeds_to_use,
        paths=paths,
    )

    _save_metadata(
        paths=paths,
        dataset_name=dataset_name,
        classifier_name=classifier_name,
        experiment_signature=experiment_signature,
        parameter_grid_size=len(configurations),
        numerical_features=numerical_features,
        categorical_features=categorical_features,
        folds=folds,
        seeds_to_use=seeds_to_use,
        train_row_count=len(train_features),
        test_row_count=len(test_features),
        selected_configuration=selected_configuration,
    )

    # paths.remove_validation_checkpoint()

    return ExperimentResult(
        artifact_paths=paths,
        selected_configuration=selected_configuration,
    )


# ----------------------------------------
# Artifact loading
# ----------------------------------------


def load_validation_fold_results(
    artifact_directory: Path,
) -> pd.DataFrame:
    """Load persisted fold-level validation results."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    return pd.read_csv(
        paths.validation_folds,
    )


def load_validation_seed_results(
    artifact_directory: Path,
) -> pd.DataFrame:
    """Load persisted seed-level validation results."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    return pd.read_csv(
        paths.validation_seeds,
    )


def load_validation_configuration_results(
    artifact_directory: Path,
) -> pd.DataFrame:
    """Load persisted configuration-level validation results."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    return pd.read_csv(
        paths.validation_configurations,
    )


def load_selected_configuration(
    artifact_directory: Path,
) -> dict[str, Any]:
    """Load the selected configuration recorded in experiment metadata."""
    metadata = load_experiment_metadata(
        artifact_directory,
    )

    selected_configuration = metadata.get(
        "selected_configuration",
    )

    if not isinstance(selected_configuration, dict):
        raise ValueError(
            "Experiment metadata does not contain a valid "
            "'selected_configuration' object.",
        )

    return dict(selected_configuration)


def load_experiment_metadata(
    artifact_directory: Path,
) -> dict[str, Any]:
    """Load experiment metadata."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    return dict(
        json.loads(
            paths.metadata.read_text(
                encoding="utf-8",
            ),
        ),
    )


def load_final_model(
    artifact_directory: Path,
    seed: int,
) -> FittedClassificationModel:
    """Load one persisted final model."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    model_path = paths.models_directory / f"seed_{seed}.joblib"

    return joblib.load(
        model_path,
    )


def load_final_models(
    artifact_directory: Path,
) -> dict[int, FittedClassificationModel]:
    """Load all persisted final models."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    model_paths = sorted(
        paths.models_directory.glob(
            "seed_*.joblib",
        ),
    )

    if not model_paths:
        raise FileNotFoundError(
            f"No final models were found in '{paths.models_directory}'.",
        )

    models: dict[int, FittedClassificationModel] = {}

    for model_path in model_paths:
        seed = int(
            model_path.stem.removeprefix(
                "seed_",
            ),
        )

        models[seed] = joblib.load(
            model_path,
        )

    return dict(
        sorted(
            models.items(),
        ),
    )


def load_test_predictions(
    artifact_directory: Path,
) -> pd.DataFrame:
    """Load and combine persisted test predictions from all seeds."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    prediction_paths = sorted(
        paths.predictions_directory.glob(
            "seed_*.csv",
        ),
    )

    if not prediction_paths:
        raise FileNotFoundError(
            "No persisted test predictions were found in "
            f"'{paths.predictions_directory}'.",
        )

    return pd.concat(
        (
            pd.read_csv(
                path,
            )
            for path in prediction_paths
        ),
        ignore_index=True,
    )


def load_feature_importances(
    artifact_directory: Path,
) -> pd.DataFrame:
    """Load and combine persisted feature-importance data."""
    paths = ExperimentArtifactPaths.from_root(
        artifact_directory,
    )

    feature_importance_paths = sorted(
        paths.feature_importances_directory.glob(
            "seed_*.csv",
        ),
    )

    if not feature_importance_paths:
        raise FileNotFoundError(
            "No persisted feature-importances were found in "
            f"'{paths.feature_importances_directory}'.",
        )

    return pd.concat(
        (
            pd.read_csv(
                path,
            )
            for path in feature_importance_paths
        ),
        ignore_index=True,
    )
