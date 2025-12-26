import pytest

from khipu_sdk.config import KhipuConfig


def test_from_env_missing_api_key(monkeypatch):
    monkeypatch.delenv("KHIPU_API_KEY", raising=False)
    with pytest.raises(ValueError):
        KhipuConfig.from_env()


def test_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("KHIPU_API_KEY", "test-key")
    monkeypatch.setenv("KHIPU_BASE_URL", "https://example.com")
    monkeypatch.setenv("KHIPU_TIMEOUT", "12.5")

    cfg = KhipuConfig.from_env()
    assert cfg.api_key == "test-key"
    assert cfg.base_url == "https://example.com"
    assert cfg.timeout == 12.5
