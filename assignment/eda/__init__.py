"""Data presenting API."""

from eda.common import (
    CategoricalFeatureStatistics,
    FeatureInspection,
    FeatureMetadata,
    FeaturePlotSpecification,
    FeaturePlotType,
    NumericalFeatureStatistics,
)
from eda.features import (
    inspect_feature,
    render_feature_plot,
    render_feature_plots,
    summarize_feature,
)
from eda.palette import (
    CONTINUOUS_PALETTE,
    DISCRETE_PALETTE,
    get_aggregate_color,
    get_category_colors,
)

__all__ = [
    "CONTINUOUS_PALETTE",
    "DISCRETE_PALETTE",
    "CategoricalFeatureStatistics",
    "FeatureInspection",
    "FeatureMetadata",
    "FeaturePlotSpecification",
    "FeaturePlotType",
    "NumericalFeatureStatistics",
    "get_aggregate_color",
    "get_category_colors",
    "inspect_feature",
    "render_feature_plot",
    "render_feature_plots",
    "summarize_feature",
]
