"""High-level Khipu client.

``KhipuClient`` is the only supported integration surface. It wraps the two
OpenAPI-generated clients (Instant Payments v3 and Automatic Payments v1) and
is responsible for three things the generated layer does not do:

1. validating money and currency *before* anything is serialised,
2. mapping every failure onto the SDK exception taxonomy in :mod:`khipu_sdk.errors`,
3. promoting the fields a caller needs onto stable result dataclasses.

The SDK performs **no retries**. Khipu publishes no idempotency key and no
lookup-by-``transaction_id`` endpoint, so an automatic retry of a create-payment
request could produce a second live payment. Retry policy is the caller's
decision; the exception taxonomy exists so that decision can be made correctly.
"""

from __future__ import annotations

import importlib
import json
import logging
from enum import Enum
from types import ModuleType
from typing import Any, Callable, Optional

import httpx

from .config import KhipuConfig
from .errors import (
    KhipuApiError,
    KhipuConfigurationError,
    KhipuConnectionError,
    KhipuResponseError,
    KhipuTimeoutError,
    KhipuValidationError,
    truncate,
)
from .money import AmountInput, amount_from_wire, amount_to_wire, normalize_amount, validate_currency
from .types import (
    AutomaticChargeCreateResult,
    AutomaticSubscriptionCreateResult,
    AutomaticSubscriptionStatus,
    InstantPaymentCreateResult,
    InstantPaymentStatus,
)

logger = logging.getLogger(__name__)

__all__ = ["KhipuClient"]

#: Transport failures where the connection was never established, so the
#: request provably did not reach Khipu. Everything else is treated as
#: ambiguous -- the SDK never claims certainty httpx does not provide.
_NOT_DELIVERED: tuple[type[Exception], ...] = (
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
    httpx.ConnectError,
    httpx.UnsupportedProtocol,
    httpx.LocalProtocolError,
)

#: Raised by the generated ``from_dict`` parsers when a success body is not
#: usable: malformed JSON (ValueError), a missing required field (KeyError), a
#: field of the wrong shape (TypeError/AttributeError) or an unparseable
#: timestamp.
_PARSE_FAILURES: tuple[type[Exception], ...] = (
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    OverflowError,
)

#: Keys Khipu uses for human-readable error text, in preference order.
_ERROR_MESSAGE_KEYS = ("message", "error", "detail", "title", "description", "errors")

_MISSING_GENERATED_HINT = (
    "The generated Khipu clients are not importable. This normally means the "
    "installed distribution is incomplete; reinstall the package, or run "
    "`make generate-all` in a source checkout."
)


def _scalar(value: Any) -> Any:
    """Unwrap a generated str-backed Enum into a plain ``str``."""
    if isinstance(value, Enum):
        return value.value
    return value


def _field(model: Any, name: str) -> Any:
    """Read a field from a generated model, mapping absent/``UNSET`` to ``None``."""
    value = getattr(model, name, None)
    if value is None or type(value).__name__ == "Unset":
        return None
    return value


