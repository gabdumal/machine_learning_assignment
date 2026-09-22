"""Feature-level exploratory data analysis."""

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, display
from matplotlib.figure import Figure

from eda.common import (
    CategoricalFeatureStatistics,
    FeatureInspection,
    FeatureMetadata,
    FeaturePlotSpecification,
    FeaturePlotType,
    NumericalFeatureStatistics,
)
from eda.palette import (
    CONTINUOUS_PALETTE,
    get_aggregate_color,
    get_category_colors,
)
from schema.common import (
    FeatureRole,
    FeatureSemanticType,
    FeatureSpec,
)

DEFAULT_HISTOGRAM_BIN_COUNT = 30
DEFAULT_FIGURE_SIZE = (10.0, 6.0)
DEFAULT_BOXPLOT_FIGURE_SIZE = (12.0, 7.0)


def inspect_feature(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    *,
    histogram_bin_count: int = DEFAULT_HISTOGRAM_BIN_COUNT,
) -> FeatureInspection:
    """Inspect one feature without rendering visualizations.

    The returned ``FeatureInspection`` contains the feature metadata,
    descriptive statistics, and specifications for the visualizations
    appropriate for the feature type.

    Args:
        data_frame: DataFrame containing the feature and target columns.
        feature_specification: Schema specification of the feature to inspect.
        target_feature_specification: Schema specification of the target used
            for stratified visualizations.
        histogram_bin_count: Number of bins used for numerical histograms.

    Returns:
        A complete, non-rendered feature inspection.

    Raises:
        ValueError: If required columns are missing, the target is invalid,
            or the histogram bin count is invalid.
    """

    _validate_feature_and_target_columns(
        data_frame=data_frame,
        feature_specification=feature_specification,
        target_feature_specification=target_feature_specification,
    )

    if histogram_bin_count <= 0:
        raise ValueError("Histogram bin count must be greater than zero.")

    metadata_table = _create_feature_metadata_table(
        feature_specification,
    )

    statistics_table = _create_feature_statistics_table(
        data_frame=data_frame,
        feature_specification=feature_specification,
    )

    plot_specifications = _create_feature_plot_specifications(
        feature_specification=feature_specification,
        target_feature_specification=target_feature_specification,
        histogram_bin_count=histogram_bin_count,
    )

    return FeatureInspection(
        metadata_table=metadata_table,
        statistics_table=statistics_table,
        plots=plot_specifications,
    )


