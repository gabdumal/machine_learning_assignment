"""Cross-validation result statistics and notebook display helpers.

This module summarizes the validation results produced by the ML experiment
engine. It intentionally does not perform model fitting or model selection.

Expected validation-result columns
----------------------------------
The API accepts the fold-level validation DataFrame produced by the
experiment engine. The following columns are required:

    configuration_id
    seed
    fold
    macro_f1

Additional columns are preserved by the fold-level table when possible.

The configuration definitions are supplied separately so the parameter values
retain their original Python types and can be displayed alongside the metrics.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from IPython.display import HTML, display

# ----------------------------------------
# Constants
# ----------------------------------------

REQUIRED_VALIDATION_COLUMNS = frozenset(
    {
        "configuration_id",
        "seed",
        "fold",
        "macro_f1",
    },
)


# ----------------------------------------
# Result type
# ----------------------------------------


@dataclass(frozen=True, slots=True)
class CrossValidationStatistics:
    """Compiled cross-validation statistics."""

    fold_results_table: pd.DataFrame
    seed_summary_table: pd.DataFrame
    configuration_table: pd.DataFrame
    selected_configuration_table: pd.DataFrame


# ----------------------------------------
# Public API
# ----------------------------------------


def compile_cross_validation_statistics(
    validation_results: pd.DataFrame,
    configurations: Sequence[Mapping[str, Any]],
    *,
    selected_configuration_id: str | None = None,
) -> CrossValidationStatistics:
    """Compile fold, seed, configuration, and selected-result statistics.

    The aggregation follows the experiment methodology:

    1. Compute the mean metric across folds for each seed.
    2. Compute the mean and standard deviation across those seed-level means
       for each configuration.

    No validation result is recomputed or modified.

    Args:
        validation_results:
            Fold-level validation results. Must contain
            ``configuration_id``, ``seed``, ``fold``, and ``macro_f1``.

        configurations:
            Original configuration definitions. Each mapping must contain
            ``configuration_id`` and may contain ``parameters``.

        selected_configuration_id:
            Optional configuration ID to expose in the selected-configuration
            table. When omitted, the configuration with the highest
            ``macro_f1_mean`` is selected for reporting.

    Returns:
        A ``CrossValidationStatistics`` object containing four DataFrames.

    Raises:
        ValueError:
            If required columns are missing, validation results are empty,
            configuration definitions are inconsistent, or the requested
            selected configuration does not exist.
    """
    _validate_validation_results(validation_results)
    configuration_records = _normalize_configurations(configurations)

    fold_results_table = _create_fold_results_table(
        validation_results,
    )

    seed_summary_table = _create_seed_summary_table(
        validation_results,
    )

    configuration_table = _create_configuration_table(
        seed_summary_table=seed_summary_table,
        configurations=configuration_records,
    )

    selected_id = _resolve_selected_configuration_id(
        configuration_table=configuration_table,
        selected_configuration_id=selected_configuration_id,
    )

    selected_configuration_table = _create_selected_configuration_table(
        configuration_table=configuration_table,
        configuration_id=selected_id,
    )

    return CrossValidationStatistics(
        fold_results_table=fold_results_table,
        seed_summary_table=seed_summary_table,
        configuration_table=configuration_table,
        selected_configuration_table=selected_configuration_table,
    )


def display_cross_validation_statistics(
    statistics: CrossValidationStatistics,
    *,
    show_fold_results: bool = True,
    show_seed_summary: bool = True,
    show_configuration_table: bool = True,
    show_selected_configuration: bool = True,
) -> None:
    """Display compiled cross-validation statistics in a notebook.

    Args:
        statistics:
            Result returned by ``compile_cross_validation_statistics()``.

        show_fold_results:
            Display fold-level validation metrics.

        show_seed_summary:
            Display per-seed means across folds.

        show_configuration_table:
            Display per-configuration aggregate metrics.

        show_selected_configuration:
            Display the selected configuration and its aggregate metrics.
    """
    if show_configuration_table:
        _display_section(
            title="Cross-validation configurations",
            table=statistics.configuration_table,
        )

    if show_seed_summary:
        _display_section(
            title="Cross-validation seed summary",
            table=statistics.seed_summary_table,
        )

    if show_fold_results:
        _display_section(
            title="Cross-validation fold results",
            table=statistics.fold_results_table,
        )

    if show_selected_configuration:
        _display_section(
            title="Selected configuration",
            table=statistics.selected_configuration_table,
        )


# ----------------------------------------
# Validation
# ----------------------------------------


def _validate_validation_results(
    validation_results: pd.DataFrame,
) -> None:
    """Validate the minimum fold-level validation-result schema."""
    if validation_results.empty:
        raise ValueError("Validation results are empty.")

    missing_columns = REQUIRED_VALIDATION_COLUMNS - set(
        validation_results.columns,
    )

    if missing_columns:
        raise ValueError(
            "Validation results are missing required columns: "
            f"{tuple(sorted(missing_columns))}.",
        )

    if validation_results[["configuration_id", "seed", "fold"]].isna().any().any():
        raise ValueError(
            "Validation results contain missing configuration, seed, or fold values.",
        )

    metric_values = pd.to_numeric(
        validation_results["macro_f1"],
        errors="coerce",
    )

    if metric_values.isna().any():
        raise ValueError(
            "Validation results contain non-numeric macro_f1 values.",
        )

    if not np.isfinite(
        metric_values.to_numpy(dtype=float),
    ).all():
        raise ValueError(
            "Validation results contain non-finite macro_f1 values.",
        )

    if ((metric_values < 0.0) | (metric_values > 1.0)).any():
        raise ValueError(
            "macro_f1 values must be within the [0, 1] interval.",
        )


def _normalize_configurations(
    configurations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Validate and copy configuration definitions."""
    if not configurations:
        raise ValueError("No configuration definitions were provided.")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for configuration in configurations:
        if "configuration_id" not in configuration:
            raise ValueError(
                "Each configuration definition must contain 'configuration_id'.",
            )

        configuration_id = str(configuration["configuration_id"])

        if configuration_id in seen_ids:
            raise ValueError(
                f"Duplicate configuration ID: '{configuration_id}'.",
            )

        seen_ids.add(configuration_id)

        normalized_configuration = dict(configuration)
        normalized_configuration["configuration_id"] = configuration_id

        if "parameters" in normalized_configuration:
            parameters = normalized_configuration["parameters"]

            if parameters is None:
                normalized_configuration["parameters"] = {}
            elif not isinstance(parameters, Mapping):
                raise ValueError(
                    f"Configuration '{configuration_id}' has a "
                    "'parameters' value that is not a mapping.",
                )
            else:
                normalized_configuration["parameters"] = dict(parameters)
        else:
            normalized_configuration["parameters"] = {}

        normalized.append(normalized_configuration)

    return tuple(normalized)


