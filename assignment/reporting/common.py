"""Shared definitions for experiment-result reporting.

The reporting layer distinguishes between:

* metrics that are required by the assignment;
* metrics that are optional but explicitly permitted by the assignment; and
* confusion matrices, which are reported as matrices rather than as a scalar
  mean ± standard deviation value.

For scalar cross-validation metrics, the presentation convention is always
``mean ± std``. Standard deviation is therefore an internal statistic, not a
separate report column.
"""

from enum import StrEnum
from typing import Final

REPORT_DISPLAY_DECIMALS: Final[int] = 12


class MetricName(StrEnum):
    """Classification metrics used by the experiment reports."""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    ROC_AUC = "roc_auc"
    PR_AUC = "pr_auc"
    MCC = "mcc"
    BALANCED_ACCURACY = "balanced_accuracy"


class ReportTableName(StrEnum):
    """Names of report tables produced by reporting modules."""

    FOLD_RESULTS = "fold_results"
    SEED_SUMMARY = "seed_summary"
    CONFIGURATION_RESULTS = "configuration_results"
    SELECTED_CONFIGURATION = "selected_configuration"
    CONFUSION_MATRIX = "confusion_matrix"


class MetricAveraging(StrEnum):
    """Averaging strategies for multiclass classification metrics."""

    MACRO = "macro"
    WEIGHTED = "weighted"
    MICRO = "micro"


# ---------------------------------------------------------------------------
# Canonical column names
# ---------------------------------------------------------------------------

CONFIGURATION_ID_COLUMN: Final[str] = "configuration_id"
SEED_COLUMN: Final[str] = "seed"
FOLD_COLUMN: Final[str] = "fold"

ACCURACY_COLUMN: Final[str] = "accuracy"
PRECISION_COLUMN: Final[str] = "precision"
RECALL_COLUMN: Final[str] = "recall"
F1_SCORE_COLUMN: Final[str] = "macro_f1"
ROC_AUC_COLUMN: Final[str] = "roc_auc"
PR_AUC_COLUMN: Final[str] = "pr_auc"
MCC_COLUMN: Final[str] = "mcc"
BALANCED_ACCURACY_COLUMN: Final[str] = "balanced_accuracy"
CONFUSION_MATRIX_COLUMN: Final[str] = "confusion_matrix"

# Internal aggregation names. These are not intended to become separate
# displayed columns in report tables.
MEAN_SUFFIX: Final[str] = "_mean"
STD_SUFFIX: Final[str] = "_std"

# Display convention required by the reporting layer.
MEAN_STD_SEPARATOR: Final[str] = " ± "


# ---------------------------------------------------------------------------
# Assignment metric groups
# ---------------------------------------------------------------------------

REQUIRED_METRICS: Final[tuple[MetricName, ...]] = (
    MetricName.ACCURACY,
    MetricName.PRECISION,
    MetricName.RECALL,
    MetricName.F1_SCORE,
    MetricName.ROC_AUC,
    # Confusion matrices are intentionally not included here because they are
    # not scalar metrics and are represented by a dedicated report table.
)

OPTIONAL_METRICS: Final[tuple[MetricName, ...]] = (
    MetricName.PR_AUC,
    MetricName.MCC,
    MetricName.BALANCED_ACCURACY,
)

ALL_SCALAR_METRICS: Final[tuple[MetricName, ...]] = (
    *REQUIRED_METRICS,
    *OPTIONAL_METRICS,
)


# Precision, recall, and F-score are multiclass metrics for this project.
# Macro averaging gives each class equal weight and is the convention used for
# the primary model-selection metric (macro F1).
MACRO_AVERAGED_METRICS: Final[frozenset[MetricName]] = frozenset(
    {
        MetricName.PRECISION,
        MetricName.RECALL,
        MetricName.F1_SCORE,
        MetricName.ROC_AUC,
        MetricName.PR_AUC,
    },
)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_mean_std(
    mean: float,
    std: float,
    *,
    decimals: int = REPORT_DISPLAY_DECIMALS,
) -> str:
    """Format a scalar result using the report's mean ± std convention."""
    return f"{mean:.{decimals}f}{MEAN_STD_SEPARATOR}{std:.{decimals}f}"
