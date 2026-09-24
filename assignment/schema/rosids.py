"""ROSIDS23 dataset schema."""

from enum import StrEnum


class RosidsLabel(StrEnum):
    """Known multiclass labels in the ROSIDS23 dataset."""

    BENIGN = "Benign"
    DOS = "DoS"
    SUBFLOOD = "Subflood"
    UNAUTHORIZED_PUBLISH = "UnauthPub"
    UNAUTHORIZED_SUBSCRIBE = "UnauthSub"
