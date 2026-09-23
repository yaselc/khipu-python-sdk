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
    """PAC subscription state from ``GET /v1/automatic-payment/subscription/{id}``.

    This is the only authoritative view of a subscription. Khipu's
    ``notify_url`` callback carries no signature, no token and no
    provider-authenticated field, so a callback claiming ``"enabled"`` is a
    hint to re-read this endpoint, never evidence on its own.

    ``subscription_id`` is an **opaque provider string**. Khipu's schema example
    shows a UUID, but the live API issues short mixed-case alphanumeric tokens;
    the SDK imposes no syntax on it.

    ``status`` is Khipu's own value, passed through as a plain string:
    ``PENDING`` before the customer signs the bank mandate, then ``SIGNED`` /
    ``ENABLED``, ``DISABLED``, or ``DISCARDED`` once the subscription has been
    unsubscribed. Only ``ENABLED`` permits a charge.

    ``service_reference`` comes back **empty** until the customer signs. ``""``
    is a value Khipu sent, not an absence, and the SDK never rewrites it to
    ``None``. Khipu's schema carries no ``customer_bank_code``; anything it
    sends that this type does not promote stays reachable through ``raw``.
    """

    subscription_id: str
    status: Optional[str] = None
    developer: Optional[bool] = None
    service_reference: Optional[str] = None
    raw: Optional[Any] = field(default=None, repr=False)


@dataclass(frozen=True)
class AutomaticChargeCreateResult:
    payment_id: str
    raw: Optional[Any] = field(default=None, repr=False)
