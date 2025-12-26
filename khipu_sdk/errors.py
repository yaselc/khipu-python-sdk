from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class KhipuError(Exception):
    """Base exception for all SDK errors."""


@dataclass(frozen=True)
class KhipuApiError(KhipuError):
    """Raised when the underlying generated client fails or Khipu returns an API error."""

    status_code: int
    message: str
    payload: Optional[Any] = None

    def __str__(self) -> str:
        return f"Khipu API error {self.status_code}: {self.message}"
