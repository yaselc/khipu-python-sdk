"""Configuration validation on the real HTTP boundary.

F4 of #41. An invalid :class:`KhipuConfig` must fail before any request can be
built, and a valid one must keep sending exactly one request with the
configured base URL, credential and timeout. ``pytest_httpx`` intercepts at the
transport layer, so no network access occurs.
"""

from __future__ import annotations

import math

import httpx
import pytest

from khipu_sdk import (
    KhipuClient,
    KhipuConfig,
    KhipuConfigurationError,
    KhipuConnectionError,
    KhipuTimeoutError,
)

API_KEY = "unit-test-api-key-must-never-leak"
PAYMENT_ID = "gqzdy6chjne9"

PAYMENT = {
    "payment_id": PAYMENT_ID,
    "payment_url": f"https://khipu.com/payment/info/{PAYMENT_ID}",
    "simplified_transfer_url": f"https://app.khipu.com/payment/simplified/{PAYMENT_ID}",
    "transfer_url": f"https://khipu.com/payment/manual/{PAYMENT_ID}",
    "app_url": f"khipu:///pos/{PAYMENT_ID}",
    "ready_for_terminal": False,
    "notification_token": "9dec8aa176c5223026919b3b5579a4776923e646ff3be686b9e6b62ec042e91f",
    "receiver_id": 985101,
    "conciliation_date": "2026-03-01T13:00:00.000Z",
    "subject": "Aporte",
    "amount": "10000",
    "currency": "CLP",
    "status": "done",
    "status_detail": "normal",
    "body": "Detalle",
    "picture_url": "https://example.com/pic.png",
    "receipt_url": "https://example.com/receipt.pdf",
    "return_url": "https://example.com/return",
    "cancel_url": "https://example.com/cancel",
    "notify_url": "https://example.com/notify",
    "notify_api_version": "3.0",
    "expires_date": "2026-03-02T13:00:00.000Z",
    "attachment_urls": [],
    "bank": "Banco",
    "bank_id": "Bawdf",
    "payer_name": "Jane",
    "payer_email": "jane@example.com",
    "personal_identifier": "11.111.111-1",
    "bank_account_number": "001",
    "out_of_date_conciliation": False,
    "transaction_id": "ORDER-1",
    "custom": "",
    "responsible_user_email": "owner@example.com",
    "send_reminders": False,
    "send_email": False,
    "payment_method": "simplified_transfer",
    "funds_source": "",
}

INVALID_CONFIGS = [
    {"api_key": ""},
    {"api_key": "   "},
    {"api_key": f"{API_KEY}\r\nX-Injected: 1"},
    {"api_key": f"{API_KEY}é"},
    {"api_key": API_KEY, "base_url": "ftp://payment-api.khipu.com"},
    {"api_key": API_KEY, "base_url": "payment-api.khipu.com"},
    {"api_key": API_KEY, "base_url": f"https://user:{API_KEY}@payment-api.khipu.com"},
    {"api_key": API_KEY, "base_url": "https://payment-api.khipu.com#fragment"},
    {"api_key": API_KEY, "base_url": "https://payment-api.khipu.com "},
    {"api_key": API_KEY, "timeout": None},
    {"api_key": API_KEY, "timeout": 0},
    {"api_key": API_KEY, "timeout": -1},
    {"api_key": API_KEY, "timeout": math.nan},
    {"api_key": API_KEY, "timeout": math.inf},
    {"api_key": API_KEY, "timeout": httpx.Timeout(10.0, read=None)},
]


def get_payment(client: KhipuClient):
    return client.get_instant_payment(payment_id=PAYMENT_ID)


@pytest.mark.parametrize("kwargs", INVALID_CONFIGS)
def test_invalid_configuration_never_sends_a_request(kwargs, httpx_mock):
    with pytest.raises(KhipuConfigurationError) as exc:
        get_payment(KhipuClient(KhipuConfig(**kwargs)))
    assert httpx_mock.get_requests() == [], "no request may be sent"
    assert API_KEY not in str(exc.value)
    assert API_KEY not in repr(exc.value.args)


