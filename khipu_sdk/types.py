"""Stable result types returned by :class:`~khipu_sdk.client.KhipuClient`.

These dataclasses are the supported integration surface. They carry every field
a consuming application needs in order to correlate and verify a payment, so
callers never have to import generated ``attrs`` model classes.

``raw`` is kept only as an escape hatch for fields the facade does not promote.
It is excluded from ``repr`` because the underlying Khipu payment model carries
payer PII (name, email, personal identifier, bank account number) that must not
end up in logs or error reports by accident.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

__all__ = [
    "InstantPaymentCreateResult",
    "InstantPaymentStatus",
    "AutomaticSubscriptionCreateResult",
    "AutomaticSubscriptionStatus",
    "AutomaticChargeCreateResult",
]


@dataclass(frozen=True)
class InstantPaymentCreateResult:
    """Everything Khipu returns from ``POST /v3/payments``.

    Khipu's create response carries no status, amount, currency, expiry or
    merchant reference; those are only available from
    :meth:`~khipu_sdk.client.KhipuClient.get_instant_payment`. This type
    deliberately does not pretend otherwise.
    """

    payment_id: str
    payment_url: str
    simplified_transfer_url: str
    transfer_url: str
    app_url: str
    ready_for_terminal: bool
    raw: Optional[Any] = field(default=None, repr=False)


@dataclass(frozen=True)
class InstantPaymentStatus:
    """Payment state from ``GET /v3/payments/{id}``.

    ``status`` is one of ``pending``, ``verifying`` or ``done``.
    ``status_detail`` refines it and is the field that reveals a reversal:
    ``status == "done"`` together with ``status_detail == "reversed"`` means the
    money was returned to the payer. The SDK surfaces that fact and leaves the
    policy decision to the caller.
    """

    payment_id: str
    transaction_id: Optional[str] = None
    custom: Optional[str] = None
    status: Optional[str] = None
    status_detail: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    receiver_id: Optional[int] = None
    notification_token: Optional[str] = None
    expires_date: Optional[dt.datetime] = None
    conciliation_date: Optional[dt.datetime] = None
    out_of_date_conciliation: Optional[bool] = None
    raw: Optional[Any] = field(default=None, repr=False)


@dataclass(frozen=True)
class AutomaticSubscriptionCreateResult:
    subscription_id: str
    redirect_url: str
    raw: Optional[Any] = field(default=None, repr=False)


@dataclass(frozen=True)
class AutomaticSubscriptionStatus:
    subscription_id: str
    status: Optional[str] = None
    raw: Optional[Any] = field(default=None, repr=False)


@dataclass(frozen=True)
class AutomaticChargeCreateResult:
    payment_id: str
    raw: Optional[Any] = field(default=None, repr=False)
