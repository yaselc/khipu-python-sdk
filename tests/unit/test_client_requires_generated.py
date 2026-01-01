import pytest

from khipu_sdk.client import KhipuClient
from khipu_sdk.config import KhipuConfig
from khipu_sdk.errors import KhipuApiError


def test_requires_generated_clients_when_not_present(monkeypatch):
    monkeypatch.setattr(KhipuClient, "_build_instant_client", lambda self: None)
    client = KhipuClient(KhipuConfig(api_key="x"))
    with pytest.raises(KhipuApiError) as exc:
        client.create_instant_payment(
            amount=1000,
            currency="CLP",
            subject="Test",
            transaction_id="ORDER-1",
        )
    assert "make generate-all" in str(exc.value)
