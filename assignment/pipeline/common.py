"""Common machine-learning pipeline and hyperparameter-search utilities."""

from collections.abc import Sequence
from itertools import product
from typing import Any, Final

import numpy as np
import pandas as pd
from imblearn.over_sampling import RandomOverSampler
from imblearn.pipeline import Pipeline
from sklearn.base import ClassifierMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder
from xgboost import XGBClassifier

from definitions import SEEDS

FeatureLabels = tuple[str, ...]

# String sentinel used in parameter grids. The actual sampler is constructed
# with the current CV seed immediately before fitting.
RANDOM_OVER_SAMPLER: Final[str] = "random_over_sampler"

CV_FOLDS: Final[int] = 2


DECISION_TREE_PARAM_GRID: Final[dict[str, Sequence[Any]]] = {
    "sampler": [
        "passthrough",
        RANDOM_OVER_SAMPLER,
    ],
    "classifier__criterion": [
        "gini",
        "entropy",
    ],
    "classifier__max_depth": [
        None,
        10,
        20,
    ],
    "classifier__min_samples_split": [
        2,
        10,
    ],
    "classifier__min_samples_leaf": [
        1,
        5,
    ],
}


RANDOM_FOREST_PARAM_GRID: Final[dict[str, Sequence[Any]]] = {
    "sampler": [
        "passthrough",
        RANDOM_OVER_SAMPLER,
    ],
    "classifier__n_estimators": [
        100,
        200,
    ],
    "classifier__max_depth": [
        None,
        20,
    ],
    "classifier__min_samples_split": [
        2,
        10,
    ],
    "classifier__min_samples_leaf": [
        1,
        5,
    ],
}


XGBOOST_PARAM_GRID: Final[dict[str, Sequence[Any]]] = {
    "sampler": [
        "passthrough",
        RANDOM_OVER_SAMPLER,
    ],
    "classifier__n_estimators": [
        100,
        200,
    ],
    "classifier__max_depth": [
        3,
        6,
    ],
    "classifier__learning_rate": [
        0.05,
        0.1,
    ],
    "classifier__min_child_weight": [
        1,
        5,
    ],
    "classifier__subsample": [
        0.8,
        1.0,
    ],
}


def replace_non_finite_values(values: np.ndarray) -> np.ndarray:
    """Replace positive/negative infinity with NaN.

    NaN values are subsequently handled by the numerical imputer.
    """
    values = np.asarray(values, dtype=float)

    return np.where(
        np.isfinite(values),
        values,
        np.nan,
    )


def build_numeric_pipeline() -> Pipeline:
    """Build preprocessing for numerical and binary predictor features."""
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
    """Build preprocessing for categorical predictor features."""
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
    """Build the column-wise preprocessing transformer."""
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
    """Build the complete preprocessing -> sampling -> classifier pipeline."""
    preprocessor = build_preprocessor(
        numerical_features=numerical_features,
        categorical_features=categorical_features,
    )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
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


def build_xgboost_classifier() -> XGBClassifier:
    """Build the XGBoost classifier used by the search pipeline.

    random_state is set later for each CV seed so the same pipeline
    definition can be reused across all repeated CV runs.
    """
    return XGBClassifier(
        tree_method="hist",
        n_jobs=1,
    )


def build_stratified_cross_validator(
    *,
    folds: int,
    seed: int,
) -> StratifiedKFold:
    """Build a reproducible shuffled stratified cross-validator."""
    if folds < 2:
        raise ValueError(
            "folds must be at least 2.",
        )

    return StratifiedKFold(
        n_splits=folds,
        shuffle=True,
        random_state=seed,
    )


def _resolve_sampler(
    sampler_option: str,
    *,
    seed: int,
) -> str | RandomOverSampler:
    """Convert a sampler-grid option into an estimator."""
    if sampler_option == "passthrough":
        return "passthrough"

    if sampler_option == RANDOM_OVER_SAMPLER:
        return RandomOverSampler(
            random_state=seed,
        )

    raise ValueError(
        f"Unknown sampler option: {sampler_option!r}",
    )


def _expand_parameter_grid(
    parameter_grid: dict[str, Sequence[Any]],
) -> list[dict[str, Any]]:
    """Expand a parameter grid into individual configurations."""
    names = tuple(parameter_grid)

    values = [parameter_grid[name] for name in names]

    return [
        dict(zip(names, combination, strict=True)) for combination in product(*values)
    ]


def search_classifier(
    *,
    pipeline: Pipeline,
    parameter_grid: dict[str, Sequence[Any]],
    features: pd.DataFrame,
    target: pd.Series,
    folds: int = CV_FOLDS,
    seeds: Sequence[int] = SEEDS,
) -> pd.DataFrame:
    """Evaluate all configurations using repeated stratified CV.

    For each configuration:
    1. Run stratified k-fold CV for every fixed seed.
    2. Compute macro F1 on each validation fold.
    3. Average the folds within each seed.
    4. Average the seed-level scores to obtain the final mean.
    5. Compute the standard deviation across the seed-level scores.

    The held-out test set must not be passed to this function.
    """
    if len(features) != len(target):
        raise ValueError(
            "features and target must contain the same number of rows.",
        )

    seeds = tuple(seeds)

    if not seeds:
        raise ValueError(
            "At least one seed is required.",
        )

    configurations = _expand_parameter_grid(
        parameter_grid,
    )

    results: list[dict[str, Any]] = []

    for configuration_index, configuration in enumerate(
        configurations,
        start=1,
    ):
        seed_macro_f1_scores: list[float] = []

        for seed in seeds:
            cross_validator = build_stratified_cross_validator(
                folds=folds,
                seed=seed,
            )

            fold_scores: list[float] = []

            for train_indices, validation_indices in cross_validator.split(
                features,
                target,
            ):
                fold_pipeline = clone(pipeline)

                resolved_sampler = _resolve_sampler(
                    configuration["sampler"],
                    seed=seed,
                )

                fold_pipeline.set_params(
                    **{
                        **configuration,
                        "sampler": resolved_sampler,
                        "classifier__random_state": seed,
                    },
                )

                x_train = features.iloc[train_indices]
                y_train = target.iloc[train_indices]

                x_validation = features.iloc[validation_indices]
                y_validation = target.iloc[validation_indices]

                fold_pipeline.fit(
                    x_train,
                    y_train,
                )

                predictions = np.asarray(
                    fold_pipeline.predict(x_validation),
                )

                fold_macro_f1 = f1_score(
                    y_validation,
                    predictions,
                    average="macro",
                )

                fold_scores.append(
                    float(fold_macro_f1),
                )

            seed_macro_f1_scores.append(
                float(np.mean(fold_scores)),
            )

        macro_f1_mean = float(
            np.mean(seed_macro_f1_scores),
        )

        macro_f1_std = float(
            np.std(
                seed_macro_f1_scores,
                ddof=1,
            )
            if len(seed_macro_f1_scores) > 1
            else 0.0,
        )

        results.append(
            {
                "configuration_index": configuration_index,
                **configuration,
                "macro_f1_mean": macro_f1_mean,
                "macro_f1_std": macro_f1_std,
                "seed_macro_f1_scores": tuple(
                    seed_macro_f1_scores,
                ),
            },
        )

    return pd.DataFrame(results).sort_values(
        by="macro_f1_mean",
        ascending=False,
        ignore_index=True,
    )
