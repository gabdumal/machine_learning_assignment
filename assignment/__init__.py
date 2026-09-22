"""Assignment package root."""

from .schema.common import (
    DatasetSchema,
    FeatureDataType,
    FeatureRole,
    FeatureSemanticType,
    FeatureSpec,
    SchemaValidationError,
)
from .schema.genis import GENIS_FEATURES, GENIS_SCHEMA

__all__ = [
    "GENIS_FEATURES",
    "GENIS_SCHEMA",
    "DatasetSchema",
    "FeatureDataType",
    "FeatureRole",
    "FeatureSemanticType",
    "FeatureSpec",
    "SchemaValidationError",
]
