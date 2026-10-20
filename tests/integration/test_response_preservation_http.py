"""HTTP status and body survive a generated parsing failure (#42).

The generated ``sync_detailed`` functions parse the body before they return,
so a parse failure used to discard the response. A PAC ``422`` whose
``ChargeError`` body was empty, non-JSON or incomplete was then reported as a
malformed *success* with no status (audit #41, F1), and a ``2xx`` create body
that failed strict parsing lost its status and body -- and with it the
``payment_id`` Khipu had returned (F2).

These tests assert the corrected behaviour over the real HTTP boundary:
every non-2xx is a :class:`KhipuApiError` with its real status, and a 2xx that
cannot be parsed is a :class:`KhipuResponseError` that keeps the status and a
bounded body. Exactly one request is sent in every case.
"""

from __future__ import annotations

import json
import pickle
from decimal import Decimal

import httpx
import pytest

from khipu_sdk import (
    KhipuApiError,
    KhipuClient,
    KhipuConfig,
    KhipuConnectionError,
    KhipuResponseError,
    KhipuTimeoutError,
    KhipuValidationError,
)
from khipu_sdk.errors import MAX_BODY_CHARS

BASE_URL = "https://payment-api.khipu.com"
PAYMENTS_URL = f"{BASE_URL}/v3/payments"
SUBSCRIPTION_URL = f"{BASE_URL}/v1/automatic-payment/subscription"
CHARGE_URL = f"{BASE_URL}/v1/automatic-payment/charge-intent"
API_KEY = "unit-test-api-key-must-never-leak"
PAYMENT_ID = "gqzdy6chjne9"

CREATE_RESPONSE = {
    "payment_id": PAYMENT_ID,
    "payment_url": f"https://khipu.com/payment/info/{PAYMENT_ID}",
    "simplified_transfer_url": f"https://app.khipu.com/payment/simplified/{PAYMENT_ID}",
    "transfer_url": f"https://khipu.com/payment/manual/{PAYMENT_ID}",
    "app_url": f"khipu:///pos/{PAYMENT_ID}",
    "ready_for_terminal": False,
}


@pytest.fixture
def client() -> KhipuClient:
    return KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL))


def create_payment(client: KhipuClient, **overrides):
    kwargs = dict(
        amount=Decimal("10000"),
        currency="CLP",
        subject="Aporte",
        transaction_id="CONTRIB-9f2c",
    )
    kwargs.update(overrides)
    return client.create_instant_payment(**kwargs)


def create_subscription(client: KhipuClient):
    return client.create_subscription(
        name="Jane Doe",
        email="jane@example.com",
        max_amount=Decimal("50000"),
        max_amount_per_charge=Decimal("20000"),
        currency="CLP",
        notify_url="https://example.com/pac/notify",
        return_url="https://example.com/pac/return",
        cancel_url="https://example.com/pac/cancel",
    )


def charge(client: KhipuClient):
    return client.create_charge(
        subscription_id="sub-1",
        amount=Decimal("20000"),
        subject="Monthly fee",
        error_response_url="https://example.com/pac/error",
        notify_url="https://example.com/pac/notify",
    )


def assert_no_secret(exc: Exception) -> None:
    for rendered in (str(exc), repr(exc), repr(exc.args), pickle.dumps(exc)):
        text = rendered.decode("latin-1") if isinstance(rendered, bytes) else rendered
        assert API_KEY not in text


def assert_one_request(httpx_mock) -> None:
    assert len(httpx_mock.get_requests()) == 1