# ----------------------------------------
# Fold-level statistics
# ----------------------------------------


def _create_fold_results_table(
    validation_results: pd.DataFrame,
) -> pd.DataFrame:
    """Create a clean fold-level result table."""
    result = validation_results.copy()

    result["configuration_id"] = result["configuration_id"].astype(str)
    result["macro_f1"] = pd.to_numeric(
        result["macro_f1"],
        errors="raise",
    )

    result = result.sort_values(
        by=["configuration_id", "seed", "fold"],
        kind="stable",
    ).reset_index(drop=True)

    preferred_columns = [
        "configuration_id",
        "seed",
        "fold",
        "macro_f1",
    ]

    remaining_columns = [
        column for column in result.columns if column not in preferred_columns
    ]

    return result[preferred_columns + remaining_columns].copy()


# ----------------------------------------
# Seed-level statistics
# ----------------------------------------


def _create_seed_summary_table(
    validation_results: pd.DataFrame,
) -> pd.DataFrame:
    """Compute one mean macro-F1 per configuration and seed."""
    working = validation_results[
        [
            "configuration_id",
            "seed",
            "fold",
            "macro_f1",
        ]
    ].copy()

    working["configuration_id"] = working["configuration_id"].astype(str)
    working["macro_f1"] = pd.to_numeric(
        working["macro_f1"],
        errors="raise",
    )

    seed_summary = working.groupby(
        ["configuration_id", "seed"],
        as_index=False,
    ).agg(
        fold_count=("fold", "nunique"),
        macro_f1_mean=("macro_f1", "mean"),
        macro_f1_std=("macro_f1", "std"),
    )

    seed_summary["macro_f1_std"] = (
        seed_summary["macro_f1_std"].fillna(0.0).astype(float)
    )

    return seed_summary.sort_values(
        by=["configuration_id", "seed"],
        kind="stable",
    ).reset_index(drop=True)


