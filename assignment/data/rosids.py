"""ROSIDS23 dataset loading functions."""

from pathlib import Path

from data.common import DatasetBundle
from data.loader import CsvDatasetLoader
from schema.rosids import ROSIDS_SCHEMA


def load_rosids(
    csv_file_path: Path,
) -> DatasetBundle:
    """Load the complete ROSIDS23 dataset from a CSV file.

    Args:
        csv_file_path: Path to the ROSIDS23 CSV file.

    Returns:
        A dataset bundle containing the complete ROSIDS23 dataset as its
        full partition.

    Raises:
        CsvLoadingError: If the CSV file cannot be loaded or does not conform
            to the ROSIDS23 schema.
    """

    dataset_loader = CsvDatasetLoader(ROSIDS_SCHEMA)

    return dataset_loader.load_bundle(
        full_csv_file_path=csv_file_path,
    )
