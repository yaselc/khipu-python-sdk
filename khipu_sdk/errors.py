"""Exception hierarchy for the Khipu SDK.

The taxonomy exists so a caller can tell apart outcomes that have very
different financial consequences. In particular, for ``create_instant_payment``
the caller MUST be able to distinguish:

* a definite response from Khipu (:class:`KhipuApiError`),
* a local input problem that never reached the network
  (:class:`KhipuValidationError`),
* an ambiguous network outcome where Khipu may or may not have accepted the
  request (:class:`KhipuTimeoutError`, and :class:`KhipuConnectionError` when
  ``request_may_have_been_delivered`` is true).

Every exception here is picklable so it survives Celery result backends and
multiprocessing boundaries. That is why each class sets ``self.args``
explicitly via ``super().__init__`` with exactly the positional arguments its
constructor takes -- ``Exception.__reduce__`` reconstructs from ``args``.
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    "KhipuError",
    "KhipuConfigurationError",
    "KhipuValidationError",
    "KhipuTransportError",
    "KhipuTimeoutError",
    "KhipuConnectionError",
    "KhipuApiError",
    "KhipuResponseError",
]

#: Upper bound applied to any response body embedded in an exception, so that a
#: large or hostile payload cannot flood logs.
MAX_BODY_CHARS = 500


def truncate(text: str, limit: int = MAX_BODY_CHARS) -> str:
    """Bound a textual payload for safe inclusion in an exception."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated, {len(text)} chars total]"


class KhipuError(Exception):
    """Base exception for all SDK errors."""


class KhipuConfigurationError(KhipuError):
    """The SDK is not usable as configured.

    Raised when the generated clients are missing from the installed
    distribution, or the configuration is structurally invalid. No HTTP request
    was attempted.
    """


class KhipuValidationError(KhipuError):
    """Client-side input was rejected before any HTTP request was made.

    Examples: an unsupported currency, a CLP amount with a fractional part, or
    an amount that cannot be interpreted as a decimal number.

    No request reached Khipu, so this outcome is never ambiguous.
    """


class KhipuTransportError(KhipuError):
    """A network-level failure: no HTTP response was received from Khipu.

    ``request_may_have_been_delivered`` reflects what the underlying transport
    can actually tell us. It is ``False`` only when the connection was never
    established (so the request provably did not reach Khipu) and ``True``
    otherwise. The SDK never claims certainty that httpx does not provide.
    """

    def __init__(
        self, message: str, request_may_have_been_delivered: bool = True
    ) -> None:
        super().__init__(message, request_may_have_been_delivered)
        self.message = message
        self.request_may_have_been_delivered = request_may_have_been_delivered

    def __str__(self) -> str:
        return self.message


class KhipuTimeoutError(KhipuTransportError):
    """A request timed out.

    For ``create_instant_payment`` this is an AMBIGUOUS outcome: Khipu may have
    created the payment. Do not blindly retry -- see the idempotency section of
    the README.
    """


class KhipuConnectionError(KhipuTransportError):
    """A connection-level failure (DNS, TCP connect, TLS, broken stream)."""


class KhipuApiError(KhipuError):
    """Khipu returned an HTTP response with a non-success status.

    This is a definite outcome: Khipu was reached and answered.

    ``payload`` holds the parsed JSON error body when Khipu sent one, and
    ``body`` holds a bounded textual copy of the raw body. Neither ever
    contains request headers or credentials.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        payload: Optional[Any] = None,
        body: Optional[str] = None,
    ) -> None:
        super().__init__(status_code, message, payload, body)
        self.status_code = status_code
        self.message = message
        self.payload = payload
        self.body = body

    def __str__(self) -> str:
        return f"Khipu API error {self.status_code}: {self.message}"


class KhipuResponseError(KhipuError):
    """Khipu returned a success status but the body could not be used.

    Covers malformed JSON and responses missing fields the API contract
    declares as required. This is deliberately NOT a :class:`KhipuApiError`:
    Khipu did not report an error, the SDK could not interpret the answer.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code, body)
        self.message = message
        self.status_code = status_code
        self.body = body

    def __str__(self) -> str:
        if self.status_code is None:
            return f"Malformed Khipu response: {self.message}"
        return f"Malformed Khipu response (HTTP {self.status_code}): {self.message}"