class TestPacChargeRejection:
    """F1: a 422 is a definite refusal whatever its body looks like."""

    @pytest.mark.parametrize(
        "response, payload",
        [
            (
                {"json": {"error_code": "INVALID_AMOUNT", "error_message": "Monto inválido"}},
                {"error_code": "INVALID_AMOUNT", "error_message": "Monto inválido"},
            ),
            ({"json": {"error_code": "INVALID_AMOUNT"}}, {"error_code": "INVALID_AMOUNT"}),
            ({"json": {"error_message": "rechazado"}}, {"error_message": "rechazado"}),
            ({"json": {"message": "rechazado"}}, {"message": "rechazado"}),
            ({"json": {}}, {}),
            ({"json": ["not", "an", "object"]}, ["not", "an", "object"]),
            ({"content": b"Unprocessable Entity"}, None),
            ({"content": b""}, None),
        ],
        ids=[
            "complete",
            "missing-error-message",
            "missing-error-code",
            "foreign-keys",
            "empty-object",
            "json-array",
            "non-json",
            "empty",
        ],
    )
    def test_every_422_body_is_an_api_error_with_the_real_status(
        self, client, httpx_mock, response, payload
    ):
        httpx_mock.add_response(url=CHARGE_URL, status_code=422, **response)

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        error = exc.value
        assert not isinstance(error, KhipuResponseError)
        assert error.status_code == 422
        assert error.payload == payload
        if "content" in response:
            assert error.body == (response["content"].decode() or None)
        else:
            assert json.loads(error.body) == response["json"]
        assert error.message
        assert_one_request(httpx_mock)

    def test_the_rejection_reason_is_still_preferred_as_the_message(self, client, httpx_mock):
        httpx_mock.add_response(
            url=CHARGE_URL,
            status_code=422,
            json={"error_code": "SUBSCRIPTION_NOT_CHARGEABLE", "error_message": "No cobrable"},
        )

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        assert exc.value.message == "No cobrable"
        assert str(exc.value) == "Khipu API error 422: No cobrable"

    def test_an_empty_422_says_so(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=422, content=b"")

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        assert exc.value.message == "HTTP 422 with an empty response body"
        assert exc.value.payload is None
        assert exc.value.body is None

    def test_an_oversized_422_body_is_bounded(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=422, content=b"x" * 10_000)

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        assert exc.value.body is not None
        assert exc.value.body.startswith("x" * MAX_BODY_CHARS)
        assert "truncated, 10000 chars total" in exc.value.body
        assert len(exc.value.message) < 1000

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 429, 500, 503, 599])
    def test_any_other_non_2xx_is_an_api_error_too(self, client, httpx_mock, status):
        """Including statuses the generated client does not enumerate or name."""
        httpx_mock.add_response(url=CHARGE_URL, status_code=status, content=b"<html>")

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        assert exc.value.status_code == status
        assert exc.value.body == "<html>"
        assert_one_request(httpx_mock)


