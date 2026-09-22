"""Schema definitions for assignment datasets."""

from .common import (
    DatasetSchema,
    FeatureDataType,
    FeatureRole,
    FeatureSemanticType,
    FeatureSpec,
    SchemaValidationError,
)
from .genis import (
    GENIS_FEATURES,
    GENIS_SCHEMA,
    GenisCategoryLabel,
    GenisSubcategoryLabel,
)
from .rosids import (
    ROSIDS_FEATURES,
    ROSIDS_SCHEMA,
    RosidsLabel,
)

__all__ = [
    "GENIS_FEATURES",
    "GENIS_SCHEMA",
    "ROSIDS_FEATURES",
    "ROSIDS_SCHEMA",
    "DatasetSchema",
    "FeatureDataType",
    "FeatureRole",
    "FeatureSemanticType",
    "FeatureSpec",
    "GenisCategoryLabel",
    "GenisSubcategoryLabel",
    "RosidsLabel",
    "SchemaValidationError",
]
