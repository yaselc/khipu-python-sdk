"""``**extra_fields`` on the three create methods, over the real HTTP boundary.

F5 of #41. ``create_instant_payment``, ``create_subscription`` and
``create_charge`` accept ``**extra_fields`` as a compatibility escape hatch.
These tests pin what actually reaches the JSON body, in two layers:

* The handwritten wrapper merges ``extra_fields`` into the payload verbatim.
  It does not validate, convert, rename or drop them.
* The generated request model (``from_dict``/``to_dict``) routes a key it
  declares through its typed attribute and keeps every other key in
  ``additional_properties``, which ``to_dict`` serialises as a top-level key.

So a recognized field is sent under its declared name, and an unknown or
misspelled key is *not* omitted by the SDK: it is sent verbatim and raises
nothing. Whether Khipu accepts, ignores or rejects such a key is provider
behavior the SDK cannot see. The unknown-key tests are characterization tests
of the current behavior, not a promise that it is desirable; they exist so a
change to it is a deliberate decision.
"""

from __future__ import annotations

import datetime
import inspect
import json
from decimal import Decimal
from typing import Any

import attrs
import pytest

from khipu_sdk import KhipuClient, KhipuConfig, KhipuValidationError

BASE_URL = "https://payment-api.khipu.com"
PAYMENTS_URL = f"{BASE_URL}/v3/payments"
SUBSCRIPTION_URL = f"{BASE_URL}/v1/automatic-payment/subscription"
CHARGE_URL = f"{BASE_URL}/v1/automatic-payment/charge-intent"
API_KEY = "unit-test-api-key"

PAYMENT_CREATED = {
    "payment_id": "gqzdy6chjne9",
    "payment_url": "https://khipu.com/payment/info/gqzdy6chjne9",
    "simplified_transfer_url": "https://app.khipu.com/payment/simplified/gqzdy6chjne9",
    "transfer_url": "https://khipu.com/payment/manual/gqzdy6chjne9",
    "app_url": "khipu:///pos/gqzdy6chjne9",
    "ready_for_terminal": False,
}
SUBSCRIPTION_CREATED = {
    "subscription_id": "sub-1",
    "redirect_url": "https://khipu.com/pac/redirect/sub-1",
}
CHARGE_CREATED = {"payment_id": "charge-1"}

PAYMENT_BASE = {
    "amount": 10000,
    "currency": "CLP",
    "subject": "Order 123",
    "transaction_id": "ORDER-123",
}
SUBSCRIPTION_BASE = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "max_amount": 50000,
    "max_amount_per_charge": 20000,
    "currency": "CLP",
    "notify_url": "https://example.com/pac/notify",
    "return_url": "https://example.com/pac/return",
    "cancel_url": "https://example.com/pac/cancel",
}
CHARGE_BASE = {
    "subscription_id": "sub-1",
    "amount": 20000,
    "subject": "Monthly fee",
    "error_response_url": "https://example.com/pac/error",
    "notify_url": "https://example.com/pac/notify",
}


@pytest.fixture
def client() -> KhipuClient:
    return KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL))


def create_payment(client: KhipuClient, **extra_fields: Any):
    return client.create_instant_payment(
        amount=Decimal("10000"),
        currency="CLP",
        subject="Order 123",
        transaction_id="ORDER-123",
        **extra_fields,
    )


def create_subscription(client: KhipuClient, **extra_fields: Any):
    return client.create_subscription(
        name="Jane Doe",
        email="jane@example.com",
        max_amount=Decimal("50000"),
        max_amount_per_charge=Decimal("20000"),
        currency="CLP",
        notify_url="https://example.com/pac/notify",
        return_url="https://example.com/pac/return",
        cancel_url="https://example.com/pac/cancel",
        **extra_fields,
    )


def create_charge(client: KhipuClient, **extra_fields: Any):
    return client.create_charge(
        subscription_id="sub-1",
        amount=Decimal("20000"),
        currency="CLP",
        subject="Monthly fee",
        error_response_url="https://example.com/pac/error",
        notify_url="https://example.com/pac/notify",
        **extra_fields,
    )


def sent_json(httpx_mock) -> dict[str, Any]:
    """The JSON object of the single request sent, decoded from the raw body."""
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.headers["content-type"] == "application/json"
    body = json.loads(request.content)
    assert isinstance(body, dict)
    return body


# Each create method, with the response it needs, its minimal wire body and the
# URL it posts to, so behavior shared by all three is checked on each of them.
OPERATIONS = {
    "instant_payment": (create_payment, PAYMENTS_URL, 200, PAYMENT_CREATED, PAYMENT_BASE),
    "subscription": (
        create_subscription,
        SUBSCRIPTION_URL,
        200,
        SUBSCRIPTION_CREATED,
        SUBSCRIPTION_BASE,
    ),
    "charge": (create_charge, CHARGE_URL, 201, CHARGE_CREATED, CHARGE_BASE),
}


@pytest.fixture(params=sorted(OPERATIONS))
def operation(request):
    return OPERATIONS[request.param]


