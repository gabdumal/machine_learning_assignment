"""GENIS dataset loading functions."""

from pathlib import Path

import pandas as pd

from data.common import DatasetBundle
from data.loader import CsvDatasetLoader
from schema.genis import GENIS_SCHEMA


def load_genis(
    training_csv_file_path: Path,
    test_csv_file_path: Path,
) -> DatasetBundle:
    """Load the official GENIS training and test CSV files.

    Args:
        training_csv_file_path: Path to the GENIS training CSV file.
        test_csv_file_path: Path to the GENIS test CSV file.

    Returns:
        A dataset bundle containing the GENIS training and test partitions.

    Raises:
        CsvLoadingError: If either CSV file cannot be loaded or does not
            conform to the GENIS schema.
    """

    dataset_loader = CsvDatasetLoader(GENIS_SCHEMA)

    return dataset_loader.load_bundle(
        training_csv_file_path=training_csv_file_path,
        test_csv_file_path=test_csv_file_path,
    )


def merge_genis_partitions(
    genis_dataset_bundle: DatasetBundle,
) -> pd.DataFrame:
    """Merge the GENIS training and test DataFrames."""

    if genis_dataset_bundle.train is None:
        raise ValueError("GENIS training partition is not available.")

    if genis_dataset_bundle.test is None:
        raise ValueError("GENIS test partition is not available.")

    return pd.concat(
        (
            genis_dataset_bundle.train.data_frame,
            genis_dataset_bundle.test.data_frame,
        ),
        ignore_index=True,
    )
