import pickle

import pytest

from khipu_sdk.errors import (
    KhipuApiError,
    KhipuConfigurationError,
    KhipuConnectionError,
    KhipuError,
    KhipuResponseError,
    KhipuTimeoutError,
    KhipuTransportError,
    KhipuValidationError,
)

ALL_ERRORS = [
    KhipuError("boom"),
    KhipuConfigurationError("boom"),
    KhipuValidationError("boom"),
    KhipuTransportError("boom"),
    KhipuTimeoutError("boom"),
    KhipuConnectionError("boom"),
    KhipuApiError(status_code=400, message="bad", payload={"errors": "x"}, body='{"errors":"x"}'),
    KhipuResponseError("malformed", status_code=200, body="<html>"),
]


class TestHierarchy:
    @pytest.mark.parametrize("exc", ALL_ERRORS, ids=lambda e: type(e).__name__)
    def test_every_error_derives_from_khipu_error(self, exc):
        assert isinstance(exc, KhipuError)

    def test_timeout_and_connection_are_transport_errors(self):
        assert issubclass(KhipuTimeoutError, KhipuTransportError)
        assert issubclass(KhipuConnectionError, KhipuTransportError)

    def test_timeout_is_not_an_api_error(self):
        """A timeout must never be mistaken for a response from Khipu."""
        assert not issubclass(KhipuTimeoutError, KhipuApiError)
        assert not issubclass(KhipuConnectionError, KhipuApiError)
        assert not issubclass(KhipuResponseError, KhipuApiError)


class TestDeliverySemantics:
    def test_timeout_defaults_to_possibly_delivered(self):
        assert KhipuTimeoutError("read timeout").request_may_have_been_delivered is True

    def test_connect_failure_can_state_request_was_not_delivered(self):
        exc = KhipuConnectionError("connect failed", request_may_have_been_delivered=False)
        assert exc.request_may_have_been_delivered is False


class TestApiError:
    def test_preserves_status_payload_and_body(self):
        exc = KhipuApiError(
            status_code=400, message="Monto inválido", payload={"errors": "amount"}, body="{...}"
        )
        assert exc.status_code == 400
        assert exc.message == "Monto inválido"
        assert exc.payload == {"errors": "amount"}
        assert exc.body == "{...}"

    def test_str_includes_status_and_message(self):
        exc = KhipuApiError(status_code=401, message="Invalid API key")
        assert str(exc) == "Khipu API error 401: Invalid API key"


class TestPickling:
    @pytest.mark.parametrize("exc", ALL_ERRORS, ids=lambda e: type(e).__name__)
    def test_round_trips_through_pickle(self, exc):
        restored = pickle.loads(pickle.dumps(exc))
        assert type(restored) is type(exc)
        assert str(restored) == str(exc)

    def test_api_error_retains_attributes_after_pickling(self):
        exc = KhipuApiError(status_code=403, message="Forbidden", payload={"a": 1}, body="raw")
        restored = pickle.loads(pickle.dumps(exc))
        assert restored.status_code == 403
        assert restored.message == "Forbidden"
        assert restored.payload == {"a": 1}
        assert restored.body == "raw"

    def test_transport_error_retains_delivery_flag_after_pickling(self):
        exc = KhipuConnectionError("nope", request_may_have_been_delivered=False)
        restored = pickle.loads(pickle.dumps(exc))
        assert restored.request_may_have_been_delivered is False
