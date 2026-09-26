"""Feature-level exploratory data analysis."""

from collections.abc import Callable, Sequence
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, display
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.figure import Figure
from matplotlib.ticker import FixedFormatter, FixedLocator

from eda.common import (
    CategoricalFeatureStatistics,
    FeatureInspection,
    FeatureMetadata,
    FeaturePlotSpecification,
    FeaturePlotType,
    FrequencyAxisScale,
    NumericalAxisScale,
    NumericalFeatureStatistics,
)
from eda.palette import (
    get_aggregate_color,
    get_discrete_colors,
)
from schema.common import (
    FeatureRole,
    FeatureSemanticType,
    FeatureSpec,
)

# ----------------------------------------
# Constants
# ----------------------------------------

DEFAULT_HISTOGRAM_BIN_COUNT = 30
DEFAULT_FIGURE_SIZE = (10.0, 6.0)
DEFAULT_BOXPLOT_FIGURE_SIZE = (12.0, 7.0)

MINIMUM_INTERIOR_TICK_COUNT = 5
MINIMUM_TICK_SPACING_FACTOR = 0.6

_DISTRIBUTION_TICK_QUANTILES = (
    0.25,
    0.50,
    0.75,
)

_FREQUENCY_PLOT_TYPES = frozenset(
    {
        FeaturePlotType.HISTOGRAM,
        FeaturePlotType.STRATIFIED_HISTOGRAM,
        FeaturePlotType.BAR_CHART,
        FeaturePlotType.STRATIFIED_BAR_CHART,
    }
)

_NUMERICAL_PLOT_TYPES = frozenset(
    {
        FeaturePlotType.HISTOGRAM,
        FeaturePlotType.STRATIFIED_HISTOGRAM,
        FeaturePlotType.BOXPLOT,
    }
)

_HISTOGRAM_PLOT_TYPES = frozenset(
    {
        FeaturePlotType.HISTOGRAM,
        FeaturePlotType.STRATIFIED_HISTOGRAM,
    }
)

_CATEGORICAL_PLOT_TYPES = frozenset(
    {
        FeaturePlotType.BAR_CHART,
        FeaturePlotType.STRATIFIED_BAR_CHART,
    }
)

AxisTransform = Callable[[np.ndarray], np.ndarray]
AxisTransformPair = tuple[AxisTransform, AxisTransform]
AxisScale = FrequencyAxisScale | NumericalAxisScale
HorizontalAlignment = Literal["left", "center", "right"]


# ----------------------------------------
# Public API
# ----------------------------------------


def inspect_feature(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    *,
    histogram_bin_count: int = DEFAULT_HISTOGRAM_BIN_COUNT,
    frequency_axis_scale: FrequencyAxisScale = FrequencyAxisScale.LINEAR,
    numerical_axis_scale: NumericalAxisScale = NumericalAxisScale.LINEAR,
) -> FeatureInspection:
    """Inspect one feature without rendering visualizations.

    The returned ``FeatureInspection`` contains the feature metadata,
    descriptive statistics, and specifications for visualizations
    appropriate for the feature type.

    Args:
        data_frame:
            DataFrame containing the feature and target columns.

        feature_specification:
            Schema specification of the feature to inspect.

        target_feature_specification:
            Schema specification of the target used for stratified
            visualizations.

        histogram_bin_count:
            Number of bins used for numerical histograms.

        frequency_axis_scale:
            Scale used for the Y axis of frequency-based plots.

        numerical_axis_scale:
            Scale used for the X axis of numerical histograms.

    Returns:
        A complete, non-rendered feature inspection.

    Raises:
        ValueError:
            If required columns are missing, the target is invalid,
            or any plot configuration is invalid.
    """

    _validate_feature_and_target_columns(
        data_frame=data_frame,
        feature_specification=feature_specification,
        target_feature_specification=target_feature_specification,
    )

    if histogram_bin_count <= 0:
        raise ValueError(
            "Histogram bin count must be greater than zero.",
        )

    normalized_frequency_axis_scale = FrequencyAxisScale(
        frequency_axis_scale,
    )
    normalized_numerical_axis_scale = NumericalAxisScale(
        numerical_axis_scale,
    )

    return FeatureInspection(
        metadata_table=_create_feature_metadata_table(
            feature_specification,
        ),
        statistics_table=_create_feature_statistics_table(
            data_frame=data_frame,
            feature_specification=feature_specification,
        ),
        plots=_create_feature_plot_specifications(
            feature_specification=feature_specification,
            target_feature_specification=target_feature_specification,
            histogram_bin_count=histogram_bin_count,
            frequency_axis_scale=normalized_frequency_axis_scale,
            numerical_axis_scale=normalized_numerical_axis_scale,
        ),
    )


