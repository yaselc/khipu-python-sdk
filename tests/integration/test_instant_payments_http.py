"""End-to-end facade tests that exercise the real HTTP boundary.

These deliberately do NOT monkeypatch the generated ``sync_detailed``
functions. Every test runs the full path:

    KhipuClient -> generated request model -> serialization -> httpx
      -> mocked HTTP response -> generated response parsing -> facade result

No network access occurs; ``pytest_httpx`` intercepts at the transport layer.
"""

from __future__ import annotations

import datetime as dt
import json
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

BASE_URL = "https://payment-api.khipu.com"
PAYMENTS_URL = f"{BASE_URL}/v3/payments"
PAYMENT_ID = "gqzdy6chjne9"
API_KEY = "unit-test-api-key"

CREATE_RESPONSE = {
    "payment_id": PAYMENT_ID,
    "payment_url": f"https://khipu.com/payment/info/{PAYMENT_ID}",
    "simplified_transfer_url": f"https://app.khipu.com/payment/simplified/{PAYMENT_ID}",
    "transfer_url": f"https://khipu.com/payment/manual/{PAYMENT_ID}",
    "app_url": f"khipu:///pos/{PAYMENT_ID}",
    "ready_for_terminal": False,
}


def get_response(**overrides: object) -> dict:
    """A complete, spec-shaped GET /v3/payments/{id} body."""
    body = {
        **CREATE_RESPONSE,
        "notification_token": "9dec8aa176c5223026919b3b5579a4776923e646ff3be686b9e6b62ec042e91f",
        "receiver_id": 985101,
        "conciliation_date": "2026-03-01T13:00:00.000Z",
        "subject": "Aporte",
        # Khipu publishes amount as a decimal string (spec example: "1000.0000").
        "amount": "10000",
        "currency": "CLP",
        "status": "done",
        "status_detail": "normal",
        "body": "Detalle",
        "picture_url": "https://example.com/pic.png",
        "receipt_url": "https://example.com/receipt",
        "return_url": "https://example.com/return",
        "cancel_url": "https://example.com/cancel",
        "notify_url": "https://example.com/notify",
        "notify_api_version": "3.0",
        "expires_date": "2026-12-31T15:45:00-04:00",
        "attachment_urls": [],
        "bank": "Banco Estado",
        "bank_id": "SDdGj",
        "payer_name": "Nombre Pagador",
        "payer_email": "pagador@example.com",
        "personal_identifier": "11.000.111-9",
        "bank_account_number": "001120490689",
        "out_of_date_conciliation": False,
        "transaction_id": "CONTRIB-9f2c",
        "custom": "CONTRIB-9f2c-custom",
        "responsible_user_email": "responsible@example.com",
        "send_reminders": False,
        "send_email": False,
        "payment_method": "simplified_transfer",
        "funds_source": "debit",
    }
    body.update(overrides)
    return body


@pytest.fixture
def client() -> KhipuClient:
    return KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL))


def create(client: KhipuClient, **overrides):
    kwargs = dict(
        amount=Decimal("10000"),
        currency="CLP",
        subject="Aporte",
        transaction_id="CONTRIB-9f2c",
    )
    kwargs.update(overrides)
    return client.create_instant_payment(**kwargs)


