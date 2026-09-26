"""ROSIDS23 feature transformations and transformed dataset schema."""

from enum import StrEnum

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from definitions import SEED, TEST_SIZE
from loading.rosids import (
    SOURCE_ROSIDS_FEATURES,
    SOURCE_ROSIDS_SCHEMA,
    source_rosids_df,
)
from schema.common import (
    FeatureDataType,
    FeatureRole,
    FeatureSemanticType,
    SourceFeatureSpec,
    TransformedDatasetSchema,
    TransformedFeatureSpec,
)
from transformation.common import (
    to_transformed_feature_spec,
    transform_data_frame,
)

# ----------------------------------------
# Transformation
# ----------------------------------------

SOURCE_ROSIDS_FEATURES_BY_LABEL: dict[str, SourceFeatureSpec] = {
    feature.label: feature for feature in SOURCE_ROSIDS_FEATURES
}


class RosidsPortCategory(StrEnum):
    """Semantic categories used to represent ROSIDS port values."""

    NOT_APPLICABLE = "not_applicable"
    WELL_KNOWN = "well_known"
    REGISTERED = "registered"
    DYNAMIC = "dynamic"
    TELNET = "telnet"
    SSDP = "ssdp"
    MDNS = "mdns"
    ROS = "ros"


ROSIDS_EXCLUDED_FEATURE_LABELS: frozenset[str] = frozenset(
    {
        "forward_push_flag_count",
        "forward_urgent_flag_count",
        "backward_urgent_flag_count",
        "urg_flag_count",
        "cwe_flag_count",
        "ece_flag_count",
        "forward_bytes_per_block_average",
        "forward_packets_per_block_average",
        "forward_block_rate_average",
        "backward_bytes_per_block_average",
        "backward_packets_per_block_average",
        "backward_block_rate_average",
        "initial_forward_window_bytes",
        "forward_segment_size_minimum",
    },
)


DESTINATION_PORT_CATEGORIES: dict[
    int,
    RosidsPortCategory,
] = {
    1900: RosidsPortCategory.SSDP,
    5353: RosidsPortCategory.MDNS,
    11311: RosidsPortCategory.ROS,
}

SOURCE_PORT_CATEGORIES: dict[
    int,
    RosidsPortCategory,
] = {
    23: RosidsPortCategory.TELNET,
    **DESTINATION_PORT_CATEGORIES,
}


def categorize_port(
    source_data_frame: pd.DataFrame,
    feature_label: str,
    port_categories: dict[int, RosidsPortCategory],
) -> pd.Series:
    """Map a ROSIDS port number to a semantic category."""

    port_series = pd.to_numeric(
        source_data_frame[feature_label],
        errors="raise",
    ).astype("int64")

    def categorize_port_value(
        port: int,
    ) -> RosidsPortCategory:
        if port == 0:
            return RosidsPortCategory.NOT_APPLICABLE

        explicit_category = port_categories.get(port)

        if explicit_category is not None:
            return explicit_category

        if port <= 1023:
            return RosidsPortCategory.WELL_KNOWN

        if port <= 49151:
            return RosidsPortCategory.REGISTERED

        if port <= 65535:
            return RosidsPortCategory.DYNAMIC

        raise ValueError(
            f"Invalid {feature_label}: {port}",
        )

    return port_series.map(categorize_port_value).astype("string")


def transform_protocol(
    source_data_frame: pd.DataFrame,
) -> pd.Series:
    """Map ROSIDS protocol numbers to protocol names."""

    protocol_series = pd.to_numeric(
        source_data_frame["protocol"],
        errors="raise",
    )

    protocol = protocol_series.map(
        {
            0: "not_applicable",
            6: "tcp",
            17: "udp",
        },
    )

    return protocol.astype("string")


def transform_flow_bytes_per_second(
    source_data_frame: pd.DataFrame,
) -> pd.Series:
    """Replace non-finite flow byte-rate values with missing values."""

    return source_data_frame["flow_bytes_per_second"].replace(
        [np.inf, -np.inf],
        np.nan,
    )


def transform_initial_backward_window_bytes(
    source_data_frame: pd.DataFrame,
) -> pd.Series:
    """Replace the ROSIDS -1 sentinel with a missing value."""

    return source_data_frame["initial_backward_window_bytes"].replace(
        -1,
        np.nan,
    )


