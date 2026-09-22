from enum import StrEnum

import pandas as pd
from IPython.display import display

from loading.genis import SOURCE_GENIS_FEATURES, SOURCE_GENIS_SCHEMA, source_genis_df
from schema.common import (
    FeatureDataType,
    FeatureRole,
    FeatureSemanticType,
    SourceFeatureSpec,
    TransformedDatasetSchema,
    TransformedFeatureSpec,
)
from transformation.common import transform_data_frame

SOURCE_GENIS_FEATURES_BY_LABEL: dict[str, SourceFeatureSpec] = {
    feature.label: feature for feature in SOURCE_GENIS_FEATURES
}


def identity_transform(
    source_data_frame: pd.DataFrame,
    source_feature_label: str,
) -> pd.Series:
    """Return a source feature unchanged."""

    return source_data_frame[source_feature_label].copy()


def to_transformed_feature_spec(
    source_feature_specification: SourceFeatureSpec,
) -> TransformedFeatureSpec:
    """Create a transformed feature with an identity transformation."""

    return TransformedFeatureSpec(
        label=source_feature_specification.label,
        name=source_feature_specification.name,
        data_type=source_feature_specification.data_type,
        semantic_type=source_feature_specification.semantic_type,
        role=source_feature_specification.role,
        description=source_feature_specification.description,
        category_enum=source_feature_specification.category_enum,
        datetime_formats=source_feature_specification.datetime_formats,
        source_feature_labels=(source_feature_specification.label,),
        transformer=lambda data_frame: identity_transform(
            data_frame,
            source_feature_specification.label,
        ),
    )


class GenisDestinationPortCategory(StrEnum):
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


def categorize_destination_port(
    source_data_frame: pd.DataFrame,
) -> pd.Series:
    """Map destination ports to semantic categories."""

    destination_port_series = source_data_frame["destination_port"].astype("int64")

    explicit_port_categories: dict[int, GenisDestinationPortCategory] = {
        21: GenisDestinationPortCategory.FTP,
        22: GenisDestinationPortCategory.SSH,
        53: GenisDestinationPortCategory.DNS,
        80: GenisDestinationPortCategory.HTTP,
        137: GenisDestinationPortCategory.NETBIOS,
        138: GenisDestinationPortCategory.NETBIOS,
        443: GenisDestinationPortCategory.HTTPS,
        445: GenisDestinationPortCategory.SMB,
        587: GenisDestinationPortCategory.SMTPS,
        5353: GenisDestinationPortCategory.MDNS,
    }

    def categorize_port(
        destination_port: int,
    ) -> GenisDestinationPortCategory:
        if destination_port == 0:
            return GenisDestinationPortCategory.NOT_APPLICABLE

        explicit_category = explicit_port_categories.get(destination_port)

        if explicit_category is not None:
            return explicit_category

        if destination_port <= 1023:
            return GenisDestinationPortCategory.WELL_KNOWN

        if destination_port <= 49151:
            return GenisDestinationPortCategory.REGISTERED

        if destination_port <= 65535:
            return GenisDestinationPortCategory.DYNAMIC

        raise ValueError(
            f"Invalid destination port: {destination_port}",
        )

    return destination_port_series.map(categorize_port).astype("string")


TRANSFORMED_GENIS_DESTINATION_PORT = TransformedFeatureSpec(
    label="destination_port_category",
    name="Destination Port Category",
    data_type=FeatureDataType.STRING,
    semantic_type=FeatureSemanticType.CATEGORICAL,
    role=FeatureRole.PREDICTOR,
    description=(
        "Semantic category assigned to the destination port based on "
        "explicit service ports and standardized port ranges."
    ),
    category_enum=GenisDestinationPortCategory,
    source_feature_labels=("destination_port",),
    transformer=categorize_destination_port,
)


def build_transformed_genis_features() -> tuple[TransformedFeatureSpec, ...]:
    """Build the complete treated GENIS feature collection."""

    transformed_genis_features: list[TransformedFeatureSpec] = []

    for source_feature_specification in SOURCE_GENIS_FEATURES:
        if source_feature_specification.role not in {
            FeatureRole.PREDICTOR,
            FeatureRole.TARGET,
        }:
            continue

        if source_feature_specification.label == "destination_port":
            transformed_genis_features.append(
                TRANSFORMED_GENIS_DESTINATION_PORT,
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


transformed_genis_df = transform_data_frame(
    source_data_frame=source_genis_df,
    source_dataset_schema=SOURCE_GENIS_SCHEMA,
    transformed_dataset_schema=TRANSFORMED_GENIS_SCHEMA,
)


display(transformed_genis_df)
