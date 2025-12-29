from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class InstantPaymentCreateResult:
    payment_id: str
    payment_url: str
    status: Optional[str] = None
    raw: Optional[Any] = None


@dataclass(frozen=True)
class InstantPaymentStatus:
    payment_id: str
    status: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    raw: Optional[Any] = None


@dataclass(frozen=True)
class AutomaticSubscriptionCreateResult:
    subscription_id: str
    redirect_url: str
    raw: Optional[Any] = None


@dataclass(frozen=True)
class AutomaticSubscriptionStatus:
    subscription_id: str
    status: Optional[str] = None
    raw: Optional[Any] = None


@dataclass(frozen=True)
class AutomaticChargeCreateResult:
    payment_id: str
    raw: Optional[Any] = None
