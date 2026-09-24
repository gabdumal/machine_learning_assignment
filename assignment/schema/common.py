"""Common schema definitions for network-traffic datasets."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


class FeatureDataType(StrEnum):
    """Physical representation expected for a feature in a pandas DataFrame."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    DATETIME = "datetime"


class FeatureSemanticType(StrEnum):
    """Semantic interpretation of a feature."""

    NUMERIC = "numeric"
    BINARY = "binary"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"


class FeatureRole(StrEnum):
    """Role of a feature in the machine-learning dataset."""

    PREDICTOR = "predictor"
    TARGET = "target"
    IDENTIFIER = "identifier"
    METADATA = "metadata"


class SchemaValidationError(ValueError):
    """Raised when a dataset schema is internally inconsistent."""


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureSpec:
    """Describes one feature independently of its source representation."""

    label: str
    name: str
    data_type: FeatureDataType
    semantic_type: FeatureSemanticType
    role: FeatureRole
    description: str
    category_enum: type[StrEnum] | None = None
    datetime_formats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate invariants that must always hold for a feature."""

        if not self.label:
            raise SchemaValidationError(
                "Feature label must not be empty.",
            )

        if not self.name:
            raise SchemaValidationError(
                "Feature name must not be empty.",
            )

        if not self.description:
            raise SchemaValidationError(
                f"Feature description must not be empty for '{self.label}'.",
            )

        if self.semantic_type is FeatureSemanticType.DATETIME:
            if len(self.datetime_formats) == 0:
                raise SchemaValidationError(
                    f"Datetime feature '{self.label}' must define a datetime format.",
                )
        elif len(self.datetime_formats) >= 1:
            raise SchemaValidationError(
                f"Feature '{self.label}' defines a datetime format "
                "but is not a datetime feature.",
            )

        if self.semantic_type is FeatureSemanticType.NUMERIC:  # noqa: SIM102
            if self.data_type not in {
                FeatureDataType.INTEGER,
                FeatureDataType.FLOAT,
            }:
                raise SchemaValidationError(
                    f"Numeric feature '{self.label}' must use an integer "
                    "or float data type.",
                )

        if self.semantic_type is FeatureSemanticType.DATETIME:  # noqa: SIM102
            if self.data_type is not FeatureDataType.DATETIME:
                raise SchemaValidationError(
                    f"Datetime feature '{self.label}' must use the "
                    f"{FeatureDataType.DATETIME.value!r} data type.",
                )

        if self.semantic_type is FeatureSemanticType.CATEGORICAL:
            if self.category_enum is not None and not issubclass(
                self.category_enum,
                StrEnum,
            ):
                raise SchemaValidationError(
                    f"Category enum for '{self.label}' must inherit from StrEnum.",
                )
        elif self.category_enum is not None:
            raise SchemaValidationError(
                f"Feature '{self.label}' defines a category enum "
                "but is not categorical.",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFeatureSpec(FeatureSpec):
    """Describes a feature originating directly from a source dataset."""

    source_column_name: str

    def __post_init__(self) -> None:
        """Validate source-feature-specific invariants."""

        super().__post_init__()

        if not self.source_column_name:
            raise SchemaValidationError(
                f"Source column name must not be empty for '{self.label}'.",
            )


FeatureTransformer = Callable[
    [pd.DataFrame],
    pd.Series,
]


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformedFeatureSpec(FeatureSpec):
    """Describes a feature produced by transforming source features."""

    source_feature_labels: tuple[str, ...]
    transformer: FeatureTransformer

    def __post_init__(self) -> None:
        """Validate transformed-feature-specific invariants."""

        super().__post_init__()

        if len(self.source_feature_labels) == 0:
            raise SchemaValidationError(
                f"Transformed feature '{self.label}' must reference "
                "at least one source feature.",
            )

        if any(
            not source_feature_label
            for source_feature_label in self.source_feature_labels
        ):
            raise SchemaValidationError(
                f"Transformed feature '{self.label}' contains an empty "
                "source feature label.",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetSchema:
    """Immutable description of a dataset representation."""

    dataset_name: str
    features: tuple[FeatureSpec, ...]
    target_feature_label: str

    def __post_init__(self) -> None:
        """Validate the common dataset-schema invariants."""

        if not self.dataset_name:
            raise SchemaValidationError(
                "Dataset name must not be empty.",
            )

        if not self.features:
            raise SchemaValidationError(
                f"Dataset '{self.dataset_name}' must define at least one feature.",
            )

        feature_labels = tuple(feature.label for feature in self.features)

        if len(feature_labels) != len(set(feature_labels)):
            raise SchemaValidationError(
                f"Dataset '{self.dataset_name}' contains duplicate feature labels.",
            )

        if self.target_feature_label not in feature_labels:
            raise SchemaValidationError(
                f"Target feature '{self.target_feature_label}' is not "
                f"defined in dataset '{self.dataset_name}'.",
            )

        target_features = tuple(
            feature for feature in self.features if feature.role is FeatureRole.TARGET
        )

        if len(target_features) != 1:
            raise SchemaValidationError(
                f"Dataset '{self.dataset_name}' must define exactly "
                f"one {FeatureRole.TARGET.value!r} feature; found "
                f"{len(target_features)}.",
            )

        if target_features[0].label != self.target_feature_label:
            raise SchemaValidationError(
                "The explicitly configured target_feature_label does not "
                "match the feature marked as the target.",
            )

    def all_features(self) -> tuple[FeatureSpec, ...]:
        """Return all features in their declared order."""

        return self.features

    def predictor_features(self) -> tuple[FeatureSpec, ...]:
        """Return features intended as model predictors."""

        return tuple(
            feature
            for feature in self.features
            if feature.role is FeatureRole.PREDICTOR
        )

    def identifier_features(self) -> tuple[FeatureSpec, ...]:
        """Return features that identify records or entities."""

        return tuple(
            feature
            for feature in self.features
            if feature.role is FeatureRole.IDENTIFIER
        )

    def metadata_features(self) -> tuple[FeatureSpec, ...]:
        """Return features containing metadata rather than model inputs."""

        return tuple(
            feature for feature in self.features if feature.role is FeatureRole.METADATA
        )

    def target_feature(self) -> FeatureSpec:
        """Return the unique target feature."""

        for feature in self.features:
            if feature.label == self.target_feature_label:
                return feature

        raise SchemaValidationError(
            f"Target feature '{self.target_feature_label}' could not be found.",
        )

    def get_feature(self, feature_label: str) -> FeatureSpec:
        """Return a feature by its canonical label.

        Raises:
            KeyError: If no feature has the requested label.
        """

        for feature in self.features:
            if feature.label == feature_label:
                return feature

        raise KeyError(
            f"Feature '{feature_label}' is not defined in "
            f"dataset '{self.dataset_name}'.",
        )

    def feature_labels(self) -> tuple[str, ...]:
        """Return canonical feature labels in schema order."""

        return tuple(feature.label for feature in self.features)

    def predictor_feature_labels(self) -> tuple[str, ...]:
        """Return canonical labels for predictor features."""

        return tuple(feature.label for feature in self.predictor_features())


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceDatasetSchema(DatasetSchema):
    """Immutable schema describing the original source dataset."""

    def __post_init__(self) -> None:
        """Validate source-dataset-specific invariants."""

        super().__post_init__()

        non_source_features = tuple(
            feature
            for feature in self.features
            if not isinstance(feature, SourceFeatureSpec)
        )

        if non_source_features:
            non_source_feature_labels = tuple(
                feature.label for feature in non_source_features
            )

            raise SchemaValidationError(
                f"Source dataset '{self.dataset_name}' contains features "
                "that are not SourceFeatureSpec instances: "
                f"{non_source_feature_labels!r}.",
            )

    def all_features(self) -> tuple[SourceFeatureSpec, ...]:
        """Return all source features in their declared order."""

        return tuple(
            feature
            for feature in self.features
            if isinstance(feature, SourceFeatureSpec)
        )

    def predictor_features(self) -> tuple[SourceFeatureSpec, ...]:
        """Return source features intended as model predictors."""

        return tuple(
            feature
            for feature in self.features
            if isinstance(feature, SourceFeatureSpec)
            and feature.role is FeatureRole.PREDICTOR
        )

    def identifier_features(self) -> tuple[SourceFeatureSpec, ...]:
        """Return source features that identify records or entities."""

        return tuple(
            feature
            for feature in self.features
            if isinstance(feature, SourceFeatureSpec)
            and feature.role is FeatureRole.IDENTIFIER
        )

    def metadata_features(self) -> tuple[SourceFeatureSpec, ...]:
        """Return source features containing metadata."""

        return tuple(
            feature
            for feature in self.features
            if isinstance(feature, SourceFeatureSpec)
            and feature.role is FeatureRole.METADATA
        )

    def target_feature(self) -> SourceFeatureSpec:
        """Return the unique source target feature."""

        target_feature = super().target_feature()

        if not isinstance(target_feature, SourceFeatureSpec):
            raise SchemaValidationError(
                f"Target feature '{target_feature.label}' in source "
                f"dataset '{self.dataset_name}' is not a "
                "SourceFeatureSpec.",
            )

        return target_feature

    def get_feature(self, feature_label: str) -> SourceFeatureSpec:
        """Return a source feature by its canonical label.

        Raises:
            KeyError: If no feature has the requested label.
        """

        feature = super().get_feature(feature_label)

        if not isinstance(feature, SourceFeatureSpec):
            raise SchemaValidationError(
                f"Feature '{feature_label}' in source dataset "
                f"'{self.dataset_name}' is not a SourceFeatureSpec.",
            )

        return feature

    def feature_labels(self) -> tuple[str, ...]:
        """Return canonical source-feature labels."""

        return tuple(feature.label for feature in self.all_features())

    def predictor_feature_labels(self) -> tuple[str, ...]:
        """Return canonical labels for source predictor features."""

        return tuple(feature.label for feature in self.predictor_features())

    def source_column_names(self) -> tuple[str, ...]:
        """Return original CSV column names in schema order."""

        return tuple(feature.source_column_name for feature in self.all_features())


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformedDatasetSchema(DatasetSchema):
    """Immutable schema describing a transformed machine-learning dataset."""

    def __post_init__(self) -> None:
        """Validate transformed-dataset-specific invariants."""

        super().__post_init__()

        unsupported_features = tuple(
            feature
            for feature in self.features
            if not isinstance(
                feature,
                TransformedFeatureSpec,
            )
        )

        if unsupported_features:
            unsupported_feature_labels = tuple(
                feature.label for feature in unsupported_features
            )

            raise SchemaValidationError(
                f"Transformed dataset '{self.dataset_name}' contains "
                "unsupported feature specifications: "
                f"{unsupported_feature_labels!r}.",
            )

    def all_features(
        self,
    ) -> tuple[TransformedFeatureSpec, ...]:
        """Return all transformed-dataset features in declared order."""

        return tuple(
            feature
            for feature in self.features
            if isinstance(
                feature,
                TransformedFeatureSpec,
            )
        )

    def predictor_features(
        self,
    ) -> tuple[TransformedFeatureSpec, ...]:
        """Return transformed features intended as model predictors."""

        return tuple(
            feature
            for feature in self.all_features()
            if feature.role is FeatureRole.PREDICTOR
        )

    def identifier_features(
        self,
    ) -> tuple[TransformedFeatureSpec, ...]:
        """Return transformed features that identify records or entities."""

        return tuple(
            feature
            for feature in self.all_features()
            if feature.role is FeatureRole.IDENTIFIER
        )

    def metadata_features(
        self,
    ) -> tuple[TransformedFeatureSpec, ...]:
        """Return transformed features containing metadata."""

        return tuple(
            feature
            for feature in self.all_features()
            if feature.role is FeatureRole.METADATA
        )

    def target_feature(
        self,
    ) -> TransformedFeatureSpec:
        """Return the unique transformed target feature."""

        target_feature = super().target_feature()

        if not isinstance(
            target_feature,
            TransformedFeatureSpec,
        ):
            raise SchemaValidationError(
                f"Target feature '{target_feature.label}' in transformed "
                f"dataset '{self.dataset_name}' has an unsupported "
                "feature specification type.",
            )

        return target_feature

    def get_feature(
        self,
        feature_label: str,
    ) -> TransformedFeatureSpec:
        """Return a transformed feature by its canonical label.

        Raises:
            KeyError: If no feature has the requested label.
        """

        feature = super().get_feature(feature_label)

        if not isinstance(
            feature,
            TransformedFeatureSpec,
        ):
            raise SchemaValidationError(
                f"Feature '{feature_label}' in transformed dataset "
                f"'{self.dataset_name}' has an unsupported feature "
                "specification type.",
            )

        return feature

    def feature_labels(self) -> tuple[str, ...]:
        """Return canonical transformed-feature labels."""

        return tuple(feature.label for feature in self.all_features())

    def predictor_feature_labels(self) -> tuple[str, ...]:
        """Return canonical labels for transformed predictor features."""

        return tuple(feature.label for feature in self.predictor_features())
