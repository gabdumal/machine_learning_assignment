"""Common data structures for exploratory data analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from schema.common import (
    FeatureRole,
    FeatureSemanticType,
    FeatureSpec,
)


class FeaturePlotType(StrEnum):
    """Types of plots supported by feature-level exploratory analysis."""

    BOXPLOT = "boxplot"
    HISTOGRAM = "histogram"
    STRATIFIED_HISTOGRAM = "stratified_histogram"
    BAR_CHART = "bar_chart"
    STRATIFIED_BAR_CHART = "stratified_bar_chart"


@dataclass(frozen=True, slots=True)
class FeaturePlotSpecification:
    """Configuration describing one feature-level visualization.

    This class intentionally contains no rendered Matplotlib objects.
    It describes what should be plotted so that rendering can be deferred
    until the caller explicitly requests it.
    """

    plot_type: FeaturePlotType
    feature_label: str
    target_feature_label: str | None = None
    histogram_bin_count: int | None = None

    def __post_init__(self) -> None:
        """Validate the invariants of the plot specification."""

        requires_target_feature = self.plot_type in {
            FeaturePlotType.BOXPLOT,
            FeaturePlotType.STRATIFIED_HISTOGRAM,
            FeaturePlotType.STRATIFIED_BAR_CHART,
        }

        if requires_target_feature and self.target_feature_label is None:
            raise ValueError(
                f"Plot type '{self.plot_type.value}' requires a target feature label."
            )

        does_not_use_target = self.plot_type in {
            FeaturePlotType.HISTOGRAM,
            FeaturePlotType.BAR_CHART,
        }

        if does_not_use_target and self.target_feature_label is not None:
            raise ValueError(
                f"Plot type '{self.plot_type.value}' must not define a "
                "target feature label."
            )

        uses_histogram_bins = self.plot_type in {
            FeaturePlotType.HISTOGRAM,
            FeaturePlotType.STRATIFIED_HISTOGRAM,
        }

        if uses_histogram_bins:
            if self.histogram_bin_count is None:
                raise ValueError(
                    f"Plot type '{self.plot_type.value}' requires a "
                    "histogram bin count."
                )

            if self.histogram_bin_count <= 0:
                raise ValueError("Histogram bin count must be greater than zero.")

        if not uses_histogram_bins and self.histogram_bin_count is not None:
            raise ValueError(
                f"Plot type '{self.plot_type.value}' must not define a "
                "histogram bin count."
            )


@dataclass(frozen=True, slots=True)
class FeatureInspection:
    """Complete non-rendered EDA description for one dataset feature."""

    metadata_table: pd.DataFrame
    statistics_table: pd.DataFrame
    plots: tuple[FeaturePlotSpecification, ...]


@dataclass(frozen=True, slots=True)
class FeatureMetadata:
    """Typed metadata describing one feature."""

    name: str
    label: str
    semantic_type: FeatureSemanticType
    role: FeatureRole
    description: str

    @classmethod
    def from_feature_specification(
        cls,
        feature_specification: FeatureSpec,
    ) -> FeatureMetadata:
        """Create metadata from a feature schema specification."""

        return cls(
            name=feature_specification.name,
            label=feature_specification.label,
            semantic_type=feature_specification.semantic_type,
            role=feature_specification.role,
            description=feature_specification.description,
        )


@dataclass(frozen=True, slots=True)
class NumericalFeatureStatistics:
    """Descriptive statistics calculated for one numerical feature."""

    minimum: float
    maximum: float
    mean: float
    standard_deviation: float
    percentile_05: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_95: float


@dataclass(frozen=True, slots=True)
class CategoricalFeatureStatistics:
    """Frequency statistics calculated for one categorical feature."""

    category: str
    count: int
    frequency: float
