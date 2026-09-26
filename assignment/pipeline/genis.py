"""GENIS machine-learning pipeline configuration."""

from collections.abc import Sequence
from typing import Any, Final, Literal

import pandas as pd
from imblearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from definitions import SEEDS
from pipeline.common import (
    CV_FOLDS,
    DECISION_TREE_PARAM_GRID,
    RANDOM_FOREST_PARAM_GRID,
    XGBOOST_PARAM_GRID,
    build_classification_pipeline,
    build_xgboost_classifier,
    search_classifier,
)
from schema.common import FeatureSemanticType
from transformation.genis import (
    TRANSFORMED_GENIS_SCHEMA,
    genis_df_for_test,
    genis_df_for_train,
)

# ----------------------------------------
# Dataset
# ----------------------------------------

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


GENIS_X_TRAIN: Final[pd.DataFrame] = genis_df_for_train.loc[
    :,
    GENIS_PREDICTOR_FEATURES,
].copy()

GENIS_Y_TRAIN: Final[pd.Series] = genis_df_for_train.loc[
    :,
    GENIS_TARGET_FEATURE,
].copy()

GENIS_X_TEST: Final[pd.DataFrame] = genis_df_for_test.loc[
    :,
    GENIS_PREDICTOR_FEATURES,
].copy()

GENIS_Y_TEST: Final[pd.Series] = genis_df_for_test.loc[
    :,
    GENIS_TARGET_FEATURE,
].copy()


# ----------------------------------------
# Classifiers
# ----------------------------------------

GENIS_DECISION_TREE: Final[DecisionTreeClassifier] = DecisionTreeClassifier()

GENIS_RANDOM_FOREST: Final[RandomForestClassifier] = RandomForestClassifier(
    n_jobs=1,
)

GENIS_XGBOOST = build_xgboost_classifier()


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

GENIS_PARAMETER_GRIDS: Final[dict[str, dict[str, Sequence[Any]]]] = {
    "decision_tree": DECISION_TREE_PARAM_GRID,
    "random_forest": RANDOM_FOREST_PARAM_GRID,
    "xgboost": XGBOOST_PARAM_GRID,
}


# ----------------------------------------
# Pipelines
# ----------------------------------------

GENIS_PIPELINES: Final[dict[str, Pipeline]] = {
    "decision_tree": GENIS_DECISION_TREE_PIPELINE,
    "random_forest": GENIS_RANDOM_FOREST_PIPELINE,
    "xgboost": GENIS_XGBOOST_PIPELINE,
}


# ----------------------------------------
# Hyperparameter search
# ----------------------------------------


def search_genis_classifier(
    classifier_name: Literal["decision_tree", "random_forest", "xgboost"],
) -> pd.DataFrame:
    """Search one GENIS classifier using repeated stratified CV.

    The test set is never used during hyperparameter selection.

    Args:
        classifier_name: One of the configured GENIS classifier names.

    Returns:
        One row per hyperparameter configuration, sorted by mean
        macro F1 in descending order.
    """
    try:
        pipeline = GENIS_PIPELINES[classifier_name]
        parameter_grid = GENIS_PARAMETER_GRIDS[classifier_name]
    except KeyError as error:
        available_classifiers = ", ".join(
            GENIS_PIPELINES,
        )
        raise ValueError(
            f"Unknown GENIS classifier: {classifier_name!r}. "
            f"Available classifiers: {available_classifiers}.",
        ) from error

    return search_classifier(
        pipeline=pipeline,
        parameter_grid=parameter_grid,
        features=GENIS_X_TRAIN,
        target=GENIS_Y_TRAIN,
        folds=CV_FOLDS,
        seeds=SEEDS,
    )
