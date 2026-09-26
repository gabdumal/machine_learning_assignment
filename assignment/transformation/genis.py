"""GENIS feature transformations and transformed dataset schema."""

from enum import StrEnum

import pandas as pd

from loading.genis import (
    SOURCE_GENIS_FEATURES,
    SOURCE_GENIS_SCHEMA,
    source_genis_df_for_test,
    source_genis_df_for_train,
)
from schema.common import (
    FeatureDataType,
    FeatureRole,
    FeatureSemanticType,
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


class GenisPortCategory(StrEnum):
    """Semantic categories used to represent destination ports."""

    NOT_APPLICABLE = "not_applicable"
    WELL_KNOWN = "well_known"
    FTP = "ftp"
    SSH = "ssh"
    DNS = "dns"
    HTTP = "http"
    NETBIOS = "netbios"
    HTTPS = "https"
    SMB = "smb"
    SMTPS = "smtps"
    REGISTERED = "registered"
    MDNS = "mdns"
    DYNAMIC = "dynamic"


GENIS_EXCLUDED_FEATURE_LABELS: frozenset[str] = frozenset(
    {
        "destination_tcp_base",
        "source_tos",
        "source_tcp_base",
        "protocol_ipv6_icmp",
        "flags_e_d",
        "flags_e_g",
        "flags_e_r",
        "flags_e_u",
        "state_clo",
        "state_nrs",
        "state_tst",
        "state_urh",
        "state_urhpro",
    }
)


source_port_categories: dict[
    int,
    GenisPortCategory,
] = {
    80: GenisPortCategory.HTTP,
    137: GenisPortCategory.NETBIOS,
    138: GenisPortCategory.NETBIOS,
    5353: GenisPortCategory.MDNS,
}


destination_port_categories: dict[
    int,
    GenisPortCategory,
] = {
    21: GenisPortCategory.FTP,
    22: GenisPortCategory.SSH,
    53: GenisPortCategory.DNS,
    443: GenisPortCategory.HTTPS,
    445: GenisPortCategory.SMB,
    587: GenisPortCategory.SMTPS,
    **source_port_categories,
}


def categorize_port(
    source_data_frame: pd.DataFrame,
    feature_label: str,
    port_categories: dict[
        int,
        GenisPortCategory,
    ],
) -> pd.Series:
    """Map ports to semantic categories."""

    port_series = source_data_frame[feature_label].astype("int64")

    def categorize_port_range(
        port: int,
    ) -> GenisPortCategory:
        """Assign a semantic category to one port."""

        if port == 0:
            return GenisPortCategory.NOT_APPLICABLE

        explicit_category = port_categories.get(port)

        if explicit_category is not None:
            return explicit_category

        if port <= 1023:
            return GenisPortCategory.WELL_KNOWN

        if port <= 49151:
            return GenisPortCategory.REGISTERED

        if port <= 65535:
            return GenisPortCategory.DYNAMIC

        raise ValueError(
            f"Invalid destination port: {port}",
        )

    return port_series.map(categorize_port_range).astype("string")


def merge_icmp_protocols(
    source_data_frame: pd.DataFrame,
) -> pd.Series:
    """Merge IPv4 ICMP and IPv6 ICMP indicators into one ICMP feature."""

    icmp = source_data_frame["protocol_icmp"].astype("boolean")
    ipv6_icmp = source_data_frame["protocol_ipv6_icmp"].astype("boolean")

    return (icmp | ipv6_icmp).astype("boolean")


def build_transformed_genis_features() -> tuple[TransformedFeatureSpec, ...]:
    """Build the complete treated GENIS feature collection."""

    transformed_genis_features: list[TransformedFeatureSpec] = []

    for source_feature_specification in SOURCE_GENIS_FEATURES:
        source_feature_label = source_feature_specification.label

        if source_feature_label in GENIS_EXCLUDED_FEATURE_LABELS:
            continue

        if source_feature_specification.role not in {
            FeatureRole.PREDICTOR,
            FeatureRole.TARGET,
        }:
            continue

        if source_feature_label == "destination_port":
            transformed_genis_features.append(
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
                    category_enum=GenisPortCategory,
                    source_feature_labels=("destination_port",),
                    transformer=lambda dataframe: categorize_port(
                        dataframe,
                        "destination_port",
                        destination_port_categories,
                    ),
                ),
            )
            continue

        if source_feature_label == "source_port":
            transformed_genis_features.append(
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
                    category_enum=GenisPortCategory,
                    source_feature_labels=("source_port",),
                    transformer=lambda dataframe: categorize_port(
                        dataframe,
                        "source_port",
                        source_port_categories,
                    ),
                ),
            )
            continue

        if source_feature_label == "protocol_ipv6_icmp":
            continue

        if source_feature_label == "protocol_icmp":
            transformed_genis_features.append(
                TransformedFeatureSpec(
                    label="protocol_icmp",
                    name="Protocol: ICMP",
                    data_type=FeatureDataType.INTEGER,
                    semantic_type=FeatureSemanticType.BINARY,
                    role=FeatureRole.PREDICTOR,
                    description=(
                        "Binary indicator for ICMP traffic, merging IPv4 "
                        "ICMP and IPv6 ICMP traffic."
                    ),
                    source_feature_labels=(
                        "protocol_icmp",
                        "protocol_ipv6_icmp",
                    ),
                    transformer=merge_icmp_protocols,
                ),
            )
            continue

        transformed_genis_features.append(
            to_transformed_feature_spec(
                source_feature_specification,
            ),
        )

    return tuple(transformed_genis_features)


TRANSFORMED_GENIS_FEATURES: tuple[TransformedFeatureSpec, ...] = (
    build_transformed_genis_features()
)


TRANSFORMED_GENIS_SCHEMA = TransformedDatasetSchema(
    dataset_name="GENIS",
    target_feature_label="category_label",
    features=TRANSFORMED_GENIS_FEATURES,
)


genis_df_for_train = transform_data_frame(
    source_data_frame=source_genis_df_for_train,
    source_dataset_schema=SOURCE_GENIS_SCHEMA,
    transformed_dataset_schema=TRANSFORMED_GENIS_SCHEMA,
)

genis_df_for_test = transform_data_frame(
    source_data_frame=source_genis_df_for_test,
    source_dataset_schema=SOURCE_GENIS_SCHEMA,
    transformed_dataset_schema=TRANSFORMED_GENIS_SCHEMA,
)

merged_transformed_genis_df = pd.concat(
    (
        genis_df_for_train,
        genis_df_for_test,
    ),
    ignore_index=True,
)
