"""Common schema definitions for network-traffic datasets."""

from dataclasses import dataclass
from enum import StrEnum


class FeatureDataType(StrEnum):
    """Physical representation expected for a feature in a pandas DataFrame."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    DATETIME = "datetime"


class FeatureSemanticType(StrEnum):
    """Semantic interpretation of a feature."""

    NUMERIC = "numeric"
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


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """Describes one dataset feature independently of pandas."""

    label: str
    name: str
    source_column_name: str
    data_type: FeatureDataType
    semantic_type: FeatureSemanticType
    role: FeatureRole
    description: str
    category_enum: type[StrEnum] | None = None

    def __post_init__(self) -> None:
        """Validate invariants that must always hold for a feature."""

        if not self.label:
            raise SchemaValidationError("Feature label must not be empty.")

        if not self.name:
            raise SchemaValidationError("Feature name must not be empty.")

        if not self.source_column_name:
            raise SchemaValidationError(
                f"Source column name must not be empty for '{self.label}'."
            )

        if not self.description:
            raise SchemaValidationError(
                f"Feature description must not be empty for '{self.label}'."
            )

        if self.semantic_type is FeatureSemanticType.DATETIME:  # noqa: SIM102
            if self.data_type is not FeatureDataType.DATETIME:
                raise SchemaValidationError(
                    f"Datetime feature '{self.label}' must use "
                    f"{FeatureDataType.DATETIME.value!r} as its data type."
                )

        if self.semantic_type is FeatureSemanticType.NUMERIC:  # noqa: SIM102
            if self.data_type not in {
                FeatureDataType.INTEGER,
                FeatureDataType.FLOAT,
            }:
                raise SchemaValidationError(
                    f"Numeric feature '{self.label}' must use an integer or "
                    "float data type."
                )

        if self.semantic_type is FeatureSemanticType.CATEGORICAL:
            if self.category_enum is not None and not issubclass(
                self.category_enum,
                StrEnum,
            ):
                raise SchemaValidationError(
                    f"Category enum for '{self.label}' must inherit from StrEnum."
                )
        elif self.category_enum is not None:
            raise SchemaValidationError(
                f"Feature '{self.label}' defines a category enum but is not "
                "categorical."
            )


@dataclass(frozen=True, slots=True)
class DatasetSchema:
    """Immutable description of the columns and target of a dataset."""

    dataset_name: str
    features: tuple[FeatureSpec, ...]
    target_feature_label: str

    def __post_init__(self) -> None:
        """Validate the complete dataset schema."""

        if not self.dataset_name:
            raise SchemaValidationError("Dataset name must not be empty.")

        if not self.features:
            raise SchemaValidationError(
                f"Dataset '{self.dataset_name}' must define at least one feature."
            )

        feature_labels = tuple(feature.label for feature in self.features)
        source_column_names = tuple(
            feature.source_column_name for feature in self.features
        )

        if len(feature_labels) != len(set(feature_labels)):
            raise SchemaValidationError(
                f"Dataset '{self.dataset_name}' contains duplicate feature labels."
            )

        if len(source_column_names) != len(set(source_column_names)):
            raise SchemaValidationError(
                f"Dataset '{self.dataset_name}' contains duplicate source column names."
            )

        if self.target_feature_label not in feature_labels:
            raise SchemaValidationError(
                f"Target feature '{self.target_feature_label}' is not defined "
                f"in dataset '{self.dataset_name}'."
            )

        target_features = tuple(
            feature for feature in self.features if feature.role is FeatureRole.TARGET
        )

        if len(target_features) != 1:
            raise SchemaValidationError(
                f"Dataset '{self.dataset_name}' must define exactly one "
                f"{FeatureRole.TARGET.value!r} feature; found "
                f"{len(target_features)}."
            )

        if target_features[0].label != self.target_feature_label:
            raise SchemaValidationError(
                "The explicitly configured target_feature_label does not "
                "match the feature marked as the target."
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

        # This is unreachable because DatasetSchema validates the invariant.
        raise SchemaValidationError(
            f"Target feature '{self.target_feature_label}' could not be found."
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
            f"dataset '{self.dataset_name}'."
        )

    def feature_labels(self) -> tuple[str, ...]:
        """Return canonical feature labels in schema order."""

        return tuple(feature.label for feature in self.features)

    def predictor_feature_labels(self) -> tuple[str, ...]:
        """Return canonical labels for all predictor features."""

        return tuple(feature.label for feature in self.predictor_features())

    def source_column_names(self) -> tuple[str, ...]:
        """Return original dataset column names in schema order."""

        return tuple(feature.source_column_name for feature in self.features)
