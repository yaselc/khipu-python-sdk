import pytest

from khipu_sdk import KhipuClient, KhipuConfig
from khipu_sdk.errors import KhipuApiError, KhipuConfigurationError


def test_missing_generated_client_raises_a_configuration_error(monkeypatch):
    """A broken/incomplete installation is a configuration problem, not an API error."""
    monkeypatch.setattr(KhipuClient, "_build_instant_client", lambda self: None)
    client = KhipuClient(KhipuConfig(api_key="x"))

    with pytest.raises(KhipuConfigurationError) as exc:
        client.create_instant_payment(
            amount=1000,
            currency="CLP",
            subject="Test",
            transaction_id="ORDER-1",
        )

    assert "generated" in str(exc.value).lower()
    assert not isinstance(exc.value, KhipuApiError), (
        "a missing generated client must never masquerade as a Khipu HTTP error"
    )
