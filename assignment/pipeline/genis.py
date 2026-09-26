"""GENIS machine-learning experiment configuration."""

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
from transformation.genis import (
    TRANSFORMED_GENIS_SCHEMA,
    genis_df_for_test,
    genis_df_for_train,
)

# ----------------------------------------
# Dataset configuration
# ----------------------------------------

GENIS_DATASET_NAME: Final[str] = "GENIS"

GENIS_TARGET_FEATURE: Final[str] = TRANSFORMED_GENIS_SCHEMA.target_feature_label

GENIS_PREDICTOR_FEATURES: Final[tuple[str, ...]] = tuple(
    feature.label for feature in TRANSFORMED_GENIS_SCHEMA.predictor_features()
)

GENIS_NUMERICAL_FEATURES: Final[tuple[str, ...]] = tuple(
    feature.label
    for feature in TRANSFORMED_GENIS_SCHEMA.predictor_features()
    if feature.semantic_type
    in {
        FeatureSemanticType.NUMERIC,
        FeatureSemanticType.BINARY,
    }
)

GENIS_CATEGORICAL_FEATURES: Final[tuple[str, ...]] = tuple(
    feature.label
    for feature in TRANSFORMED_GENIS_SCHEMA.predictor_features()
    if feature.semantic_type is FeatureSemanticType.CATEGORICAL
)


GENIS_X_TRAIN: Final[pd.DataFrame] = genis_df_for_train[
    list(GENIS_PREDICTOR_FEATURES)
].copy()


GENIS_Y_TRAIN: Final[pd.Series] = genis_df_for_train[GENIS_TARGET_FEATURE].copy()

GENIS_X_TEST: Final[pd.DataFrame] = genis_df_for_test[
    list(GENIS_PREDICTOR_FEATURES)
].copy()

GENIS_Y_TEST: Final[pd.Series] = genis_df_for_test[GENIS_TARGET_FEATURE].copy()


# ----------------------------------------
# Artifact configuration
# ----------------------------------------

GENIS_ARTIFACT_ROOT: Final[Path] = ARTIFACT_ROOT / GENIS_DATASET_NAME.lower()


GENIS_VALIDATION_WORKERS: Final[int] = DEFAULT_VALIDATION_WORKERS


# ----------------------------------------
# Classifier configuration
# ----------------------------------------

GENIS_DECISION_TREE: Final[DecisionTreeClassifier] = DecisionTreeClassifier()

GENIS_RANDOM_FOREST: Final[RandomForestClassifier] = RandomForestClassifier(
    n_jobs=1,
)

GENIS_XGBOOST: Final = build_xgboost_classifier()


# ----------------------------------------
# Classification pipelines
# ----------------------------------------

GENIS_DECISION_TREE_PIPELINE: Final[Pipeline] = build_classification_pipeline(
    numerical_features=GENIS_NUMERICAL_FEATURES,
    categorical_features=GENIS_CATEGORICAL_FEATURES,
    classifier=GENIS_DECISION_TREE,
)

GENIS_RANDOM_FOREST_PIPELINE: Final[Pipeline] = build_classification_pipeline(
    numerical_features=GENIS_NUMERICAL_FEATURES,
    categorical_features=GENIS_CATEGORICAL_FEATURES,
    classifier=GENIS_RANDOM_FOREST,
)

GENIS_XGBOOST_PIPELINE: Final[Pipeline] = build_classification_pipeline(
    numerical_features=GENIS_NUMERICAL_FEATURES,
    categorical_features=GENIS_CATEGORICAL_FEATURES,
    classifier=GENIS_XGBOOST,
)


# ----------------------------------------
# Hyperparameter grids
# ----------------------------------------

GENIS_DECISION_TREE_PARAMETER_GRID: Final[ParameterGrid] = DECISION_TREE_PARAM_GRID

GENIS_RANDOM_FOREST_PARAMETER_GRID: Final[ParameterGrid] = RANDOM_FOREST_PARAM_GRID

GENIS_XGBOOST_PARAMETER_GRID: Final[ParameterGrid] = XGBOOST_PARAM_GRID


# ----------------------------------------
# Experiment definitions
# ----------------------------------------

GENIS_EXPERIMENTS: Final[dict[str, tuple[Pipeline, ParameterGrid]]] = {
    "decision_tree": (
        GENIS_DECISION_TREE_PIPELINE,
        GENIS_DECISION_TREE_PARAMETER_GRID,
    ),
    "random_forest": (
        GENIS_RANDOM_FOREST_PIPELINE,
        GENIS_RANDOM_FOREST_PARAMETER_GRID,
    ),
    "xgboost": (
        GENIS_XGBOOST_PIPELINE,
        GENIS_XGBOOST_PARAMETER_GRID,
    ),
}


# ----------------------------------------
# Experiment execution
# ----------------------------------------


def run_genis_experiment(
    classifier_name: str,
) -> ExperimentResult:
    """Run one GENIS classifier experiment.

    Validation is performed using only the GENIS training partition.
    Once validation selects the configuration with the highest mean
    macro F1 across the fixed seeds, the selected configuration is
    fitted on the complete training partition for every seed.

    All validation results, final models, test predictions, class
    probabilities, feature importances, and experiment metadata are
    persisted by ``pipeline.common``.
    """
    try:
        pipeline, parameter_grid = GENIS_EXPERIMENTS[classifier_name]
    except KeyError as error:
        available_classifiers = ", ".join(
            GENIS_EXPERIMENTS,
        )

        raise ValueError(
            f"Unknown GENIS classifier: {classifier_name!r}. "
            f"Available classifiers: {available_classifiers}.",
        ) from error

    return run_classifier_experiment(
        dataset_name=GENIS_DATASET_NAME,
        classifier_name=classifier_name,
        base_pipeline=pipeline,
        parameter_grid=parameter_grid,
        train_features=GENIS_X_TRAIN,
        train_target=GENIS_Y_TRAIN,
        test_features=GENIS_X_TEST,
        test_target=GENIS_Y_TEST,
        numerical_features=GENIS_NUMERICAL_FEATURES,
        categorical_features=GENIS_CATEGORICAL_FEATURES,
        artifact_directory=(GENIS_ARTIFACT_ROOT / classifier_name),
        folds=CV_FOLDS,
        seeds_to_use=SEEDS,
        max_workers=GENIS_VALIDATION_WORKERS,
    )


def run_genis_decision_tree() -> ExperimentResult:
    """Run the GENIS Decision Tree experiment."""
    return run_genis_experiment(
        "decision_tree",
    )


def run_genis_random_forest() -> ExperimentResult:
    """Run the GENIS Random Forest experiment."""
    return run_genis_experiment(
        "random_forest",
    )


def run_genis_xgboost() -> ExperimentResult:
    """Run the GENIS XGBoost experiment."""
    return run_genis_experiment(
        "xgboost",
    )


def run_all_genis_experiments() -> dict[str, ExperimentResult]:
    """Run all configured GENIS classifier experiments."""
    results: dict[str, ExperimentResult] = {}

    for classifier_name in GENIS_EXPERIMENTS:
        results[classifier_name] = run_genis_experiment(
            classifier_name,
        )

    return results