class TestAuthentication:
    def test_api_key_is_sent_as_x_api_key_header(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        create(client)

        request = httpx_mock.get_requests()[0]
        header_matches = request.headers.get("x-api-key") == API_KEY
        assert header_matches, "x-api-key header missing or did not match configured credential"

    def test_credential_is_not_sent_in_the_body_or_query(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        create(client)

        request = httpx_mock.get_requests()[0]
        assert API_KEY not in request.content.decode()
        assert API_KEY not in str(request.url)


class TestPaymentCreation:
    def test_sends_the_expected_json_body(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        create(
            client,
            body="Detalle del aporte",
            return_url="https://example.com/return",
            cancel_url="https://example.com/cancel",
            notify_url="https://example.com/notify",
        )

        sent = json.loads(httpx_mock.get_requests()[0].content)
        assert sent == {
            "amount": 10000,
            "currency": "CLP",
            "subject": "Aporte",
            "transaction_id": "CONTRIB-9f2c",
            "body": "Detalle del aporte",
            "return_url": "https://example.com/return",
            "cancel_url": "https://example.com/cancel",
            "notify_url": "https://example.com/notify",
        }

    def test_posts_to_the_v3_payments_endpoint(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        create(client)

        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"
        assert str(request.url) == PAYMENTS_URL

    def test_decimal_amount_serializes_as_an_exact_integer_for_clp(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        create(client, amount=Decimal("10000.0000"))

        assert json.loads(httpx_mock.get_requests()[0].content)["amount"] == 10000

    def test_decimal_amount_serializes_exactly_for_a_two_decimal_currency(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        create(client, amount=Decimal("10.50"), currency="USD")

        assert json.loads(httpx_mock.get_requests()[0].content)["amount"] == 10.5

    def test_result_exposes_every_url_khipu_returns(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        result = create(client)

        assert result.payment_id == PAYMENT_ID
        assert result.payment_url == CREATE_RESPONSE["payment_url"]
        assert result.simplified_transfer_url == CREATE_RESPONSE["simplified_transfer_url"]
        assert result.transfer_url == CREATE_RESPONSE["transfer_url"]
        assert result.app_url == CREATE_RESPONSE["app_url"]
        assert result.ready_for_terminal is False

    def test_result_has_no_misleading_always_none_status_field(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        result = create(client)

        # Khipu's create response carries no status; the facade must not pretend it does.
        assert not hasattr(result, "status")


class TestClientSideValidation:
    """Invalid input must be rejected before any HTTP request is made."""

    def test_fractional_clp_is_rejected_without_calling_khipu(self, client, httpx_mock):
        with pytest.raises(KhipuValidationError) as exc:
            create(client, amount=Decimal("9700.5"))

        assert "CLP" in str(exc.value)
        assert httpx_mock.get_requests() == [], "no request may reach Khipu"

    def test_unsupported_currency_is_rejected_without_calling_khipu(self, client, httpx_mock):
        with pytest.raises(KhipuValidationError):
            create(client, currency="XYZ")

        assert httpx_mock.get_requests() == []

    def test_zero_amount_is_rejected_without_calling_khipu(self, client, httpx_mock):
        with pytest.raises(KhipuValidationError):
            create(client, amount=Decimal("0"))

        assert httpx_mock.get_requests() == []

    def test_validation_error_is_not_reported_as_an_http_500(self, client, httpx_mock):
        with pytest.raises(KhipuValidationError) as exc:
            create(client, amount=Decimal("9700.5"))

        assert not isinstance(exc.value, KhipuApiError)


class TestPaymentRetrieval:
    def test_promotes_correlation_fields_without_touching_raw(self, client, httpx_mock):
        httpx_mock.add_response(url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response())
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.payment_id == PAYMENT_ID
        assert payment.transaction_id == "CONTRIB-9f2c"
        assert payment.custom == "CONTRIB-9f2c-custom"
        assert payment.status == "done"
        assert payment.status_detail == "normal"
        assert payment.amount == Decimal("10000")
        assert payment.currency == "CLP"
        assert payment.receiver_id == 985101
        assert payment.notification_token == get_response()["notification_token"]
        assert payment.out_of_date_conciliation is False

    def test_exposes_timestamps_as_datetimes(self, client, httpx_mock):
        httpx_mock.add_response(url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response())
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert isinstance(payment.expires_date, dt.datetime)
        assert isinstance(payment.conciliation_date, dt.datetime)
        assert payment.expires_date.year == 2026

    @pytest.mark.parametrize("status", ["pending", "verifying", "done"])
    def test_exposes_the_real_khipu_status_values_as_plain_strings(
        self, client, httpx_mock, status
    ):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response(status=status)
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.status == status
        assert type(payment.status) is str, "facade must not leak the generated enum type"

    def test_surfaces_reversed_status_detail_without_deciding_policy(self, client, httpx_mock):
        """status=done + status_detail=reversed means the money went back to the payer."""
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            json=get_response(status="done", status_detail="reversed"),
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.status == "done"
        assert payment.status_detail == "reversed"
        assert type(payment.status_detail) is str

    def test_raw_remains_available_as_an_escape_hatch(self, client, httpx_mock):
        httpx_mock.add_response(url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response())
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.raw.payer_email == "pagador@example.com"

    def test_repr_does_not_leak_payer_pii_from_raw(self, client, httpx_mock):
        httpx_mock.add_response(url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response())
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        text = repr(payment)
        assert "11.000.111-9" not in text
        assert "001120490689" not in text


class TestAmountRepresentation:
    """The published spec types payment amounts as strings; the facade must keep
    exposing Decimal regardless of how the JSON encodes the number."""

    def test_string_amount_becomes_decimal(self, client, httpx_mock):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response(amount="10000")
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.amount == Decimal("10000")
        assert isinstance(payment.amount, Decimal)

    def test_string_amount_in_the_specs_four_decimal_form(self, client, httpx_mock):
        """The spec's own example is "1000.0000"."""
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response(amount="10000.0000")
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.amount == Decimal("10000")

    def test_fractional_string_amount_keeps_full_precision(self, client, httpx_mock):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            json=get_response(amount="0.1000", currency="USD"),
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.amount == Decimal("0.1")

    def test_numeric_amount_still_supported_for_compatibility(self, client, httpx_mock):
        """Older responses encoded amount as a JSON number; keep accepting them."""
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response(amount=10000)
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.amount == Decimal("10000")

    def test_fractional_numeric_amount_avoids_binary_float_noise(self, client, httpx_mock):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            json=get_response(amount=0.1, currency="USD"),
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.amount == Decimal("0.1")

    def test_amount_is_never_exposed_as_float_or_str(self, client, httpx_mock):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response(amount="10000.0000")
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert not isinstance(payment.amount, (float, str))


class TestRefundStatusDetail:
    """Khipu's published status_detail vocabulary now includes refund states.

    The SDK surfaces them verbatim and makes no business decision about them.
    """

    @pytest.mark.parametrize(
        "status_detail",
        [
            "pending",
            "normal",
            "marked-paid-by-receiver",
            "rejected-by-payer",
            "marked-as-abuse",
            "reversed",
            "partially-refunded",
            "fully-refunded",
        ],
    )
    def test_every_published_status_detail_reaches_the_facade_as_a_string(
        self, client, httpx_mock, status_detail
    ):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            json=get_response(status_detail=status_detail),
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.status_detail == status_detail
        assert type(payment.status_detail) is str

    def test_partially_refunded_is_surfaced_alongside_done(self, client, httpx_mock):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            json=get_response(status="done", status_detail="partially-refunded"),
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.status == "done"
        assert payment.status_detail == "partially-refunded"

    def test_fully_refunded_is_surfaced_alongside_done(self, client, httpx_mock):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            json=get_response(status="done", status_detail="fully-refunded"),
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        assert payment.status == "done"
        assert payment.status_detail == "fully-refunded"

    def test_refund_states_need_no_raw_access(self, client, httpx_mock):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            json=get_response(status="done", status_detail="fully-refunded"),
        )
        payment = client.get_instant_payment(payment_id=PAYMENT_ID)

        promoted = (payment.status, payment.status_detail, payment.amount, payment.transaction_id)
        assert all(v is not None for v in promoted)


class TestCorrelation:
    def test_transaction_id_and_custom_round_trip_through_create_and_get(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE)
        httpx_mock.add_response(url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response())

        create(client, custom="CONTRIB-9f2c-custom")
        sent = json.loads(httpx_mock.get_requests()[0].content)
        assert sent["transaction_id"] == "CONTRIB-9f2c"
        assert sent["custom"] == "CONTRIB-9f2c-custom"

        fetched = client.get_instant_payment(payment_id=PAYMENT_ID)
        assert fetched.transaction_id == sent["transaction_id"]
        assert fetched.custom == sent["custom"]

    def test_sdk_makes_no_deduplication_claim_and_does_not_cache_creates(
        self, client, httpx_mock
    ):
        """transaction_id is correlation only. Two creates with the same
        transaction_id produce two independent HTTP requests: the SDK provides
        no duplicate protection and Khipu documents none."""
        httpx_mock.add_response(url=PAYMENTS_URL, json=CREATE_RESPONSE, is_reusable=True)

        create(client)
        create(client)

        assert len(httpx_mock.get_requests()) == 2


class TestApiErrors:
    def test_400_preserves_khipus_structured_error_body(self, client, httpx_mock):
        httpx_mock.add_response(
            url=PAYMENTS_URL, status_code=400, json={"message": "Monto inválido", "code": 42}
        )
        with pytest.raises(KhipuApiError) as exc:
            create(client)

        assert exc.value.status_code == 400
        assert exc.value.message == "Monto inválido"
        assert exc.value.payload == {"message": "Monto inválido", "code": 42}
        assert "Monto inválido" in str(exc.value)

    def test_400_with_non_json_body_keeps_a_bounded_text_message(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=400, content=b"Bad Request")
        with pytest.raises(KhipuApiError) as exc:
            create(client)

        assert exc.value.status_code == 400
        assert "Bad Request" in exc.value.message
        assert exc.value.payload is None

    def test_oversized_error_body_is_truncated(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=400, content=b"x" * 10_000)
        with pytest.raises(KhipuApiError) as exc:
            create(client)

        assert len(exc.value.message) < 1000
        assert "truncated" in exc.value.message

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_failures_keep_their_status_and_message(self, client, httpx_mock, status):
        httpx_mock.add_response(
            url=PAYMENTS_URL, status_code=status, json={"message": "Invalid API key"}
        )
        with pytest.raises(KhipuApiError) as exc:
            create(client)

        assert exc.value.status_code == status
        assert exc.value.message == "Invalid API key"

    def test_khipu_500_is_an_api_error_distinguishable_from_a_local_timeout(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(
            url=PAYMENTS_URL, status_code=500, json={"message": "Internal error"}
        )
        with pytest.raises(KhipuApiError) as exc:
            create(client)

        assert exc.value.status_code == 500
        assert not isinstance(exc.value, KhipuTimeoutError)

    def test_undocumented_status_still_maps_to_an_api_error(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=429, json={"message": "slow down"})
        with pytest.raises(KhipuApiError) as exc:
            create(client)

        assert exc.value.status_code == 429

    def test_error_message_never_contains_the_api_key(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=403, json={"message": "denied"})
        with pytest.raises(KhipuApiError) as exc:
            create(client)

        assert API_KEY not in str(exc.value)
        assert API_KEY not in repr(exc.value)


class TestTransportFailures:
    def test_read_timeout_raises_khipu_timeout_error(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))
        with pytest.raises(KhipuTimeoutError) as exc:
            create(client)

        assert not isinstance(exc.value, KhipuApiError)
        assert exc.value.request_may_have_been_delivered is True

    def test_connect_timeout_is_a_timeout_that_was_not_delivered(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectTimeout("connect timed out"))
        with pytest.raises(KhipuTimeoutError) as exc:
            create(client)

        assert exc.value.request_may_have_been_delivered is False

    def test_connect_error_raises_khipu_connection_error(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectError("name resolution failed"))
        with pytest.raises(KhipuConnectionError) as exc:
            create(client)

        assert not isinstance(exc.value, KhipuTimeoutError)
        assert exc.value.request_may_have_been_delivered is False

    def test_broken_stream_is_a_connection_error_that_may_have_been_delivered(
        self, client, httpx_mock
    ):
        httpx_mock.add_exception(httpx.ReadError("connection reset"))
        with pytest.raises(KhipuConnectionError) as exc:
            create(client)

        assert exc.value.request_may_have_been_delivered is True

    def test_transport_failure_message_never_contains_the_api_key(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))
        with pytest.raises(KhipuTimeoutError) as exc:
            create(client)

        assert API_KEY not in str(exc.value)

    def test_create_payment_is_never_retried_automatically(self, client, httpx_mock):
        """A retry could create a second live payment; Khipu offers no idempotency key."""
        httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))
        with pytest.raises(KhipuTimeoutError):
            create(client)

        assert len(httpx_mock.get_requests()) == 1

    def test_get_payment_is_not_retried_either(self, client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))
        with pytest.raises(KhipuTimeoutError):
            client.get_instant_payment(payment_id=PAYMENT_ID)

        assert len(httpx_mock.get_requests()) == 1


class TestMalformedResponses:
    def test_malformed_json_on_success_is_a_response_error_not_a_fake_500(
        self, client, httpx_mock
    ):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, content=b"<html>oops</html>")
        with pytest.raises(KhipuResponseError) as exc:
            create(client)

        assert not isinstance(exc.value, KhipuApiError)

    def test_missing_required_field_on_success_is_a_response_error(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, json={"payment_id": PAYMENT_ID})
        with pytest.raises(KhipuResponseError) as exc:
            create(client)

        assert "payment_url" in str(exc.value)

    def test_missing_required_field_on_get_is_a_response_error(self, client, httpx_mock):
        incomplete = get_response()
        del incomplete["notification_token"]
        httpx_mock.add_response(url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=incomplete)

        with pytest.raises(KhipuResponseError):
            client.get_instant_payment(payment_id=PAYMENT_ID)

    def test_response_error_is_not_confused_with_a_khipu_500(self, client, httpx_mock):
        httpx_mock.add_response(url=PAYMENTS_URL, status_code=200, content=b"not json")
        with pytest.raises(KhipuResponseError) as exc:
            create(client)

        assert getattr(exc.value, "status_code", None) != 500


REFUND_PAID = {
    "id": "b31bd9aa-273b-4aed-9516-85866d47a931",
    "status": "paid",
    "amount": "600.0000",
    "currency": "CLP",
    "request_date": "2026-08-28T14:03:22.000Z",
    "authorization_date": "2026-08-28T14:05:12.000Z",
    "payout_date": "2026-09-01T09:30:00.000Z",
}
REFUND_EXPIRED = {
    "id": "9f2e7c55-4d18-4b6a-b7e3-8c0d1a2f3b4c",
    "status": "expired",
    "amount": "150.0000",
    "currency": "CLP",
    "request_date": "2026-08-28T14:03:22.000Z",
    "expiration_date": "2026-08-31T03:00:00.000Z",
}


class TestRefundSettlementFields:
    """Khipu's 2026-09 Instant Payments revision adds three optional fields.

    ``refunds``, ``total_refunded`` and ``void_payout_date`` are **additive and
    optional**: no required field changed, and the ``status`` / ``status_detail``
    vocabularies are byte-identical to the previous document. They refine *when
    money actually moved* -- an expired refund never pays out, and
    ``total_refunded`` excludes those -- which the ``status_detail`` vocabulary
    alone cannot express.

    The facade deliberately does not promote them yet: that is an API-design
    decision, not a spec-sync one. These tests pin that they parse, that
    absence is fine, and that they are reachable, so promoting them later is a
    small step rather than a rediscovery.
    """

    def get(self, client, httpx_mock, **overrides):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}", json=get_response(**overrides)
        )
        return client.get_instant_payment(payment_id=PAYMENT_ID)

    def test_a_body_carrying_the_new_fields_parses(self, client, httpx_mock):
        status = self.get(
            client,
            httpx_mock,
            status_detail="partially-refunded",
            refunds=[REFUND_PAID, REFUND_EXPIRED],
            total_refunded="600.0000",
        )

        assert status.status == "done"
        assert status.status_detail == "partially-refunded"

    def test_a_body_without_them_still_parses(self, client, httpx_mock):
        """They are optional: the previous document's bodies remain valid."""
        status = self.get(client, httpx_mock)

        assert status.status_detail == "normal"
        assert type(status.raw.refunds).__name__ == "Unset"
        assert type(status.raw.total_refunded).__name__ == "Unset"
        assert type(status.raw.void_payout_date).__name__ == "Unset"

    def test_promoted_fields_are_unaffected_by_the_new_ones(self, client, httpx_mock):
        """The spec sync must not disturb anything a caller already relies on."""
        status = self.get(
            client,
            httpx_mock,
            refunds=[REFUND_PAID],
            total_refunded="600.0000",
        )

        assert status.payment_id == PAYMENT_ID
        assert status.transaction_id == "CONTRIB-9f2c"
        assert status.custom == "CONTRIB-9f2c-custom"
        assert status.amount == Decimal("10000")
        assert status.currency == "CLP"
        assert status.receiver_id == 985101
        assert status.notification_token.startswith("9dec8aa1")
        assert status.out_of_date_conciliation is False

    @pytest.mark.parametrize(
        "refund_status", ["pending", "authorized", "paid", "expired"]
    )
    def test_every_published_refund_status_parses(
        self, client, httpx_mock, refund_status
    ):
        status = self.get(
            client,
            httpx_mock,
            refunds=[{**REFUND_PAID, "status": refund_status}],
        )

        assert status.raw.refunds[0].status.value == refund_status

    def test_refund_detail_is_reachable_through_raw(self, client, httpx_mock):
        status = self.get(
            client, httpx_mock, refunds=[REFUND_PAID, REFUND_EXPIRED]
        )

        paid, expired = status.raw.refunds
        assert paid.id == REFUND_PAID["id"]
        assert paid.payout_date == dt.datetime(
            2026, 9, 1, 9, 30, tzinfo=dt.timezone.utc
        )
        assert type(expired.payout_date).__name__ == "Unset", (
            "an expired refund never paid out; absence must not read as a date"
        )
        assert expired.expiration_date == dt.datetime(
            2026, 8, 31, 3, 0, tzinfo=dt.timezone.utc
        )

    def test_total_refunded_is_reported_verbatim_and_never_recomputed(
        self, client, httpx_mock
    ):
        """Khipu excludes expired refunds from this total. The SDK does not sum."""
        status = self.get(
            client,
            httpx_mock,
            refunds=[REFUND_PAID, REFUND_EXPIRED],
            total_refunded="600.0000",
        )

        assert status.raw.total_refunded == "600.0000"

    def test_void_payout_date_parses_on_a_reversed_payment(self, client, httpx_mock):
        status = self.get(
            client,
            httpx_mock,
            status_detail="reversed",
            void_payout_date="2026-09-02T09:30:00.000Z",
        )

        assert status.status_detail == "reversed"
        assert status.raw.void_payout_date == dt.datetime(
            2026, 9, 2, 9, 30, tzinfo=dt.timezone.utc
        )

    def test_an_unknown_future_field_is_kept_not_dropped(self, client, httpx_mock):
        status = self.get(client, httpx_mock, some_future_field="x")

        assert status.raw.additional_properties["some_future_field"] == "x"


class TestInstantPaymentsSuccessStatusIsUnchanged:
    """Instant Payments declares exactly 200. Nothing else may be read as success.

    The Automatic Payments charge endpoint carries a narrow compatibility
    allowance for a 200 alongside its documented 201. That allowance is
    endpoint-scoped, and these tests exist so it can never quietly become a
    global rule.
    """

    @pytest.mark.parametrize("status_code", [201, 202, 204])
    def test_create_rejects_a_success_status_khipu_does_not_document(
        self, client, httpx_mock, status_code
    ):
        httpx_mock.add_response(
            url=PAYMENTS_URL, status_code=status_code, json=CREATE_RESPONSE
        )

        with pytest.raises(KhipuResponseError):
            create(client)

    @pytest.mark.parametrize("status_code", [201, 202, 204])
    def test_get_rejects_a_success_status_khipu_does_not_document(
        self, client, httpx_mock, status_code
    ):
        httpx_mock.add_response(
            url=f"{PAYMENTS_URL}/{PAYMENT_ID}",
            status_code=status_code,
            json=get_response(),
        )

        with pytest.raises(KhipuResponseError):
            client.get_instant_payment(payment_id=PAYMENT_ID)
