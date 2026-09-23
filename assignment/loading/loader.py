"""CSV loading utilities for network-traffic datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from loading.common import (
    DatasetBundle,
    DatasetPartition,
    DatasetSplit,
)
from schema.common import (
    FeatureDataType,
    FeatureSemanticType,
    SourceDatasetSchema,
    SourceFeatureSpec,
)

DATA_ROOT = Path(__file__).resolve().parent.parent / "_data"


class CsvLoadingError(ValueError):
    """Raised when a CSV file cannot be loaded according to its schema."""


class CsvDatasetLoader:
    """Load and validate CSV files according to a source dataset schema.

    The loader is intentionally limited to ingestion and schema-level
    normalization. It does not perform feature selection, imputation,
    encoding, scaling, balancing, splitting, or any other preprocessing
    operation required for model training.
    """

    def __init__(
        self,
        dataset_schema: SourceDatasetSchema,
    ) -> None:
        """Create a loader for the provided dataset schema."""

        self._dataset_schema = dataset_schema

    def load_partition(
        self,
        csv_file_path: Path,
        *,
        dataset_split: DatasetSplit = DatasetSplit.FULL,
    ) -> DatasetPartition:
        """Load one CSV file into a validated dataset partition.

        The original CSV column names are validated against the schema and
        then replaced with their canonical snake_case feature labels.

        Args:
            csv_file_path: Path to the CSV file.
            dataset_split: Logical partition represented by the file.

        Returns:
            A validated dataset partition containing the canonical DataFrame.

        Raises:
            CsvLoadingError: If the file does not exist, cannot be read, has
                an invalid schema, or contains invalid feature values.
        """

        self._validate_csv_file_path(csv_file_path)

        try:
            data_frame = pd.read_csv(
                csv_file_path,
                low_memory=False,
            )
        except (
            OSError,
            pd.errors.ParserError,
            UnicodeDecodeError,
        ) as error:
            raise CsvLoadingError(
                f"Could not read CSV file '{csv_file_path}'."
            ) from error

        self._validate_source_columns(data_frame)

        canonical_data_frame = self._rename_columns_to_canonical_labels(
            data_frame,
        )

        canonical_data_frame = self._convert_feature_data_types(
            canonical_data_frame,
        )

        self._validate_categorical_values(
            canonical_data_frame,
        )

        return DatasetPartition(
            data_frame=canonical_data_frame,
            split=dataset_split,
            source_path=csv_file_path,
        )

    def load_bundle(
        self,
        *,
        full_csv_file_path: Path | None = None,
        training_csv_file_path: Path | None = None,
        test_csv_file_path: Path | None = None,
    ) -> DatasetBundle:
        """Load one or more CSV files into a dataset bundle.

        A bundle may contain:
            - one complete unsplit dataset;
            - an official training and test pair;
            - a complete dataset together with its partitions.

        At least one path must be supplied.

        Args:
            full_csv_file_path: Path to a complete unsplit CSV dataset.
            training_csv_file_path: Path to the training CSV dataset.
            test_csv_file_path: Path to the test CSV dataset.

        Returns:
            A dataset bundle containing every requested partition.

        Raises:
            CsvLoadingError: If no paths are supplied or a requested file
                cannot be loaded according to the schema.
        """

        if (
            full_csv_file_path is None
            and training_csv_file_path is None
            and test_csv_file_path is None
        ):
            raise CsvLoadingError(
                f"No CSV file was provided for dataset "
                f"'{self._dataset_schema.dataset_name}'."
            )

        full_partition = (
            self.load_partition(
                full_csv_file_path,
                dataset_split=DatasetSplit.FULL,
            )
            if full_csv_file_path is not None
            else None
        )

        training_partition = (
            self.load_partition(
                training_csv_file_path,
                dataset_split=DatasetSplit.TRAIN,
            )
            if training_csv_file_path is not None
            else None
        )

        test_partition = (
            self.load_partition(
                test_csv_file_path,
                dataset_split=DatasetSplit.TEST,
            )
            if test_csv_file_path is not None
            else None
        )

        return DatasetBundle(
            dataset_name=self._dataset_schema.dataset_name,
            full=full_partition,
            train=training_partition,
            test=test_partition,
        )

    @staticmethod
    def _validate_csv_file_path(
        csv_file_path: Path,
    ) -> None:
        """Validate that a CSV path refers to an existing regular file."""

        if not csv_file_path.exists():
            raise CsvLoadingError(f"CSV file does not exist: '{csv_file_path}'.")

        if not csv_file_path.is_file():
            raise CsvLoadingError(f"CSV path is not a regular file: '{csv_file_path}'.")

    def _validate_source_columns(
        self,
        data_frame: pd.DataFrame,
    ) -> None:
        """Ensure that the DataFrame exactly matches the source schema."""

        source_column_names = self._dataset_schema.source_column_names()

        if data_frame.columns.has_duplicates:
            duplicated_column_names = tuple(
                data_frame.columns[data_frame.columns.duplicated()].unique()
            )

            raise CsvLoadingError(
                f"Dataset '{self._dataset_schema.dataset_name}' contains "
                f"duplicate CSV columns: {duplicated_column_names!r}."
            )

        expected_column_names = set(source_column_names)
        actual_column_names = set(data_frame.columns)

        missing_column_names = tuple(
            sorted(
                expected_column_names - actual_column_names,
            )
        )

        unexpected_column_names = tuple(
            sorted(
                actual_column_names - expected_column_names,
            )
        )

        if missing_column_names or unexpected_column_names:
            error_parts: list[str] = []

            if missing_column_names:
                error_parts.append(
                    f"missing columns: {missing_column_names!r}",
                )

            if unexpected_column_names:
                error_parts.append(
                    f"unexpected columns: {unexpected_column_names!r}",
                )

            details = "; ".join(error_parts)

            raise CsvLoadingError(
                f"CSV schema mismatch for dataset "
                f"'{self._dataset_schema.dataset_name}': {details}."
            )

        if tuple(data_frame.columns) != source_column_names:
            raise CsvLoadingError(
                f"CSV column order for dataset "
                f"'{self._dataset_schema.dataset_name}' does not match "
                "the declared schema."
            )

    def _rename_columns_to_canonical_labels(
        self,
        data_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """Replace source column names with canonical feature labels."""

        source_to_canonical_label_mapping = {
            feature.source_column_name: feature.label
            for feature in self._dataset_schema.all_features()
        }

        return data_frame.rename(
            columns=source_to_canonical_label_mapping,
        )

    def _convert_feature_data_types(
        self,
        data_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """Convert every feature according to its schema definition."""

        converted_data_frame = data_frame.copy()

        for feature_specification in self._dataset_schema.all_features():
            converted_data_frame[feature_specification.label] = (
                self._convert_feature_column(
                    converted_data_frame[feature_specification.label],
                    feature_specification,
                )
            )

        return converted_data_frame

    @staticmethod
    def _convert_feature_column(
        feature_series: pd.Series,
        feature_specification: SourceFeatureSpec,
    ) -> pd.Series:
        """Convert one feature according to its schema definition."""

        if feature_specification.semantic_type is FeatureSemanticType.BINARY:
            return feature_series.astype("boolean")

        match feature_specification.data_type:
            case FeatureDataType.INTEGER:
                return pd.to_numeric(
                    feature_series,
                    errors="raise",
                ).astype("Int64")

            case FeatureDataType.FLOAT:
                return pd.to_numeric(
                    feature_series,
                    errors="raise",
                ).astype("Float64")

            case FeatureDataType.STRING:
                return feature_series.astype("string")

            case FeatureDataType.DATETIME:
                return _parse_datetime_column(
                    feature_series,
                    feature_specification,
                )

            case _:
                raise CsvLoadingError(
                    f"Unsupported data type "
                    f"'{feature_specification.data_type}' for feature "
                    f"'{feature_specification.label}'."
                )

    def _validate_categorical_values(
        self,
        data_frame: pd.DataFrame,
    ) -> None:
        """Validate categorical values against their declared enums."""

        for feature_specification in self._dataset_schema.all_features():
            if feature_specification.category_enum is None:
                continue

            feature_series = data_frame[feature_specification.label].dropna()

            observed_values = set(
                feature_series.tolist(),
            )

            allowed_values = {
                category.value for category in feature_specification.category_enum
            }

            unexpected_values = tuple(
                sorted(
                    observed_values - allowed_values,
                )
            )

            if unexpected_values:
                raise CsvLoadingError(
                    f"Feature '{feature_specification.label}' in dataset "
                    f"'{self._dataset_schema.dataset_name}' contains "
                    f"unexpected categorical values: "
                    f"{unexpected_values!r}. Expected values are "
                    f"{tuple(sorted(allowed_values))!r}."
                )


def _parse_datetime_column(
    feature_series: pd.Series,
    feature_specification: SourceFeatureSpec,
) -> pd.Series:
    """Parse a datetime column using its declared formats."""

    if not feature_specification.datetime_formats:
        raise CsvLoadingError(
            f"Datetime feature '{feature_specification.label}' does not "
            "declare any accepted datetime formats."
        )

    parsed_values = pd.Series(
        pd.NaT,
        index=feature_series.index,
        dtype="datetime64[ns]",
    )

    remaining_mask = feature_series.notna()

    for datetime_format in feature_specification.datetime_formats:
        parsed_candidates = pd.to_datetime(
            feature_series,
            format=datetime_format,
            errors="coerce",
        )

        newly_parsed_mask = remaining_mask & parsed_candidates.notna()

        parsed_values.loc[newly_parsed_mask] = parsed_candidates.loc[newly_parsed_mask]

        remaining_mask &= ~newly_parsed_mask

        if not remaining_mask.any():
            break

    if remaining_mask.any():
        invalid_values = tuple(
            feature_series.loc[remaining_mask].astype("string").dropna().unique()
        )

        raise CsvLoadingError(
            f"Feature '{feature_specification.label}' contains "
            f"unsupported datetime values: {invalid_values!r}."
        )

    return parsed_values
