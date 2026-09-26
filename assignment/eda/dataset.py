"""Dataset-level exploratory data analysis."""

from collections.abc import Mapping
from typing import Any, cast

import numpy as np
import pandas as pd
from IPython.display import HTML, display

from eda.common import DatasetStatistics
from schema.common import (
    DatasetSchema,
    FeatureSemanticType,
)

# ----------------------------------------
# Public API
# ----------------------------------------


def compile_dataset_statistics(
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> DatasetStatistics:
    """Compile descriptive statistics for supplied dataset partitions.

    The partitions are processed independently. They are never concatenated,
    which is important when one partition is an official holdout/test set.

    Args:
        data_partitions:
            Mapping from partition name to DataFrame.

        dataset_schema:
            Schema describing the DataFrame representation.

    Returns:
        A compiled ``DatasetStatistics`` object.

    Raises:
        ValueError:
            If no partitions are supplied, a partition is empty, or required
            schema features are missing.
    """
    if not data_partitions:
        raise ValueError("At least one dataset partition must be supplied.")

    for partition_name, data_frame in data_partitions.items():
        if not partition_name:
            raise ValueError(
                "Dataset partition names must not be empty.",
            )

        if data_frame.empty:
            raise ValueError(
                f"Dataset partition '{partition_name}' is empty.",
            )

        _validate_partition_columns(
            data_frame=data_frame,
            dataset_schema=dataset_schema,
            partition_name=partition_name,
        )

    return DatasetStatistics(
        dataset_name=dataset_schema.dataset_name,
        overview_table=_compile_overview_table(
            data_partitions=data_partitions,
            dataset_schema=dataset_schema,
        ),
        target_distribution_table=_compile_target_distribution_table(
            data_partitions=data_partitions,
            dataset_schema=dataset_schema,
        ),
        feature_inventory_table=_compile_feature_inventory_table(
            dataset_schema=dataset_schema,
        ),
        data_quality_table=_compile_data_quality_table(
            data_partitions=data_partitions,
            dataset_schema=dataset_schema,
        ),
        numerical_statistics_table=_compile_numerical_statistics_table(
            data_partitions=data_partitions,
            dataset_schema=dataset_schema,
        ),
        binary_statistics_table=_compile_binary_statistics_table(
            data_partitions=data_partitions,
            dataset_schema=dataset_schema,
        ),
        categorical_statistics_table=_compile_categorical_statistics_table(
            data_partitions=data_partitions,
            dataset_schema=dataset_schema,
        ),
        datetime_statistics_table=_compile_datetime_statistics_table(
            data_partitions=data_partitions,
            dataset_schema=dataset_schema,
        ),
    )


def display_dataset_statistics(
    statistics: DatasetStatistics,
    *,
    show_feature_inventory: bool = True,
    show_data_quality: bool = True,
    show_numerical_statistics: bool = True,
    show_binary_statistics: bool = True,
    show_categorical_statistics: bool = True,
    show_datetime_statistics: bool = True,
) -> None:
    """Display compiled dataset statistics in a Jupyter notebook.

    Args:
        statistics:
            Result returned by ``compile_dataset_statistics()``.

        show_feature_inventory:
            Display the feature/schema inventory.

        show_data_quality:
            Display missing and non-finite value counts.

        show_numerical_statistics:
            Display descriptive statistics for numerical features.

        show_binary_statistics:
            Display counts/frequencies for binary features.

        show_categorical_statistics:
            Display counts/frequencies for categorical features.

        show_datetime_statistics:
            Display datetime ranges and missing counts.
    """
    display(
        HTML(
            f"<h1>{statistics.dataset_name}</h1>",
        ),
    )

    _display_section(
        title="Dataset overview",
        table=statistics.overview_table,
    )

    _display_section(
        title="Target distribution",
        table=statistics.target_distribution_table,
    )

    if show_feature_inventory:
        _display_section(
            title="Feature inventory",
            table=statistics.feature_inventory_table,
        )

    if show_data_quality:
        _display_section(
            title="Data quality",
            table=statistics.data_quality_table,
        )

    if show_numerical_statistics:
        _display_section(
            title="Numerical statistics",
            table=statistics.numerical_statistics_table,
        )

    if show_binary_statistics:
        _display_section(
            title="Binary statistics",
            table=statistics.binary_statistics_table,
        )

    if show_categorical_statistics:
        _display_section(
            title="Categorical statistics",
            table=statistics.categorical_statistics_table,
        )

    if show_datetime_statistics:
        _display_section(
            title="Datetime statistics",
            table=statistics.datetime_statistics_table,
        )


# ----------------------------------------
# Validation
# ----------------------------------------


def _validate_partition_columns(
    *,
    data_frame: pd.DataFrame,
    dataset_schema: DatasetSchema,
    partition_name: str,
) -> None:
    """Validate that a DataFrame contains every schema feature."""
    required_columns = set(dataset_schema.feature_labels())
    actual_columns = set(data_frame.columns)

    missing_columns = required_columns - actual_columns

    if missing_columns:
        raise ValueError(
            f"Dataset partition '{partition_name}' is missing schema "
            f"features: {tuple(sorted(missing_columns))}.",
        )


# ----------------------------------------
# Overview
# ----------------------------------------


def _compile_overview_table(
    *,
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile one overview row per partition."""
    predictor_count = len(dataset_schema.predictor_features())
    identifier_count = len(dataset_schema.identifier_features())
    metadata_count = len(dataset_schema.metadata_features())
    target_feature = dataset_schema.target_feature()

    rows: list[dict[str, object]] = []

    for partition_name, data_frame in data_partitions.items():
        rows.append(
            {
                "partition": partition_name,
                "rows": len(data_frame),
                "columns": len(data_frame.columns),
                "predictors": predictor_count,
                "identifiers": identifier_count,
                "metadata": metadata_count,
                "target": target_feature.label,
            },
        )

    return pd.DataFrame(rows)


# ----------------------------------------
# Target distribution
# ----------------------------------------


def _compile_target_distribution_table(
    *,
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile target-class counts and frequencies."""
    target_label = dataset_schema.target_feature().label

    rows: list[dict[str, object]] = []

    for partition_name, data_frame in data_partitions.items():
        target_series = data_frame[target_label]
        value_counts = target_series.value_counts(dropna=False)
        total_count = len(target_series)

        for category, count in value_counts.items():
            category_value = cast(Any, category)
            category_label = (
                "<missing>" if pd.isna(category_value) else str(category_value)
            )

            rows.append(
                {
                    "partition": partition_name,
                    "target": target_label,
                    "category": category_label,
                    "count": int(count),
                    "frequency": (
                        float(count / total_count) if total_count > 0 else 0.0
                    ),
                },
            )

    columns = (
        "partition",
        "target",
        "category",
        "count",
        "frequency",
    )

    return pd.DataFrame(rows, columns=columns)


# ----------------------------------------
# Feature inventory
# ----------------------------------------


def _compile_feature_inventory_table(
    *,
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile schema information for every feature."""
    rows: list[dict[str, object]] = []

    for feature in dataset_schema.all_features():
        rows.append(
            {
                "feature": feature.label,
                "name": feature.name,
                "data_type": feature.data_type.value,
                "semantic_type": feature.semantic_type.value,
                "role": feature.role.value,
                "description": feature.description,
            },
        )

    columns = (
        "feature",
        "name",
        "data_type",
        "semantic_type",
        "role",
        "description",
    )

    return pd.DataFrame(rows, columns=columns)


# ----------------------------------------
# Data quality
# ----------------------------------------


def _compile_data_quality_table(
    *,
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile missing and non-finite value counts."""
    rows: list[dict[str, object]] = []

    for partition_name, data_frame in data_partitions.items():
        for feature in dataset_schema.all_features():
            series = data_frame[feature.label]

            missing_count = int(series.isna().sum())
            non_finite_count = 0

            if feature.semantic_type in (
                FeatureSemanticType.NUMERIC,
                FeatureSemanticType.BINARY,
            ):
                numeric_values = pd.to_numeric(
                    series,
                    errors="coerce",
                ).to_numpy(
                    dtype=float,
                )

                non_finite_mask = ~np.isfinite(numeric_values) & ~np.isnan(
                    numeric_values
                )

                non_finite_count = int(
                    np.count_nonzero(non_finite_mask),
                )

            rows.append(
                {
                    "partition": partition_name,
                    "feature": feature.label,
                    "role": feature.role.value,
                    "semantic_type": feature.semantic_type.value,
                    "missing_count": missing_count,
                    "missing_frequency": (
                        float(missing_count / len(series)) if len(series) > 0 else 0.0
                    ),
                    "non_finite_count": non_finite_count,
                },
            )

    columns = (
        "partition",
        "feature",
        "role",
        "semantic_type",
        "missing_count",
        "missing_frequency",
        "non_finite_count",
    )

    return pd.DataFrame(rows, columns=columns)


# ----------------------------------------
# Numerical statistics
# ----------------------------------------


def _compile_numerical_statistics_table(
    *,
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile descriptive statistics for numerical features."""
    numerical_features = tuple(
        feature
        for feature in dataset_schema.all_features()
        if feature.semantic_type is FeatureSemanticType.NUMERIC
    )

    rows: list[dict[str, object]] = []

    for partition_name, data_frame in data_partitions.items():
        for feature in numerical_features:
            series = pd.to_numeric(
                data_frame[feature.label],
                errors="coerce",
            )

            values = series.to_numpy(dtype=float)
            finite_values = values[np.isfinite(values)]

            if finite_values.size == 0:
                continue

            rows.append(
                {
                    "partition": partition_name,
                    "feature": feature.label,
                    "minimum": float(np.min(finite_values)),
                    "maximum": float(np.max(finite_values)),
                    "mean": float(np.mean(finite_values)),
                    "standard_deviation": float(np.std(finite_values)),
                    "percentile_05": float(np.percentile(finite_values, 5)),
                    "percentile_25": float(np.percentile(finite_values, 25)),
                    "percentile_50": float(np.percentile(finite_values, 50)),
                    "percentile_75": float(np.percentile(finite_values, 75)),
                    "percentile_95": float(np.percentile(finite_values, 95)),
                },
            )

    columns = (
        "partition",
        "feature",
        "minimum",
        "maximum",
        "mean",
        "standard_deviation",
        "percentile_05",
        "percentile_25",
        "percentile_50",
        "percentile_75",
        "percentile_95",
    )

    return pd.DataFrame(rows, columns=columns)


# ----------------------------------------
# Binary statistics
# ----------------------------------------


def _compile_binary_statistics_table(
    *,
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile counts and frequencies for binary features."""
    binary_features = tuple(
        feature
        for feature in dataset_schema.all_features()
        if feature.semantic_type is FeatureSemanticType.BINARY
    )

    rows: list[dict[str, object]] = []

    for partition_name, data_frame in data_partitions.items():
        for feature in binary_features:
            series = data_frame[feature.label]
            value_counts = series.value_counts(dropna=False)
            total_count = len(series)

            for value, count in value_counts.items():
                value_value = cast(Any, value)
                value_label = "<missing>" if pd.isna(value_value) else str(value_value)

                rows.append(
                    {
                        "partition": partition_name,
                        "feature": feature.label,
                        "value": value_label,
                        "count": int(count),
                        "frequency": (
                            float(count / total_count) if total_count > 0 else 0.0
                        ),
                    },
                )

    columns = (
        "partition",
        "feature",
        "value",
        "count",
        "frequency",
    )

    return pd.DataFrame(rows, columns=columns)


# ----------------------------------------
# Categorical statistics
# ----------------------------------------


def _compile_categorical_statistics_table(
    *,
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile frequency statistics for categorical features."""
    categorical_features = tuple(
        feature
        for feature in dataset_schema.all_features()
        if feature.semantic_type is FeatureSemanticType.CATEGORICAL
    )

    rows: list[dict[str, object]] = []

    for partition_name, data_frame in data_partitions.items():
        for feature in categorical_features:
            series = data_frame[feature.label]
            value_counts = series.value_counts(dropna=False)
            total_count = len(series)

            for category, count in value_counts.items():
                category_value = cast(Any, category)
                category_label = (
                    "<missing>" if pd.isna(category_value) else str(category_value)
                )

                rows.append(
                    {
                        "partition": partition_name,
                        "feature": feature.label,
                        "category": category_label,
                        "count": int(count),
                        "frequency": (
                            float(count / total_count) if total_count > 0 else 0.0
                        ),
                    },
                )

    columns = (
        "partition",
        "feature",
        "category",
        "count",
        "frequency",
    )

    return pd.DataFrame(rows, columns=columns)


# ----------------------------------------
# Datetime statistics
# ----------------------------------------


def _compile_datetime_statistics_table(
    *,
    data_partitions: Mapping[str, pd.DataFrame],
    dataset_schema: DatasetSchema,
) -> pd.DataFrame:
    """Compile basic statistics for datetime features."""
    datetime_features = tuple(
        feature
        for feature in dataset_schema.all_features()
        if feature.semantic_type is FeatureSemanticType.DATETIME
    )

    rows: list[dict[str, object]] = []

    for partition_name, data_frame in data_partitions.items():
        for feature in datetime_features:
            series = pd.to_datetime(
                data_frame[feature.label],
                errors="coerce",
            )

            valid_values = series.dropna()

            rows.append(
                {
                    "partition": partition_name,
                    "feature": feature.label,
                    "minimum": (
                        valid_values.min() if not valid_values.empty else pd.NaT
                    ),
                    "maximum": (
                        valid_values.max() if not valid_values.empty else pd.NaT
                    ),
                    "missing_count": int(series.isna().sum()),
                    "unique_count": int(valid_values.nunique()),
                },
            )

    columns = (
        "partition",
        "feature",
        "minimum",
        "maximum",
        "missing_count",
        "unique_count",
    )

    return pd.DataFrame(rows, columns=columns)


# ----------------------------------------
# Display helpers
# ----------------------------------------


def _display_section(
    *,
    title: str,
    table: pd.DataFrame,
) -> None:
    """Display one titled statistics table."""
    display(
        HTML(
            f"<h2>{title}</h2>",
        ),
    )

    display(table)
