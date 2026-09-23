"""Automatic Payments (PAC) facade tests over the real HTTP boundary.

Replaces the previous ``SimpleNamespace``-based tests, which stubbed out
``sync_detailed`` and therefore hid the ``create_charge`` signature defect: the
generated ``ChargeRequest`` requires ``error_response_url``, ``custom`` and
``notify_url``, and the old tests smuggled them through ``**extra_fields``.
These tests call the public documented signature only.
"""

from __future__ import annotations

import inspect
import json
from decimal import Decimal

import pytest

from khipu_sdk import (
    KhipuApiError,
    KhipuClient,
    KhipuConfig,
    KhipuResponseError,
    KhipuValidationError,
)

BASE_URL = "https://payment-api.khipu.com"
SUBSCRIPTION_URL = f"{BASE_URL}/v1/automatic-payment/subscription"
CHARGE_URL = f"{BASE_URL}/v1/automatic-payment/charge-intent"
API_KEY = "unit-test-api-key"

SUBSCRIPTION_CREATED = {
    "subscription_id": "sub-1",
    "redirect_url": "https://khipu.com/pac/redirect/sub-1",
}
SUBSCRIPTION_STATUS = {
    "subscription_id": "sub-1",
    "status": "ENABLED",
    "developer": False,
    "service_reference": "ref-1",
}
CHARGE_CREATED = {"payment_id": "charge-1"}


@pytest.fixture
def client() -> KhipuClient:
    return KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL))


def charge(client: KhipuClient, **overrides):
    kwargs = dict(
        subscription_id="sub-1",
        amount=Decimal("20000"),
        subject="Monthly fee",
        body="Subscription monthly charge",
        transaction_id="INVOICE-2026-0001",
        error_response_url="https://example.com/pac/error",
        custom="INVOICE-2026-0001",
        notify_url="https://example.com/pac/notify",
    )
    kwargs.update(overrides)
    return client.create_charge(**kwargs)


class TestSubscription:
    def test_create_subscription_sends_expected_body(self, client, httpx_mock):
        httpx_mock.add_response(url=SUBSCRIPTION_URL, json=SUBSCRIPTION_CREATED)
        result = client.create_subscription(
            name="Jane Doe",
            email="jane@example.com",
            max_amount=Decimal("50000"),
            max_amount_per_charge=Decimal("20000"),
            currency="CLP",
            notify_url="https://example.com/pac/notify",
            return_url="https://example.com/pac/return",
            cancel_url="https://example.com/pac/cancel",
        )

        sent = json.loads(httpx_mock.get_requests()[0].content)
        assert sent["max_amount"] == 50000
        assert sent["max_amount_per_charge"] == 20000
        assert sent["currency"] == "CLP"
        assert result.subscription_id == "sub-1"
        assert result.redirect_url == SUBSCRIPTION_CREATED["redirect_url"]

    def test_create_subscription_rejects_fractional_clp(self, client, httpx_mock):
        with pytest.raises(KhipuValidationError):
            client.create_subscription(
                name="Jane Doe",
                email="jane@example.com",
                max_amount=Decimal("50000.5"),
                max_amount_per_charge=Decimal("20000"),
                currency="CLP",
                notify_url="https://example.com/pac/notify",
                return_url="https://example.com/pac/return",
                cancel_url="https://example.com/pac/cancel",
            )
        assert httpx_mock.get_requests() == []

    def test_get_subscription_exposes_status_as_a_plain_string(self, client, httpx_mock):
        httpx_mock.add_response(url=f"{SUBSCRIPTION_URL}/sub-1", json=SUBSCRIPTION_STATUS)
        status = client.get_subscription(subscription_id="sub-1")

        assert status.subscription_id == "sub-1"
        assert status.status == "ENABLED"
        assert type(status.status) is str, "facade must not leak the generated enum type"


