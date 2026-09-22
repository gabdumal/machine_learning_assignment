"""Color palettes used by exploratory data analysis."""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib import colormaps
from matplotlib.colors import Colormap

# ColorBrewer Set2 with the first two colors inverted.
#
# Index 0 is intentionally reserved for:
#   - aggregate data;
#   - data without a discrete category.
#
# Target categories must always start at index 1.
DISCRETE_PALETTE: tuple[str, ...] = (
    "#fc8d62",
    "#66c2a5",
    "#ffd92f",
    "#e78ac3",
    "#a6d854",
    "#8da0cb",
    "#e5c494",
    "#b3b3b3",
)

AGGREGATE_COLOR_INDEX = 0
CATEGORY_COLOR_START_INDEX = 1

CONTINUOUS_PALETTE_NAME = "Oranges"

MAXIMUM_CATEGORY_COUNT = len(DISCRETE_PALETTE) - CATEGORY_COLOR_START_INDEX

CONTINUOUS_PALETTE: Colormap = colormaps[CONTINUOUS_PALETTE_NAME]


def get_aggregate_color() -> str:
    """Return the color reserved for aggregate or uncategorized data."""

    return DISCRETE_PALETTE[AGGREGATE_COLOR_INDEX]


def get_category_colors(category_count: int) -> tuple[str, ...]:
    """Return colors for a number of discrete categories.

    Category colors always start at index 1 because index 0 is reserved
    for aggregate or uncategorized data.

    Args:
        category_count: Number of discrete categories requiring colors.

    Returns:
        A tuple containing one color per category.

    Raises:
        ValueError: If ``category_count`` is negative or exceeds the
            available number of category colors.
    """

    if category_count < 0:
        raise ValueError("Category count must not be negative.")

    if category_count > MAXIMUM_CATEGORY_COUNT:
        raise ValueError(
            f"Requested {category_count} category colors, but only "
            f"{MAXIMUM_CATEGORY_COUNT} are available."
        )

    category_start_index = CATEGORY_COLOR_START_INDEX
    category_end_index = category_start_index + category_count

    return DISCRETE_PALETTE[category_start_index:category_end_index]


def get_discrete_colors(
    category_count: int,
    *,
    include_aggregate: bool = False,
) -> tuple[str, ...]:
    """Return colors for categorical visualization.

    Args:
        category_count: Number of target categories.
        include_aggregate: Whether to include the reserved aggregate color
            as the first color.

    Returns:
        A tuple of colors in visualization order.
    """

    category_colors = get_category_colors(category_count)

    if include_aggregate:
        return (
            get_aggregate_color(),
            *category_colors,
        )

    return category_colors


def get_categorical_color_map(
    category_count: int,
    *,
    include_aggregate: bool = False,
) -> Sequence[str]:
    """Return a categorical color sequence suitable for plotting.

    This is an alias-oriented API intended for plotting libraries that
    expect a generic sequence of colors.
    """

    return get_discrete_colors(
        category_count,
        include_aggregate=include_aggregate,
    )
