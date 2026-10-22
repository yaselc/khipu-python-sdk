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
from typing import Any, Optional

import httpx

from .config import KhipuConfig, validate_config
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
#: ``error_message`` is Khipu's own key on the ChargeError body returned with
#: a 422 charge rejection; ``error_code`` stays reachable via ``payload``.
_ERROR_MESSAGE_KEYS = (
    "message",
    "error_message",
    "error",
    "detail",
    "title",
    "description",
    "errors",
)

#: Success statuses the SDK accepts for ``POST /v1/automatic-payment/charge-intent``
#: *in addition to* the 201 Khipu documents today. Khipu's own specification said
#: 200 until its 2026-09 revision, so a merchant account still answering the older
#: contract must not lose a payment id Khipu did return.
#:
#: This list is deliberately closed. Every other 2xx is rejected, because a status
#: Khipu has never documented for this endpoint carries no promise that a charge
#: was created -- 202 Accepted most obviously means the opposite.
_CHARGE_SUCCESS_COMPATIBILITY_STATUSES: frozenset[int] = frozenset({200})

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
        # KhipuConfig validates itself on construction. Checking again here also
        # rejects an httpx.Timeout that was made unbounded afterwards, before
        # any httpx client is built.
        validate_config(config)
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

    def _invoke(self, endpoint: ModuleType, *, client: Any, **kwargs: Any) -> Any:
        """Send exactly one request through a generated endpoint and parse it.

        A generated ``sync_detailed`` is three steps: ``_get_kwargs`` builds the
        request, one ``request()`` on the client's httpx client sends it, and
        ``_build_response`` parses the body *before* returning. A parse failure in
        that last step therefore discards the ``httpx.Response`` with its status
        and body, which turned a 422 rejection with an incomplete ``ChargeError``
        into a "malformed success" and lost the ``payment_id`` of a create whose
        success body failed strict parsing (#42).

        The facade runs the same three steps itself so the response is still in
        hand when parsing fails. ``tests/unit/test_generated_endpoint_contract.py``
        pins the generated ``sync_detailed`` to that shape, so a generator change
        that adds a step fails CI instead of being silently bypassed.

        Every non-2xx status is classified here, before any generated parsing,
        as :class:`~khipu_sdk.errors.KhipuApiError`. No retry happens here or
        anywhere else in the SDK.
        """
        httpx_client = client.get_httpx_client()
        # ``httpx.Client.request`` is ``build_request`` followed by ``send``; the
        # split only separates local encoding failures from transport ones.
        try:
            request = httpx_client.build_request(**endpoint._get_kwargs(**kwargs))
        except Exception as exc:  # noqa: BLE001 - normalised into the SDK taxonomy
            # Encoding happens before anything is sent, so nothing reached Khipu.
            raise KhipuValidationError(
                f"Could not serialise the request payload: {type(exc).__name__}: {exc}"
            ) from exc

        try:
            response = httpx_client.send(request)
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

        status = int(response.status_code)
        text = self._decode_body(response)
        if not 200 <= status < 300:
            raise self._api_error(status, text)

        try:
            return endpoint._build_response(client=client, response=response)
        except _PARSE_FAILURES as exc:
            raise KhipuResponseError(
                f"Khipu returned a success status with a body the SDK could not "
                f"parse ({type(exc).__name__}: {exc})",
                status_code=status,
                body=truncate(text) if text else None,
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

    def _unwrap(
        self,
        result: Any,
        *,
        compatibility_model: Optional[Any] = None,
        compatibility_statuses: frozenset[int] = frozenset(),
    ) -> Any:
        """Return the parsed model, or raise the appropriate SDK exception.

        The generated clients parse only the exact success statuses Khipu's
        current document declares. Khipu has already changed one of them --
        ``POST /charge-intent`` moved from 200 to 201 -- so an endpoint may name
        a *closed set* of additional statuses it still accepts, together with the
        model to parse them with.

        That set is a compatibility allowance, never a blanket rule: a 2xx
        outside it is reported as :class:`~khipu_sdk.errors.KhipuResponseError`
        rather than being given the meaning of a documented success. A financial
        result is not inferred from a status code Khipu never documented for the
        endpoint. A body that cannot be parsed still raises, whatever its status.

        Only a 2xx response reaches this point: :meth:`_invoke` has already
        raised :class:`~khipu_sdk.errors.KhipuApiError` for every other status.
        """
        status = int(result.status_code)
        text = self._decode_body(result)

        parsed = getattr(result, "parsed", None)
        if (
            parsed is None
            and compatibility_model is not None
            and status in compatibility_statuses
            and text
        ):
            try:
                parsed = compatibility_model.from_dict(json.loads(text))
            except _PARSE_FAILURES:
                parsed = None

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
            endpoint, client=client, body=self._build_model(model_cls, payload)
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

        result = self._invoke(endpoint, client=client, id=payment_id)
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
        max_amount_per_charge: AmountInput,
        currency: str,
        notify_url: str,
        return_url: str,
        cancel_url: str,
        **extra_fields: Any,
    ) -> AutomaticSubscriptionCreateResult:
        """Create a PAC subscription (``POST /v1/automatic-payment/subscription``).

        ``max_amount`` caps what may be charged per month; Khipu also requires
        ``max_amount_per_charge``, the cap on a single charge, which it
        documents as not exceeding ``max_amount``. That relationship is Khipu's
        to enforce -- the SDK sends both and lets the provider answer -- but
        both are validated against the currency's minor-unit scale first.
        """
        client = self._require(self._automatic, name="Automatic Payments")
        currency = validate_currency(currency)
        normalized_max_amount = normalize_amount(max_amount, currency)
        normalized_max_amount_per_charge = normalize_amount(
            max_amount_per_charge, currency
        )

        payload: dict[str, Any] = {
            "name": name,
            "email": email,
            "max_amount": amount_to_wire(normalized_max_amount),
            "max_amount_per_charge": amount_to_wire(
                normalized_max_amount_per_charge
            ),
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
            endpoint, client=client, body=self._build_model(model_cls, payload)
        )
        parsed = self._unwrap(result)

        return AutomaticSubscriptionCreateResult(
            subscription_id=parsed.subscription_id,
            redirect_url=parsed.redirect_url,
            raw=parsed,
        )

    def get_subscription(self, *, subscription_id: str) -> AutomaticSubscriptionStatus:
        """Fetch a PAC subscription (``GET /v1/automatic-payment/subscription/{id}``).

        This authenticated read is the only trustworthy source for a mandate's
        state. The ``notify_url`` callback Khipu sends once the customer signs
        is unsigned and unauthenticated, so treat it as a trigger to call this
        method rather than as the answer.

        ``subscription_id`` is passed through verbatim: Khipu's ids are opaque
        provider tokens and the SDK validates no syntax against them.

        See :class:`~khipu_sdk.types.AutomaticSubscriptionStatus` for the
        status vocabulary and for what ``service_reference`` means before the
        customer signs.
        """
        client = self._require(self._automatic, name="Automatic Payments")
        endpoint = self._import_generated(
            "generated.automatic_payments.api.default.fetch_subscription_status_1"
        )

        result = self._invoke(endpoint, client=client, id=subscription_id)
        parsed = self._unwrap(result)

        return AutomaticSubscriptionStatus(
            subscription_id=parsed.subscription_id,
            status=_scalar(_field(parsed, "status")),
            developer=_field(parsed, "developer"),
            service_reference=_field(parsed, "service_reference"),
            raw=parsed,
        )

    def create_charge(
        self,
        *,
        subscription_id: str,
        amount: AmountInput,
        subject: str,
        error_response_url: str,
        notify_url: str,
        body: Optional[str] = None,
        custom: Optional[str] = None,
        transaction_id: Optional[str] = None,
        currency: Optional[str] = None,
        notify_api_version: Optional[str] = None,
        **extra_fields: Any,
    ) -> AutomaticChargeCreateResult:
        """Charge a PAC subscription (``POST /v1/automatic-payment/charge-intent``).

        ``error_response_url`` and ``notify_url`` are required by Khipu's
        ``ChargeRequest`` schema and are therefore required here.

        ``body``, ``custom`` and ``transaction_id`` are optional, matching the
        schema. Omitting one leaves the field out of the request entirely; the
        SDK never sends ``null`` and never invents a value. They remain the only
        merchant-side correlation and description fields Khipu echoes back, so an
        application that reconciles charges against its own records will want
        them -- but that is the application's policy to enforce, not a
        requirement the SDK imposes on every consumer.

        ``transaction_id`` is **not** an idempotency key. Khipu's ``ChargeError``
        vocabulary mentions ``IDEMPOTENCY_KEY_REUSED``, but the published
        ``ChargeRequest`` defines no idempotency field or header, so the SDK
        neither sends one nor treats any field as one. The no-retry policy
        described in this module's docstring is unchanged.

        The charge payload carries no currency -- it is inherited from the
        subscription -- so pass ``currency`` if you want the SDK to apply
        minor-unit validation to ``amount``. It is used for local validation
        only and is never sent to Khipu.

        ``notify_api_version`` selects the contract Khipu uses for the
        ``notify_url`` callback. It is optional, as in Khipu's schema, and the
        SDK chooses no default: a value is sent exactly as given and ``None``
        leaves the field out. An application that needs signed JSON
        notifications requests ``"3.0"`` explicitly.
        """
        client = self._require(self._automatic, name="Automatic Payments")
        if currency is not None:
            validate_currency(currency)
        normalized_amount = normalize_amount(amount, currency)

        payload: dict[str, Any] = {
            "subscription_id": subscription_id,
            "amount": amount_to_wire(normalized_amount),
            "subject": subject,
            "error_response_url": error_response_url,
            "notify_url": notify_url,
            **extra_fields,
        }
        for key, optional_value in (
            ("body", body),
            ("custom", custom),
            ("transaction_id", transaction_id),
            ("notify_api_version", notify_api_version),
        ):
            if optional_value is not None:
                payload[key] = optional_value

        endpoint = self._import_generated(
            "generated.automatic_payments.api.default.create_charge_1"
        )
        model_cls = self._import_generated(
            "generated.automatic_payments.models.charge_request"
        ).ChargeRequest
        result_cls = self._import_generated(
            "generated.automatic_payments.models.charge_result"
        ).ChargeResult

        result = self._invoke(
            endpoint, client=client, body=self._build_model(model_cls, payload)
        )
        parsed = self._unwrap(
            result,
            compatibility_model=result_cls,
            compatibility_statuses=_CHARGE_SUCCESS_COMPATIBILITY_STATUSES,
        )

        return AutomaticChargeCreateResult(payment_id=parsed.payment_id, raw=parsed)
