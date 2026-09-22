from pathlib import Path

from data import load_genis, load_rosids, merge_genis_partitions

DATA_ROOT = Path(__file__).resolve().parent / "_data"

genis_dataset_bundle = load_genis(
    training_csv_file_path=DATA_ROOT / "genis/genis-60-sec-train.csv",
    test_csv_file_path=DATA_ROOT / "genis/genis-60-sec-test.csv",
)
genis_df = merge_genis_partitions(genis_dataset_bundle)

rosids_dataset_bundle = load_rosids(
    csv_file_path=DATA_ROOT / "rosids23/ROSIDS23.csv",
)
assert rosids_dataset_bundle.full is not None
rosids_df = rosids_dataset_bundle.full.data_frame