class KhipuClient:
    """High-level Khipu SDK wrapper.

    Wraps the generated Instant Payments (v3) and Automatic Payments (v1/PAC)
    clients. Consuming applications should import only from ``khipu_sdk``.
    """

    def __init__(self, config: KhipuConfig):
        self._config = config
        self._instant = self._build_instant_client()
        self._automatic = self._build_automatic_client()

    def __repr__(self) -> str:
        # Never render the config or the generated clients: both hold the API key.
        return f"{type(self).__name__}(base_url={self._config.base_url!r})"

    @property
    def config(self) -> KhipuConfig:
        return self._config

    # ------------------------------------------------------------------
    # Generated client wiring
    # ------------------------------------------------------------------

    def _import_generated(self, module_path: str) -> ModuleType:
        try:
            return importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            if (exc.name or "").startswith("generated"):
                raise KhipuConfigurationError(
                    f"{_MISSING_GENERATED_HINT} (missing module: {exc.name})"
                ) from exc
            raise

    def _build_client(self, module_path: str) -> Any:
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            logger.debug("Generated client import failed for %s: %s", module_path, exc)
            return None
        return module.Client(
            base_url=self._config.base_url,
            headers={"x-api-key": self._config.api_key},
            timeout=self._config.timeout,
        )

    def _build_instant_client(self) -> Any:
        return self._build_client("generated.instant_payments.client")

    def _build_automatic_client(self) -> Any:
        return self._build_client("generated.automatic_payments.client")

    def _require(self, client: Any, *, name: str) -> Any:
        if client is None:
            raise KhipuConfigurationError(f"{name}: {_MISSING_GENERATED_HINT}")
        return client

    # ------------------------------------------------------------------
    # Request/response plumbing
    # ------------------------------------------------------------------

    def _build_model(self, model_cls: Any, payload: dict[str, Any]) -> Any:
        """Build a generated request model, reporting failures as client-side."""
        try:
            return model_cls.from_dict(payload)
        except Exception as exc:  # noqa: BLE001 - normalised into the SDK taxonomy
            raise KhipuValidationError(
                f"Could not build the {model_cls.__name__} request payload: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    def _invoke(self, endpoint: Callable[..., Any], **kwargs: Any) -> Any:
        """Call a generated endpoint, normalising transport/parse failures.

        No retry happens here or anywhere else in the SDK.
        """
        try:
            return endpoint(**kwargs)
        except httpx.TimeoutException as exc:
            raise KhipuTimeoutError(
                f"Request to Khipu timed out ({type(exc).__name__}: {exc})",
                request_may_have_been_delivered=not isinstance(exc, _NOT_DELIVERED),
            ) from exc
        except httpx.TransportError as exc:
            raise KhipuConnectionError(
                f"Could not reach Khipu ({type(exc).__name__}: {exc})",
                request_may_have_been_delivered=not isinstance(exc, _NOT_DELIVERED),
            ) from exc
        except _PARSE_FAILURES as exc:
            raise KhipuResponseError(
                f"Khipu returned a body the SDK could not parse "
                f"({type(exc).__name__}: {exc})"
            ) from exc

    @staticmethod
    def _decode_body(result: Any) -> str:
        content = getattr(result, "content", b"") or b""
        if isinstance(content, str):
            return content.strip()
        return content.decode("utf-8", errors="replace").strip()

    @staticmethod
    def _api_error(status: int, text: str) -> KhipuApiError:
        """Build a :class:`KhipuApiError` preserving Khipu's diagnostics safely.

        The body is parsed as JSON when possible and always truncated before it
        reaches the message. Request headers are never touched, so the API key
        cannot leak here.
        """
        payload: Optional[Any] = None
        if text:
            try:
                payload = json.loads(text)
            except ValueError:
                payload = None

        message: Optional[str] = None
        if isinstance(payload, dict):
            for key in _ERROR_MESSAGE_KEYS:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    message = value.strip()
                    break
            if message is None:
                message = truncate(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        elif text:
            message = truncate(text)
        else:
            message = f"HTTP {status} with an empty response body"

        return KhipuApiError(
            status_code=status,
            message=message,
            payload=payload,
            body=truncate(text) if text else None,
        )

    def _unwrap(self, result: Any) -> Any:
        """Return the parsed model, or raise the appropriate SDK exception."""
        status = int(result.status_code)
        text = self._decode_body(result)

        if not 200 <= status < 300:
            raise self._api_error(status, text)

        parsed = getattr(result, "parsed", None)
        if parsed is None:
            raise KhipuResponseError(
                "Khipu returned a success status with no usable body",
                status_code=status,
                body=truncate(text) if text else None,
            )
        return parsed

    # ------------------------------------------------------------------
    # Instant Payments (v3)
    # ------------------------------------------------------------------

    def create_instant_payment(
        self,
        *,
        amount: AmountInput,
        currency: str,
        subject: str,
        transaction_id: str,
        body: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        notify_url: Optional[str] = None,
        **extra_fields: Any,
    ) -> InstantPaymentCreateResult:
        """Create a payment (``POST /v3/payments``).

        ``amount`` should be a :class:`~decimal.Decimal`; ``int`` and ``str`` are
        also exact. It is validated against the currency's minor-unit scale
        before serialisation, so a fractional CLP amount can never be sent.

        ``transaction_id`` and ``custom`` are opaque merchant correlation
        fields, echoed back by :meth:`get_instant_payment`. **They are not
        idempotency keys**: Khipu documents no deduplication on them, and the
        SDK performs no duplicate protection and no automatic retry. A timeout
        here is an ambiguous outcome -- see :class:`~khipu_sdk.errors.KhipuTimeoutError`.
        """
        client = self._require(self._instant, name="Instant Payments")
        currency = validate_currency(currency)
        normalized_amount = normalize_amount(amount, currency)

        payload: dict[str, Any] = {
            "amount": amount_to_wire(normalized_amount),
            "currency": currency,
            "subject": subject,
            "transaction_id": transaction_id,
            **extra_fields,
        }
        for key, value in (
            ("body", body),
            ("return_url", return_url),
            ("cancel_url", cancel_url),
            ("notify_url", notify_url),
        ):
            if value is not None:
                payload[key] = value

        endpoint = self._import_generated("generated.instant_payments.api.default.post_payment")
        model_cls = self._import_generated(
            "generated.instant_payments.models.payment_post_payment"
        ).PaymentPostPayment

        result = self._invoke(
            endpoint.sync_detailed, client=client, body=self._build_model(model_cls, payload)
        )
        parsed = self._unwrap(result)

        return InstantPaymentCreateResult(
            payment_id=parsed.payment_id,
            payment_url=parsed.payment_url,
            simplified_transfer_url=parsed.simplified_transfer_url,
            transfer_url=parsed.transfer_url,
            app_url=parsed.app_url,
            ready_for_terminal=parsed.ready_for_terminal,
            raw=parsed,
        )

    def get_instant_payment(self, *, payment_id: str) -> InstantPaymentStatus:
        """Fetch a payment by its Khipu ``payment_id`` (``GET /v3/payments/{id}``).

        Lookup is by Khipu's identifier only; Khipu publishes no endpoint to
        find a payment by merchant ``transaction_id``.
        """
        client = self._require(self._instant, name="Instant Payments")
        endpoint = self._import_generated(
            "generated.instant_payments.api.default.get_payment_by_id"
        )

        result = self._invoke(endpoint.sync_detailed, id=payment_id, client=client)
        parsed = self._unwrap(result)

        return InstantPaymentStatus(
            payment_id=parsed.payment_id,
            transaction_id=_field(parsed, "transaction_id"),
            custom=_field(parsed, "custom"),
            status=_scalar(_field(parsed, "status")),
            status_detail=_scalar(_field(parsed, "status_detail")),
            amount=amount_from_wire(_field(parsed, "amount")),
            currency=_field(parsed, "currency"),
            receiver_id=_field(parsed, "receiver_id"),
            notification_token=_field(parsed, "notification_token"),
            expires_date=_field(parsed, "expires_date"),
            conciliation_date=_field(parsed, "conciliation_date"),
            out_of_date_conciliation=_field(parsed, "out_of_date_conciliation"),
            raw=parsed,
        )

    # ------------------------------------------------------------------
    # Automatic Payments (PAC, v1)
    # ------------------------------------------------------------------

    def create_subscription(
        self,
        *,
        name: str,
        email: str,
        max_amount: AmountInput,
        currency: str,
        notify_url: str,
        return_url: str,
        cancel_url: str,
        **extra_fields: Any,
    ) -> AutomaticSubscriptionCreateResult:
        """Create a PAC subscription (``POST /v1/automatic-payment/subscription``)."""
        client = self._require(self._automatic, name="Automatic Payments")
        currency = validate_currency(currency)
        normalized_max_amount = normalize_amount(max_amount, currency)

        payload: dict[str, Any] = {
            "name": name,
            "email": email,
            "max_amount": amount_to_wire(normalized_max_amount),
            "currency": currency,
            "notify_url": notify_url,
            "return_url": return_url,
            "cancel_url": cancel_url,
            **extra_fields,
        }

        endpoint = self._import_generated(
            "generated.automatic_payments.api.default.create_subscription_1"
        )
        model_cls = self._import_generated(
            "generated.automatic_payments.models.subscription_creation_request"
        ).SubscriptionCreationRequest

        result = self._invoke(
            endpoint.sync_detailed, client=client, body=self._build_model(model_cls, payload)
        )
        parsed = self._unwrap(result)

        return AutomaticSubscriptionCreateResult(
            subscription_id=parsed.subscription_id,
            redirect_url=parsed.redirect_url,
            raw=parsed,
        )

    def get_subscription(self, *, subscription_id: str) -> AutomaticSubscriptionStatus:
        """Fetch a PAC subscription (``GET /v1/automatic-payment/subscription/{id}``)."""
        client = self._require(self._automatic, name="Automatic Payments")
        endpoint = self._import_generated(
            "generated.automatic_payments.api.default.fetch_subscription_status_1"
        )

        result = self._invoke(endpoint.sync_detailed, id=subscription_id, client=client)
        parsed = self._unwrap(result)

        return AutomaticSubscriptionStatus(
            subscription_id=parsed.subscription_id,
            status=_scalar(_field(parsed, "status")),
            raw=parsed,
        )

    def create_charge(
        self,
        *,
        subscription_id: str,
        amount: AmountInput,
        subject: str,
        body: str,
        transaction_id: str,
        error_response_url: str,
        custom: str,
        notify_url: str,
        currency: Optional[str] = None,
        **extra_fields: Any,
    ) -> AutomaticChargeCreateResult:
        """Charge a PAC subscription (``POST /v1/automatic-payment/charge-intent``).

        ``error_response_url``, ``custom`` and ``notify_url`` are required by
        Khipu's ``ChargeRequest`` schema and are therefore required here.

        The charge payload carries no currency -- it is inherited from the
        subscription -- so pass ``currency`` if you want the SDK to apply
        minor-unit validation to ``amount``. It is used for local validation
        only and is never sent to Khipu.
        """
        client = self._require(self._automatic, name="Automatic Payments")
        if currency is not None:
            validate_currency(currency)
        normalized_amount = normalize_amount(amount, currency)

        payload: dict[str, Any] = {
            "subscription_id": subscription_id,
            "amount": amount_to_wire(normalized_amount),
            "subject": subject,
            "body": body,
            "transaction_id": transaction_id,
            "error_response_url": error_response_url,
            "custom": custom,
            "notify_url": notify_url,
            **extra_fields,
        }

        endpoint = self._import_generated(
            "generated.automatic_payments.api.default.create_charge_1"
        )
        model_cls = self._import_generated(
            "generated.automatic_payments.models.charge_request"
        ).ChargeRequest

        result = self._invoke(
            endpoint.sync_detailed, client=client, body=self._build_model(model_cls, payload)
        )
        parsed = self._unwrap(result)

        return AutomaticChargeCreateResult(payment_id=parsed.payment_id, raw=parsed)
