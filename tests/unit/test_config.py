import dataclasses
import math
import pickle
import traceback

import httpx
import pytest

from khipu_sdk import KhipuClient, KhipuConfigurationError, KhipuError
from khipu_sdk.config import KhipuConfig

SECRET = "super-secret-api-key-value"

ENV_VARS = ("KHIPU_API_KEY", "KHIPU_BASE_URL", "KHIPU_TIMEOUT")


@pytest.fixture
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def rendered(exc: BaseException) -> str:
    """Everything an exception exposes: message, repr, args and full chain."""
    parts = [str(exc), repr(exc), repr(exc.args)]
    parts.extend(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return "\n".join(parts)


def test_from_env_missing_api_key(clean_env):
    with pytest.raises(ValueError):
        KhipuConfig.from_env()


def test_from_env_reads_values(clean_env):
    clean_env.setenv("KHIPU_API_KEY", "test-key")
    clean_env.setenv("KHIPU_BASE_URL", "https://example.com")
    clean_env.setenv("KHIPU_TIMEOUT", "12.5")

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
        assert "base_url='https://example.com'" in text

    def test_str_does_not_expose_api_key(self):
        assert SECRET not in str(KhipuConfig(api_key=SECRET))

    def test_format_does_not_expose_api_key(self):
        assert SECRET not in f"{KhipuConfig(api_key=SECRET)}"

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"base_url": "ftp://example.com"},
            {"base_url": f"https://user:{SECRET}@example.com"},
            {"base_url": f"https://{SECRET}@example.com"},
            {"base_url": f"https://example.com/#{SECRET}"},
            {"base_url": f"https://example.com/{SECRET} x"},
            {"timeout": 0},
            {"timeout": math.nan},
            {"timeout": httpx.Timeout(10.0, read=None)},
        ],
        ids=["scheme", "userinfo", "user", "fragment", "space", "zero", "nan", "phase"],
    )
    def test_errors_for_other_fields_do_not_expose_the_key_or_the_value(self, kwargs):
        with pytest.raises(KhipuConfigurationError) as exc:
            KhipuConfig(api_key=SECRET, **kwargs)
        text = rendered(exc.value)
        assert SECRET not in text
        assert exc.value.__cause__ is None
        assert exc.value.__context__ is None

    @pytest.mark.parametrize(
        "api_key",
        [f" {SECRET}", f"{SECRET}\n", f"{SECRET}é", f"{SECRET}\x00", f"{SECRET} {SECRET}"],
        ids=["leading-space", "newline", "non-ascii", "nul", "inner-space"],
    )
    def test_invalid_key_errors_do_not_expose_the_key(self, api_key):
        with pytest.raises(KhipuConfigurationError) as exc:
            KhipuConfig(api_key=api_key)
        assert SECRET not in rendered(exc.value)
        assert exc.value.__cause__ is None
        assert exc.value.__context__ is None

    def test_env_errors_do_not_expose_the_key(self, clean_env):
        clean_env.setenv("KHIPU_API_KEY", SECRET)
        clean_env.setenv("KHIPU_TIMEOUT", SECRET)
        with pytest.raises(KhipuConfigurationError) as exc:
            KhipuConfig.from_env()
        assert SECRET not in rendered(exc.value)
        assert exc.value.__cause__ is None
        assert exc.value.__context__ is None

    def test_pickled_error_does_not_carry_the_key(self):
        with pytest.raises(KhipuConfigurationError) as exc:
            KhipuConfig(api_key=f"{SECRET}\n")
        assert SECRET.encode() not in pickle.dumps(exc.value)


class TestApiKey:
    @pytest.mark.parametrize(
        "api_key", ["k", "unit-test-api-key", "0b1c2d3e-aaaa-4bbb-8ccc-123456789abc", "A!~"]
    )
    def test_accepts_visible_ascii(self, api_key):
        assert KhipuConfig(api_key=api_key).api_key == api_key

    @pytest.mark.parametrize("api_key", ["", " ", "\t\n", "　"])
    def test_rejects_empty_or_blank(self, api_key):
        with pytest.raises(KhipuConfigurationError, match="api_key must not be empty"):
            KhipuConfig(api_key=api_key)

    @pytest.mark.parametrize("api_key", ["key ", " key", "a b", "key\r\nX-Evil: 1", "clé", "k\x7f"])
    def test_rejects_whitespace_control_and_non_ascii(self, api_key):
        with pytest.raises(KhipuConfigurationError, match="visible ASCII"):
            KhipuConfig(api_key=api_key)

    @pytest.mark.parametrize("api_key", [None, 123, b"key", ["key"]])
    def test_rejects_non_strings_naming_only_the_type(self, api_key):
        with pytest.raises(KhipuConfigurationError, match="api_key must be a string") as exc:
            KhipuConfig(api_key=api_key)
        assert type(api_key).__name__ in str(exc.value)
        assert "key" not in str(exc.value).replace("api_key", "")


