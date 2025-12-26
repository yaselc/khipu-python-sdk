import os
import pytest

from khipu_sdk import KhipuClient, KhipuConfig


pytestmark = pytest.mark.skipif(
    os.getenv("KHIPU_RUN_INTEGRATION_TESTS") != "1",
    reason="Set KHIPU_RUN_INTEGRATION_TESTS=1 to enable integration tests.",
)


def test_create_and_get_payment_smoke():
    cfg = KhipuConfig.from_env()
    client = KhipuClient(cfg)

    result = client.create_instant_payment(
        amount=1000.0,
        currency="CLP",
        subject="Integration test payment",
        transaction_id="INTEGRATION-TEST-1",
        return_url="https://example.com/return",
        cancel_url="https://example.com/cancel",
        notify_url="https://example.com/notify",
    )

    assert result.payment_id
    payment = client.get_instant_payment(payment_id=result.payment_id)
    assert payment.payment_id == result.payment_id