class TestCreateChargeSignature:
    """Regression tests for the create_charge signature defect."""

    @pytest.mark.parametrize("name", ["error_response_url", "notify_url"])
    def test_khipu_required_fields_are_declared_required_parameters(self, name):
        parameter = inspect.signature(KhipuClient.create_charge).parameters[name]
        assert parameter.default is inspect.Parameter.empty, (
            f"{name} is required by Khipu's ChargeRequest schema and must be a "
            "required parameter, not smuggled through **extra_fields"
        )

    @pytest.mark.parametrize("name", ["body", "custom", "transaction_id"])
    def test_fields_khipu_relaxed_stay_required_on_the_facade(self, name):
        """Khipu dropped these from ChargeRequest's required list.

        They stay required here on purpose. They are the merchant-side
        correlation and description fields a caller needs in order to reconcile
        a charge afterwards, sending them is always valid, and relaxing them
        would change a published signature for no gain. This test exists so the
        choice is visible rather than looking like a stale copy of the schema.
        """
        parameter = inspect.signature(KhipuClient.create_charge).parameters[name]
        assert parameter.default is inspect.Parameter.empty

    def test_charge_succeeds_using_only_the_public_signature(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        result = charge(client)

        assert result.payment_id == "charge-1"

    def test_charge_sends_every_field_khipu_requires(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        charge(client)

        sent = json.loads(httpx_mock.get_requests()[0].content)
        assert sent == {
            "subscription_id": "sub-1",
            "amount": 20000,
            "subject": "Monthly fee",
            "body": "Subscription monthly charge",
            "transaction_id": "INVOICE-2026-0001",
            "error_response_url": "https://example.com/pac/error",
            "custom": "INVOICE-2026-0001",
            "notify_url": "https://example.com/pac/notify",
        }

    def test_omitting_a_required_field_is_a_python_type_error_not_a_runtime_500(self, client):
        with pytest.raises(TypeError):
            client.create_charge(  # type: ignore[call-arg]
                subscription_id="sub-1",
                amount=Decimal("20000"),
                subject="Monthly fee",
                body="Invoice",
                transaction_id="INVOICE-1",
            )


class TestChargeMoney:
    def test_currency_is_optional_and_never_sent_on_the_wire(self, client, httpx_mock):
        """ChargeRequest has no currency field; it is inherited from the subscription."""
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        charge(client, currency="CLP")

        assert "currency" not in json.loads(httpx_mock.get_requests()[0].content)

    def test_currency_enables_minor_unit_validation_for_the_charge_amount(
        self, client, httpx_mock
    ):
        with pytest.raises(KhipuValidationError):
            charge(client, amount=Decimal("20000.5"), currency="CLP")
        assert httpx_mock.get_requests() == []

    def test_amount_is_still_checked_for_positivity_without_a_currency(
        self, client, httpx_mock
    ):
        with pytest.raises(KhipuValidationError):
            charge(client, amount=Decimal("0"))
        assert httpx_mock.get_requests() == []


class TestMaxAmountPerCharge:
    """Khipu added `max_amount_per_charge` to the required creation fields (#9)."""

    def subscribe(self, client, **overrides):
        kwargs = dict(
            name="Jane Doe",
            email="jane@example.com",
            max_amount=Decimal("50000"),
            max_amount_per_charge=Decimal("20000"),
            currency="CLP",
            notify_url="https://example.com/pac/notify",
            return_url="https://example.com/pac/return",
            cancel_url="https://example.com/pac/cancel",
        )
        kwargs.update(overrides)
        return client.create_subscription(**kwargs)

    def test_it_is_a_required_parameter_not_an_extra_field(self):
        parameter = inspect.signature(KhipuClient.create_subscription).parameters[
            "max_amount_per_charge"
        ]
        assert parameter.default is inspect.Parameter.empty, (
            "max_amount_per_charge is required by Khipu's SubscriptionCreationRequest "
            "schema and must be a required parameter, not smuggled through "
            "**extra_fields"
        )

    def test_omitting_it_is_a_python_type_error_not_a_runtime_400(self, client):
        with pytest.raises(TypeError):
            client.create_subscription(  # type: ignore[call-arg]
                name="Jane Doe",
                email="jane@example.com",
                max_amount=Decimal("50000"),
                currency="CLP",
                notify_url="https://example.com/pac/notify",
                return_url="https://example.com/pac/return",
                cancel_url="https://example.com/pac/cancel",
            )

    def test_it_is_serialised_on_the_wire(self, client, httpx_mock):
        httpx_mock.add_response(url=SUBSCRIPTION_URL, json=SUBSCRIPTION_CREATED)
        self.subscribe(client, max_amount_per_charge=Decimal("7500"))

        assert json.loads(httpx_mock.get_requests()[0].content)[
            "max_amount_per_charge"
        ] == 7500

    def test_it_gets_the_same_minor_unit_validation_as_max_amount(
        self, client, httpx_mock
    ):
        with pytest.raises(KhipuValidationError):
            self.subscribe(client, max_amount_per_charge=Decimal("7500.5"))
        assert httpx_mock.get_requests() == []


class TestChargeResponseStatus:
    """Khipu documents POST /charge-intent as 201 Created."""

    def test_the_documented_201_is_unwrapped(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)

        assert charge(client).payment_id == "charge-1"

    def test_a_200_is_still_unwrapped(self, client, httpx_mock):
        """Khipu's document said 200 until recently; both must work.

        This provider has twice served bodies its own schema contradicted, so a
        success status the generated client does not enumerate must not cost the
        caller the payment id it already returned.
        """
        httpx_mock.add_response(url=CHARGE_URL, status_code=200, json=CHARGE_CREATED)

        assert charge(client).payment_id == "charge-1"

    def test_a_success_status_with_an_unusable_body_is_still_an_error(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, text="not json")

        with pytest.raises(KhipuResponseError):
            charge(client)


class TestChargeRejection:
    """Khipu returns 422 with a ChargeError body when it refuses a charge."""

    def test_a_422_rejection_surfaces_khipus_own_reason(self, client, httpx_mock):
        httpx_mock.add_response(
            url=CHARGE_URL,
            status_code=422,
            json={
                "error_code": "MAX_AMOUNT_PER_CHARGE_EXCEEDED",
                "error_message": (
                    "amount exceeds the maximum allowed per charge for this "
                    "subscription"
                ),
            },
        )

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        assert exc.value.status_code == 422
        assert "exceeds the maximum allowed per charge" in exc.value.message
        assert exc.value.payload["error_code"] == "MAX_AMOUNT_PER_CHARGE_EXCEEDED"

    def test_a_403_is_a_definite_api_error(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=403, json={})

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        assert exc.value.status_code == 403
