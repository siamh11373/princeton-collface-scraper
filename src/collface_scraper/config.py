"""Configuration with no persistent credential storage."""

import hashlib
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .errors import ConfigurationError

TARGET = "https://collface.deptcpanel.princeton.edu"
CAS_ORIGIN = "https://fed.princeton.edu"


def origin(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"


@dataclass(frozen=True)
class Credentials:
    username: str = field(repr=False)
    password: str = field(repr=False)

    @property
    def account_key(self) -> str:
        return hashlib.sha256(self.username.strip().casefold().encode()).hexdigest()


def load_credentials() -> Credentials:
    username = os.getenv("COLLFACE_USERNAME")
    password = os.getenv("COLLFACE_PASSWORD")
    if username is None and password is None:
        raise ConfigurationError(
            "Set COLLFACE_USERNAME and COLLFACE_PASSWORD in the process environment."
        )
    if not isinstance(username, str) or not username.strip() or not password:
        raise ConfigurationError("Set both CollFace credential environment variables.")
    return Credentials(username=username.strip(), password=password)
