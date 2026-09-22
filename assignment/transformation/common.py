from __future__ import annotations

import pandas as pd

from schema.common import (
    SourceDatasetSchema,
    TransformedDatasetSchema,
)


def transform_data_frame(
    source_data_frame: pd.DataFrame,
    source_dataset_schema: SourceDatasetSchema,
    transformed_dataset_schema: TransformedDatasetSchema,
) -> pd.DataFrame:
    """Transform a source DataFrame according to a transformed schema."""

    source_feature_labels = set(
        source_dataset_schema.feature_labels(),
    )

    transformed_columns: dict[str, pd.Series] = {}

    for transformed_feature_specification in transformed_dataset_schema.all_features():
        missing_source_feature_labels = (
            set(transformed_feature_specification.source_feature_labels)
            - source_feature_labels
        )

        if missing_source_feature_labels:
            raise ValueError(
                f"Transformed feature "
                f"'{transformed_feature_specification.label}' references "
                f"source features that are not present in the source "
                f"schema: {missing_source_feature_labels!r}.",
            )

        missing_data_frame_columns = set(
            transformed_feature_specification.source_feature_labels
        ) - set(source_data_frame.columns)

        if missing_data_frame_columns:
            raise ValueError(
                f"Transformed feature "
                f"'{transformed_feature_specification.label}' requires "
                f"source DataFrame columns that are missing: "
                f"{missing_data_frame_columns!r}.",
            )

        transformed_feature_series = transformed_feature_specification.transformer(
            source_data_frame,
        )

        if not isinstance(transformed_feature_series, pd.Series):
            raise TypeError(
                f"Transformer for feature "
                f"'{transformed_feature_specification.label}' must return "
                "a pandas Series.",
            )

        if not transformed_feature_series.index.equals(
            source_data_frame.index,
        ):
            raise ValueError(
                f"Transformer for feature "
                f"'{transformed_feature_specification.label}' returned "
                "a Series with an index that does not match the source "
                "DataFrame.",
            )

        transformed_columns[transformed_feature_specification.label] = (
            transformed_feature_series
        )

    transformed_data_frame = pd.DataFrame(
        transformed_columns,
        index=source_data_frame.index,
    )

    return transformed_data_frame
