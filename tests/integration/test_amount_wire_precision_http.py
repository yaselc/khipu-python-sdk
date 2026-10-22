"""Amounts on the real HTTP boundary: sent exactly, or rejected before sending.

F3 of #41. The generated models type ``amount`` as ``float``, so a
non-integral amount crosses the wire as a JSON float. These tests read the
amount token straight from the request body, so they check the decimal value
Khipu would receive, and they assert that a rejected amount produces no
request at all.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from khipu_sdk import KhipuClient, KhipuConfig, KhipuValidationError

BASE_URL = "https://payment-api.khipu.com"
PAYMENTS_URL = f"{BASE_URL}/v3/payments"
SUBSCRIPTION_URL = f"{BASE_URL}/v1/automatic-payment/subscription"
CHARGE_URL = f"{BASE_URL}/v1/automatic-payment/charge-intent"
API_KEY = "unit-test-api-key"

CREATE_RESPONSE = {
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


@pytest.fixture
def client() -> KhipuClient:
    return KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL))


def wire_token(content: bytes, field: str) -> str:
    """The literal JSON number sent for ``field``, as it appears on the wire."""
    match = re.search(rb'"' + field.encode() + rb'":\s*([^,}\s]+)', content)
    assert match is not None, content
    return match.group(1).decode()


def create_payment(client: KhipuClient, amount, currency: str):
    return client.create_instant_payment(
        amount=amount,
        currency=currency,
        subject="Order",
        transaction_id="ORDER-1",
    )


def create_charge(client: KhipuClient, amount, currency=None):
    return client.create_charge(
        subscription_id="sub-1",
        amount=amount,
        currency=currency,
        subject="Monthly fee",
        error_response_url="https://example.com/pac/error",
        custom="INVOICE-1",
        notify_url="https://example.com/pac/notify",
    )


def create_subscription(client: KhipuClient, max_amount, per_charge, currency: str):
    return client.create_subscription(
        name="Jane Doe",
        email="jane@example.com",
        max_amount=max_amount,
        max_amount_per_charge=per_charge,
        currency=currency,
        notify_url="https://example.com/pac/notify",
        return_url="https://example.com/pac/return",
        cancel_url="https://example.com/pac/cancel",
    )


class TestInstantPaymentAmountOnTheWire:
    @pytest.mark.parametrize(
        ("amount", "currency", "token"),
        [
            (Decimal("10000"), "CLP", "10000"),
            (Decimal("10000.0000"), "CLP", "10000"),
            (Decimal("9007199254740993"), "CLP", "9007199254740993"),
            (Decimal("1.2345"), "CLF", "1.2345"),
            (Decimal("123456789012.3457"), "CLF", "123456789012.3457"),
            (Decimal("19.99"), "USD", "19.99"),
            (Decimal("12.30"), "USD", "12.3"),
            (Decimal("0.10"), "USD", "0.1"),
            (Decimal("9999999999999.99"), "USD", "9999999999999.99"),
            ("1.2345", "CLF", "1.2345"),
            (10000, "CLP", "10000"),
        ],
    )
    def test_accepted_amount_is_sent_exactly(self, client, httpx_mock, amount, currency, token):
        httpx_mock.add_response(url=PAYMENTS_URL, method="POST", json=CREATE_RESPONSE)
        create_payment(client, amount, currency)

        content = httpx_mock.get_requests()[0].content
        assert wire_token(content, "amount") == token
        assert Decimal(token) == Decimal(str(amount))

    @pytest.mark.parametrize(
        ("amount", "currency"),
        [
            (Decimal("1234567890123.4567"), "CLF"),  # audit: would be sent as ...4568
            (Decimal("1234567890123456.78"), "USD"),  # audit: would be sent as ...456.8
            (Decimal("1" + "0" * 400 + ".5"), "USD"),  # overflows float
            ("1234567890123.4567", "CLF"),
        ],
    )
    def test_lossy_amount_is_rejected_without_a_request(
        self, client, httpx_mock, amount, currency
    ):
        with pytest.raises(KhipuValidationError, match="not rounded automatically"):
            create_payment(client, amount, currency)
        assert httpx_mock.get_requests() == []

    @pytest.mark.parametrize(
        ("amount", "currency"),
        [
            (Decimal("NaN"), "USD"),
            (Decimal("Infinity"), "USD"),
            (Decimal("0"), "USD"),
            (Decimal("-1"), "CLP"),
            ("not-a-number", "CLF"),
            (Decimal("9700.5"), "CLP"),
            (Decimal("1.23456"), "CLF"),
        ],
    )
    def test_invalid_amount_is_rejected_without_a_request(
        self, client, httpx_mock, amount, currency
    ):
        with pytest.raises(KhipuValidationError):
            create_payment(client, amount, currency)
        assert httpx_mock.get_requests() == []


class TestChargeAmountOnTheWire:
    """The charge intent carries no currency, so only the wire check applies."""

    @pytest.mark.parametrize(
        ("amount", "token"),
        [
            (Decimal("20000"), "20000"),
            (Decimal("123456789012345678901234567890"), "123456789012345678901234567890"),
            (Decimal("1.2345"), "1.2345"),
            (Decimal("0.1"), "0.1"),
            (Decimal("0.30000000000000004"), "0.30000000000000004"),
            # A float input keeps the caller's own float error; the SDK adds none.
            (0.1 + 0.2, "0.30000000000000004"),
        ],
    )
    def test_accepted_amount_is_sent_exactly(self, client, httpx_mock, amount, token):
        httpx_mock.add_response(url=CHARGE_URL, method="POST", json=CHARGE_CREATED)
        create_charge(client, amount)

        content = httpx_mock.get_requests()[0].content
        assert wire_token(content, "amount") == token
        assert b'"currency"' not in content

    @pytest.mark.parametrize(
        "amount",
        [
            Decimal("1234567890123.4567"),
            Decimal("0.12345678901234567891"),
            Decimal("1" + "0" * 400 + ".5"),  # overflows float
            Decimal("1E-400"),  # underflows float to 0.0
        ],
    )
    def test_lossy_amount_is_rejected_without_a_request(self, client, httpx_mock, amount):
        with pytest.raises(KhipuValidationError, match="not rounded automatically"):
            create_charge(client, amount)
        assert httpx_mock.get_requests() == []

    @pytest.mark.parametrize("amount", [Decimal("NaN"), Decimal("-Infinity"), 0, "abc"])
    def test_invalid_amount_is_rejected_without_a_request(self, client, httpx_mock, amount):
        with pytest.raises(KhipuValidationError):
            create_charge(client, amount)
        assert httpx_mock.get_requests() == []

    def test_explicit_currency_still_applies_minor_units(self, client, httpx_mock):
        with pytest.raises(KhipuValidationError, match="CLP admits 0"):
            create_charge(client, Decimal("20000.5"), currency="CLP")
        assert httpx_mock.get_requests() == []


class TestSubscriptionCapsOnTheWire:
    def test_accepted_caps_are_sent_exactly(self, client, httpx_mock):
        httpx_mock.add_response(url=SUBSCRIPTION_URL, method="POST", json=SUBSCRIPTION_CREATED)
        create_subscription(client, Decimal("123456789012.3457"), Decimal("1.2345"), "CLF")

        content = httpx_mock.get_requests()[0].content
        assert wire_token(content, "max_amount") == "123456789012.3457"
        assert wire_token(content, "max_amount_per_charge") == "1.2345"

    @pytest.mark.parametrize(
        ("max_amount", "per_charge"),
        [
            (Decimal("1234567890123.4567"), Decimal("1.2345")),
            (Decimal("1.2345"), Decimal("1234567890123.4567")),
        ],
    )
    def test_a_lossy_cap_is_rejected_without_a_request(
        self, client, httpx_mock, max_amount, per_charge
    ):
        with pytest.raises(KhipuValidationError, match="not rounded automatically"):
            create_subscription(client, max_amount, per_charge, "CLF")
        assert httpx_mock.get_requests() == []
