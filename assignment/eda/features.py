"""Feature-level exploratory data analysis."""

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, display
from matplotlib.axes import Axes
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

_CATEGORICAL_PLOT_TYPES = frozenset(
    {
        FeaturePlotType.BAR_CHART,
        FeaturePlotType.STRATIFIED_BAR_CHART,
    }
)

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
    descriptive statistics, and specifications for the visualizations
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
                numerical_axis_scale=(plot_specification.numerical_axis_scale),
                frequency_axis_scale=(plot_specification.frequency_axis_scale),
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
                numerical_axis_scale=(plot_specification.numerical_axis_scale),
                frequency_axis_scale=(plot_specification.frequency_axis_scale),
            )

        case FeaturePlotType.BAR_CHART:
            return _render_categorical_aggregate_bar_chart(
                data_frame=data_frame,
                feature_specification=feature_specification,
                frequency_axis_scale=(plot_specification.frequency_axis_scale),
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
                frequency_axis_scale=(plot_specification.frequency_axis_scale),
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
    """Return validated numerical feature values as Python floats."""

    numerical_series = pd.to_numeric(
        feature_series,
        errors="raise",
    )

    if numerical_series.empty:
        raise ValueError(
            "Cannot analyze an empty numerical feature.",
        )

    if numerical_series.isna().any():
        raise ValueError(
            "Numerical feature contains missing values.",
        )

    numerical_values = numerical_series.to_numpy(
        dtype=float,
    )

    if not np.isfinite(numerical_values).all():
        raise ValueError(
            "Numerical feature contains non-finite values.",
        )

    return numerical_values.tolist()


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
# Histogram utilities
# ----------------------------------------


def _calculate_histogram_bin_edges(
    numerical_values: Sequence[float],
    histogram_bin_count: int,
    numerical_axis_scale: NumericalAxisScale,
) -> list[float]:
    """Calculate common histogram bin edges for comparable distributions."""

    if histogram_bin_count <= 0:
        raise ValueError(
            "Histogram bin count must be greater than zero.",
        )

    minimum_value = min(numerical_values)
    maximum_value = max(numerical_values)

    if minimum_value == maximum_value:
        return [
            minimum_value - 0.5,
            maximum_value + 0.5,
        ]

    numerical_array = np.asarray(
        numerical_values,
        dtype=float,
    )

    match numerical_axis_scale:
        case NumericalAxisScale.LINEAR:
            transformed_values = numerical_array
            inverse_transform = lambda values: values

        case NumericalAxisScale.CUBE_ROOT:
            transformed_values = np.cbrt(
                numerical_array,
            )
            inverse_transform = lambda values: np.power(
                values,
                3,
            )

        case NumericalAxisScale.SQRT:
            if minimum_value < 0:
                raise ValueError(
                    "Square-root numerical axes require non-negative feature values.",
                )

            transformed_values = np.sqrt(
                numerical_array,
            )
            inverse_transform = lambda values: np.power(
                values,
                2,
            )

        case _:
            raise ValueError(
                f"Unsupported numerical axis scale '{numerical_axis_scale}'.",
            )

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


def _configure_numerical_axis(
    axes: Axes,
    numerical_axis_scale: NumericalAxisScale,
) -> None:
    """Configure the X axis for a numerical visualization."""

    match numerical_axis_scale:
        case NumericalAxisScale.LINEAR:
            axes.set_xscale("linear")

        case NumericalAxisScale.SQRT:
            axes.set_xscale(
                "function",
                functions=(
                    np.sqrt,
                    lambda value: np.power(value, 2),
                ),
            )

        case NumericalAxisScale.CUBE_ROOT:
            axes.set_xscale(
                "function",
                functions=(
                    np.cbrt,
                    lambda value: np.power(value, 3),
                ),
            )

        case _:
            raise ValueError(
                f"Unsupported numerical axis scale '{numerical_axis_scale}'.",
            )


# ----------------------------------------
# Axis configuration
# ----------------------------------------


def _get_nice_frequency_tick_step(
    maximum_frequency: float,
    *,
    target_tick_count: int = 8,
) -> float:
    """Calculate a human-friendly frequency tick interval."""

    if maximum_frequency <= 0:
        return 1.0

    if target_tick_count < 2:
        raise ValueError(
            "Target tick count must be at least two.",
        )

    rough_step = maximum_frequency / (target_tick_count - 1)

    exponent = np.floor(np.log10(rough_step))
    magnitude = 10.0**exponent
    normalized_step = rough_step / magnitude

    if normalized_step <= 1.0:
        nice_step = 1.0
    elif normalized_step <= 2.0:
        nice_step = 2.0
    elif normalized_step <= 5.0:
        nice_step = 5.0
    else:
        nice_step = 10.0

    return nice_step * magnitude


def _format_frequency_tick(value: float) -> str:
    """Format a frequency tick using readable units."""

    if value >= 1_000_000:
        scaled_value = value / 1_000_000
        formatted_value = f"{scaled_value:.1f}".rstrip("0").rstrip(".")
        return f"{formatted_value}M"

    if value >= 1_000:
        scaled_value = value / 1_000
        formatted_value = f"{scaled_value:.1f}".rstrip("0").rstrip(".")
        return f"{formatted_value}k"

    if value.is_integer():
        return str(int(value))

    return f"{value:g}"


def _get_linear_frequency_tick_values(
    maximum_frequency: float,
    *,
    target_tick_count: int = 8,
) -> tuple[float, ...]:
    """Return nice linearly spaced frequency tick values."""

    if maximum_frequency < 0:
        raise ValueError(
            "Maximum frequency must not be negative.",
        )

    if maximum_frequency == 0:
        return (0.0,)

    tick_step = _get_nice_frequency_tick_step(
        maximum_frequency=maximum_frequency,
        target_tick_count=target_tick_count,
    )

    tick_values = np.arange(
        0.0,
        maximum_frequency + tick_step,
        tick_step,
    )

    return tuple(float(tick) for tick in tick_values if tick <= maximum_frequency)


def _get_logarithmic_frequency_tick_values(
    maximum_frequency: float,
) -> tuple[float, ...]:
    """Return logarithmically spaced frequency ticks plus the maximum."""

    if maximum_frequency < 0:
        raise ValueError(
            "Maximum frequency must not be negative.",
        )

    if maximum_frequency == 0:
        return (0.0,)

    maximum_exponent = int(
        np.floor(np.log10(maximum_frequency)),
    )

    minimum_exponent = 1

    if maximum_exponent < minimum_exponent:
        minimum_exponent = 0

    logarithmic_ticks = tuple(
        float(10**exponent)
        for exponent in range(
            minimum_exponent,
            maximum_exponent + 1,
        )
    )

    # Add the exact maximum so the highest bar has a corresponding tick.
    if maximum_frequency not in logarithmic_ticks:
        logarithmic_ticks += (maximum_frequency,)

    return (0.0, *logarithmic_ticks)


def _configure_frequency_ticks(
    axes: Axes,
    *,
    frequency_axis_scale: FrequencyAxisScale,
    maximum_frequency: float,
) -> None:
    """Configure major frequency ticks in raw frequency units."""

    if frequency_axis_scale in {
        FrequencyAxisScale.CUBE_ROOT,
        FrequencyAxisScale.LOG1P,
    }:
        frequency_tick_values = _get_logarithmic_frequency_tick_values(
            maximum_frequency=maximum_frequency,
        )
    else:
        frequency_tick_values = _get_linear_frequency_tick_values(
            maximum_frequency=maximum_frequency,
        )

    tick_labels = tuple(
        _format_frequency_tick(value) for value in frequency_tick_values
    )

    axes.yaxis.set_major_locator(
        FixedLocator(frequency_tick_values),
    )
    axes.yaxis.set_major_formatter(
        FixedFormatter(tick_labels),
    )


def _configure_frequency_axis(
    axes: Axes,
    frequency_axis_scale: FrequencyAxisScale,
    *,
    maximum_frequency: float,
) -> None:
    """Configure the Y axis for a frequency-based visualization."""

    match frequency_axis_scale:
        case FrequencyAxisScale.LINEAR:
            axes.set_yscale("linear")
            axes.set_ylabel("Frequency")

        case FrequencyAxisScale.SQRT:
            axes.set_yscale(
                "function",
                functions=(
                    np.sqrt,
                    lambda value: np.power(value, 2),
                ),
            )
            axes.set_ylabel("Frequency (sqrt)")

        case FrequencyAxisScale.CUBE_ROOT:
            axes.set_yscale(
                "function",
                functions=(
                    np.cbrt,
                    lambda value: np.power(value, 3),
                ),
            )
            axes.set_ylabel("Frequency (cube root)")

        case FrequencyAxisScale.LOG1P:
            axes.set_yscale(
                "function",
                functions=(
                    np.log1p,
                    np.expm1,
                ),
            )
            axes.set_ylabel("Frequency (log1p)")

        case _:
            raise ValueError(
                f"Unsupported frequency axis scale '{frequency_axis_scale}'.",
            )

    _configure_frequency_ticks(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        maximum_frequency=maximum_frequency,
    )

    axes.set_ylim(bottom=0)


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

    histogram_frequencies = np.asarray(
        frequencies,
        dtype=float,
    )

    maximum_frequency = (
        float(histogram_frequencies.max()) if histogram_frequencies.size > 0 else 0.0
    )

    axes.set_title(
        f"Distribution of {feature_specification.name}",
    )
    axes.set_xlabel(
        feature_specification.name,
    )

    _configure_numerical_axis(
        axes=axes,
        numerical_axis_scale=numerical_axis_scale,
    )

    _configure_frequency_axis(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        maximum_frequency=maximum_frequency,
    )

    axes.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.4,
    )

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

    target_category_values = _get_feature_category_order(
        feature_series=target_series.tolist(),
        feature_specification=target_feature_specification,
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

    maximum_frequency = 0.0

    for target_category_value, target_category_color in zip(
        target_category_values,
        target_category_colors,
        strict=True,
    ):
        target_category_mask = target_series == target_category_value

        category_values = feature_series.loc[target_category_mask].to_numpy(
            dtype=float,
        )

        frequencies, _, _ = axes.hist(
            category_values,
            bins=histogram_bin_edges,
            color=target_category_color,
            alpha=0.55,
            edgecolor="black",
            label=target_category_value,
        )

        histogram_frequencies = np.asarray(
            frequencies,
            dtype=float,
        )

        if histogram_frequencies.size > 0:
            maximum_frequency = max(
                maximum_frequency,
                float(histogram_frequencies.max()),
            )

    axes.set_title(
        f"{feature_specification.name} by {target_feature_specification.name}",
    )
    axes.set_xlabel(
        feature_specification.name,
    )

    _configure_numerical_axis(
        axes=axes,
        numerical_axis_scale=numerical_axis_scale,
    )

    _configure_frequency_axis(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        maximum_frequency=maximum_frequency,
    )

    axes.legend(
        title=target_feature_specification.name,
    )

    axes.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.4,
    )

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

    target_category_values = _get_feature_category_order(
        feature_series=target_series.tolist(),
        feature_specification=target_feature_specification,
    )

    numerical_feature_series = pd.to_numeric(
        data_frame[feature_specification.label],
        errors="raise",
    )

    boxplot_values: list[list[float]] = [
        feature_values,
    ]

    for target_category_value in target_category_values:
        target_category_mask = target_series == target_category_value

        category_values = (
            numerical_feature_series.loc[target_category_mask]
            .to_numpy(dtype=float)
            .tolist()
        )

        boxplot_values.append(
            category_values,
        )

    boxplot_colors = get_discrete_colors(
        len(target_category_values),
        include_aggregate=True,
    )

    boxplot_labels = (
        "Aggregate",
        *target_category_values,
    )

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

    axes.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.4,
    )

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

    category_counts = np.asarray(
        [
            int(value_counts.get(category_value, 0))
            for category_value in category_values
        ],
        dtype=float,
    )

    maximum_frequency = (
        float(np.max(category_counts)) if category_counts.size > 0 else 0.0
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
        maximum_frequency=maximum_frequency,
    )

    axes.tick_params(
        axis="x",
        rotation=45,
    )

    axes.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.4,
    )

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

    target_category_values = _get_feature_category_order(
        feature_series=target_series.tolist(),
        feature_specification=target_feature_specification,
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

    maximum_frequency = (
        float(category_counts.to_numpy(dtype=float).max())
        if not category_counts.empty
        else 0.0
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

    _configure_frequency_axis(
        axes=axes,
        frequency_axis_scale=frequency_axis_scale,
        maximum_frequency=maximum_frequency,
    )

    axes.set_xticks(
        x_positions,
    )
    axes.set_xticklabels(
        feature_category_values,
        rotation=45,
        ha="right",
    )

    axes.legend(
        title=target_feature_specification.name,
    )

    axes.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.4,
    )

    figure.tight_layout()

    return figure