@pytest.mark.parametrize(
    "env",
    [
        {"KHIPU_API_KEY": ""},
        {"KHIPU_API_KEY": API_KEY, "KHIPU_TIMEOUT": ""},
        {"KHIPU_API_KEY": API_KEY, "KHIPU_TIMEOUT": "nan"},
        {"KHIPU_API_KEY": API_KEY, "KHIPU_BASE_URL": ""},
    ],
)
def test_invalid_environment_never_sends_a_request(env, monkeypatch, httpx_mock):
    for name in ("KHIPU_API_KEY", "KHIPU_BASE_URL", "KHIPU_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(KhipuConfigurationError):
        get_payment(KhipuClient(KhipuConfig.from_env()))
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize(
    "base_url",
    [
        "https://payment-api.khipu.com",
        "https://payment-api.khipu.com/",
        "http://127.0.0.1:8080",
        "http://localhost:8080/mock",
    ],
)
def test_valid_configuration_sends_exactly_one_request(base_url, httpx_mock):
    expected = f"{base_url.rstrip('/')}/v3/payments/{PAYMENT_ID}"
    httpx_mock.add_response(method="GET", url=expected, json=PAYMENT)
    client = KhipuClient(KhipuConfig(api_key=API_KEY, base_url=base_url))

    assert get_payment(client).payment_id == PAYMENT_ID

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert str(requests[0].url) == expected
    assert requests[0].headers["x-api-key"] == API_KEY


@pytest.mark.parametrize(
    "timeout,expected",
    [
        (7.5, {"connect": 7.5, "read": 7.5, "write": 7.5, "pool": 7.5}),
        (3, {"connect": 3, "read": 3, "write": 3, "pool": 3}),
        (
            httpx.Timeout(connect=1.0, read=20.0, write=5.0, pool=2.0),
            {"connect": 1.0, "read": 20.0, "write": 5.0, "pool": 2.0},
        ),
    ],
)
def test_configured_timeout_reaches_the_request(timeout, expected, httpx_mock):
    httpx_mock.add_response(json=PAYMENT)
    get_payment(KhipuClient(KhipuConfig(api_key=API_KEY, timeout=timeout)))
    assert httpx_mock.get_requests()[0].extensions["timeout"] == expected


def test_from_env_configuration_sends_one_request(monkeypatch, httpx_mock):
    monkeypatch.setenv("KHIPU_API_KEY", API_KEY)
    monkeypatch.setenv("KHIPU_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("KHIPU_TIMEOUT", "4")
    httpx_mock.add_response(url=f"http://127.0.0.1:8080/v3/payments/{PAYMENT_ID}", json=PAYMENT)

    get_payment(KhipuClient(KhipuConfig.from_env()))

    request = httpx_mock.get_requests()[0]
    assert request.extensions["timeout"]["read"] == 4.0
    assert request.headers["x-api-key"] == API_KEY


def test_transport_timeouts_are_still_mapped(httpx_mock):
    httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))
    with pytest.raises(KhipuTimeoutError) as exc:
        get_payment(KhipuClient(KhipuConfig(api_key=API_KEY, timeout=0.5)))
    assert exc.value.request_may_have_been_delivered is True
    assert not isinstance(exc.value, KhipuConfigurationError)
    assert len(httpx_mock.get_requests()) == 1


def test_connection_errors_are_still_mapped(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    with pytest.raises(KhipuConnectionError) as exc:
        get_payment(KhipuClient(KhipuConfig(api_key=API_KEY, base_url="http://127.0.0.1:8080")))
    assert exc.value.request_may_have_been_delivered is False
    assert not isinstance(exc.value, KhipuConfigurationError)
    assert len(httpx_mock.get_requests()) == 1
