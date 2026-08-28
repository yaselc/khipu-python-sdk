from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Union

import httpx

__all__ = ["KhipuConfig"]

#: A single float applies to httpx's connect, read, write and pool phases.
#: Pass an ``httpx.Timeout`` to control them independently.
TimeoutValue = Union[float, httpx.Timeout]


@dataclass(frozen=True)
class KhipuConfig:
    """Connection settings for :class:`~khipu_sdk.client.KhipuClient`.

    ``api_key`` is excluded from ``repr`` so the credential cannot leak through
    logging, Sentry local-variable capture or a Django debug page.
    """

    api_key: str = field(repr=False)
    base_url: str = "https://payment-api.khipu.com"
    #: Never ``None``: an unbounded timeout would let a stalled Khipu request
    #: pin a worker indefinitely.
    timeout: TimeoutValue = 10.0

    @classmethod
    def from_env(cls, prefix: str = "KHIPU_") -> "KhipuConfig":
        api_key = os.getenv(f"{prefix}API_KEY")
        if not api_key:
            raise ValueError(f"Missing environment variable: {prefix}API_KEY")

        base_url = os.getenv(f"{prefix}BASE_URL", cls.base_url)
        timeout_str = os.getenv(f"{prefix}TIMEOUT")
        timeout: TimeoutValue = float(timeout_str) if timeout_str else cls.timeout

        return cls(api_key=api_key, base_url=base_url, timeout=timeout)
