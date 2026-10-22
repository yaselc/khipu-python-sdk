"""Connection settings and their validation.

Every check here runs when a :class:`KhipuConfig` is constructed, so a
misconfiguration is reported as :class:`~khipu_sdk.errors.KhipuConfigurationError`
before any HTTP request can be built. Error messages never include the value
that was rejected: an API key, or a URL or environment variable that carries
one by mistake, must not reach logs through an exception. Values that fail a
check are never normalised into acceptable ones.
"""

from __future__ import annotations

import ipaddress
import math
import os
import re
from dataclasses import dataclass, field
from typing import Optional, Union
from urllib.parse import urlsplit

import httpx

from .errors import KhipuConfigurationError

__all__ = ["KhipuConfig"]

#: A single float applies to httpx's connect, read, write and pool phases.
#: Pass an ``httpx.Timeout`` to control them independently.
TimeoutValue = Union[float, httpx.Timeout]

_TIMEOUT_PHASES = ("connect", "read", "write", "pool")

_ALLOWED_SCHEMES = frozenset({"http", "https"})

#: One DNS label. Underscores are accepted because local and container
#: hostnames (for example Docker Compose service names) use them.
_HOST_LABEL = re.compile(r"[A-Za-z0-9_](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9_])?")

_BASE_URL_FORMAT = (
    "base_url must be an absolute http:// or https:// URL with a hostname, "
    "for example 'https://payment-api.khipu.com'"
)


@dataclass(frozen=True)
class KhipuConfig:
    """Connection settings for :class:`~khipu_sdk.client.KhipuClient`.

    ``api_key`` is excluded from ``repr`` so the credential cannot leak through
    logging, Sentry local-variable capture or a Django debug page.

    Construction raises :class:`~khipu_sdk.errors.KhipuConfigurationError` (also
    a ``ValueError``) when a value is invalid; see :func:`validate_config`.
    """

    api_key: str = field(repr=False)
    base_url: str = "https://payment-api.khipu.com"
    #: Never ``None``: an unbounded timeout would let a stalled Khipu request
    #: pin a worker indefinitely.
    timeout: TimeoutValue = 10.0

    def __post_init__(self) -> None:
        validate_config(self)

    @classmethod
    def from_env(cls, prefix: str = "KHIPU_") -> "KhipuConfig":
        """Build a config from ``{prefix}API_KEY``, ``BASE_URL`` and ``TIMEOUT``.

        An unset ``BASE_URL`` or ``TIMEOUT`` uses the default. A variable that is
        set but blank is an error rather than a silent fallback to the default.
        """
        api_key = os.getenv(f"{prefix}API_KEY")
        if not api_key:
            raise KhipuConfigurationError(
                f"Missing or empty environment variable: {prefix}API_KEY"
            )

        base_url = os.getenv(f"{prefix}BASE_URL", cls.base_url)
        timeout_str = os.getenv(f"{prefix}TIMEOUT")
        timeout: TimeoutValue = (
            cls.timeout
            if timeout_str is None
            else _parse_env_seconds(timeout_str, f"{prefix}TIMEOUT")
        )

        return cls(api_key=api_key, base_url=base_url, timeout=timeout)


def validate_config(config: KhipuConfig) -> None:
    """Raise :class:`KhipuConfigurationError` unless ``config`` is usable.

    Runs on construction and again in :class:`~khipu_sdk.client.KhipuClient`,
    which also covers an ``httpx.Timeout`` mutated after the config was built.
    """
    _validate_api_key(config.api_key)
    _validate_base_url(config.base_url)
    _validate_timeout(config.timeout)


def _validate_api_key(api_key: object) -> None:
    # Named ``api_key`` rather than ``value`` so error trackers that capture
    # frame locals scrub it with their default denylist.
    if not isinstance(api_key, str):
        raise KhipuConfigurationError(
            f"api_key must be a string, not {type(api_key).__name__}"
        )
    if not api_key.strip():
        raise KhipuConfigurationError("api_key must not be empty or blank")
    # It is sent as the x-api-key header. A character outside visible ASCII
    # either fails header encoding inside httpx, with the key attached to the
    # error, or is whitespace that would be sent as part of the credential.
    if not all("\x21" <= char <= "\x7e" for char in api_key):
        raise KhipuConfigurationError(
            "api_key must contain only visible ASCII characters, "
            "with no whitespace or control characters"
        )


