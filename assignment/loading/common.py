"""Common data structures for loaded network-traffic datasets."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pandas as pd


class DatasetSplit(StrEnum):
    """Logical partition represented by a loaded dataset."""

    FULL = "full"
    TRAIN = "train"
    TEST = "test"


@dataclass(frozen=True, slots=True)
class DatasetPartition:
    """A loaded dataset partition together with its provenance."""

    data_frame: pd.DataFrame
    split: DatasetSplit
    source_path: Path

    def __post_init__(self) -> None:
        """Validate invariants of the loaded partition."""

        if self.data_frame.empty:
            raise ValueError(
                f"Dataset partition '{self.split.value}' loaded from "
                f"'{self.source_path}' is empty."
            )

        if not self.source_path:
            raise ValueError("Dataset partition source path must not be empty.")


@dataclass(frozen=True, slots=True)
class DatasetBundle:
    """Collection of available partitions for one dataset."""

    dataset_name: str
    full: DatasetPartition | None = None
    train: DatasetPartition | None = None
    test: DatasetPartition | None = None

    def __post_init__(self) -> None:
        """Validate the consistency of the dataset bundle."""

        if not self.dataset_name:
            raise ValueError("Dataset name must not be empty.")

        available_partition_count = sum(
            partition is not None for partition in (self.full, self.train, self.test)
        )

        if available_partition_count == 0:
            raise ValueError(
                f"Dataset '{self.dataset_name}' must contain at least one "
                "loaded partition."
            )

        if self.full is not None and self.full.split is not DatasetSplit.FULL:
            raise ValueError("The 'full' partition must use DatasetSplit.FULL.")

        if self.train is not None and self.train.split is not DatasetSplit.TRAIN:
            raise ValueError("The 'train' partition must use DatasetSplit.TRAIN.")

        if self.test is not None and self.test.split is not DatasetSplit.TEST:
            raise ValueError("The 'test' partition must use DatasetSplit.TEST.")

        partition_dataset_names = {
            partition.split
            for partition in (self.full, self.train, self.test)
            if partition is not None
        }

        if len(partition_dataset_names) != available_partition_count:
            raise ValueError(
                f"Dataset '{self.dataset_name}' contains duplicate partitions."
            )

    @property
    def has_full_partition(self) -> bool:
        """Return whether a complete unsplit dataset is available."""

        return self.full is not None

    @property
    def has_training_partition(self) -> bool:
        """Return whether a training partition is available."""

        return self.train is not None

    @property
    def has_test_partition(self) -> bool:
        """Return whether a test partition is available."""

        return self.test is not None
