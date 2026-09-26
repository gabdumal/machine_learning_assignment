"""Presentation helpers for persisted cross-validation results.

The experiment engine is responsible for fitting models, calculating metrics,
aggregating folds/seeds, and selecting the configuration. This module only
validates and formats those persisted artifacts for notebook display.

The displayed scalar convention is:

    mean ± std

for configuration-level results. Standard deviation is never shown as a
separate display column. Confusion matrices are intentionally outside this
module.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from IPython.display import HTML, display

from pipeline.common import (
    load_selected_configuration,
    load_validation_configuration_results,
    load_validation_fold_results,
    load_validation_seed_results,
)
from reporting.common import format_mean_std

CONFIGURATION_ID_COLUMN = "configuration_id"
SEED_COLUMN = "seed"
FOLD_COLUMN = "fold"

# These names are the persisted validation metrics produced by
# pipeline.common. ``macro_f1`` is the primary selection metric and is also
# the F1-score reported by the project.
METRIC_COLUMNS: tuple[str, ...] = (
    "accuracy",
    "precision",
    "recall",
    "macro_f1",
    "roc_auc",
    "pr_auc",
    "mcc",
    "balanced_accuracy",
)

REQUIRED_METRIC_COLUMNS: tuple[str, ...] = (
    "accuracy",
    "precision",
    "recall",
    "macro_f1",
    "roc_auc",
)

OPTIONAL_METRIC_COLUMNS: tuple[str, ...] = (
    "pr_auc",
    "mcc",
    "balanced_accuracy",
)

# Seed-level artifacts use ``mean_<metric>`` because they contain the mean of
# the fold values for that seed. Configuration-level artifacts use
# ``<metric>_mean`` and ``<metric>_std``.
SEED_METRIC_COLUMNS = tuple(f"mean_{metric}" for metric in METRIC_COLUMNS)
CONFIGURATION_MEAN_COLUMNS = tuple(f"{metric}_mean" for metric in METRIC_COLUMNS)
CONFIGURATION_STD_COLUMNS = tuple(f"{metric}_std" for metric in METRIC_COLUMNS)


@dataclass(frozen=True, slots=True)
class CrossValidationStatistics:
    """Notebook-ready cross-validation result tables."""

    fold_results_table: pd.DataFrame
    seed_summary_table: pd.DataFrame
    configuration_table: pd.DataFrame
    selected_configuration_table: pd.DataFrame


def compile_cross_validation_statistics(
    *,
    fold_results: pd.DataFrame,
    seed_results: pd.DataFrame,
    configuration_results: pd.DataFrame,
    selected_configuration: Mapping[str, Any],
) -> CrossValidationStatistics:
    """Prepare persisted CV artifacts for notebook display.

    No metric is recomputed here. The function requires all required metrics
    and all optional metrics produced by the experiment engine to be present
    in the persisted artifacts.
    """
    _validate_fold_results(fold_results)
    _validate_seed_results(seed_results)
    _validate_configuration_results(configuration_results)
    selected_configuration_id = _validate_selected_configuration(
        selected_configuration,
    )

    fold_table = _prepare_fold_results_table(fold_results)
    seed_table = _prepare_seed_summary_table(seed_results)
    configuration_table = _prepare_configuration_table(configuration_results)

    _validate_configuration_id_consistency(
        fold_results=fold_table,
        seed_results=seed_table,
        configuration_results=configuration_table,
    )

    selected_table = _create_selected_configuration_table(
        configuration_table=configuration_table,
        configuration_id=selected_configuration_id,
    )

    return CrossValidationStatistics(
        fold_results_table=fold_table,
        seed_summary_table=seed_table,
        configuration_table=configuration_table,
        selected_configuration_table=selected_table,
    )


def display_cross_validation_statistics(
    statistics: CrossValidationStatistics,
    *,
    show_configuration_table: bool = True,
    show_seed_summary: bool = True,
    show_fold_results: bool = True,
    show_selected_configuration: bool = True,
) -> None:
    """Display all CV tables in a notebook."""
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


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_fold_results(table: pd.DataFrame) -> None:
    _validate_required_columns(
        table,
        required_columns={
            CONFIGURATION_ID_COLUMN,
            SEED_COLUMN,
            FOLD_COLUMN,
            *METRIC_COLUMNS,
        },
        table_name="fold_results",
    )
    if table.empty:
        raise ValueError("fold_results is empty.")

    _validate_identifier_columns(
        table,
        table_name="fold_results",
        columns=(CONFIGURATION_ID_COLUMN, SEED_COLUMN, FOLD_COLUMN),
    )
    _validate_metrics(
        table,
        metric_columns=METRIC_COLUMNS,
        table_name="fold_results",
    )


def _validate_seed_results(table: pd.DataFrame) -> None:
    _validate_required_columns(
        table,
        required_columns={
            CONFIGURATION_ID_COLUMN,
            SEED_COLUMN,
            *SEED_METRIC_COLUMNS,
        },
        table_name="seed_results",
    )
    if table.empty:
        raise ValueError("seed_results is empty.")

    _validate_identifier_columns(
        table,
        table_name="seed_results",
        columns=(CONFIGURATION_ID_COLUMN, SEED_COLUMN),
    )
    _validate_metrics(
        table,
        metric_columns=SEED_METRIC_COLUMNS,
        table_name="seed_results",
    )


def _validate_configuration_results(table: pd.DataFrame) -> None:
    _validate_required_columns(
        table,
        required_columns={
            CONFIGURATION_ID_COLUMN,
            *CONFIGURATION_MEAN_COLUMNS,
            *CONFIGURATION_STD_COLUMNS,
        },
        table_name="configuration_results",
    )
    if table.empty:
        raise ValueError("configuration_results is empty.")

    _validate_identifier_columns(
        table,
        table_name="configuration_results",
        columns=(CONFIGURATION_ID_COLUMN,),
    )
    _validate_configuration_metrics(table)


def _validate_selected_configuration(
    selected_configuration: Mapping[str, Any],
) -> str:
    if not isinstance(selected_configuration, Mapping):
        raise TypeError("selected_configuration must be a mapping.")

    if CONFIGURATION_ID_COLUMN not in selected_configuration:
        raise ValueError(
            "selected_configuration must contain 'configuration_id'.",
        )

    return str(selected_configuration[CONFIGURATION_ID_COLUMN])


def _validate_required_columns(
    table: pd.DataFrame,
    *,
    required_columns: set[str],
    table_name: str,
) -> None:
    missing_columns = required_columns - set(table.columns)
    if missing_columns:
        raise ValueError(
            f"{table_name} is missing required columns: "
            f"{tuple(sorted(missing_columns))}.",
        )


def _validate_identifier_columns(
    table: pd.DataFrame,
    *,
    table_name: str,
    columns: tuple[str, ...],
) -> None:
    if table[list(columns)].isna().any().any():
        raise ValueError(
            f"{table_name} contains missing identifier values.",
        )


def _validate_metrics(
    table: pd.DataFrame,
    *,
    metric_columns: tuple[str, ...],
    table_name: str,
) -> None:
    for column in metric_columns:
        values = pd.to_numeric(table[column], errors="coerce")

        if values.isna().any():
            raise ValueError(
                f"{table_name}.{column} contains non-numeric values.",
            )

        array = values.to_numpy(dtype=float)
        if not np.isfinite(array).all():
            raise ValueError(
                f"{table_name}.{column} contains non-finite values.",
            )

        metric_name = _metric_name_from_column(column)

        if metric_name == "mcc":
            if ((array < -1.0) | (array > 1.0)).any():
                raise ValueError(
                    f"{table_name}.{column} values must be within [-1, 1].",
                )
        elif ((array < 0.0) | (array > 1.0)).any():
            raise ValueError(
                f"{table_name}.{column} values must be within [0, 1].",
            )


def _validate_configuration_metrics(table: pd.DataFrame) -> None:
    _validate_metrics(
        table,
        metric_columns=CONFIGURATION_MEAN_COLUMNS,
        table_name="configuration_results",
    )
    _validate_metrics(
        table,
        metric_columns=CONFIGURATION_STD_COLUMNS,
        table_name="configuration_results",
    )

    for metric in METRIC_COLUMNS:
        std = pd.to_numeric(
            table[f"{metric}_std"],
            errors="coerce",
        ).to_numpy(dtype=float)
        if (std < 0.0).any():
            raise ValueError(
                f"configuration_results.{metric}_std contains negative values.",
            )


def _metric_name_from_column(column: str) -> str:
    if column.startswith("mean_"):
        return column.removeprefix("mean_")
    if column.endswith("_mean"):
        return column.removesuffix("_mean")
    if column.endswith("_std"):
        return column.removesuffix("_std")
    return column


# ---------------------------------------------------------------------------
# Table preparation
# ---------------------------------------------------------------------------


def _prepare_fold_results_table(table: pd.DataFrame) -> pd.DataFrame:
    result = table.copy()
    _normalize_identifiers(result, include_fold=True)

    for metric in METRIC_COLUMNS:
        result[metric] = pd.to_numeric(
            result[metric],
            errors="raise",
        ).astype(float)

    parameter_columns = _parameter_columns(
        result.columns,
        excluded={
            CONFIGURATION_ID_COLUMN,
            SEED_COLUMN,
            FOLD_COLUMN,
            *METRIC_COLUMNS,
        },
    )

    columns = [
        CONFIGURATION_ID_COLUMN,
        SEED_COLUMN,
        FOLD_COLUMN,
        *parameter_columns,
        *METRIC_COLUMNS,
    ]

    return result[columns].copy()


def _prepare_seed_summary_table(table: pd.DataFrame) -> pd.DataFrame:
    result = table.copy()
    _normalize_identifiers(result, include_fold=False)

    for metric, source_column in zip(
        METRIC_COLUMNS,
        SEED_METRIC_COLUMNS,
        strict=True,
    ):
        result[source_column] = pd.to_numeric(
            result[source_column],
            errors="raise",
        ).astype(float)

    parameter_columns = _parameter_columns(
        result.columns,
        excluded={
            CONFIGURATION_ID_COLUMN,
            SEED_COLUMN,
            *SEED_METRIC_COLUMNS,
        },
    )

    display_result = result[
        [
            CONFIGURATION_ID_COLUMN,
            SEED_COLUMN,
            *parameter_columns,
            *SEED_METRIC_COLUMNS,
        ]
    ].copy()

    display_result = display_result.rename(
        columns=dict(
            zip(
                SEED_METRIC_COLUMNS,
                METRIC_COLUMNS,
                strict=True,
            ),
        ),
    )

    return display_result.reset_index(drop=True)


def _prepare_configuration_table(table: pd.DataFrame) -> pd.DataFrame:
    result = table.copy()
    result[CONFIGURATION_ID_COLUMN] = result[CONFIGURATION_ID_COLUMN].astype(str)

    for metric in METRIC_COLUMNS:
        result[f"{metric}_mean"] = pd.to_numeric(
            result[f"{metric}_mean"],
            errors="raise",
        ).astype(float)
        result[f"{metric}_std"] = pd.to_numeric(
            result[f"{metric}_std"],
            errors="raise",
        ).astype(float)

    parameter_columns = _parameter_columns(
        result.columns,
        excluded={
            CONFIGURATION_ID_COLUMN,
            *CONFIGURATION_MEAN_COLUMNS,
            *CONFIGURATION_STD_COLUMNS,
        },
        excluded_prefixes=("seed_",),
    )
    seed_macro_columns = [
        column
        for column in result.columns
        if column.startswith("seed_") and column.endswith("_macro_f1")
    ]

    display_result = result[
        [
            CONFIGURATION_ID_COLUMN,
            *parameter_columns,
            *seed_macro_columns,
            *CONFIGURATION_MEAN_COLUMNS,
        ]
    ].copy()

    for metric in METRIC_COLUMNS:
        display_result[f"{metric} (mean ± std)"] = [
            format_mean_std(
                mean,
                std,
                decimals=5,
            )
            for mean, std in zip(
                result[f"{metric}_mean"],
                result[f"{metric}_std"],
                strict=True,
            )
        ]

    display_result = display_result.drop(
        columns=[
            *CONFIGURATION_MEAN_COLUMNS,
        ],
    )

    _restore_parameter_none_values(
        display_result,
        parameter_columns,
    )

    return display_result.reset_index(drop=True)


def _create_selected_configuration_table(
    *,
    configuration_table: pd.DataFrame,
    configuration_id: str,
) -> pd.DataFrame:
    selected_rows = configuration_table[
        configuration_table[CONFIGURATION_ID_COLUMN] == configuration_id
    ].copy()

    if selected_rows.empty:
        raise ValueError(
            f"Selected configuration '{configuration_id}' was not found in "
            "configuration_results.",
        )

    # The selected table is intentionally concise: it contains the actual
    # hyperparameters and every scalar CV metric as mean ± std. The per-seed
    # macro-F1 audit columns are specific to the full configuration ranking.
    seed_macro_columns = [
        column
        for column in selected_rows.columns
        if column.startswith("seed_") and column.endswith("_macro_f1")
    ]
    if seed_macro_columns:
        selected_rows = selected_rows.drop(columns=seed_macro_columns)

    return selected_rows.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Consistency and formatting helpers
# ---------------------------------------------------------------------------


def _normalize_identifiers(
    table: pd.DataFrame,
    *,
    include_fold: bool,
) -> None:
    table[CONFIGURATION_ID_COLUMN] = table[CONFIGURATION_ID_COLUMN].astype(str)
    table[SEED_COLUMN] = pd.to_numeric(
        table[SEED_COLUMN],
        errors="raise",
    ).astype(int)

    if include_fold:
        table[FOLD_COLUMN] = pd.to_numeric(
            table[FOLD_COLUMN],
            errors="raise",
        ).astype(int)


def _parameter_columns(
    columns: pd.Index[str],
    *,
    excluded: set[str],
    excluded_prefixes: tuple[str, ...] = (),
) -> list[str]:
    return [
        column
        for column in columns
        if column not in excluded
        and not any(column.startswith(prefix) for prefix in excluded_prefixes)
    ]


def _restore_parameter_none_values(
    table: pd.DataFrame,
    parameter_columns: list[str],
) -> None:
    for column in parameter_columns:
        if table[column].dtype.kind == "f":
            table[column] = table[column].where(
                ~table[column].isna(),
                None,
            )


def _validate_configuration_id_consistency(
    *,
    fold_results: pd.DataFrame,
    seed_results: pd.DataFrame,
    configuration_results: pd.DataFrame,
) -> None:
    fold_ids = set(fold_results[CONFIGURATION_ID_COLUMN].astype(str))
    seed_ids = set(seed_results[CONFIGURATION_ID_COLUMN].astype(str))
    configuration_ids = set(
        configuration_results[CONFIGURATION_ID_COLUMN].astype(str),
    )

    if fold_ids != seed_ids or seed_ids != configuration_ids:
        raise ValueError(
            "Cross-validation artifacts contain inconsistent configuration IDs."
        )


def _display_section(
    *,
    title: str,
    table: pd.DataFrame,
) -> None:
    display(
        HTML(
            f"<h3>{title}</h3>",
        ),
    )
    display(table)


def load_and_display_cross_validation_statistics(artifact_directory: Path):
    fold_results = load_validation_fold_results(artifact_directory)
    seed_results = load_validation_seed_results(artifact_directory)
    configuration_results = load_validation_configuration_results(artifact_directory)
    selected_configuration = load_selected_configuration(artifact_directory)

    statistics = compile_cross_validation_statistics(
        fold_results=fold_results,
        seed_results=seed_results,
        configuration_results=configuration_results,
        selected_configuration=selected_configuration,
    )

    display_cross_validation_statistics(statistics)
