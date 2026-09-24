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

import httpx
import pytest

from khipu_sdk import (
    KhipuApiError,
    KhipuClient,
    KhipuConfig,
    KhipuResponseError,
    KhipuTimeoutError,
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
    def test_fields_khipu_relaxed_are_optional_on_the_facade(self, name):
        """Khipu dropped these from ChargeRequest's required list.

        The SDK mirrors the provider contract and nothing more. Requiring a
        field Khipu does not require would push one application's reconciliation
        policy onto every consumer of the SDK; an application that needs these
        fields enforces that in its own service layer.
        """
        parameter = inspect.signature(KhipuClient.create_charge).parameters[name]
        assert parameter.default is None

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

class TestOptionalChargeFields:
    """`body`, `custom` and `transaction_id` follow Khipu's optionality."""

    def minimal(self, client, **overrides):
        kwargs = dict(
            subscription_id="sub-1",
            amount=Decimal("20000"),
            subject="Monthly fee",
            error_response_url="https://example.com/pac/error",
            notify_url="https://example.com/pac/notify",
        )
        kwargs.update(overrides)
        return client.create_charge(**kwargs)

    def test_a_charge_succeeds_without_any_of_them(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)

        assert self.minimal(client).payment_id == "charge-1"

    def test_omitted_fields_are_absent_from_the_payload(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        self.minimal(client)

        sent = json.loads(httpx_mock.get_requests()[0].content)
        assert sent == {
            "subscription_id": "sub-1",
            "amount": 20000,
            "subject": "Monthly fee",
            "error_response_url": "https://example.com/pac/error",
            "notify_url": "https://example.com/pac/notify",
        }

    @pytest.mark.parametrize("name", ["body", "custom", "transaction_id"])
    def test_an_omitted_field_is_never_sent_as_null(self, client, httpx_mock, name):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        self.minimal(client)

        sent = json.loads(httpx_mock.get_requests()[0].content)
        assert name not in sent, f"{name} must be omitted, not sent as null"

    @pytest.mark.parametrize(
        "name,value",
        [
            ("body", "Servicio XYZ - Septiembre 2026"),
            ("custom", "INVOICE-2026-0001"),
            ("transaction_id", "INVOICE-2026-0001"),
        ],
    )
    def test_a_supplied_field_is_serialised_unchanged(
        self, client, httpx_mock, name, value
    ):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        self.minimal(client, **{name: value})

        assert json.loads(httpx_mock.get_requests()[0].content)[name] == value

    def test_an_empty_string_is_sent_rather_than_treated_as_omission(
        self, client, httpx_mock
    ):
        """Only ``None`` means "do not send"; "" is a value the caller chose."""
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        self.minimal(client, custom="")

        assert json.loads(httpx_mock.get_requests()[0].content)["custom"] == ""

    @pytest.mark.parametrize("name", ["error_response_url", "notify_url"])
    def test_the_fields_khipu_still_requires_stay_required(self, name):
        parameter = inspect.signature(KhipuClient.create_charge).parameters[name]
        assert parameter.default is inspect.Parameter.empty

    def test_an_existing_caller_passing_every_field_is_unaffected(
        self, client, httpx_mock
    ):
        """The correlation-field call shape from 0.2.0 must behave identically."""
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        result = charge(client)

        assert result.payment_id == "charge-1"
        assert json.loads(httpx_mock.get_requests()[0].content) == {
            "subscription_id": "sub-1",
            "amount": 20000,
            "subject": "Monthly fee",
            "body": "Subscription monthly charge",
            "transaction_id": "INVOICE-2026-0001",
            "error_response_url": "https://example.com/pac/error",
            "custom": "INVOICE-2026-0001",
            "notify_url": "https://example.com/pac/notify",
        }


class TestChargeNotifyApiVersion:
    """``notify_api_version`` selects Khipu's notification contract (#14).

    It is optional in Khipu's ``ChargeRequest`` and the SDK keeps it optional:
    the application chooses its notification contract, the SDK never picks one.
    A value is sent exactly as given; ``None`` means the key is not sent at all.
    """

    #: The request body a minimal charge sent before this parameter existed.
    MINIMAL_BODY = {
        "subscription_id": "sub-1",
        "amount": 20000,
        "subject": "Monthly fee",
        "error_response_url": "https://example.com/pac/error",
        "notify_url": "https://example.com/pac/notify",
    }

    def minimal(self, client, **overrides):
        kwargs = dict(
            subscription_id="sub-1",
            amount=Decimal("20000"),
            subject="Monthly fee",
            error_response_url="https://example.com/pac/error",
            notify_url="https://example.com/pac/notify",
        )
        kwargs.update(overrides)
        return client.create_charge(**kwargs)

    def sent(self, httpx_mock) -> dict:
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        return json.loads(requests[0].content)

    def test_it_is_an_explicit_optional_parameter_defaulting_to_none(self):
        parameter = inspect.signature(KhipuClient.create_charge).parameters[
            "notify_api_version"
        ]

        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is None

    @pytest.mark.parametrize(
        "name", ["subscription_id", "amount", "subject", "error_response_url", "notify_url"]
    )
    def test_the_required_charge_fields_stay_required(self, name):
        parameter = inspect.signature(KhipuClient.create_charge).parameters[name]

        assert parameter.default is inspect.Parameter.empty

    def test_extra_fields_is_still_accepted(self):
        kinds = {
            p.kind for p in inspect.signature(KhipuClient.create_charge).parameters.values()
        }

        assert inspect.Parameter.VAR_KEYWORD in kinds

    def test_a_supplied_version_is_serialised_unchanged(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        result = self.minimal(client, notify_api_version="3.0")

        assert result.payment_id == "charge-1"
        assert self.sent(httpx_mock) == {**self.MINIMAL_BODY, "notify_api_version": "3.0"}

    @pytest.mark.parametrize("value", ["1.3", "3.0", "", "4.0-future"])
    def test_the_sdk_does_not_restrict_the_value(self, client, httpx_mock, value):
        """Khipu's schema declares a free string; the SDK neither validates nor maps it."""
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        self.minimal(client, notify_api_version=value)

        assert self.sent(httpx_mock)["notify_api_version"] == value

    def test_omitting_it_sends_no_key_and_no_default(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        self.minimal(client)

        assert self.sent(httpx_mock) == self.MINIMAL_BODY

    def test_explicit_none_sends_no_key_rather_than_null(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        self.minimal(client, notify_api_version=None)

        assert self.sent(httpx_mock) == self.MINIMAL_BODY

    def test_existing_charge_fields_are_unchanged_alongside_it(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json=CHARGE_CREATED)
        charge(client, notify_api_version="3.0")

        assert self.sent(httpx_mock) == {
            "subscription_id": "sub-1",
            "amount": 20000,
            "subject": "Monthly fee",
            "body": "Subscription monthly charge",
            "transaction_id": "INVOICE-2026-0001",
            "error_response_url": "https://example.com/pac/error",
            "custom": "INVOICE-2026-0001",
            "notify_url": "https://example.com/pac/notify",
            "notify_api_version": "3.0",
        }

    def test_a_timeout_is_not_retried(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("read timed out"), url=CHARGE_URL)

        with pytest.raises(KhipuTimeoutError):
            self.minimal(client, notify_api_version="3.0")

        assert len(httpx_mock.get_requests()) == 1


class TestChargeSuccessStatusIsNotOpenEnded:
    """Only 201 (published) and 200 (previous contract) mean success.

    A financial result must not be inferred from a status code Khipu has never
    documented for this endpoint. 202 in particular means *accepted, not yet
    processed* -- giving it the semantics of 201 would report a charge as
    created when the provider said no such thing.
    """

    @pytest.mark.parametrize("accepted", [201, 200])
    def test_an_accepted_status_with_a_usable_body_succeeds(
        self, client, httpx_mock, accepted
    ):
        httpx_mock.add_response(
            url=CHARGE_URL, status_code=accepted, json=CHARGE_CREATED
        )

        assert charge(client).payment_id == "charge-1"

    @pytest.mark.parametrize("rejected", [202, 203, 206])
    def test_another_2xx_is_not_promoted_to_success_even_with_a_valid_body(
        self, client, httpx_mock, rejected
    ):
        httpx_mock.add_response(
            url=CHARGE_URL, status_code=rejected, json=CHARGE_CREATED
        )

        with pytest.raises(KhipuResponseError) as exc:
            charge(client)

        assert exc.value.status_code == rejected

    def test_204_no_content_is_not_a_successful_charge(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=204)

        with pytest.raises(KhipuResponseError):
            charge(client)

    @pytest.mark.parametrize("accepted", [201, 200])
    def test_an_unusable_body_on_an_accepted_status_still_raises(
        self, client, httpx_mock, accepted
    ):
        httpx_mock.add_response(url=CHARGE_URL, status_code=accepted, text="not json")

        with pytest.raises(KhipuResponseError):
            charge(client)

    @pytest.mark.parametrize("accepted", [201, 200])
    def test_a_body_missing_payment_id_on_an_accepted_status_raises(
        self, client, httpx_mock, accepted
    ):
        httpx_mock.add_response(url=CHARGE_URL, status_code=accepted, json={})

        with pytest.raises(KhipuResponseError):
            charge(client)
