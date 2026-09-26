"""ROSIDS machine-learning experiment configuration."""

from pathlib import Path
from typing import Final

import pandas as pd
from imblearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from definitions import SEEDS
from pipeline.common import (
    ARTIFACT_ROOT,
    CV_FOLDS,
    DECISION_TREE_PARAM_GRID,
    DEFAULT_VALIDATION_WORKERS,
    RANDOM_FOREST_PARAM_GRID,
    XGBOOST_PARAM_GRID,
    ExperimentResult,
    ParameterGrid,
    build_classification_pipeline,
    build_xgboost_classifier,
    run_classifier_experiment,
)
from schema.common import FeatureSemanticType
from transformation.rosids import (
    TRANSFORMED_ROSIDS_SCHEMA,
    rosids_df_for_test,
    rosids_df_for_train,
)

# ----------------------------------------
# Dataset configuration
# ----------------------------------------

ROSIDS_DATASET_NAME: Final[str] = "ROSIDS"

ROSIDS_TARGET_FEATURE: Final[str] = TRANSFORMED_ROSIDS_SCHEMA.target_feature_label

ROSIDS_PREDICTOR_FEATURES: Final[tuple[str, ...]] = tuple(
    feature.label for feature in TRANSFORMED_ROSIDS_SCHEMA.predictor_features()
)

ROSIDS_NUMERICAL_FEATURES: Final[tuple[str, ...]] = tuple(
    feature.label
    for feature in TRANSFORMED_ROSIDS_SCHEMA.predictor_features()
    if feature.semantic_type
    in {
        FeatureSemanticType.NUMERIC,
        FeatureSemanticType.BINARY,
    }
)

ROSIDS_CATEGORICAL_FEATURES: Final[tuple[str, ...]] = tuple(
    feature.label
    for feature in TRANSFORMED_ROSIDS_SCHEMA.predictor_features()
    if feature.semantic_type is FeatureSemanticType.CATEGORICAL
)


ROSIDS_X_TRAIN: Final[pd.DataFrame] = rosids_df_for_train[
    list(ROSIDS_PREDICTOR_FEATURES)
].copy()


ROSIDS_Y_TRAIN: Final[pd.Series] = rosids_df_for_train[ROSIDS_TARGET_FEATURE].copy()

ROSIDS_X_TEST: Final[pd.DataFrame] = rosids_df_for_test[
    list(ROSIDS_PREDICTOR_FEATURES)
].copy()

ROSIDS_Y_TEST: Final[pd.Series] = rosids_df_for_test[ROSIDS_TARGET_FEATURE].copy()


# ----------------------------------------
# Artifact configuration
# ----------------------------------------

ROSIDS_ARTIFACT_ROOT: Final[Path] = ARTIFACT_ROOT / ROSIDS_DATASET_NAME.lower()


ROSIDS_VALIDATION_WORKERS: Final[int] = DEFAULT_VALIDATION_WORKERS


# ----------------------------------------
# Classifier configuration
# ----------------------------------------

ROSIDS_DECISION_TREE: Final[DecisionTreeClassifier] = DecisionTreeClassifier()

ROSIDS_RANDOM_FOREST: Final[RandomForestClassifier] = RandomForestClassifier(
    n_jobs=1,
)

ROSIDS_XGBOOST: Final = build_xgboost_classifier()


# ----------------------------------------
# Classification pipelines
# ----------------------------------------

ROSIDS_DECISION_TREE_PIPELINE: Final[Pipeline] = build_classification_pipeline(
    numerical_features=ROSIDS_NUMERICAL_FEATURES,
    categorical_features=ROSIDS_CATEGORICAL_FEATURES,
    classifier=ROSIDS_DECISION_TREE,
)

ROSIDS_RANDOM_FOREST_PIPELINE: Final[Pipeline] = build_classification_pipeline(
    numerical_features=ROSIDS_NUMERICAL_FEATURES,
    categorical_features=ROSIDS_CATEGORICAL_FEATURES,
    classifier=ROSIDS_RANDOM_FOREST,
)