class TestTimeout:
    @pytest.mark.parametrize("timeout", [10.0, 0.001, 1, 30, 1e-9, 86400.0])
    def test_accepts_finite_positive_scalars_unchanged(self, timeout):
        cfg = KhipuConfig(api_key="k", timeout=timeout)
        assert cfg.timeout == timeout
        assert type(cfg.timeout) is type(timeout)

    @pytest.mark.parametrize(
        "timeout", [0, 0.0, -0.0, -1, -0.5, math.nan, math.inf, -math.inf, 10**400]
    )
    def test_rejects_non_positive_or_non_finite(self, timeout):
        with pytest.raises(KhipuConfigurationError, match="finite number of seconds"):
            KhipuConfig(api_key="k", timeout=timeout)

    def test_rejects_none(self):
        with pytest.raises(KhipuConfigurationError, match="None"):
            KhipuConfig(api_key="k", timeout=None)

    @pytest.mark.parametrize("timeout", [True, False, "10", b"10", (5, 10), [10]])
    def test_rejects_other_types(self, timeout):
        with pytest.raises(KhipuConfigurationError, match="must be an int, a float"):
            KhipuConfig(api_key="k", timeout=timeout)

    def test_accepts_httpx_timeout_with_separate_phases(self):
        timeout = httpx.Timeout(5.0, connect=1.5, pool=0.5)
        cfg = KhipuConfig(api_key="k", timeout=timeout)
        assert cfg.timeout is timeout
        assert (timeout.connect, timeout.read, timeout.write, timeout.pool) == (1.5, 5.0, 5.0, 0.5)

    @pytest.mark.parametrize("phase", ["connect", "read", "write", "pool"])
    @pytest.mark.parametrize("bad", [None, 0, -1.0, math.nan, math.inf, True, "5"])
    def test_rejects_httpx_timeout_with_an_invalid_phase(self, phase, bad):
        timeout = httpx.Timeout(5.0, **{phase: bad})
        with pytest.raises(KhipuConfigurationError, match=f"timeout.{phase} "):
            KhipuConfig(api_key="k", timeout=timeout)

    def test_rejects_fully_unbounded_httpx_timeout(self):
        with pytest.raises(KhipuConfigurationError, match="timeout.connect"):
            KhipuConfig(api_key="k", timeout=httpx.Timeout(None))