class TestSignatures:
    @pytest.mark.parametrize(
        "method", ["create_instant_payment", "create_subscription", "create_charge"]
    )
    def test_extra_fields_catchall_is_kept(self, method):
        parameters = inspect.signature(getattr(KhipuClient, method)).parameters

        assert parameters["extra_fields"].kind is inspect.Parameter.VAR_KEYWORD

    def test_custom_is_not_an_explicit_instant_payment_parameter(self):
        """Instant Payments ``custom`` goes through ``extra_fields`` (documented)."""
        parameters = inspect.signature(KhipuClient.create_instant_payment).parameters

        assert "custom" not in parameters

    def test_every_charge_request_field_is_an_explicit_parameter(self):
        """The README says ``extra_fields`` on ``create_charge`` only carries
        fields ``ChargeRequest`` does not declare. If the spec grows a field,
        this fails so that statement is revisited."""
        from khipu_sdk._generated.automatic_payments.models.charge_request import ChargeRequest

        declared = {f.name for f in attrs.fields(ChargeRequest)} - {"additional_properties"}
        parameters = set(inspect.signature(KhipuClient.create_charge).parameters)

        assert declared <= parameters


class TestRecognizedFields:
    def test_instant_payment_custom_is_serialised_as_a_string(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        result = create_payment(client, custom="order=123;cart=42")

        assert result.payment_id == "gqzdy6chjne9"
        assert sent_json(httpx_mock) == {**PAYMENT_BASE, "custom": "order=123;cart=42"}

    def test_instant_payment_custom_and_transaction_id_are_independent(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, custom="<cart><item sku='A1'/></cart>")

        body = sent_json(httpx_mock)
        assert body["transaction_id"] == "ORDER-123"
        assert body["custom"] == "<cart><item sku='A1'/></cart>"

    def test_omitting_custom_sends_no_custom_key(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client)

        assert sent_json(httpx_mock) == PAYMENT_BASE

    def test_other_declared_instant_payment_fields(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(
            client,
            bank_id="SDdGj",
            payer_email="payer@example.com",
            send_email=True,
            notify_api_version="3.0",
        )

        assert sent_json(httpx_mock) == {
            **PAYMENT_BASE,
            "bank_id": "SDdGj",
            "payer_email": "payer@example.com",
            "send_email": True,
            "notify_api_version": "3.0",
        }

    def test_subscription_declared_fields(self, client, httpx_mock):
        httpx_mock.add_response(url=SUBSCRIPTION_URL, json=SUBSCRIPTION_CREATED)
        result = create_subscription(
            client,
            service_reference="CONTRACT-77",
            description="Monthly plan",
            image_url="https://example.com/logo.png",
        )

        assert result.subscription_id == "sub-1"
        assert sent_json(httpx_mock) == {
            **SUBSCRIPTION_BASE,
            "service_reference": "CONTRACT-77",
            "description": "Monthly plan",
            "image_url": "https://example.com/logo.png",
        }

    def test_charge_custom_is_serialised_through_its_explicit_parameter(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        result = create_charge(client, custom="INVOICE-2026-0001")

        assert result.payment_id == "charge-1"
        assert sent_json(httpx_mock) == {**CHARGE_BASE, "custom": "INVOICE-2026-0001"}


class TestUnknownAndMisspelledKeys:
    """Characterization: the SDK forwards undeclared keys verbatim and raises
    nothing. A typo therefore does not set the field it was meant for."""

    @pytest.mark.parametrize("key", ["costum", "Custom", "transactionId", "x_merchant_ref"])
    def test_undeclared_key_is_sent_verbatim(self, client, httpx_mock, operation, key):
        create, url, status, response, base = operation
        httpx_mock.add_response(url=url, status_code=status, json=response)
        create(client, **{key: "value-1"})

        assert sent_json(httpx_mock) == {**base, key: "value-1"}

    def test_a_misspelled_custom_does_not_set_custom(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, costum="order=123")

        body = sent_json(httpx_mock)
        assert "custom" not in body
        assert body["costum"] == "order=123"

    def test_a_misspelled_subscription_field_does_not_set_the_field(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(url=SUBSCRIPTION_URL, json=SUBSCRIPTION_CREATED)
        create_subscription(client, service_refrence="CONTRACT-77")

        body = sent_json(httpx_mock)
        assert "service_reference" not in body
        assert body["service_refrence"] == "CONTRACT-77"

    def test_a_misspelled_charge_field_does_not_set_the_field(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        create_charge(client, transacion_id="INVOICE-1")

        body = sent_json(httpx_mock)
        assert "transaction_id" not in body
        assert body["transacion_id"] == "INVOICE-1"

    def test_a_misspelled_explicit_parameter_becomes_an_extra_field(
        self, client, httpx_mock
    ):
        """The catch-all also swallows typos of explicit parameters."""
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, return_ulr="https://example.com/return")

        body = sent_json(httpx_mock)
        assert "return_url" not in body
        assert body["return_ulr"] == "https://example.com/return"

    def test_non_string_values_are_sent_as_their_json_type(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, x_meta={"a": [1, 2]}, x_flag=False, x_none=None)

        assert sent_json(httpx_mock) == {
            **PAYMENT_BASE,
            "x_meta": {"a": [1, 2]},
            "x_flag": False,
            "x_none": None,
        }


class TestWrapperDoesNotConvertValues:
    """The wrapper passes ``extra_fields`` values through unchanged; only the
    generated model's own parsing and JSON encoding apply to them."""

    def test_wrong_type_for_a_declared_field_is_sent_unchanged(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, custom=123, send_email="yes")

        body = sent_json(httpx_mock)
        assert body["custom"] == 123
        assert body["send_email"] == "yes"

    def test_none_for_a_declared_extra_field_is_sent_as_null(self, client, httpx_mock):
        """Unlike the explicit optional parameters, which omit ``None``."""
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, custom=None, body=None)

        body = sent_json(httpx_mock)
        assert body["custom"] is None
        assert "body" not in body

    def test_declared_date_time_field_accepts_an_iso_8601_string(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, expires_date="2026-12-31T15:45:00-04:00")

        assert sent_json(httpx_mock)["expires_date"] == "2026-12-31T15:45:00-04:00"

    def test_declared_date_time_field_rejects_a_datetime_object(self, client, httpx_mock):
        expires = datetime.datetime(2026, 12, 31, 15, 45, tzinfo=datetime.timezone.utc)

        with pytest.raises(KhipuValidationError, match="PaymentPostPayment"):
            create_payment(client, expires_date=expires)
        assert httpx_mock.get_requests() == []

    @pytest.mark.parametrize(
        "value", [Decimal("1.5"), datetime.datetime(2026, 1, 1), {1, 2}]
    )
    def test_non_json_value_is_rejected_before_sending(
        self, client, httpx_mock, operation, value
    ):
        create = operation[0]

        with pytest.raises(KhipuValidationError, match="serialise"):
            create(client, x_extra=value)
        assert httpx_mock.get_requests() == []


class TestPrecedenceAndMoneySafety:
    @pytest.mark.parametrize(
        ("create", "key"),
        [
            (create_payment, "amount"),
            (create_payment, "currency"),
            (create_payment, "transaction_id"),
            (create_subscription, "max_amount"),
            (create_subscription, "max_amount_per_charge"),
            (create_subscription, "currency"),
            (create_charge, "amount"),
            (create_charge, "currency"),
            (create_charge, "subject"),
        ],
    )
    def test_a_named_parameter_cannot_be_overridden(self, client, httpx_mock, create, key):
        """Python binds every named parameter, so ``extra_fields`` can never
        carry one and bypass amount or currency validation."""
        with pytest.raises(TypeError, match="multiple values"):
            create(client, **{key: "999"})
        assert httpx_mock.get_requests() == []

    def test_case_variants_do_not_replace_the_validated_amount(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=PAYMENT_CREATED)
        create_payment(client, Amount=1, CURRENCY="USD")

        body = sent_json(httpx_mock)
        assert body["amount"] == 10000
        assert body["currency"] == "CLP"
        assert body["Amount"] == 1
        assert body["CURRENCY"] == "USD"

    def test_charge_currency_stays_local_only(self, client, httpx_mock):
        """``currency`` validates the amount locally and is never sent; an
        undeclared look-alike is forwarded but does not change validation."""
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        create_charge(client, currency_code="USD")

        body = sent_json(httpx_mock)
        assert "currency" not in body
        assert body["currency_code"] == "USD"
        assert body["amount"] == 20000

    def test_fractional_clp_is_still_rejected_with_extra_fields(self, client, httpx_mock):
        with pytest.raises(KhipuValidationError):
            client.create_instant_payment(
                amount=Decimal("10000.5"),
                currency="CLP",
                subject="Order 123",
                transaction_id="ORDER-123",
                custom="order=123",
            )
        assert httpx_mock.get_requests() == []


class TestGeneratedModelRouting:
    """What the generated model does with the payload the wrapper builds."""

    @pytest.mark.parametrize(
        ("module", "name", "base", "declared"),
        [
            (
                "khipu_sdk._generated.instant_payments.models.payment_post_payment",
                "PaymentPostPayment",
                PAYMENT_BASE,
                "custom",
            ),
            (
                "khipu_sdk._generated.automatic_payments.models.subscription_creation_request",
                "SubscriptionCreationRequest",
                SUBSCRIPTION_BASE,
                "service_reference",
            ),
            (
                "khipu_sdk._generated.automatic_payments.models.charge_request",
                "ChargeRequest",
                CHARGE_BASE,
                "custom",
            ),
        ],
    )
    def test_declared_keys_are_attributes_and_others_are_additional(
        self, module, name, base, declared
    ):
        import importlib

        model_cls = getattr(importlib.import_module(module), name)
        model = model_cls.from_dict({**base, declared: "known", "costum": "unknown"})

        assert getattr(model, declared) == "known"
        assert model.additional_properties == {"costum": "unknown"}
        assert model.to_dict() == {**base, declared: "known", "costum": "unknown"}
