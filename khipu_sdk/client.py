from __future__ import annotations

import logging
from typing import Any, Optional

from .config import KhipuConfig
from .errors import KhipuApiError
from .types import (
    AutomaticChargeCreateResult,
    AutomaticSubscriptionCreateResult,
    AutomaticSubscriptionStatus,
    InstantPaymentCreateResult,
    InstantPaymentStatus,
)

logger = logging.getLogger(__name__)


class KhipuClient:
    """High-level Khipu SDK wrapper.

    This class wraps two OpenAPI-generated clients:
    - Instant Payments API (v3)
    - Automatic Payments API (v1 / PAC)

    Generated clients are expected under:
    - generated/instant_payments/
    - generated/automatic_payments/

    The SDK layer is the only supported integration surface for your Django app.
    """

    def __init__(self, config: KhipuConfig):
        self._config = config
        self._instant = self._build_instant_client()
        self._automatic = self._build_automatic_client()

    @property
    def config(self) -> KhipuConfig:
        return self._config

    # ---------------------------------------------------------------------
    # Client builders
    # ---------------------------------------------------------------------

    def _build_instant_client(self):
        try:
            from generated.instant_payments.client import Client as InstantClient  # type: ignore
        except ModuleNotFoundError as exc:
            logger.debug("Instant Payments generated client import failed: %s", exc)
            return None

        # NOTE: openapi-python-client's Client signature can vary depending on config.
        # This is a sensible default. Adjust only this SDK layer if needed.
        return InstantClient(
            base_url=self._config.base_url,
            headers={
                "x-api-key": self._config.api_key,
            },
            timeout=self._config.timeout,
        )

    def _build_automatic_client(self):
        try:
            from generated.automatic_payments.client import Client as AutomaticClient  # type: ignore
        except ModuleNotFoundError as exc:
            logger.debug("Automatic Payments generated client import failed: %s", exc)
            return None

        return AutomaticClient(
            base_url=self._config.base_url,
            headers={
                "x-api-key": self._config.api_key,
            },
            timeout=self._config.timeout,
        )

    def _require(self, client: Any, *, name: str) -> Any:
        if client is None:
            raise KhipuApiError(
                status_code=500,
                message=(
                    f"{name} generated client is not available. "
                    "Run `make generate-all` (requires openapi-python-client)."
                ),
            )
        return client

    # ---------------------------------------------------------------------
    # Instant Payments
    # ---------------------------------------------------------------------

    def create_instant_payment(
        self,
        *,
        amount: float,
        currency: str,
        subject: str,
        transaction_id: str,
        body: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        notify_url: Optional[str] = None,
        **extra_fields: Any,
    ) -> InstantPaymentCreateResult:
        client = self._require(self._instant, name="Instant Payments")

        payload: dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "subject": subject,
            "transaction_id": transaction_id,
            **extra_fields,
        }
        if body is not None:
            payload["body"] = body
        if return_url is not None:
            payload["return_url"] = return_url
        if cancel_url is not None:
            payload["cancel_url"] = cancel_url
        if notify_url is not None:
            payload["notify_url"] = notify_url

        try:
            from generated.instant_payments.api.payments import post_v3_payments  # type: ignore
            from generated.instant_payments.models.payment_post_payment import PaymentPostPayment  # type: ignore

            result = post_v3_payments.sync_detailed(
                client=client,
                body=PaymentPostPayment.from_dict(payload),
            )
        except ModuleNotFoundError as exc:
            if str(exc).startswith("No module named 'generated."):
                raise KhipuApiError(
                    status_code=500,
                    message=(
                        "Generated client code is missing or incomplete. "
                        "Run `make generate-all` to regenerate the clients."
                    ),
                ) from exc
            raise
        except Exception as exc:
            raise KhipuApiError(status_code=500, message=str(exc)) from exc

        if not getattr(result, "parsed", None):
            raise KhipuApiError(status_code=getattr(result, "status_code", 500), message="Empty response")

        parsed = result.parsed
        return InstantPaymentCreateResult(
            payment_id=getattr(parsed, "payment_id"),
            payment_url=getattr(parsed, "payment_url"),
            status=getattr(parsed, "status", None),
            raw=parsed,
        )

    def get_instant_payment(self, *, payment_id: str) -> InstantPaymentStatus:
        client = self._require(self._instant, name="Instant Payments")

        try:
            from generated.instant_payments.api.payments import get_v3_payments_id  # type: ignore

            result = get_v3_payments_id.sync_detailed(
                id=payment_id,
                client=client,
            )
        except ModuleNotFoundError as exc:
            if str(exc).startswith("No module named 'generated."):
                raise KhipuApiError(
                    status_code=500,
                    message=(
                        "Generated client code is missing or incomplete. "
                        "Run `make generate-all` to regenerate the clients."
                    ),
                ) from exc
            raise
        except Exception as exc:
            raise KhipuApiError(status_code=500, message=str(exc)) from exc

        if not getattr(result, "parsed", None):
            raise KhipuApiError(status_code=getattr(result, "status_code", 500), message="Empty response")

        parsed = result.parsed
        return InstantPaymentStatus(
            payment_id=getattr(parsed, "payment_id"),
            status=getattr(parsed, "status", None),
            amount=getattr(parsed, "amount", None),
            currency=getattr(parsed, "currency", None),
            raw=parsed,
        )

    # ---------------------------------------------------------------------
    # Automatic Payments (PAC)
    # ---------------------------------------------------------------------

    def create_subscription(
        self,
        *,
        name: str,
        email: str,
        max_amount: float,
        currency: str,
        notify_url: str,
        return_url: str,
        cancel_url: str,
        **extra_fields: Any,
    ) -> AutomaticSubscriptionCreateResult:
        client = self._require(self._automatic, name="Automatic Payments")

        payload: dict[str, Any] = {
            "name": name,
            "email": email,
            "max_amount": max_amount,
            "currency": currency,
            "notify_url": notify_url,
            "return_url": return_url,
            "cancel_url": cancel_url,
            **extra_fields,
        }

        try:
            from generated.automatic_payments.api.automatic_payment import post_v1_automatic_payment_subscription  # type: ignore
            from generated.automatic_payments.models.subscription_creation_request import SubscriptionCreationRequest  # type: ignore

            result = post_v1_automatic_payment_subscription.sync_detailed(
                client=client,
                body=SubscriptionCreationRequest.from_dict(payload),
            )
        except ModuleNotFoundError as exc:
            if str(exc).startswith("No module named 'generated."):
                raise KhipuApiError(
                    status_code=500,
                    message=(
                        "Generated client code is missing or incomplete. "
                        "Run `make generate-all` to regenerate the clients."
                    ),
                ) from exc
            raise
        except Exception as exc:
            raise KhipuApiError(status_code=500, message=str(exc)) from exc

        if not getattr(result, "parsed", None):
            raise KhipuApiError(status_code=getattr(result, "status_code", 500), message="Empty response")

        parsed = result.parsed
        return AutomaticSubscriptionCreateResult(
            subscription_id=getattr(parsed, "subscription_id"),
            redirect_url=getattr(parsed, "redirect_url"),
            raw=parsed,
        )

    def get_subscription(self, *, subscription_id: str) -> AutomaticSubscriptionStatus:
        client = self._require(self._automatic, name="Automatic Payments")

        try:
            from generated.automatic_payments.api.automatic_payment import get_v1_automatic_payment_subscription_id  # type: ignore

            result = get_v1_automatic_payment_subscription_id.sync_detailed(
                id=subscription_id,
                client=client,
            )
        except ModuleNotFoundError as exc:
            if str(exc).startswith("No module named 'generated."):
                raise KhipuApiError(
                    status_code=500,
                    message=(
                        "Generated client code is missing or incomplete. "
                        "Run `make generate-all` to regenerate the clients."
                    ),
                ) from exc
            raise
        except Exception as exc:
            raise KhipuApiError(status_code=500, message=str(exc)) from exc

        if not getattr(result, "parsed", None):
            raise KhipuApiError(status_code=getattr(result, "status_code", 500), message="Empty response")

        parsed = result.parsed
        return AutomaticSubscriptionStatus(
            subscription_id=getattr(parsed, "subscription_id"),
            status=getattr(parsed, "status", None),
            raw=parsed,
        )

    def create_charge(
        self,
        *,
        subscription_id: str,
        amount: float,
        subject: str,
        body: str,
        transaction_id: str,
        **extra_fields: Any,
    ) -> AutomaticChargeCreateResult:
        client = self._require(self._automatic, name="Automatic Payments")

        payload: dict[str, Any] = {
            "subscription_id": subscription_id,
            "amount": amount,
            "subject": subject,
            "body": body,
            "transaction_id": transaction_id,
            **extra_fields,
        }

        try:
            from generated.automatic_payments.api.automatic_payment import post_v1_automatic_payment_charge_intent  # type: ignore
            from generated.automatic_payments.models.charge_request import ChargeRequest  # type: ignore

            result = post_v1_automatic_payment_charge_intent.sync_detailed(
                client=client,
                body=ChargeRequest.from_dict(payload),
            )
        except ModuleNotFoundError as exc:
            if str(exc).startswith("No module named 'generated."):
                raise KhipuApiError(
                    status_code=500,
                    message=(
                        "Generated client code is missing or incomplete. "
                        "Run `make generate-all` to regenerate the clients."
                    ),
                ) from exc
            raise
        except Exception as exc:
            raise KhipuApiError(status_code=500, message=str(exc)) from exc

        if not getattr(result, "parsed", None):
            raise KhipuApiError(status_code=getattr(result, "status_code", 500), message="Empty response")

        parsed = result.parsed
        return AutomaticChargeCreateResult(
            payment_id=getattr(parsed, "payment_id"),
            raw=parsed,
        )