class TestBaseUrl:
    @pytest.mark.parametrize(
        "base_url",
        [
            "https://payment-api.khipu.com",
            "https://payment-api.khipu.com/",
            "https://example.com:8443/proxy/khipu",
            "http://localhost",
            "http://localhost:8080",
            "http://127.0.0.1:9000/",
            "http://[::1]:8080",
            "http://khipu_mock:8000",
            "HTTPS://Example.COM",
            "https://xn--bcher-kva.example",
            "https://example.com.",
            "https://example.com/v?x=1",
        ],
    )
    def test_accepts_absolute_http_and_https_urls_unchanged(self, base_url):
        assert KhipuConfig(api_key="k", base_url=base_url).base_url == base_url

    @pytest.mark.parametrize(
        "base_url",
        [
            "ftp://example.com",
            "file:///etc/passwd",
            "example.com",
            "//example.com",
            "/v3",
            "https:example.com",
            "https://",
            "https:///path",
            "javascript:alert(1)",
        ],
    )
    def test_rejects_relative_or_non_http_urls(self, base_url):
        with pytest.raises(KhipuConfigurationError, match="absolute http"):
            KhipuConfig(api_key="k", base_url=base_url)

    @pytest.mark.parametrize(
        "base_url", ["https://user:pass@example.com", "https://user@example.com", "https://@example.com"]
    )
    def test_rejects_embedded_credentials(self, base_url):
        with pytest.raises(KhipuConfigurationError, match="credentials"):
            KhipuConfig(api_key="k", base_url=base_url)

    @pytest.mark.parametrize("base_url", ["https://example.com#x", "https://example.com/#", "https://example.com/p#"])
    def test_rejects_fragments(self, base_url):
        with pytest.raises(KhipuConfigurationError, match="fragment"):
            KhipuConfig(api_key="k", base_url=base_url)

    @pytest.mark.parametrize(
        "base_url",
        [
            "",
            " https://example.com",
            "https://example.com ",
            "https://exa mple.com",
            "https://example.com/a b",
            "https://exa\nmple.com",
            "https://exa\tmple.com",
            "https://bücher.example",
        ],
    )
    def test_rejects_whitespace_control_and_non_ascii(self, base_url):
        with pytest.raises(KhipuConfigurationError, match="whitespace"):
            KhipuConfig(api_key="k", base_url=base_url)

    @pytest.mark.parametrize(
        "base_url",
        [
            "https://:443",
            "https://example.com:",
            "https://example.com:0",
            "https://example.com:65536",
            "https://example.com:abc",
            "https://example.com:80:80",
            "https://-bad.example",
            "https://bad-.example",
            "https://bad..example",
            "https://.example",
            "https://" + "a" * 64 + ".example",
            "https://" + ".".join(["a" * 60] * 5),
            "https://256.1.1.1",
            "https://1.2.3",
            "https://exa%20mple.com",
            "https://exa!mple.com",
            "https://[::1",
            "https://[not-ipv6]",
            "https://[::1]x",
        ],
    )
    def test_rejects_invalid_hosts_and_ports(self, base_url):
        with pytest.raises(KhipuConfigurationError, match="base_url"):
            KhipuConfig(api_key="k", base_url=base_url)

    @pytest.mark.parametrize("base_url", [None, b"https://example.com", 1])
    def test_rejects_non_strings(self, base_url):
        with pytest.raises(KhipuConfigurationError, match="base_url must be a string"):
            KhipuConfig(api_key="k", base_url=base_url)


class TestFromEnv:
    def test_defaults_when_only_the_key_is_set(self, clean_env):
        clean_env.setenv("KHIPU_API_KEY", "k")
        cfg = KhipuConfig.from_env()
        assert cfg == KhipuConfig(api_key="k")

    def test_custom_prefix(self, clean_env):
        clean_env.setenv("SHOP_API_KEY", "shop-key")
        clean_env.setenv("SHOP_BASE_URL", "http://127.0.0.1:8080")
        clean_env.setenv("SHOP_TIMEOUT", "3")
        cfg = KhipuConfig.from_env(prefix="SHOP_")
        assert (cfg.api_key, cfg.base_url, cfg.timeout) == ("shop-key", "http://127.0.0.1:8080", 3.0)

    def test_custom_prefix_names_its_own_variables(self, clean_env):
        clean_env.setenv("KHIPU_API_KEY", "k")
        with pytest.raises(KhipuConfigurationError, match="SHOP_API_KEY"):
            KhipuConfig.from_env(prefix="SHOP_")
        clean_env.setenv("SHOP_API_KEY", "k")
        clean_env.setenv("SHOP_TIMEOUT", "soon")
        with pytest.raises(KhipuConfigurationError, match="SHOP_TIMEOUT"):
            KhipuConfig.from_env(prefix="SHOP_")

    @pytest.mark.parametrize("value", [None, ""])
    def test_missing_or_empty_key(self, clean_env, value):
        if value is not None:
            clean_env.setenv("KHIPU_API_KEY", value)
        with pytest.raises(KhipuConfigurationError, match="KHIPU_API_KEY"):
            KhipuConfig.from_env()

    @pytest.mark.parametrize("value", ["   ", "key with spaces", "key\n"])
    def test_blank_or_invalid_key(self, clean_env, value):
        clean_env.setenv("KHIPU_API_KEY", value)
        with pytest.raises(KhipuConfigurationError, match="api_key"):
            KhipuConfig.from_env()

    @pytest.mark.parametrize("value", ["", " ", "ftp://example.com", "https://u:p@example.com"])
    def test_invalid_base_url(self, clean_env, value):
        clean_env.setenv("KHIPU_API_KEY", "k")
        clean_env.setenv("KHIPU_BASE_URL", value)
        with pytest.raises(KhipuConfigurationError, match="base_url"):
            KhipuConfig.from_env()

    @pytest.mark.parametrize("value,expected", [("12.5", 12.5), ("3", 3.0), (" 7 ", 7.0), ("1e-3", 0.001)])
    def test_timeout_values(self, clean_env, value, expected):
        clean_env.setenv("KHIPU_API_KEY", "k")
        clean_env.setenv("KHIPU_TIMEOUT", value)
        assert KhipuConfig.from_env().timeout == expected

    @pytest.mark.parametrize("value", ["", "  "])
    def test_blank_timeout_is_rejected_not_defaulted(self, clean_env, value):
        clean_env.setenv("KHIPU_API_KEY", "k")
        clean_env.setenv("KHIPU_TIMEOUT", value)
        with pytest.raises(KhipuConfigurationError, match="KHIPU_TIMEOUT is set but empty"):
            KhipuConfig.from_env()

    @pytest.mark.parametrize("value", ["abc", "10s", "1,5", "0x10", "None"])
    def test_malformed_timeout(self, clean_env, value):
        clean_env.setenv("KHIPU_API_KEY", "k")
        clean_env.setenv("KHIPU_TIMEOUT", value)
        with pytest.raises(KhipuConfigurationError, match="KHIPU_TIMEOUT must be a number"):
            KhipuConfig.from_env()

    @pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "Infinity", "1e400"])
    def test_non_positive_or_non_finite_timeout(self, clean_env, value):
        clean_env.setenv("KHIPU_API_KEY", "k")
        clean_env.setenv("KHIPU_TIMEOUT", value)
        with pytest.raises(KhipuConfigurationError, match="KHIPU_TIMEOUT must be a finite"):
            KhipuConfig.from_env()