ROSIDS_XGBOOST_PIPELINE: Final[Pipeline] = build_classification_pipeline(
    numerical_features=ROSIDS_NUMERICAL_FEATURES,
    categorical_features=ROSIDS_CATEGORICAL_FEATURES,
    classifier=ROSIDS_XGBOOST,
)


# ----------------------------------------
# Hyperparameter grids
# ----------------------------------------

ROSIDS_DECISION_TREE_PARAMETER_GRID: Final[ParameterGrid] = DECISION_TREE_PARAM_GRID

ROSIDS_RANDOM_FOREST_PARAMETER_GRID: Final[ParameterGrid] = RANDOM_FOREST_PARAM_GRID

ROSIDS_XGBOOST_PARAMETER_GRID: Final[ParameterGrid] = XGBOOST_PARAM_GRID


# ----------------------------------------
# Experiment definitions
# ----------------------------------------

ROSIDS_EXPERIMENTS: Final[dict[str, tuple[Pipeline, ParameterGrid]]] = {
    "decision_tree": (
        ROSIDS_DECISION_TREE_PIPELINE,
        ROSIDS_DECISION_TREE_PARAMETER_GRID,
    ),
    "random_forest": (
        ROSIDS_RANDOM_FOREST_PIPELINE,
        ROSIDS_RANDOM_FOREST_PARAMETER_GRID,
    ),
    "xgboost": (
        ROSIDS_XGBOOST_PIPELINE,
        ROSIDS_XGBOOST_PARAMETER_GRID,
    ),
}


# ----------------------------------------
# Experiment execution
# ----------------------------------------


def run_rosids_experiment(
    classifier_name: str,
) -> ExperimentResult:
    """Run one ROSIDS classifier experiment.

    Validation is performed using only the ROSIDS training partition.
    Once validation selects the configuration with the highest mean
    macro F1 across the fixed seeds, the selected configuration is
    fitted on the complete training partition for every seed.

    All validation results, final models, test predictions, class
    probabilities, feature importances, and experiment metadata are
    persisted by ``pipeline.common``.
    """
    try:
        pipeline, parameter_grid = ROSIDS_EXPERIMENTS[classifier_name]
    except KeyError as error:
        available_classifiers = ", ".join(
            ROSIDS_EXPERIMENTS,
        )

        raise ValueError(
            f"Unknown ROSIDS classifier: {classifier_name!r}. "
            f"Available classifiers: {available_classifiers}.",
        ) from error

    return run_classifier_experiment(
        dataset_name=ROSIDS_DATASET_NAME,
        classifier_name=classifier_name,
        base_pipeline=pipeline,
        parameter_grid=parameter_grid,
        train_features=ROSIDS_X_TRAIN,
        train_target=ROSIDS_Y_TRAIN,
        test_features=ROSIDS_X_TEST,
        test_target=ROSIDS_Y_TEST,
        numerical_features=ROSIDS_NUMERICAL_FEATURES,
        categorical_features=ROSIDS_CATEGORICAL_FEATURES,
        artifact_directory=(ROSIDS_ARTIFACT_ROOT / classifier_name),
        folds=CV_FOLDS,
        seeds_to_use=SEEDS,
        max_workers=ROSIDS_VALIDATION_WORKERS,
    )


def run_rosids_decision_tree() -> ExperimentResult:
    """Run the ROSIDS Decision Tree experiment."""
    return run_rosids_experiment(
        "decision_tree",
    )


def run_rosids_random_forest() -> ExperimentResult:
    """Run the ROSIDS Random Forest experiment."""
    return run_rosids_experiment(
        "random_forest",
    )


def run_rosids_xgboost() -> ExperimentResult:
    """Run the ROSIDS XGBoost experiment."""
    return run_rosids_experiment(
        "xgboost",
    )


def run_all_rosids_experiments() -> dict[str, ExperimentResult]:
    """Run all configured ROSIDS classifier experiments."""
    results: dict[str, ExperimentResult] = {}

    for classifier_name in ROSIDS_EXPERIMENTS:
        results[classifier_name] = run_rosids_experiment(
            classifier_name,
        )

    return results
