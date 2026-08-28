"""Python SDK for the Khipu Instant Payments (v3) and Automatic Payments (v1) APIs.

Everything a consuming application needs is exported here. Importing from
``khipu_sdk.client``, ``khipu_sdk.errors`` etc. also works, but importing from
``generated.*`` is not supported.
"""

from .client import KhipuClient
from .config import KhipuConfig
from .errors import (
    KhipuApiError,
    KhipuConfigurationError,
    KhipuConnectionError,
    KhipuError,
    KhipuResponseError,
    KhipuTimeoutError,
    KhipuTransportError,
    KhipuValidationError,
)
from .money import CURRENCY_MINOR_UNITS, SUPPORTED_CURRENCIES
from .types import (
    AutomaticChargeCreateResult,
    AutomaticSubscriptionCreateResult,
    AutomaticSubscriptionStatus,
    InstantPaymentCreateResult,
    InstantPaymentStatus,
)

__all__ = [
    # Client and configuration
    "KhipuClient",
    "KhipuConfig",
    # Exception taxonomy
    "KhipuError",
    "KhipuConfigurationError",
    "KhipuValidationError",
    "KhipuTransportError",
    "KhipuTimeoutError",
    "KhipuConnectionError",
    "KhipuApiError",
    "KhipuResponseError",
    # Result types
    "InstantPaymentCreateResult",
    "InstantPaymentStatus",
    "AutomaticSubscriptionCreateResult",
    "AutomaticSubscriptionStatus",
    "AutomaticChargeCreateResult",
    # Money helpers
    "CURRENCY_MINOR_UNITS",
    "SUPPORTED_CURRENCIES",
]