def build_transformed_rosids_features() -> tuple[TransformedFeatureSpec, ...]:
    """Build the complete treated ROSIDS feature collection."""

    transformed_rosids_features: list[TransformedFeatureSpec] = []

    for source_feature_specification in SOURCE_ROSIDS_FEATURES:
        source_feature_label = source_feature_specification.label

        if source_feature_label in ROSIDS_EXCLUDED_FEATURE_LABELS:
            continue

        if source_feature_specification.role not in {
            FeatureRole.PREDICTOR,
            FeatureRole.TARGET,
        }:
            continue

        if source_feature_label == "destination_port":
            transformed_rosids_features.append(
                TransformedFeatureSpec(
                    label="destination_port_category",
                    name="Destination Port Category",
                    data_type=FeatureDataType.STRING,
                    semantic_type=FeatureSemanticType.CATEGORICAL,
                    role=FeatureRole.PREDICTOR,
                    description=(
                        "Semantic category assigned to the destination port "
                        "based on explicit service ports and standardized "
                        "port ranges."
                    ),
                    category_enum=RosidsPortCategory,
                    source_feature_labels=("destination_port",),
                    transformer=lambda dataframe: categorize_port(
                        dataframe,
                        "destination_port",
                        DESTINATION_PORT_CATEGORIES,
                    ),
                ),
            )
            continue

        if source_feature_label == "source_port":
            transformed_rosids_features.append(
                TransformedFeatureSpec(
                    label="source_port_category",
                    name="Source Port Category",
                    data_type=FeatureDataType.STRING,
                    semantic_type=FeatureSemanticType.CATEGORICAL,
                    role=FeatureRole.PREDICTOR,
                    description=(
                        "Semantic category assigned to the source port "
                        "based on explicit service ports and standardized "
                        "port ranges."
                    ),
                    category_enum=RosidsPortCategory,
                    source_feature_labels=("source_port",),
                    transformer=lambda dataframe: categorize_port(
                        dataframe,
                        "source_port",
                        SOURCE_PORT_CATEGORIES,
                    ),
                ),
            )
            continue

        if source_feature_label == "protocol":
            transformed_rosids_features.append(
                TransformedFeatureSpec(
                    label="protocol",
                    name="Protocol",
                    data_type=FeatureDataType.STRING,
                    semantic_type=FeatureSemanticType.CATEGORICAL,
                    role=FeatureRole.PREDICTOR,
                    description=(
                        "Transport protocol represented as TCP, UDP, "
                        "or missing when the source protocol value is 0."
                    ),
                    source_feature_labels=("protocol",),
                    transformer=transform_protocol,
                ),
            )
            continue

        if source_feature_label == "flow_bytes_per_second":
            transformed_rosids_features.append(
                TransformedFeatureSpec(
                    label="flow_bytes_per_second",
                    name="Flow Bytes per Second",
                    data_type=FeatureDataType.FLOAT,
                    semantic_type=FeatureSemanticType.NUMERIC,
                    role=FeatureRole.PREDICTOR,
                    description=(
                        "Average number of bytes transmitted per second "
                        "by the flow, with non-finite values represented "
                        "as missing."
                    ),
                    source_feature_labels=("flow_bytes_per_second",),
                    transformer=transform_flow_bytes_per_second,
                ),
            )
            continue

        if source_feature_label == "initial_backward_window_bytes":
            transformed_rosids_features.append(
                TransformedFeatureSpec(
                    label="initial_backward_window_bytes",
                    name="Initial Backward Window Bytes",
                    data_type=FeatureDataType.INTEGER,
                    semantic_type=FeatureSemanticType.NUMERIC,
                    role=FeatureRole.PREDICTOR,
                    description=(
                        "Initial TCP window size advertised by the "
                        "backward endpoint, with the source -1 sentinel "
                        "represented as missing."
                    ),
                    source_feature_labels=("initial_backward_window_bytes",),
                    transformer=transform_initial_backward_window_bytes,
                ),
            )
            continue

        transformed_rosids_features.append(
            to_transformed_feature_spec(
                source_feature_specification,
            ),
        )

    return tuple(transformed_rosids_features)


TRANSFORMED_ROSIDS_FEATURES: tuple[TransformedFeatureSpec, ...] = (
    build_transformed_rosids_features()
)


TRANSFORMED_ROSIDS_SCHEMA = TransformedDatasetSchema(
    dataset_name="ROSIDS23",
    target_feature_label="label",
    features=TRANSFORMED_ROSIDS_FEATURES,
)


transformed_rosids_df = transform_data_frame(
    source_data_frame=source_rosids_df,
    source_dataset_schema=SOURCE_ROSIDS_SCHEMA,
    transformed_dataset_schema=TRANSFORMED_ROSIDS_SCHEMA,
)


# ----------------------------------------
# Splitting
# ----------------------------------------


rosids_df_for_train, rosids_df_for_test = train_test_split(
    transformed_rosids_df,
    test_size=TEST_SIZE,
    random_state=SEED,
    stratify=transformed_rosids_df["label"],
)