def summarize_feature(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize one feature without creating or rendering plots.

    Args:
        data_frame: DataFrame containing the feature.
        feature_specification: Schema specification of the feature.

    Returns:
        A tuple containing the metadata table and statistics table.

    Raises:
        ValueError: If the feature is absent or has an unsupported semantic
            type.
    """

    _validate_feature_column(
        data_frame=data_frame,
        feature_specification=feature_specification,
    )

    metadata_table = _create_feature_metadata_table(
        feature_specification,
    )

    statistics_table = _create_feature_statistics_table(
        data_frame=data_frame,
        feature_specification=feature_specification,
    )

    return metadata_table, statistics_table


def render_feature_plot(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    plot_specification: FeaturePlotSpecification,
    *,
    target_feature_specification: FeatureSpec | None = None,
) -> Figure:
    """Render one previously configured feature visualization.

    Args:
        data_frame: DataFrame containing the feature and, when required, the
            target.
        feature_specification: Schema specification of the feature.
        plot_specification: Plot configuration returned by
            ``inspect_feature``.
        target_feature_specification: Schema specification of the target.
            Required for stratified plots.

    Returns:
        A rendered Matplotlib figure.

    Raises:
        ValueError: If the plot specification is incompatible with the
            supplied feature or target specification.
    """

    _validate_plot_feature(
        feature_specification=feature_specification,
        plot_specification=plot_specification,
    )

    if plot_specification.target_feature_label is not None:
        if target_feature_specification is None:
            raise ValueError(
                f"Plot '{plot_specification.plot_type.value}' requires a "
                "target feature specification."
            )

        if (
            target_feature_specification.label
            != plot_specification.target_feature_label
        ):
            raise ValueError(
                "The target feature specification does not match the target "
                "declared by the plot specification."
            )

        _validate_feature_column(
            data_frame=data_frame,
            feature_specification=target_feature_specification,
        )

    _validate_feature_column(
        data_frame=data_frame,
        feature_specification=feature_specification,
    )

    match plot_specification.plot_type:
        case FeaturePlotType.HISTOGRAM:
            return _render_numerical_aggregate_histogram(
                data_frame=data_frame,
                feature_specification=feature_specification,
                histogram_bin_count=_require_histogram_bin_count(
                    plot_specification,
                ),
            )

        case FeaturePlotType.BOXPLOT:
            return _render_numerical_boxplots(
                data_frame=data_frame,
                feature_specification=feature_specification,
                target_feature_specification=_require_target_feature_specification(
                    target_feature_specification,
                ),
            )

        case FeaturePlotType.STRATIFIED_HISTOGRAM:
            return _render_numerical_stratified_histogram(
                data_frame=data_frame,
                feature_specification=feature_specification,
                target_feature_specification=_require_target_feature_specification(
                    target_feature_specification,
                ),
                histogram_bin_count=_require_histogram_bin_count(
                    plot_specification,
                ),
            )

        case FeaturePlotType.BAR_CHART:
            return _render_categorical_aggregate_bar_chart(
                data_frame=data_frame,
                feature_specification=feature_specification,
            )

        case FeaturePlotType.STRATIFIED_BAR_CHART:
            return _render_categorical_stratified_bar_chart(
                data_frame=data_frame,
                feature_specification=feature_specification,
                target_feature_specification=_require_target_feature_specification(
                    target_feature_specification,
                ),
            )

        case _:
            raise ValueError(
                f"Unsupported feature plot type '{plot_specification.plot_type}'."
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
        data_frame: DataFrame containing the feature and, when required, the
            target.
        feature_specification: Schema specification of the inspected feature.
        feature_inspection: Previously computed feature inspection.
        target_feature_specification: Schema specification of the target.
            Required when the inspection contains stratified plots.

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
            f"Feature '{target_feature_specification.label}' must have the "
            f"role '{FeatureRole.TARGET.value}'."
        )

    if target_feature_specification.semantic_type is not (
        FeatureSemanticType.CATEGORICAL
    ):
        raise ValueError(
            f"Target feature '{target_feature_specification.label}' must be "
            "categorical for stratified feature visualization."
        )


def _validate_feature_column(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
) -> None:
    """Validate that the specified feature exists in the DataFrame."""

    if feature_specification.label not in data_frame.columns:
        raise ValueError(
            f"Feature '{feature_specification.label}' is not present in "
            "the supplied DataFrame."
        )


def _validate_plot_feature(
    feature_specification: FeatureSpec,
    plot_specification: FeaturePlotSpecification,
) -> None:
    """Validate that a plot specification matches its feature."""

    if plot_specification.feature_label != feature_specification.label:
        raise ValueError(
            f"Plot specification refers to feature "
            f"'{plot_specification.feature_label}', but the supplied feature "
            f"is '{feature_specification.label}'."
        )

    numerical_plot_types = {
        FeaturePlotType.HISTOGRAM,
        FeaturePlotType.STRATIFIED_HISTOGRAM,
        FeaturePlotType.BOXPLOT,
    }

    categorical_plot_types = {
        FeaturePlotType.BAR_CHART,
        FeaturePlotType.STRATIFIED_BAR_CHART,
    }

    if (
        plot_specification.plot_type in numerical_plot_types
        and feature_specification.semantic_type is not FeatureSemanticType.NUMERIC
    ):
        raise ValueError(
            f"Plot type '{plot_specification.plot_type.value}' requires a "
            "numerical feature."
        )

    if (
        plot_specification.plot_type in categorical_plot_types
        and feature_specification.semantic_type is not FeatureSemanticType.CATEGORICAL
    ):
        raise ValueError(
            f"Plot type '{plot_specification.plot_type.value}' requires a "
            "categorical feature."
        )


def _require_histogram_bin_count(
    plot_specification: FeaturePlotSpecification,
) -> int:
    """Return a configured histogram bin count."""

    if plot_specification.histogram_bin_count is None:
        raise ValueError(
            f"Plot '{plot_specification.plot_type.value}' does not define "
            "a histogram bin count."
        )

    return plot_specification.histogram_bin_count


def _require_target_feature_specification(
    target_feature_specification: FeatureSpec | None,
) -> FeatureSpec:
    """Return the required target feature specification."""

    if target_feature_specification is None:
        raise ValueError("A target feature specification is required.")

    return target_feature_specification


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
        ]
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

        case FeatureSemanticType.CATEGORICAL:
            return _create_categorical_statistics_table(
                feature_series=feature_series,
                feature_specification=feature_specification,
            )

        case _:
            raise ValueError(
                f"Feature '{feature_specification.label}' has unsupported "
                f"semantic type '{feature_specification.semantic_type}'."
            )


def _create_feature_plot_specifications(
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    histogram_bin_count: int,
) -> tuple[FeaturePlotSpecification, ...]:
    """Create plot configurations appropriate for a feature."""

    if feature_specification.semantic_type is FeatureSemanticType.NUMERIC:
        return (
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.HISTOGRAM,
                feature_label=feature_specification.label,
                histogram_bin_count=histogram_bin_count,
            ),
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.STRATIFIED_HISTOGRAM,
                feature_label=feature_specification.label,
                target_feature_label=target_feature_specification.label,
                histogram_bin_count=histogram_bin_count,
            ),
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.BOXPLOT,
                feature_label=feature_specification.label,
                target_feature_label=target_feature_specification.label,
            ),
        )

    if feature_specification.semantic_type is FeatureSemanticType.CATEGORICAL:
        return (
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.BAR_CHART,
                feature_label=feature_specification.label,
            ),
            FeaturePlotSpecification(
                plot_type=FeaturePlotType.STRATIFIED_BAR_CHART,
                feature_label=feature_specification.label,
                target_feature_label=target_feature_specification.label,
            ),
        )

    raise ValueError(
        f"Feature '{feature_specification.label}' has unsupported semantic "
        f"type '{feature_specification.semantic_type}'."
    )


def _create_numerical_statistics_table(
    feature_series: pd.Series,
) -> pd.DataFrame:
    """Create descriptive statistics for a numerical feature."""

    numerical_values = _get_numerical_values(feature_series)

    numerical_series = pd.Series(numerical_values, dtype="float64")

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
        ]
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

    total_observation_count = len(categorical_values)

    categorical_statistics: list[CategoricalFeatureStatistics] = []

    for category_value in category_values:
        category_count = sum(
            observed_category_value == category_value
            for observed_category_value in categorical_values
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
                percentage=category_frequency * 100.0,
            )
        )

    return pd.DataFrame(
        [
            {
                "category": category_statistic.category,
                "count": category_statistic.count,
                "frequency": category_statistic.frequency,
                "percentage": category_statistic.percentage,
            }
            for category_statistic in categorical_statistics
        ]
    )


def _get_numerical_values(
    feature_series: pd.Series,
) -> list[float]:
    """Return validated numerical feature values as Python floats."""

    numerical_series = pd.to_numeric(
        feature_series,
        errors="raise",
    )

    if numerical_series.empty:
        raise ValueError("Cannot analyze an empty numerical feature.")

    if numerical_series.isna().any():
        raise ValueError("Numerical feature contains missing values.")

    return [float(numerical_value) for numerical_value in numerical_series.tolist()]


def _get_categorical_values(
    feature_series: pd.Series,
) -> list[str]:
    """Return validated categorical values as Python strings."""

    categorical_series = feature_series.astype("string")

    if categorical_series.empty:
        raise ValueError("Cannot analyze an empty categorical feature.")

    if categorical_series.isna().any():
        raise ValueError("Categorical feature contains missing values.")

    return [str(category_value) for category_value in categorical_series.tolist()]


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

    return tuple(sorted(observed_category_values))


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


def _calculate_histogram_bin_edges(
    numerical_values: Sequence[float],
    histogram_bin_count: int,
) -> list[float]:
    """Calculate common histogram bin edges for comparable distributions."""

    minimum_value = min(numerical_values)
    maximum_value = max(numerical_values)

    if minimum_value == maximum_value:
        return [
            minimum_value - 0.5,
            maximum_value + 0.5,
        ]

    return [
        float(bin_edge)
        for bin_edge in np.linspace(
            minimum_value,
            maximum_value,
            histogram_bin_count + 1,
        )
    ]


def _render_numerical_aggregate_histogram(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    histogram_bin_count: int,
) -> Figure:
    """Render an aggregate histogram for a numerical feature."""

    numerical_values = _get_numerical_values(
        data_frame[feature_specification.label],
    )

    histogram_bin_edges = _calculate_histogram_bin_edges(
        numerical_values=numerical_values,
        histogram_bin_count=histogram_bin_count,
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    axes.hist(
        numerical_values,
        bins=histogram_bin_edges,
        color=CONTINUOUS_PALETTE(0.70),
        edgecolor="white",
    )

    axes.set_title(
        f"Distribution of {feature_specification.name}",
    )
    axes.set_xlabel(feature_specification.name)
    axes.set_ylabel("Frequency")
    axes.grid(
        axis="y",
        alpha=0.20,
    )

    figure.tight_layout()

    return figure


def _render_numerical_stratified_histogram(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    histogram_bin_count: int,
) -> Figure:
    """Render a target-stratified histogram for a numerical feature."""

    numerical_values = _get_numerical_values(
        data_frame[feature_specification.label],
    )

    target_category_values = _get_target_category_order(
        target_series=data_frame[target_feature_specification.label],
        target_feature_specification=target_feature_specification,
    )

    histogram_bin_edges = _calculate_histogram_bin_edges(
        numerical_values=numerical_values,
        histogram_bin_count=histogram_bin_count,
    )

    target_category_colors = get_category_colors(
        len(target_category_values),
    )

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    target_series = data_frame[target_feature_specification.label].astype("string")

    feature_series = pd.to_numeric(
        data_frame[feature_specification.label],
        errors="raise",
    )

    for target_category_value, target_category_color in zip(
        target_category_values,
        target_category_colors,
        strict=True,
    ):
        target_category_mask = target_series == target_category_value

        category_values = [
            float(feature_value)
            for feature_value in feature_series.loc[target_category_mask].tolist()
        ]

        axes.hist(
            category_values,
            bins=histogram_bin_edges,
            color=target_category_color,
            alpha=0.55,
            edgecolor="white",
            label=target_category_value,
        )

    axes.set_title(
        f"{feature_specification.name} by {target_feature_specification.name}",
    )
    axes.set_xlabel(feature_specification.name)
    axes.set_ylabel("Frequency")
    axes.legend(
        title=target_feature_specification.name,
    )
    axes.grid(
        axis="y",
        alpha=0.20,
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

    target_category_values = _get_target_category_order(
        target_series=data_frame[target_feature_specification.label],
        target_feature_specification=target_feature_specification,
    )

    target_series = data_frame[target_feature_specification.label].astype("string")

    numerical_feature_series = pd.to_numeric(
        data_frame[feature_specification.label],
        errors="raise",
    )

    boxplot_values: list[list[float]] = [
        feature_values,
    ]

    for target_category_value in target_category_values:
        target_category_mask = target_series == target_category_value

        category_values = [
            float(feature_value)
            for feature_value in numerical_feature_series.loc[
                target_category_mask
            ].tolist()
        ]

        boxplot_values.append(category_values)

    boxplot_colors = (
        get_aggregate_color(),
        *get_category_colors(len(target_category_values)),
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
        boxplot_artist.set_facecolor(box_color)
        boxplot_artist.set_alpha(0.75)

    axes.set_title(
        f"{feature_specification.name} by {target_feature_specification.name}",
    )
    axes.set_xlabel("Group")
    axes.set_ylabel(feature_specification.name)
    axes.grid(
        axis="y",
        alpha=0.20,
    )

    figure.tight_layout()

    return figure


def _render_categorical_aggregate_bar_chart(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
) -> Figure:
    """Render an aggregate frequency bar chart."""

    categorical_values = _get_categorical_values(
        data_frame[feature_specification.label],
    )

    category_values = _get_feature_category_order(
        feature_series=categorical_values,
        feature_specification=feature_specification,
    )

    category_counts = [
        categorical_values.count(category_value) for category_value in category_values
    ]

    figure, axes = plt.subplots(
        figsize=DEFAULT_FIGURE_SIZE,
    )

    axes.bar(
        category_values,
        category_counts,
        color=get_aggregate_color(),
    )

    axes.set_title(
        f"Frequency of {feature_specification.name}",
    )
    axes.set_xlabel(feature_specification.name)
    axes.set_ylabel("Frequency")
    axes.tick_params(
        axis="x",
        rotation=45,
    )
    axes.grid(
        axis="y",
        alpha=0.20,
    )

    figure.tight_layout()

    return figure


def _render_categorical_stratified_bar_chart(
    data_frame: pd.DataFrame,
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
) -> Figure:
    """Render a target-stratified categorical frequency bar chart."""

    feature_values = _get_categorical_values(
        data_frame[feature_specification.label],
    )

    target_series = data_frame[target_feature_specification.label].astype("string")

    feature_category_values = _get_feature_category_order(
        feature_series=feature_values,
        feature_specification=feature_specification,
    )

    target_category_values = _get_target_category_order(
        target_series=target_series,
        target_feature_specification=target_feature_specification,
    )

    target_category_colors = get_category_colors(
        len(target_category_values),
    )

    target_category_count = len(target_category_values)
    feature_category_count = len(feature_category_values)

    if target_category_count == 0:
        raise ValueError(
            "No target categories are available for plotting.",
        )

    bar_width = 0.8 / target_category_count
    x_positions = list(range(feature_category_count))

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
        )
    ):
        target_category_mask = target_series == target_category_value

        category_counts = [
            sum(
                1
                for index in range(len(feature_values))
                if (
                    feature_values[index] == feature_category_value
                    and bool(target_category_mask.iloc[index])
                )
            )
            for feature_category_value in feature_category_values
        ]

        horizontal_offset = (
            target_category_index - (target_category_count - 1) / 2
        ) * bar_width

        bar_positions = [
            float(x_position) + horizontal_offset for x_position in x_positions
        ]

        axes.bar(
            bar_positions,
            category_counts,
            width=bar_width,
            color=target_category_color,
            label=target_category_value,
        )

    axes.set_title(
        f"{feature_specification.name} by {target_feature_specification.name}",
    )
    axes.set_xlabel(feature_specification.name)
    axes.set_ylabel("Frequency")
    axes.set_xticks(x_positions)
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
        alpha=0.20,
    )

    figure.tight_layout()

    return figure


def display_feature(
    feature_specification: FeatureSpec,
    target_feature_specification: FeatureSpec,
    data_frame: pd.DataFrame,
):
    display(HTML(f"<h2>{feature_specification.name}</h2>"))
    feature_inspection = inspect_feature(
        data_frame=data_frame,
        feature_specification=feature_specification,
        target_feature_specification=target_feature_specification,
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
