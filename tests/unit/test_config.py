import httpx
import pytest

from khipu_sdk.config import KhipuConfig

SECRET = "super-secret-api-key-value"


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


def test_defaults_are_bounded():
    cfg = KhipuConfig(api_key="k")
    assert cfg.base_url == "https://payment-api.khipu.com"
    assert cfg.timeout == 10.0
    assert cfg.timeout is not None, "an unbounded default timeout would be unsafe"


def test_accepts_httpx_timeout_object():
    timeout = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0)
    cfg = KhipuConfig(api_key="k", timeout=timeout)
    assert cfg.timeout is timeout


class TestSecretSafety:
    def test_repr_does_not_expose_api_key(self):
        assert SECRET not in repr(KhipuConfig(api_key=SECRET))

    def test_repr_still_shows_useful_non_secret_context(self):
        text = repr(KhipuConfig(api_key=SECRET, base_url="https://example.com"))
        assert "https://example.com" in text

    def test_str_does_not_expose_api_key(self):
        assert SECRET not in str(KhipuConfig(api_key=SECRET))

    def test_format_does_not_expose_api_key(self):
        assert SECRET not in f"{KhipuConfig(api_key=SECRET)}"
