from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class KhipuConfig:
    api_key: str
    base_url: str = "https://payment-api.khipu.com"
    timeout: float = 10.0

    @classmethod
    def from_env(cls, prefix: str = "KHIPU_") -> "KhipuConfig":
        api_key = os.getenv(f"{prefix}API_KEY")
        if not api_key:
            raise ValueError(f"Missing environment variable: {prefix}API_KEY")

        base_url = os.getenv(f"{prefix}BASE_URL", cls.base_url)
        timeout_str = os.getenv(f"{prefix}TIMEOUT")
        timeout = float(timeout_str) if timeout_str else cls.timeout

        return cls(api_key=api_key, base_url=base_url, timeout=timeout)