class TestErrorContract:
    def test_errors_are_sdk_errors_and_value_errors(self):
        with pytest.raises(KhipuConfigurationError) as exc:
            KhipuConfig(api_key="")
        assert isinstance(exc.value, KhipuError)
        assert isinstance(exc.value, ValueError)

    def test_existing_value_error_handlers_still_catch_from_env(self, clean_env):
        try:
            KhipuConfig.from_env()
        except ValueError as exc:
            assert type(exc) is KhipuConfigurationError
        else:  # pragma: no cover
            pytest.fail("from_env() accepted a missing key")

    def test_error_round_trips_through_pickle(self, clean_env):
        with pytest.raises(KhipuConfigurationError) as exc:
            KhipuConfig.from_env()
        restored = pickle.loads(pickle.dumps(exc.value))
        assert type(restored) is KhipuConfigurationError
        assert str(restored) == str(exc.value)
        assert restored.args == exc.value.args


class TestImmutability:
    def test_config_is_still_frozen(self):
        cfg = KhipuConfig(api_key="k")
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.timeout = None  # type: ignore[misc]

    def test_replace_is_validated(self):
        cfg = KhipuConfig(api_key="k")
        assert dataclasses.replace(cfg, timeout=5.0).timeout == 5.0
        with pytest.raises(KhipuConfigurationError):
            dataclasses.replace(cfg, base_url="ftp://example.com")

    def test_signature_and_defaults_are_unchanged(self):
        fields = {f.name: f for f in dataclasses.fields(KhipuConfig)}
        assert list(fields) == ["api_key", "base_url", "timeout"]
        assert fields["api_key"].default is dataclasses.MISSING
        assert fields["api_key"].repr is False
        assert fields["base_url"].default == "https://payment-api.khipu.com"
        assert fields["timeout"].default == 10.0


class TestClientRevalidates:
    def test_client_rejects_a_timeout_made_unbounded_after_construction(self):
        timeout = httpx.Timeout(5.0)
        cfg = KhipuConfig(api_key="k", timeout=timeout)
        timeout.read = None
        with pytest.raises(KhipuConfigurationError, match="timeout.read"):
            KhipuClient(cfg)

    def test_client_rejects_a_config_bypassing_validation(self):
        cfg = KhipuConfig(api_key="k")
        object.__setattr__(cfg, "api_key", "")
        with pytest.raises(KhipuConfigurationError, match="api_key"):
            KhipuClient(cfg)