# ----------------------------------------
# Configuration-level statistics
# ----------------------------------------


def _create_configuration_table(
    *,
    seed_summary_table: pd.DataFrame,
    configurations: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    """Aggregate seed-level means and attach configuration parameters."""
    aggregate = seed_summary_table.groupby(
        "configuration_id",
        as_index=False,
    ).agg(
        seed_count=("seed", "nunique"),
        total_fold_count=("fold_count", "sum"),
        macro_f1_mean=("macro_f1_mean", "mean"),
        macro_f1_std=("macro_f1_mean", "std"),
        macro_f1_min=("macro_f1_mean", "min"),
        macro_f1_max=("macro_f1_mean", "max"),
    )

    aggregate["macro_f1_std"] = aggregate["macro_f1_std"].fillna(0.0).astype(float)

    configuration_by_id = {
        str(configuration["configuration_id"]): configuration
        for configuration in configurations
    }

    missing_configuration_ids = set(
        aggregate["configuration_id"].astype(str),
    ) - set(configuration_by_id)

    if missing_configuration_ids:
        raise ValueError(
            "Validation results contain configuration IDs without "
            "definitions: "
            f"{tuple(sorted(missing_configuration_ids))}.",
        )

    parameters: list[dict[str, Any]] = []
    for configuration_id in aggregate["configuration_id"].astype(str):
        parameters.append(
            dict(
                configuration_by_id[configuration_id].get(
                    "parameters",
                    {},
                ),
            ),
        )

    aggregate["parameters"] = parameters

    aggregate = aggregate.sort_values(
        by=["macro_f1_mean", "configuration_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)

    return aggregate[
        [
            "configuration_id",
            "parameters",
            "seed_count",
            "total_fold_count",
            "macro_f1_mean",
            "macro_f1_std",
            "macro_f1_min",
            "macro_f1_max",
        ]
    ].copy()


# ----------------------------------------
# Selected configuration
# ----------------------------------------


def _resolve_selected_configuration_id(
    *,
    configuration_table: pd.DataFrame,
    selected_configuration_id: str | None,
) -> str:
    """Resolve the configuration ID to report as selected."""
    if configuration_table.empty:
        raise ValueError("No configuration statistics were produced.")

    if selected_configuration_id is not None:
        normalized_id = str(selected_configuration_id)

        configuration_ids = set(
            configuration_table["configuration_id"].astype(str),
        )

        if normalized_id not in configuration_ids:
            raise ValueError(
                f"Selected configuration '{normalized_id}' was not found.",
            )

        return normalized_id

    return str(
        configuration_table.iloc[0]["configuration_id"],
    )


def _create_selected_configuration_table(
    *,
    configuration_table: pd.DataFrame,
    configuration_id: str,
) -> pd.DataFrame:
    """Create a one-row table for the selected configuration."""
    selected_rows = configuration_table[
        configuration_table["configuration_id"].astype(str) == configuration_id
    ].copy()

    if selected_rows.empty:
        raise ValueError(
            f"Configuration '{configuration_id}' was not found.",
        )

    return selected_rows.reset_index(drop=True)


# ----------------------------------------
# Display helpers
# ----------------------------------------


def _display_section(
    *,
    title: str,
    table: pd.DataFrame,
) -> None:
    """Display one titled statistics table."""
    display(
        HTML(
            f"<h2>{title}</h2>",
        ),
    )

    display(table)
