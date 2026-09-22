"""GENIS dataset loading functions."""

from pathlib import Path

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
