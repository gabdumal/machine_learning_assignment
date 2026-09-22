"""GENIS dataset schema."""

from enum import StrEnum


class GenisCategoryLabel(StrEnum):
    """Multiclass traffic categories defined by the GENIS dataset."""

    BENIGN = "benign"
    BRUTEFORCE = "bruteforce"
    DOS = "dos"
    RECON = "recon"


class GenisSubcategoryLabel(StrEnum):
    """Fine-grained traffic categories defined by the GENIS dataset."""

    BENIGN_ADMIN = "benign-admin"
    BENIGN_BACKGROUND = "benign-background"
    BENIGN_USER = "benign-user"

    BRUTEFORCE_FTP = "bruteforce-ftp"
    BRUTEFORCE_SMB = "bruteforce-smb"
    BRUTEFORCE_SSH = "bruteforce-ssh"

    DOS_HULK = "dos-hulk"
    DOS_ICMP = "dos-icmp"
    DOS_PUSHACK = "dos-pushack"
    DOS_SLOWLORIS = "dos-slowloris"
    DOS_UDP = "dos-udp"

    RECON_DNS = "recon-dns"
    RECON_NMAP = "recon-nmap"