class TestCreateParseFailureKeepsTheResponse:
    """F2: a 2xx create body that fails parsing keeps its status and body."""

    def test_instant_payment_200_missing_a_required_field_keeps_the_payment_id(
        self, client, httpx_mock
    ):
        partial = dict(CREATE_RESPONSE)
        del partial["ready_for_terminal"]
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, json=partial)

        with pytest.raises(KhipuResponseError) as exc:
            create_payment(client)

        error = exc.value
        assert not isinstance(error, KhipuApiError)
        assert error.status_code == 200
        assert json.loads(error.body) == partial
        assert PAYMENT_ID in error.body
        assert "ready_for_terminal" in error.message
        assert isinstance(error.__cause__, KeyError)
        assert_one_request(httpx_mock)

    def test_instant_payment_200_non_json_keeps_status_and_text(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, content=b"<html>oops</html>")

        with pytest.raises(KhipuResponseError) as exc:
            create_payment(client)

        assert exc.value.status_code == 200
        assert exc.value.body == "<html>oops</html>"
        assert str(exc.value).startswith("Malformed Khipu response (HTTP 200): ")

    def test_instant_payment_200_empty_body_keeps_the_status(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, content=b"")

        with pytest.raises(KhipuResponseError) as exc:
            create_payment(client)

        assert exc.value.status_code == 200
        assert exc.value.body is None

    def test_a_payment_id_within_the_retention_limit_survives_truncation(
        self, client, httpx_mock
    ):
        padded = {"payment_id": PAYMENT_ID, "padding": "p" * 5_000}
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, json=padded)

        with pytest.raises(KhipuResponseError) as exc:
            create_payment(client)

        body = exc.value.body or ""
        assert PAYMENT_ID in body
        assert "truncated" in body
        assert len(body) < MAX_BODY_CHARS + 100

    def test_the_body_is_not_promoted_to_a_result(self, client, httpx_mock):
        """A payment id in an unusable body is evidence to reconcile, not success."""
        partial = {"payment_id": PAYMENT_ID}
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, json=partial)

        with pytest.raises(KhipuResponseError) as exc:
            create_payment(client)

        assert not hasattr(exc.value, "payment_id")

    def test_subscription_200_missing_a_required_field_keeps_status_and_body(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(
            url=SUBSCRIPTION_URL, status_code=200, json={"subscription_id": "sub-1"}
        )

        with pytest.raises(KhipuResponseError) as exc:
            create_subscription(client)

        assert exc.value.status_code == 200
        assert json.loads(exc.value.body) == {"subscription_id": "sub-1"}
        assert_one_request(httpx_mock)

    def test_charge_201_with_an_unusable_body_keeps_status_and_body(self, client, httpx_mock):
        httpx_mock.add_response(url=CHARGE_URL, status_code=201, json={"id": "charge-1"})

        with pytest.raises(KhipuResponseError) as exc:
            charge(client)

        assert exc.value.status_code == 201
        assert json.loads(exc.value.body) == {"id": "charge-1"}
        assert_one_request(httpx_mock)

    @pytest.mark.parametrize("accepted", [200, 201])
    def test_charge_accepted_statuses_with_a_usable_body_still_succeed(
        self, client, httpx_mock, accepted
    ):
        httpx_mock.add_response(
            url=CHARGE_URL, status_code=accepted, json={"payment_id": "charge-1"}
        )

        assert charge(client).payment_id == "charge-1"
        assert_one_request(httpx_mock)

    @pytest.mark.parametrize("status", [202, 204, 206, 299])
    def test_charge_undocumented_2xx_is_still_rejected_with_its_status(
        self, client, httpx_mock, status
    ):
        body = b"" if status == 204 else b'{"payment_id": "charge-1"}'
        httpx_mock.add_response(url=CHARGE_URL, status_code=status, content=body)

        with pytest.raises(KhipuResponseError) as exc:
            charge(client)

        assert exc.value.status_code == status
        assert exc.value.body == (body.decode() or None)
        assert_one_request(httpx_mock)


class TestGetParseFailureKeepsTheResponse:
    def test_get_instant_payment_with_an_undeclared_enum_keeps_status_and_body(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            status_code=200,
            json={"payment_id": PAYMENT_ID, "status": "not-a-khipu-status"},
        )

        with pytest.raises(KhipuResponseError) as exc:
            client.get_instant_payment(payment_id=PAYMENT_ID)

        assert exc.value.status_code == 200
        assert PAYMENT_ID in (exc.value.body or "")
        assert_one_request(httpx_mock)

    def test_get_subscription_missing_a_required_field_keeps_status_and_body(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(
            url=f"{SUBSCRIPTION_URL}/sub-1", status_code=200, json={"status": "ENABLED"}
        )

        with pytest.raises(KhipuResponseError) as exc:
            client.get_subscription(subscription_id="sub-1")

        assert exc.value.status_code == 200
        assert json.loads(exc.value.body) == {"status": "ENABLED"}

    @pytest.mark.parametrize(
        "call, url",
        [
            (lambda c: c.get_instant_payment(payment_id=PAYMENT_ID), f"{PAYMENTS_URL}/{PAYMENT_ID}"),
            (lambda c: c.get_subscription(subscription_id="sub-1"), f"{SUBSCRIPTION_URL}/sub-1"),
        ],
        ids=["get_instant_payment", "get_subscription"],
    )
    @pytest.mark.parametrize("status", [404, 500, 599])
    def test_get_non_2xx_with_a_non_json_body_is_an_api_error(
        self, client, httpx_mock, call, url, status
    ):
        httpx_mock.add_response(url=url, status_code=status, content=b"Not Found")

        with pytest.raises(KhipuApiError) as exc:
            call(client)

        assert exc.value.status_code == status
        assert exc.value.body == "Not Found"
        assert exc.value.payload is None
        assert_one_request(httpx_mock)


class TestHygiene:
    def test_no_secret_reaches_a_response_error_and_it_pickles(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, json={"payment_id": PAYMENT_ID})

        with pytest.raises(KhipuResponseError) as exc:
            create_payment(client)

        assert_no_secret(exc.value)
        restored = pickle.loads(pickle.dumps(exc.value))
        assert type(restored) is KhipuResponseError
        assert restored.status_code == 200
        assert restored.body == exc.value.body
        assert restored.message == exc.value.message
        assert str(restored) == str(exc.value)

    def test_no_secret_reaches_an_api_error_and_it_pickles(self, client, httpx_mock):
        httpx_mock.add_response(
            url=CHARGE_URL, status_code=422, json={"error_code": "INVALID_AMOUNT"}
        )

        with pytest.raises(KhipuApiError) as exc:
            charge(client)

        assert_no_secret(exc.value)
        restored = pickle.loads(pickle.dumps(exc.value))
        assert type(restored) is KhipuApiError
        assert restored.status_code == 422
        assert restored.payload == {"error_code": "INVALID_AMOUNT"}
        assert restored.body == exc.value.body

    def test_the_request_still_carries_the_api_key_header(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)

        assert create_payment(client).payment_id == PAYMENT_ID
        request = httpx_mock.get_requests()[0]
        assert request.headers["x-api-key"] == API_KEY
        assert request.headers["content-type"] == "application/json"
        assert request.method == "POST"


class TestTransportClassificationIsUnchanged:
    @pytest.mark.parametrize(
        "call, url",
        [
            (create_payment, PAYMENTS_URL),
            (create_subscription, SUBSCRIPTION_URL),
            (charge, CHARGE_URL),
            (lambda c: c.get_subscription(subscription_id="sub-1"), f"{SUBSCRIPTION_URL}/sub-1"),
        ],
        ids=["create_instant_payment", "create_subscription", "create_charge", "get_subscription"],
    )
    @pytest.mark.parametrize(
        "raised, expected, delivered",
        [
            (httpx.ReadTimeout("read timed out"), KhipuTimeoutError, True),
            (httpx.WriteTimeout("write timed out"), KhipuTimeoutError, True),
            (httpx.ConnectTimeout("connect timed out"), KhipuTimeoutError, False),
            (httpx.PoolTimeout("pool timed out"), KhipuTimeoutError, False),
            (httpx.ConnectError("name resolution failed"), KhipuConnectionError, False),
            (httpx.ReadError("connection reset"), KhipuConnectionError, True),
            (httpx.RemoteProtocolError("peer closed"), KhipuConnectionError, True),
        ],
        ids=lambda v: type(v).__name__ if isinstance(v, Exception) else None,
    )
    def test_transport_failures_keep_their_taxonomy_and_are_not_retried(
        self, client, httpx_mock, call, url, raised, expected, delivered
    ):
        httpx_mock.add_exception(raised, url=url)

        with pytest.raises(expected) as exc:
            call(client)

        assert type(exc.value) is expected
        assert exc.value.request_may_have_been_delivered is delivered
        assert not isinstance(exc.value, (KhipuApiError, KhipuResponseError))
        assert API_KEY not in str(exc.value)
        assert_one_request(httpx_mock)


class TestUnserialisablePayload:
    """Encoding happens before sending, so nothing reached Khipu."""

    @pytest.mark.parametrize(
        "value", [Decimal("1"), {1, 2}, float("nan")], ids=["decimal", "set", "nan"]
    )
    def test_an_unserialisable_extra_field_is_a_validation_error_with_no_request(
        self, client, httpx_mock, value
    ):
        with pytest.raises(KhipuValidationError) as exc:
            create_payment(client, custom_extension=value)

        assert "serialise" in str(exc.value)
        assert httpx_mock.get_requests() == []