def _validate_base_url(value: object) -> None:
    if not isinstance(value, str):
        raise KhipuConfigurationError(
            f"base_url must be a string, not {type(value).__name__}"
        )
    # urlsplit and httpx silently drop or percent-encode these instead of
    # failing, which would send requests somewhere other than intended.
    if not value or not all("\x21" <= char <= "\x7e" for char in value):
        raise KhipuConfigurationError(
            f"{_BASE_URL_FORMAT}; it must not be empty or contain whitespace, "
            "control or non-ASCII characters (use the xn-- form of an "
            "internationalised hostname)"
        )
    if "#" in value:
        raise KhipuConfigurationError("base_url must not contain a fragment ('#')")

    netloc = _split_netloc(value)
    if netloc is None:
        raise KhipuConfigurationError(_BASE_URL_FORMAT)
    if "@" in netloc:
        raise KhipuConfigurationError(
            "base_url must not contain credentials; pass the API key as api_key"
        )
    if not _is_valid_authority(netloc):
        raise KhipuConfigurationError(
            f"{_BASE_URL_FORMAT}; its hostname or port is invalid"
        )


def _split_netloc(url: str) -> Optional[str]:
    """Return the authority of an absolute http(s) URL, or ``None``."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in _ALLOWED_SCHEMES or not parts.netloc:
        return None
    return parts.netloc


def _is_valid_authority(netloc: str) -> bool:
    """Check ``host[:port]`` where host is a DNS name, IPv4 or bracketed IPv6."""
    port: Optional[str]
    if netloc.startswith("["):
        host, bracket, rest = netloc[1:].partition("]")
        if not bracket or (rest and not rest.startswith(":")):
            return False
        port = rest[1:] if rest else None
        if not _is_ipv6(host):
            return False
    else:
        host, colon, rest = netloc.partition(":")
        port = rest if colon else None
        if not _is_hostname(host):
            return False
    if port is None:
        return True
    return port.isdigit() and 1 <= int(port) <= 65535


def _is_ipv6(host: str) -> bool:
    try:
        ipaddress.IPv6Address(host)
    except ValueError:
        return False
    return True


def _is_hostname(host: str) -> bool:
    name = host[:-1] if host.endswith(".") else host
    if not name or len(name) > 253:
        return False
    labels = name.split(".")
    # A name whose last label is numeric is read as an IPv4 address by URL
    # parsers, so it must be a valid one.
    if labels[-1].isdigit():
        try:
            ipaddress.IPv4Address(name)
        except ValueError:
            return False
        return True
    return all(_HOST_LABEL.fullmatch(label) for label in labels)


def _validate_timeout(value: object) -> None:
    if isinstance(value, httpx.Timeout):
        # httpx stores None for an unbounded phase; every phase must be bounded.
        for phase in _TIMEOUT_PHASES:
            _validate_seconds(getattr(value, phase, None), f"timeout.{phase}")
        return
    _validate_seconds(value, "timeout")


def _validate_seconds(value: object, name: str) -> None:
    if value is None:
        raise KhipuConfigurationError(
            f"{name} must be a number of seconds; None (no timeout) is not allowed"
        )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise KhipuConfigurationError(
            f"{name} must be an int, a float or an httpx.Timeout, "
            f"not {type(value).__name__}"
        )
    if not _is_finite_positive(value):
        raise KhipuConfigurationError(
            f"{name} must be a finite number of seconds greater than zero"
        )


def _is_finite_positive(value: Union[int, float]) -> bool:
    try:
        seconds = float(value)
    except OverflowError:  # an int too large for a float
        return False
    return math.isfinite(seconds) and seconds > 0


def _parse_env_seconds(text: str, name: str) -> float:
    if not text.strip():
        raise KhipuConfigurationError(
            f"Environment variable {name} is set but empty; "
            "unset it to use the default timeout"
        )
    seconds = _parse_float(text)
    # Raised outside any except block so no parsing error, which would repeat
    # the variable's raw value, is chained to the configuration error.
    if seconds is None:
        raise KhipuConfigurationError(
            f"Environment variable {name} must be a number of seconds"
        )
    _validate_seconds(seconds, name)
    return seconds


def _parse_float(text: str) -> Optional[float]:
    try:
        return float(text)
    except ValueError:
        return None