def summarize_feature(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize one feature without creating or rendering plots.

    Args:
        data_frame:
            DataFrame containing the feature.

        feature_specification:
            Schema specification of the feature.

    Returns:
        A tuple containing the metadata table and statistics table.

    Raises:
        ValueError:
            If the feature is absent, empty, invalid, or has an unsupported
            semantic type.
    """

    _validate_feature_column(
        data_frame=data_frame,
        feature_specification=feature_specification,
    )

    return (
        _create_feature_metadata_table(
            feature_specification,
        ),
        _create_feature_statistics_table(
            data_frame=data_frame,
            feature_specification=feature_specification,
        ),
    )


def render_feature_plot(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    plot_specification: FeaturePlotSpecification,
    *,
    target_feature_specification: FeatureSpec | None = None,
) -> Figure:
    """Render one previously configured feature visualization.

    Args:
        data_frame:
            DataFrame containing the feature and, when required, the target.

        feature_specification:
            Schema specification of the feature.

        plot_specification:
            Plot configuration returned by ``inspect_feature``.

        target_feature_specification:
            Schema specification of the target. Required for stratified
            plots and boxplots.

    Returns:
        A rendered Matplotlib figure.

    Raises:
        ValueError:
            If the plot specification is incompatible with the supplied
            feature or target specification.
    """

    _validate_plot_feature(
        feature_specification=feature_specification,
        plot_specification=plot_specification,
    )

    _validate_feature_column(
        data_frame=data_frame,
        feature_specification=feature_specification,
    )

    target_specification = _resolve_target_feature_specification(
        data_frame=data_frame,
        plot_specification=plot_specification,
        target_feature_specification=target_feature_specification,
    )

    match plot_specification.plot_type:
        case FeaturePlotType.HISTOGRAM:
            return _render_numerical_aggregate_histogram(
                data_frame=data_frame,
                feature_specification=feature_specification,
                histogram_bin_count=_require_histogram_bin_count(
                    plot_specification,
                ),
                numerical_axis_scale=plot_specification.numerical_axis_scale,
                frequency_axis_scale=plot_specification.frequency_axis_scale,
            )

        case FeaturePlotType.BOXPLOT:
            return _render_numerical_boxplots(
                data_frame=data_frame,
                feature_specification=feature_specification,
                target_feature_specification=(
                    _require_target_feature_specification(
                        target_specification,
                    )
                ),
            )

        case FeaturePlotType.STRATIFIED_HISTOGRAM:
            return _render_numerical_stratified_histogram(
                data_frame=data_frame,
                feature_specification=feature_specification,
                target_feature_specification=(
                    _require_target_feature_specification(
                        target_specification,
                    )
                ),
                histogram_bin_count=_require_histogram_bin_count(
                    plot_specification,
                ),
                numerical_axis_scale=plot_specification.numerical_axis_scale,
                frequency_axis_scale=plot_specification.frequency_axis_scale,
            )

        case FeaturePlotType.BAR_CHART:
            return _render_categorical_aggregate_bar_chart(
                data_frame=data_frame,
                feature_specification=feature_specification,
                frequency_axis_scale=plot_specification.frequency_axis_scale,
            )

        case FeaturePlotType.STRATIFIED_BAR_CHART:
            return _render_categorical_stratified_bar_chart(
                data_frame=data_frame,
                feature_specification=feature_specification,
                target_feature_specification=(
                    _require_target_feature_specification(
                        target_specification,
                    )
                ),
                frequency_axis_scale=plot_specification.frequency_axis_scale,
            )

        case _:
            raise ValueError(
                f"Unsupported feature plot type "
                f"'{plot_specification.plot_type.value}'.",
            )


def render_feature_plots(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    feature_inspection: FeatureInspection,
    *,
    target_feature_specification: FeatureSpec | None = None,
) -> tuple[Figure, ...]:
    """Render all plots configured by a feature inspection.

    Args:
        data_frame:
            DataFrame containing the feature and, when required, the target.

        feature_specification:
            Schema specification of the inspected feature.

        feature_inspection:
            Previously computed feature inspection.

        target_feature_specification:
            Schema specification of the target. Required when the inspection
            contains plots that use a target.

    Returns:
        Rendered figures in the same order as the inspection specifications.
    """

    return tuple(
        render_feature_plot(
            data_frame=data_frame,
            feature_specification=feature_specification,
            plot_specification=plot_specification,
            target_feature_specification=target_feature_specification,
        )
        for plot_specification in feature_inspection.plots
    )


def display_feature(
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    data_frame: pd.DataFrame,
    *,
    histogram_bin_count: int = DEFAULT_HISTOGRAM_BIN_COUNT,
    frequency_axis_scale: FrequencyAxisScale = FrequencyAxisScale.LINEAR,
    numerical_axis_scale: NumericalAxisScale = NumericalAxisScale.LINEAR,
) -> None:
    """Display feature metadata, statistics, and visualizations.

    Args:
        feature_specification:
            Schema specification of the feature.

        target_feature_specification:
            Schema specification of the target used for stratified plots.

        data_frame:
            DataFrame containing the feature and target.

        histogram_bin_count:
            Number of bins used for numerical histograms.

        frequency_axis_scale:
            Scale used for the Y axis of frequency-based plots.

        numerical_axis_scale:
            Scale used for the X axis of numerical histograms.
    """

    display(
        HTML(
            f"<h2>{feature_specification.name}</h2>",
        ),
    )

    feature_inspection = inspect_feature(
        data_frame=data_frame,
        feature_specification=feature_specification,
        target_feature_specification=target_feature_specification,
        histogram_bin_count=histogram_bin_count,
        frequency_axis_scale=frequency_axis_scale,
        numerical_axis_scale=numerical_axis_scale,
    )

    display(feature_inspection.metadata_table)
    display(feature_inspection.statistics_table)

    figures = render_feature_plots(
        data_frame=data_frame,
        feature_specification=feature_specification,
        feature_inspection=feature_inspection,
        target_feature_specification=target_feature_specification,
    )

    for figure in figures:
        display(figure)
        plt.close(figure)


# ----------------------------------------
# Validation
# ----------------------------------------


def _validate_feature_and_target_columns(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
) -> None:
    """Validate feature and target specifications used for inspection."""

    _validate_feature_column(
        data_frame=data_frame,
        feature_specification=feature_specification,
    )

    _validate_feature_column(
        data_frame=data_frame,
        feature_specification=target_feature_specification,
    )

    if target_feature_specification.role is not FeatureRole.TARGET:
        raise ValueError(
            f"Feature '{target_feature_specification.label}' must have "
            f"the role '{FeatureRole.TARGET.value}'.",
        )

    if target_feature_specification.semantic_type not in (
        FeatureSemanticType.CATEGORICAL,
        FeatureSemanticType.BINARY,
    ):
        raise ValueError(
            f"Target feature '{target_feature_specification.label}' must "
            "be categorical for stratified feature visualization.",
        )


def _validate_feature_column(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
) -> None:
    """Validate that the specified feature exists in the DataFrame."""

    if feature_specification.label not in data_frame.columns:
        raise ValueError(
            f"Feature '{feature_specification.label}' is not present "
            "in the supplied DataFrame.",
        )


def _validate_plot_feature(
    feature_specification: FeatureSpec,
    plot_specification: FeaturePlotSpecification,
) -> None:
    """Validate that a plot specification matches its feature."""

    if plot_specification.feature_label != feature_specification.label:
        raise ValueError(
            f"Plot specification refers to feature "
            f"'{plot_specification.feature_label}', but the supplied "
            f"feature is '{feature_specification.label}'.",
        )

    if (
        plot_specification.plot_type in _NUMERICAL_PLOT_TYPES
        and feature_specification.semantic_type is not FeatureSemanticType.NUMERIC
    ):
        raise ValueError(
            f"Plot type '{plot_specification.plot_type.value}' "
            "requires a numerical feature.",
        )

    if (
        plot_specification.plot_type in _CATEGORICAL_PLOT_TYPES
        and feature_specification.semantic_type
        not in (
            FeatureSemanticType.CATEGORICAL,
            FeatureSemanticType.BINARY,
        )
    ):
        raise ValueError(
            f"Plot type '{plot_specification.plot_type.value}' "
            "requires a binary or categorical feature.",
        )

    if (
        plot_specification.frequency_axis_scale is not FrequencyAxisScale.LINEAR
        and plot_specification.plot_type not in _FREQUENCY_PLOT_TYPES
    ):
        raise ValueError(
            f"Frequency axis scale "
            f"'{plot_specification.frequency_axis_scale.value}' "
            "can only be used with frequency-based plots.",
        )

    if (
        plot_specification.numerical_axis_scale is not NumericalAxisScale.LINEAR
        and plot_specification.plot_type not in _HISTOGRAM_PLOT_TYPES
    ):
        raise ValueError(
            f"Numerical axis scale "
            f"'{plot_specification.numerical_axis_scale.value}' "
            "can only be used with histogram plots.",
        )


def _resolve_target_feature_specification(
    data_frame: pd.DataFrame,
    plot_specification: FeaturePlotSpecification,
    target_feature_specification: FeatureSpec | None,
) -> FeatureSpec | None:
    """Resolve the target specification required by a plot.

    A target specification supplied to the overall rendering API is allowed
    to be present even when an individual plot does not use it. This is
    important because ``render_feature_plots()`` receives the target once
    and renders multiple plot specifications.
    """

    if plot_specification.target_feature_label is None:
        return None

    target_specification = _require_target_feature_specification(
        target_feature_specification,
    )

    if target_specification.label != plot_specification.target_feature_label:
        raise ValueError(
            "The target feature specification does not match the "
            "target declared by the plot specification.",
        )

    _validate_feature_column(
        data_frame=data_frame,
        feature_specification=target_specification,
    )

    return target_specification


def _require_target_feature_specification(
    target_feature_specification: FeatureSpec | None,
) -> FeatureSpec:
    """Return the required target feature specification."""

    if target_feature_specification is None:
        raise ValueError(
            "A target feature specification is required.",
        )

    return target_feature_specification


def _require_histogram_bin_count(
    plot_specification: FeaturePlotSpecification,
) -> int:
    """Return a configured histogram bin count."""

    if plot_specification.histogram_bin_count is None:
        raise ValueError(
            f"Plot '{plot_specification.plot_type.value}' does not "
            "define a histogram bin count.",
        )

    return plot_specification.histogram_bin_count


# ----------------------------------------
# Feature inspection construction
# ----------------------------------------


def _create_feature_metadata_table(
    feature_specification: FeatureSpec,
) -> pd.DataFrame:
    """Create the metadata table for a feature."""

    feature_metadata = FeatureMetadata.from_feature_specification(
        feature_specification,
    )

    return pd.DataFrame(
        [
            {
                "name": feature_metadata.name,
                "label": feature_metadata.label,
                "semantic_type": feature_metadata.semantic_type.value,
                "role": feature_metadata.role.value,
                "description": feature_metadata.description,
            },
        ],
    )


def _create_feature_statistics_table(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
) -> pd.DataFrame:
    """Create the appropriate statistics table for a feature."""

    feature_series = data_frame[feature_specification.label]

    match feature_specification.semantic_type:
        case FeatureSemanticType.NUMERIC:
            return _create_numerical_statistics_table(
                feature_series=feature_series,
            )

        case FeatureSemanticType.CATEGORICAL | FeatureSemanticType.BINARY:
            return _create_categorical_statistics_table(
                feature_series=feature_series,
                feature_specification=feature_specification,
            )

        case _:
            raise ValueError(
                f"Feature '{feature_specification.label}' has unsupported "
                f"semantic type '{feature_specification.semantic_type}'.",
            )


def _create_feature_plot_specifications(
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    histogram_bin_count: int,
    frequency_axis_scale: FrequencyAxisScale,
    numerical_axis_scale: NumericalAxisScale,
) -> tuple[FeaturePlotSpecification, ...]:
    """Create plot configurations appropriate for a feature."""

    if feature_specification.semantic_type is FeatureSemanticType.NUMERIC:
        return (
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.BOXPLOT,
                feature_label=feature_specification.label,
                target_feature_label=target_feature_specification.label,
            ),
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.HISTOGRAM,
                feature_label=feature_specification.label,
                histogram_bin_count=histogram_bin_count,
                frequency_axis_scale=frequency_axis_scale,
                numerical_axis_scale=numerical_axis_scale,
            ),
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.STRATIFIED_HISTOGRAM,
                feature_label=feature_specification.label,
                target_feature_label=target_feature_specification.label,
                histogram_bin_count=histogram_bin_count,
                frequency_axis_scale=frequency_axis_scale,
                numerical_axis_scale=numerical_axis_scale,
            ),
        )

    if feature_specification.semantic_type in (
        FeatureSemanticType.CATEGORICAL,
        FeatureSemanticType.BINARY,
    ):
        return (
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.BAR_CHART,
                feature_label=feature_specification.label,
                frequency_axis_scale=frequency_axis_scale,
            ),
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.STRATIFIED_BAR_CHART,
                feature_label=feature_specification.label,
                target_feature_label=target_feature_specification.label,
                frequency_axis_scale=frequency_axis_scale,
            ),
        )

    raise ValueError(
        f"Feature '{feature_specification.label}' has unsupported "
        f"semantic type '{feature_specification.semantic_type}'.",
    )


# ----------------------------------------
# Feature statistics
# ----------------------------------------


def _create_numerical_statistics_table(
    feature_series: pd.Series,
) -> pd.DataFrame:
    """Create descriptive statistics for a numerical feature."""

    numerical_series = pd.to_numeric(
        feature_series,
        errors="raise",
    )

    missing_value_count = int(numerical_series.isna().sum())

    numerical_array = numerical_series.to_numpy(dtype=float)
    infinite_value_count = int(np.isinf(numerical_array).sum())

    numerical_values = _get_numerical_values(feature_series)

    numerical_series = pd.Series(
        numerical_values,
        dtype="float64",
    )

    numerical_statistics = NumericalFeatureStatistics(
        minimum=float(numerical_series.min()),
        maximum=float(numerical_series.max()),
        mean=float(numerical_series.mean()),
        standard_deviation=float(numerical_series.std()),
        percentile_05=float(numerical_series.quantile(0.05)),
        percentile_25=float(numerical_series.quantile(0.25)),
        percentile_50=float(numerical_series.quantile(0.50)),
        percentile_75=float(numerical_series.quantile(0.75)),
        percentile_95=float(numerical_series.quantile(0.95)),
    )

    return pd.DataFrame(
        [
            {
                "statistic": "missing_values",
                "value": missing_value_count,
            },
            {
                "statistic": "infinite_values",
                "value": infinite_value_count,
            },
            {
                "statistic": "range",
                "value": (
                    f"[{numerical_statistics.minimum:g}, "
                    f"{numerical_statistics.maximum:g}]"
                ),
            },
            {
                "statistic": "minimum",
                "value": numerical_statistics.minimum,
            },
            {
                "statistic": "maximum",
                "value": numerical_statistics.maximum,
            },
            {
                "statistic": "mean",
                "value": numerical_statistics.mean,
            },
            {
                "statistic": "standard_deviation",
                "value": numerical_statistics.standard_deviation,
            },
            {
                "statistic": "percentile_05",
                "value": numerical_statistics.percentile_05,
            },
            {
                "statistic": "percentile_25",
                "value": numerical_statistics.percentile_25,
            },
            {
                "statistic": "percentile_50",
                "value": numerical_statistics.percentile_50,
            },
            {
                "statistic": "percentile_75",
                "value": numerical_statistics.percentile_75,
            },
            {
                "statistic": "percentile_95",
                "value": numerical_statistics.percentile_95,
            },
        ],
    )


def _create_categorical_statistics_table(
    feature_series: pd.Series,
    feature_specification: FeatureSpec,
) -> pd.DataFrame:
    """Create frequency statistics for a categorical feature."""

    categorical_values = _get_categorical_values(feature_series)

    category_values = _get_feature_category_order(
        feature_series=categorical_values,
        feature_specification=feature_specification,
    )

    value_counts = pd.Series(
        categorical_values,
        dtype="string",
    ).value_counts()

    total_observation_count = len(categorical_values)

    categorical_statistics: list[CategoricalFeatureStatistics] = []

    for category_value in category_values:
        category_count = int(
            value_counts.get(category_value, 0),
        )

        category_frequency = (
            category_count / total_observation_count
            if total_observation_count > 0
            else 0.0
        )

        categorical_statistics.append(
            CategoricalFeatureStatistics(
                category=category_value,
                count=category_count,
                frequency=category_frequency,
            ),
        )

    return pd.DataFrame(
        [
            {
                "category": statistic.category,
                "count": statistic.count,
                "frequency": statistic.frequency,
            }
            for statistic in categorical_statistics
        ],
    )


# ----------------------------------------
# Value normalization and validation
# ----------------------------------------


def _get_numerical_values(
    feature_series: pd.Series,
) -> list[float]:
    """Return finite numerical feature values as Python floats.

    Missing and non-finite values are excluded because they cannot be
    represented in numerical statistics or visualizations. Their counts are
    reported separately by the numerical statistics table.
    """

    numerical_series = pd.to_numeric(
        feature_series,
        errors="raise",
    )

    if numerical_series.empty:
        raise ValueError(
            "Cannot analyze an empty numerical feature.",
        )

    numerical_values = numerical_series.to_numpy(
        dtype=float,
    )
    finite_values = numerical_values[np.isfinite(numerical_values)]

    if finite_values.size == 0:
        raise ValueError(
            "Numerical feature contains no finite values.",
        )

    return finite_values.tolist()


def _get_validated_categorical_series(
    feature_series: pd.Series,
) -> pd.Series:
    """Return a validated pandas string series."""

    categorical_series = feature_series.astype("string")

    if categorical_series.empty:
        raise ValueError(
            "Cannot analyze an empty categorical feature.",
        )

    if categorical_series.isna().any():
        raise ValueError(
            "Categorical feature contains missing values.",
        )

    return categorical_series


def _get_categorical_values(
    feature_series: pd.Series,
) -> list[str]:
    """Return validated categorical values as Python strings."""

    return [
        str(category_value)
        for category_value in _get_validated_categorical_series(
            feature_series,
        ).tolist()
    ]


def _get_feature_category_order(
    feature_series: Sequence[str],
    feature_specification: FeatureSpec,
) -> tuple[str, ...]:
    """Return deterministic categories for a feature."""

    observed_category_values = set(feature_series)

    if feature_specification.category_enum is not None:
        declared_category_values = tuple(
            category.value for category in feature_specification.category_enum
        )

        return tuple(
            category_value
            for category_value in declared_category_values
            if category_value in observed_category_values
        )

    return tuple(
        sorted(observed_category_values),
    )


def _get_target_category_order(
    target_series: pd.Series,
    target_feature_specification: FeatureSpec,
) -> tuple[str, ...]:
    """Return deterministic target categories in schema order."""

    target_values = _get_categorical_values(target_series)

    return _get_feature_category_order(
        feature_series=target_values,
        feature_specification=target_feature_specification,
    )


# ----------------------------------------
# Axis transformations
# ----------------------------------------


def _get_axis_functions(
    axis_scale: AxisScale,
) -> AxisTransformPair | None:
    """Return the forward and inverse functions for an axis scale."""

    match axis_scale:
        case FrequencyAxisScale.LINEAR | NumericalAxisScale.LINEAR:
            return None

        case FrequencyAxisScale.SQRT | NumericalAxisScale.SQRT:
            return (
                np.sqrt,
                lambda values: np.power(values, 2),
            )

        case FrequencyAxisScale.CUBE_ROOT | NumericalAxisScale.CUBE_ROOT:
            return (
                np.cbrt,
                lambda values: np.power(values, 3),
            )

        case FrequencyAxisScale.LOG1P | NumericalAxisScale.LOG1P:
            return (
                np.log1p,
                np.expm1,
            )

        case _:
            raise ValueError(
                f"Unsupported axis scale '{axis_scale}'.",
            )


def _validate_axis_domain(
    minimum_value: float,
    axis_scale: AxisScale,
) -> None:
    """Validate that an axis scale is defined on the data domain."""

    match axis_scale:
        case FrequencyAxisScale.LINEAR | NumericalAxisScale.LINEAR:
            return

        case FrequencyAxisScale.SQRT | NumericalAxisScale.SQRT:
            if minimum_value < 0:
                raise ValueError(
                    "Square-root axes require non-negative values.",
                )

        case FrequencyAxisScale.LOG1P | NumericalAxisScale.LOG1P:
            if minimum_value <= -1:
                raise ValueError(
                    "Log1p axes require values greater than -1.",
                )

        case FrequencyAxisScale.CUBE_ROOT | NumericalAxisScale.CUBE_ROOT:
            return

        case _:
            raise ValueError(
                f"Unsupported axis scale '{axis_scale}'.",
            )


def _get_nice_tick_step(
    minimum_value: float,
    maximum_value: float,
    *,
    target_tick_count: int,
    minimum_interior_tick_count: int,
) -> float:
    """Calculate a readable linear tick interval."""

    if minimum_value > maximum_value:
        raise ValueError(
            "Minimum value must not exceed maximum value.",
        )

    if target_tick_count < 2:
        raise ValueError(
            "Target tick count must be at least two.",
        )

    if minimum_interior_tick_count < 0:
        raise ValueError(
            "Minimum interior tick count must not be negative.",
        )

    value_range = maximum_value - minimum_value

    if value_range <= 0:
        return 1.0

    rough_step = value_range / (target_tick_count - 1)
    exponent = np.floor(np.log10(rough_step))
    magnitude = 10.0**exponent
    target_interior_tick_count = target_tick_count - 2

    candidate_steps = tuple(
        multiplier * magnitude
        for multiplier in (
            1.0,
            1.25,
            1.5,
            2.0,
            2.5,
            5.0,
            10.0,
        )
    )

    candidates: list[tuple[int, float]] = []

    for candidate_step in candidate_steps:
        first_tick = (
            np.ceil(
                minimum_value / candidate_step,
            )
            * candidate_step
        )
        last_tick = (
            np.floor(
                maximum_value / candidate_step,
            )
            * candidate_step
        )

        if last_tick < first_tick:
            interior_tick_count = 0
        else:
            tick_range = np.arange(
                first_tick,
                last_tick + candidate_step * 0.5,
                candidate_step,
            )

            interior_tick_count = int(
                np.count_nonzero(
                    (tick_range > minimum_value) & (tick_range < maximum_value),
                ),
            )

        if interior_tick_count >= minimum_interior_tick_count:
            candidates.append(
                (
                    abs(interior_tick_count - target_interior_tick_count),
                    candidate_step,
                ),
            )

    if candidates:
        return min(
            candidates,
            key=lambda candidate: (
                candidate[0],
                candidate[1],
            ),
        )[1]

    return candidate_steps[-1]


def _get_linear_tick_values(
    minimum_value: float,
    maximum_value: float,
    *,
    target_tick_count: int = MINIMUM_INTERIOR_TICK_COUNT + 3,
    minimum_interior_tick_count: int = MINIMUM_INTERIOR_TICK_COUNT,
) -> tuple[float, ...]:
    """Return readable linear ticks with exact data-range endpoints."""

    if minimum_value > maximum_value:
        raise ValueError(
            "Minimum value must not exceed maximum value.",
        )

    if minimum_value == maximum_value:
        return (float(minimum_value),)

    tick_step = _get_nice_tick_step(
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        target_tick_count=target_tick_count,
        minimum_interior_tick_count=minimum_interior_tick_count,
    )

    first_tick = (
        np.ceil(
            minimum_value / tick_step,
        )
        * tick_step
    )

    last_tick = (
        np.floor(
            maximum_value / tick_step,
        )
        * tick_step
    )

    ticks = np.arange(
        first_tick,
        last_tick + tick_step * 0.5,
        tick_step,
    )

    interior_tick_values = [
        float(tick) for tick in ticks if minimum_value < tick < maximum_value
    ]

    if len(interior_tick_values) < minimum_interior_tick_count:
        fallback_tick_values = np.linspace(
            minimum_value,
            maximum_value,
            minimum_interior_tick_count + 2,
        )[1:-1]

        interior_tick_values.extend(float(tick) for tick in fallback_tick_values)

    interior_tick_values = sorted(
        {
            float(tick)
            for tick in interior_tick_values
            if minimum_value < tick < maximum_value
        },
    )

    return (
        float(minimum_value),
        *interior_tick_values,
        float(maximum_value),
    )


def _get_decade_tick_values(
    minimum_value: float,
    maximum_value: float,
) -> tuple[float, ...]:
    """Return decade-spaced positive ticks inside a range."""

    if maximum_value <= 0 or minimum_value >= maximum_value:
        return ()

    if minimum_value <= 0:
        first_exponent = 1
    else:
        first_exponent = max(
            1,
            int(np.ceil(np.log10(minimum_value))),
        )

    last_exponent = int(
        np.floor(np.log10(maximum_value)),
    )

    if first_exponent > last_exponent:
        return ()

    return tuple(
        float(10**exponent)
        for exponent in range(
            first_exponent,
            last_exponent + 1,
        )
        if minimum_value < 10**exponent < maximum_value
    )


def _get_quantile_tick_values(
    numerical_values: np.ndarray,
    transform: AxisTransform,
) -> list[float]:
    """Return distinct interior empirical-quantile ticks in transformed space."""

    quantile_values = np.asarray(
        np.quantile(
            numerical_values,
            _DISTRIBUTION_TICK_QUANTILES,
        ),
        dtype=float,
    )

    transformed_quantiles = transform(
        quantile_values,
    )

    return sorted(
        {float(value) for value in transformed_quantiles if np.isfinite(value)}
    )


def _select_additional_tick_values(
    candidate_values: Sequence[float],
    existing_values: Sequence[float],
    *,
    required_count: int,
    minimum_spacing: float,
    boundary_values: Sequence[float] = (),
) -> list[float]:
    """Select additional tick positions without visual crowding."""

    if required_count < 0:
        raise ValueError(
            "Required tick count must not be negative.",
        )

    if minimum_spacing < 0:
        raise ValueError(
            "Minimum tick spacing must not be negative.",
        )

    selected_values: list[float] = []

    for value in existing_values:
        candidate = float(value)

        if not np.isfinite(candidate):
            continue

        if any(
            abs(candidate - selected) < minimum_spacing for selected in selected_values
        ):
            continue

        if any(
            abs(candidate - boundary) < minimum_spacing for boundary in boundary_values
        ):
            continue

        selected_values.append(candidate)

    selected_values.sort()

    remaining_values = sorted(
        {
            float(value)
            for value in candidate_values
            if np.isfinite(value) and float(value) not in selected_values
        },
    )

    while remaining_values and len(selected_values) < required_count:
        eligible_values = [
            candidate
            for candidate in remaining_values
            if (
                all(
                    abs(candidate - selected) >= minimum_spacing
                    for selected in selected_values
                )
                and all(
                    abs(candidate - boundary) >= minimum_spacing
                    for boundary in boundary_values
                )
            )
        ]

        if not eligible_values:
            break

        selected_value = max(
            eligible_values,
            key=lambda candidate: (
                min(
                    (
                        abs(candidate - selected)
                        for selected in (
                            *selected_values,
                            *boundary_values,
                        )
                    ),
                    default=float("inf"),
                ),
                -candidate,
            ),
        )

        selected_values.append(selected_value)
        selected_values.sort()
        remaining_values.remove(selected_value)

    return selected_values


def _get_adaptive_nonlinear_tick_values(
    numerical_values: np.ndarray,
    *,
    minimum_value: float,
    maximum_value: float,
    transform: AxisTransform,
    inverse_transform: AxisTransform,
    minimum_interior_tick_count: int,
) -> tuple[float, ...]:
    """Return readable ticks for a nonlinear numeric axis."""

    transformed_minimum = float(
        transform(
            np.asarray([minimum_value], dtype=float),
        )[0],
    )
    transformed_maximum = float(
        transform(
            np.asarray([maximum_value], dtype=float),
        )[0],
    )

    transformed_range = transformed_maximum - transformed_minimum

    if transformed_range <= 0:
        return (
            float(minimum_value),
            float(maximum_value),
        )

    ideal_spacing = transformed_range / (minimum_interior_tick_count + 1)

    decade_raw_ticks = (
        _get_decade_tick_values(
            minimum_value=minimum_value,
            maximum_value=maximum_value,
        )
        if minimum_value >= 0
        else ()
    )

    decade_transformed_ticks = (
        tuple(
            float(value)
            for value in transform(
                np.asarray(
                    decade_raw_ticks,
                    dtype=float,
                ),
            )
        )
        if decade_raw_ticks
        else ()
    )

    quantile_transformed_ticks = tuple(
        value
        for value in _get_quantile_tick_values(
            numerical_values=numerical_values,
            transform=transform,
        )
        if transformed_minimum < value < transformed_maximum
    )

    fallback_ticks = tuple(
        float(value)
        for value in np.linspace(
            transformed_minimum,
            transformed_maximum,
            (minimum_interior_tick_count + 2) * 4,
        )[1:-1]
    )

    boundary_values = (
        transformed_minimum,
        transformed_maximum,
    )

    # Prefer decade landmarks, then empirical quantiles, then transformed
    # uniform positions. All three pools are filtered by the same minimum
    # spacing so labels cannot bunch together near zero.
    for spacing_factor in (
        MINIMUM_TICK_SPACING_FACTOR,
        0.45,
        0.30,
        0.15,
        0.0,
    ):
        current_spacing = ideal_spacing * spacing_factor

        selected_transformed_ticks = _select_additional_tick_values(
            candidate_values=quantile_transformed_ticks,
            existing_values=decade_transformed_ticks,
            required_count=minimum_interior_tick_count,
            minimum_spacing=current_spacing,
            boundary_values=boundary_values,
        )

        if len(selected_transformed_ticks) < minimum_interior_tick_count:
            selected_transformed_ticks = _select_additional_tick_values(
                candidate_values=fallback_ticks,
                existing_values=selected_transformed_ticks,
                required_count=minimum_interior_tick_count,
                minimum_spacing=current_spacing,
                boundary_values=boundary_values,
            )

        if len(selected_transformed_ticks) >= minimum_interior_tick_count:
            break

    selected_transformed_ticks = sorted(
        {
            float(value)
            for value in selected_transformed_ticks
            if transformed_minimum < value < transformed_maximum
        },
    )

    raw_tick_values = inverse_transform(
        np.asarray(
            (
                transformed_minimum,
                *selected_transformed_ticks,
                transformed_maximum,
            ),
            dtype=float,
        ),
    )

    return tuple(float(value) for value in raw_tick_values)


def _get_axis_tick_values(
    values: Sequence[float],
    axis_scale: AxisScale,
    *,
    minimum_value: float | None = None,
    maximum_value: float | None = None,
    minimum_interior_tick_count: int = MINIMUM_INTERIOR_TICK_COUNT,
) -> tuple[float, ...]:
    """Generate reusable, data-aware ticks for any numeric axis.

    Tick values are always returned in the original data space. The axis
    transformation is applied later by Matplotlib.

    Linear axes use human-friendly regular intervals. Positive nonlinear
    axes prefer decade landmarks such as 10, 100, 1k, and 10k. When the
    range is too small to provide enough landmarks, empirical quantiles
    and evenly spaced transformed coordinates are used as fallback.
    """

    numerical_values = np.asarray(
        values,
        dtype=float,
    )

    if numerical_values.size == 0:
        raise ValueError(
            "Cannot generate ticks from an empty collection.",
        )

    if not np.isfinite(numerical_values).all():
        raise ValueError(
            "Axis values must be finite.",
        )

    if minimum_interior_tick_count < 0:
        raise ValueError(
            "Minimum interior tick count must not be negative.",
        )

    observed_minimum = float(
        numerical_values.min(),
    )
    observed_maximum = float(
        numerical_values.max(),
    )

    axis_minimum = observed_minimum if minimum_value is None else float(minimum_value)
    axis_maximum = observed_maximum if maximum_value is None else float(maximum_value)

    if axis_minimum > axis_maximum:
        raise ValueError(
            "Minimum value must not exceed maximum value.",
        )

    _validate_axis_domain(
        minimum_value=axis_minimum,
        axis_scale=axis_scale,
    )

    if axis_minimum == axis_maximum:
        return (axis_minimum,)

    axis_functions = _get_axis_functions(
        axis_scale,
    )

    if axis_functions is None:
        return _get_linear_tick_values(
            minimum_value=axis_minimum,
            maximum_value=axis_maximum,
            target_tick_count=(minimum_interior_tick_count + 3),
            minimum_interior_tick_count=minimum_interior_tick_count,
        )

    transform, inverse_transform = axis_functions

    return _get_adaptive_nonlinear_tick_values(
        numerical_values=numerical_values,
        minimum_value=axis_minimum,
        maximum_value=axis_maximum,
        transform=transform,
        inverse_transform=inverse_transform,
        minimum_interior_tick_count=minimum_interior_tick_count,
    )


# ----------------------------------------
# Histogram utilities
# ----------------------------------------


def _calculate_histogram_bin_edges(
    numerical_values: Sequence[float],
    histogram_bin_count: int,
    numerical_axis_scale: NumericalAxisScale,
) -> list[float]:
    """Calculate common histogram bin edges in the selected X-axis space."""

    if histogram_bin_count <= 0:
        raise ValueError(
            "Histogram bin count must be greater than zero.",
        )

    numerical_array = np.asarray(
        numerical_values,
        dtype=float,
    )

    if numerical_array.size == 0:
        raise ValueError(
            "Cannot calculate histogram bins for an empty feature.",
        )

    if not np.isfinite(numerical_array).all():
        raise ValueError(
            "Histogram values must be finite.",
        )

    axis_functions = _get_axis_functions(
        numerical_axis_scale,
    )

    minimum_value = float(
        numerical_array.min(),
    )
    maximum_value = float(
        numerical_array.max(),
    )

    _validate_axis_domain(
        minimum_value=minimum_value,
        axis_scale=numerical_axis_scale,
    )

    if axis_functions is None:
        transformed_values = numerical_array
        inverse_transform: AxisTransform = lambda values: values
    else:
        transform, inverse_transform = axis_functions
        transformed_values = transform(
            numerical_array,
        )

    if minimum_value == maximum_value:
        transformed_center = float(
            transformed_values[0],
        )

        if numerical_axis_scale is NumericalAxisScale.LINEAR:
            transformed_margin = 0.5
        else:
            transformed_margin = max(
                0.5,
                abs(transformed_center) * 0.05,
            )

        transformed_bin_edges = np.array(
            (
                transformed_center - transformed_margin,
                transformed_center + transformed_margin,
            ),
            dtype=float,
        )
    else:
        transformed_bin_edges = np.linspace(
            transformed_values.min(),
            transformed_values.max(),
            histogram_bin_count + 1,
        )

    return [
        float(bin_edge)
        for bin_edge in inverse_transform(
            transformed_bin_edges,
        )
    ]


# ----------------------------------------
# Axis formatting
# ----------------------------------------


def _format_scale_name(
    axis_scale: AxisScale,
) -> str:
    """Return a human-readable axis scale name."""

    return axis_scale.value.replace(
        "_",
        " ",
    )


def _format_axis_tick(
    value: float,
) -> str:
    """Format a numeric axis tick using compact, readable notation."""

    if not np.isfinite(value):
        return ""

    if np.isclose(value, 0.0):
        return "0"

    sign = "-" if value < 0 else ""
    absolute_value = abs(value)
    suffix = ""

    if absolute_value >= 1_000_000_000:
        scaled_value = absolute_value / 1_000_000_000
        suffix = "B"
        formatted_value = f"{scaled_value:.4g}"
    elif absolute_value >= 1_000_000:
        scaled_value = absolute_value / 1_000_000
        suffix = "M"
        formatted_value = f"{scaled_value:.4g}"
    elif absolute_value >= 1_000:
        scaled_value = absolute_value / 1_000
        suffix = "k"
        formatted_value = f"{scaled_value:.4g}"
    elif absolute_value >= 1:
        suffix = ""
        formatted_value = f"{absolute_value:.4g}"
    elif absolute_value >= 1e-6:
        decimal_places = min(
            10,
            max(
                0,
                int(-np.floor(np.log10(absolute_value))) + 3,
            ),
        )
        formatted_value = f"{absolute_value:.{decimal_places}f}"
    else:
        suffix = ""
        formatted_value = f"{absolute_value:.3g}"

    if "." in formatted_value:
        formatted_value = formatted_value.rstrip("0").rstrip(".")

    return f"{sign}{formatted_value}{suffix}"


def _format_axis_label(
    name: str,
    axis_scale: AxisScale,
) -> str:
    """Create an axis label that identifies the displayed scale."""

    return f"{name} ({_format_scale_name(axis_scale)})"


def _configure_x_tick_labels(
    axes: Axes,
    *,
    label_rotation: float = 45.0,
    horizontal_alignment: HorizontalAlignment = "right",
) -> None:
    """Configure the presentation of all X-axis tick labels."""

    axes.tick_params(
        axis="x",
        labelrotation=label_rotation,
    )

    for tick_label in axes.get_xticklabels():
        tick_label.set_horizontalalignment(
            horizontal_alignment,
        )


def _configure_axis_ticks(
    axis: Axis,
    tick_values: Sequence[float],
    *,
    label_rotation: float = 0.0,
    horizontal_alignment: HorizontalAlignment = "center",
) -> None:
    """Configure fixed numeric ticks and their label presentation."""

    labels = tuple(
        _format_axis_tick(
            float(tick_value),
        )
        for tick_value in tick_values
    )

    axis.set_major_locator(
        FixedLocator(tick_values),
    )
    axis.set_major_formatter(
        FixedFormatter(labels),
    )

    if label_rotation != 0.0 or horizontal_alignment != "center":
        for tick_label in axis.get_ticklabels():
            tick_label.set_rotation(label_rotation)
            tick_label.set_horizontalalignment(
                horizontal_alignment,
            )


def _configure_axis_grid(
    axes: Axes,
) -> None:
    """Configure the shared horizontal grid styling."""

    axes.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.4,
    )


def _configure_numerical_axis(
    axes: Axes,
    numerical_axis_scale: NumericalAxisScale,
    *,
    feature_name: str,
    numerical_values: Sequence[float],
) -> None:
    """Configure a numerical X axis, including data-aware ticks and label."""

    numerical_array = np.asarray(
        numerical_values,
        dtype=float,
    )

    minimum_value = float(
        numerical_array.min(),
    )
    maximum_value = float(
        numerical_array.max(),
    )

    _validate_axis_domain(
        minimum_value=minimum_value,
        axis_scale=numerical_axis_scale,
    )

    axis_functions = _get_axis_functions(
        numerical_axis_scale,
    )

    if axis_functions is None:
        axes.set_xscale("linear")
    else:
        axes.set_xscale(
            "function",
            functions=axis_functions,
        )

    numerical_values_sequence = tuple(float(value) for value in numerical_array)

    tick_values = _get_axis_tick_values(
        values=numerical_values_sequence,
        axis_scale=numerical_axis_scale,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
    )

    _configure_axis_ticks(
        axis=axes.xaxis,
        tick_values=tick_values,
    )
    _configure_x_tick_labels(
        axes,
    )

    axes.set_xlabel(
        _format_axis_label(
            name=feature_name,
            axis_scale=numerical_axis_scale,
        ),
    )


def _configure_frequency_axis(
    axes: Axes,
    frequency_axis_scale: FrequencyAxisScale,
    *,
    frequency_values: Sequence[float],
) -> None:
    """Configure a frequency Y axis, including data-aware ticks and label."""

    frequencies = np.asarray(
        frequency_values,
        dtype=float,
    )

    if frequencies.size == 0:
        raise ValueError(
            "Cannot configure a frequency axis without frequency values.",
        )

    if not np.isfinite(frequencies).all():
        raise ValueError(
            "Frequency values must be finite.",
        )

    maximum_frequency = float(
        frequencies.max(),
    )

    _validate_axis_domain(
        minimum_value=0.0,
        axis_scale=frequency_axis_scale,
    )

    axis_functions = _get_axis_functions(
        frequency_axis_scale,
    )

    if axis_functions is None:
        axes.set_yscale("linear")
    else:
        axes.set_yscale(
            "function",
            functions=axis_functions,
        )

    tick_values = _get_axis_tick_values(
        values=frequency_values,
        axis_scale=frequency_axis_scale,
        minimum_value=0.0,
        maximum_value=maximum_frequency,
    )

    _configure_axis_ticks(
        axis=axes.yaxis,
        tick_values=tick_values,
    )

    axes.set_ylabel(
        _format_axis_label(
            name="Frequency",
            axis_scale=frequency_axis_scale,
        ),
    )

    axes.set_ylim(
        bottom=0,
    )


# ----------------------------------------
# Numerical plots
# ----------------------------------------


def _render_numerical_aggregate_histogram(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    histogram_bin_count: int,
    numerical_axis_scale: NumericalAxisScale,
    frequency_axis_scale: FrequencyAxisScale,
) -> Figure:
    """Render an aggregate histogram for a numerical feature."""

    numerical_values = _get_numerical_values(
        data_frame[feature_specification.label],
    )

    histogram_bin_edges = _calculate_histogram_bin_edges(
        numerical_values=numerical_values,
        histogram_bin_count=histogram_bin_count,
        numerical_axis_scale=numerical_axis_scale,
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    frequencies, _, _ = axes.hist(
        numerical_values,
        bins=histogram_bin_edges,
        color=get_aggregate_color(),
        edgecolor="black",
    )

    axes.set_title(
        f"Distribution of {feature_specification.name}",
    )

    _configure_numerical_axis(
        axes=axes,
        numerical_axis_scale=numerical_axis_scale,
        feature_name=feature_specification.name,
        numerical_values=numerical_values,
    )

    frequency_values = tuple(float(frequency) for frequency in frequencies)

    _configure_frequency_axis(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        frequency_values=frequency_values,
    )

    _configure_axis_grid(axes)

    figure.tight_layout()

    return figure


def _render_numerical_stratified_histogram(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    histogram_bin_count: int,
    numerical_axis_scale: NumericalAxisScale,
    frequency_axis_scale: FrequencyAxisScale,
) -> Figure:
    """Render a target-stratified histogram for a numerical feature."""

    feature_series = pd.to_numeric(
        data_frame[feature_specification.label],
        errors="raise",
    )

    numerical_values = _get_numerical_values(
        feature_series,
    )

    target_series = _get_validated_categorical_series(
        data_frame[target_feature_specification.label],
    )

    target_category_values = _get_target_category_order(
        target_series=target_series,
        target_feature_specification=target_feature_specification,
    )

    histogram_bin_edges = _calculate_histogram_bin_edges(
        numerical_values=numerical_values,
        histogram_bin_count=histogram_bin_count,
        numerical_axis_scale=numerical_axis_scale,
    )

    target_category_colors = get_discrete_colors(
        len(target_category_values),
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    histogram_frequencies: list[float] = []

    for target_category_value, target_category_color in zip(
        target_category_values,
        target_category_colors,
        strict=True,
    ):
        target_category_mask = target_series == target_category_value

        category_values = feature_series.loc[target_category_mask].to_numpy(
            dtype=float,
        )
        category_values = category_values[np.isfinite(category_values)]

        frequencies, _, _ = axes.hist(
            category_values,
            bins=histogram_bin_edges,
            color=target_category_color,
            alpha=0.55,
            edgecolor="black",
            label=target_category_value,
        )

        histogram_frequencies.extend(
            float(frequency)
            for frequency in np.asarray(
                frequencies,
                dtype=float,
            )
        )

    axes.set_title(
        f"{feature_specification.name} by {target_feature_specification.name}",
    )

    _configure_numerical_axis(
        axes=axes,
        numerical_axis_scale=numerical_axis_scale,
        feature_name=feature_specification.name,
        numerical_values=numerical_values,
    )

    _configure_frequency_axis(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        frequency_values=histogram_frequencies,
    )

    axes.legend(
        title=target_feature_specification.name,
    )

    _configure_axis_grid(axes)

    figure.tight_layout()

    return figure


def _render_numerical_boxplots(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
) -> Figure:
    """Render aggregate and target-stratified boxplots."""

    feature_values = _get_numerical_values(
        data_frame[feature_specification.label],
    )

    target_series = _get_validated_categorical_series(
        data_frame[target_feature_specification.label],
    )

    target_category_values = _get_target_category_order(
        target_series=target_series,
        target_feature_specification=target_feature_specification,
    )

    numerical_feature_series = pd.to_numeric(
        data_frame[feature_specification.label],
        errors="raise",
    )

    boxplot_values: list[list[float]] = [
        feature_values,
    ]
    boxplot_labels: list[str] = [
        "Aggregate",
    ]

    for target_category_value in target_category_values:
        target_category_mask = target_series == target_category_value

        category_values = numerical_feature_series.loc[target_category_mask].to_numpy(
            dtype=float,
        )
        category_values = category_values[np.isfinite(category_values)]

        if category_values.size == 0:
            continue

        boxplot_values.append(category_values.tolist())
        boxplot_labels.append(target_category_value)

    boxplot_colors = get_discrete_colors(
        len(boxplot_labels) - 1,
        include_aggregate=True,
    )

    boxplot_labels: list[str] = [
        "Aggregate",
        *target_category_values,
    ]

    figure, axes = plt.subplots(
        figsize=DEFAULT_BOXPLOT_FIGURE_SIZE,
    )

    boxplot_artists = axes.boxplot(
        boxplot_values,
        tick_labels=boxplot_labels,
        patch_artist=True,
        showfliers=True,
    )

    for boxplot_artist, box_color in zip(
        boxplot_artists["boxes"],
        boxplot_colors,
        strict=True,
    ):
        boxplot_artist.set_facecolor(
            box_color,
        )
        boxplot_artist.set_alpha(
            0.75,
        )

    axes.set_title(
        f"{feature_specification.name} by {target_feature_specification.name}",
    )
    axes.set_xlabel("Group")
    axes.set_ylabel(feature_specification.name)

    _configure_x_tick_labels(
        axes,
    )
    _configure_axis_grid(axes)

    figure.tight_layout()

    return figure


# ----------------------------------------
# Categorical plots
# ----------------------------------------


def _render_categorical_aggregate_bar_chart(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    frequency_axis_scale: FrequencyAxisScale,
) -> Figure:
    """Render an aggregate categorical frequency bar chart."""

    feature_series = _get_validated_categorical_series(
        data_frame[feature_specification.label],
    )

    category_values = _get_feature_category_order(
        feature_series=feature_series.tolist(),
        feature_specification=feature_specification,
    )

    value_counts = feature_series.value_counts()

    category_counts = tuple(
        float(value_counts.get(category_value, 0)) for category_value in category_values
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    axes.bar(
        category_values,
        category_counts,
        color=get_aggregate_color(),
        edgecolor="black",
    )

    axes.set_title(
        f"Frequency of {feature_specification.name}",
    )
    axes.set_xlabel(
        feature_specification.name,
    )

    _configure_frequency_axis(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        frequency_values=category_counts,
    )

    _configure_x_tick_labels(
        axes,
    )

    _configure_axis_grid(axes)

    figure.tight_layout()

    return figure


def _render_categorical_stratified_bar_chart(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    frequency_axis_scale: FrequencyAxisScale,
) -> Figure:
    """Render a target-stratified categorical frequency bar chart."""

    feature_series = _get_validated_categorical_series(
        data_frame[feature_specification.label],
    )

    target_series = _get_validated_categorical_series(
        data_frame[target_feature_specification.label],
    )

    feature_category_values = _get_feature_category_order(
        feature_series=feature_series.tolist(),
        feature_specification=feature_specification,
    )

    target_category_values = _get_target_category_order(
        target_series=target_series,
        target_feature_specification=target_feature_specification,
    )

    target_category_count = len(target_category_values)

    if target_category_count == 0:
        raise ValueError(
            "No target categories are available for plotting.",
        )

    category_counts = pd.crosstab(
        feature_series,
        target_series,
    ).reindex(
        index=feature_category_values,
        columns=target_category_values,
        fill_value=0,
    )

    target_category_colors = get_discrete_colors(
        target_category_count,
    )

    x_positions = np.arange(
        len(feature_category_values),
        dtype=float,
    )

    bar_width = 0.8 / target_category_count

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    for target_category_index, (
        target_category_value,
        target_category_color,
    ) in enumerate(
        zip(
            target_category_values,
            target_category_colors,
            strict=True,
        ),
    ):
        horizontal_offset = (
            target_category_index - (target_category_count - 1) / 2
        ) * bar_width

        axes.bar(
            x_positions + horizontal_offset,
            category_counts[target_category_value].to_numpy(
                dtype=float,
            ),
            width=bar_width,
            color=target_category_color,
            edgecolor="black",
            label=target_category_value,
        )

    axes.set_title(
        f"{feature_specification.name} by {target_feature_specification.name}",
    )
    axes.set_xlabel(
        feature_specification.name,
    )

    frequency_values = tuple(
        float(value)
        for value in category_counts.to_numpy(
            dtype=float,
        ).ravel()
    )

    _configure_frequency_axis(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        frequency_values=frequency_values,
    )

    axes.set_xticks(
        x_positions,
    )
    axes.set_xticklabels(
        feature_category_values,
    )
    _configure_x_tick_labels(
        axes,
    )

    axes.legend(
        title=target_feature_specification.name,
    )

    _configure_axis_grid(axes)

    figure.tight_layout()

    return figure
