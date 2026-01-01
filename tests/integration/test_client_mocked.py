from __future__ import annotations

from types import SimpleNamespace

import pytest

from khipu_sdk.client import KhipuClient
from khipu_sdk.config import KhipuConfig

from generated.instant_payments.api.default import get_payment_by_id, post_payment
from generated.instant_payments.models.payment_post_payment import PaymentPostPayment
from generated.automatic_payments.api.default import (
    create_charge_1,
    create_subscription_1,
    fetch_subscription_status_1,
)
from generated.automatic_payments.models.charge_request import ChargeRequest
from generated.automatic_payments.models.subscription_creation_request import (
    SubscriptionCreationRequest,
)


@pytest.fixture
def sdk(monkeypatch: pytest.MonkeyPatch) -> tuple[KhipuClient, object, object]:
    config = KhipuConfig(base_url="https://sandbox.khipu.com", api_key="test-key")

    instant_client = object()
    automatic_client = object()

    monkeypatch.setattr(KhipuClient, "_build_instant_client", lambda self: instant_client)
    monkeypatch.setattr(KhipuClient, "_build_automatic_client", lambda self: automatic_client)

    return KhipuClient(config), instant_client, automatic_client


def test_create_instant_payment_uses_generated_client(monkeypatch: pytest.MonkeyPatch, sdk: tuple[KhipuClient, object, object]) -> None:
    client, instant_client, _ = sdk
    captured: dict[str, object] = {}

    def fake_sync_detailed(*, client: object, body: PaymentPostPayment):
        captured["client"] = client
        captured["body"] = body
        return SimpleNamespace(
            parsed=SimpleNamespace(payment_id="pay-123", payment_url="https://pay", status="pending"),
            status_code=200,
        )

    monkeypatch.setattr(post_payment, "sync_detailed", fake_sync_detailed)

    result = client.create_instant_payment(
        amount=1000.0,
        currency="CLP",
        subject="Test payment",
        transaction_id="TX-1",
        body="body text",
        return_url="https://return",
        cancel_url="https://cancel",
        notify_url="https://notify",
        custom="value",
    )

    assert captured["client"] is instant_client
    payload = captured["body"].to_dict()  # type: ignore[assignment]
    assert payload == {
        "amount": 1000.0,
        "currency": "CLP",
        "subject": "Test payment",
        "transaction_id": "TX-1",
        "custom": "value",
        "body": "body text",
        "return_url": "https://return",
        "cancel_url": "https://cancel",
        "notify_url": "https://notify",
    }
    assert result.payment_id == "pay-123"
    assert result.payment_url == "https://pay"
    assert result.status == "pending"


def test_get_instant_payment_returns_status(monkeypatch: pytest.MonkeyPatch, sdk: tuple[KhipuClient, object, object]) -> None:
    client, instant_client, _ = sdk

    def fake_sync_detailed(*, id: str, client: object):
        assert id == "pay-123"
        assert client is instant_client
        return SimpleNamespace(
            parsed=SimpleNamespace(payment_id="pay-123", status="paid", amount=1000.0, currency="CLP"),
            status_code=200,
        )

    monkeypatch.setattr(get_payment_by_id, "sync_detailed", fake_sync_detailed)

    status = client.get_instant_payment(payment_id="pay-123")
    assert status.payment_id == "pay-123"
    assert status.status == "paid"
    assert status.amount == 1000.0
    assert status.currency == "CLP"


def test_automatic_payments_flow(monkeypatch: pytest.MonkeyPatch, sdk: tuple[KhipuClient, object, object]) -> None:
    client, _, automatic_client = sdk
    captured: dict[str, object] = {}

    def fake_create_subscription(*, client: object, body: SubscriptionCreationRequest):
        captured["subscription_client"] = client
        captured["subscription_body"] = body
        return SimpleNamespace(
            parsed=SimpleNamespace(subscription_id="sub-1", redirect_url="https://redirect"),
            status_code=200,
        )

    def fake_fetch_status(*, id: str, client: object):
        assert id == "sub-1"
        assert client is automatic_client
        return SimpleNamespace(
            parsed=SimpleNamespace(subscription_id="sub-1", status="active"),
            status_code=200,
        )

    def fake_create_charge(*, client: object, body: ChargeRequest):
        captured["charge_client"] = client
        captured["charge_body"] = body
        return SimpleNamespace(parsed=SimpleNamespace(payment_id="charge-1"), status_code=200)

    monkeypatch.setattr(create_subscription_1, "sync_detailed", fake_create_subscription)
    monkeypatch.setattr(fetch_subscription_status_1, "sync_detailed", fake_fetch_status)
    monkeypatch.setattr(create_charge_1, "sync_detailed", fake_create_charge)

    sub = client.create_subscription(
        name="Test user",
        email="test@example.com",
        max_amount=5000.0,
        currency="CLP",
        notify_url="https://notify",
        return_url="https://return",
        cancel_url="https://cancel",
        service_reference="ref-1",
    )
    assert captured["subscription_client"] is automatic_client
    subscription_payload = captured["subscription_body"].to_dict()  # type: ignore[assignment]
    assert subscription_payload["name"] == "Test user"
    assert subscription_payload["service_reference"] == "ref-1"

    status = client.get_subscription(subscription_id=sub.subscription_id)
    assert status.subscription_id == "sub-1"
    assert status.status == "active"

    charge = client.create_charge(
        subscription_id=sub.subscription_id,
        amount=990.0,
        subject="Monthly fee",
        body="Invoice",
        transaction_id="CH-1",
        error_response_url="https://error",
        custom="trace",
        notify_url="https://notify-charge",
        notify_api_version="1.0",
    )
    assert captured["charge_client"] is automatic_client
    charge_payload = captured["charge_body"].to_dict()  # type: ignore[assignment]
    assert charge_payload["subscription_id"] == "sub-1"
    assert charge_payload["custom"] == "trace"
    assert charge_payload["notify_api_version"] == "1.0"
    assert charge.payment_id == "charge-1"
