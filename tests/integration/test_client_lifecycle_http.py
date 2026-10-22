"""``KhipuClient`` HTTP pool lifecycle over the real httpx stack (#54).

The facade owns one lazily built ``httpx.Client`` per API. These tests run real
``httpx.Client`` and ``httpx.HTTPTransport`` objects and replace only
``HTTPTransport.handle_request`` with an in-memory responder, so pools are
really built, really used and really closed, and nothing reaches the network.

They deliberately avoid ``pytest-httpx`` so the same file also runs against
the declared minimum ``httpx`` version, which that plugin no longer supports.
"""

from __future__ import annotations

import logging
import pickle
from decimal import Decimal
from typing import Any, Callable, Optional

import httpx
import pytest

from khipu_sdk import (
    KhipuClient,
    KhipuConfig,
    KhipuConfigurationError,
    KhipuError,
    KhipuTimeoutError,
)

BASE_URL = "https://payment-api.khipu.com"
API_KEY = "lifecycle-test-api-key-must-never-leak"
PAYMENT_ID = "gqzdy6chjne9"

PAYMENT_CREATED = {
    "payment_id": PAYMENT_ID,
    "payment_url": f"https://khipu.com/payment/info/{PAYMENT_ID}",
    "simplified_transfer_url": f"https://app.khipu.com/payment/simplified/{PAYMENT_ID}",
    "transfer_url": f"https://khipu.com/payment/manual/{PAYMENT_ID}",
    "app_url": f"khipu:///pos/{PAYMENT_ID}",
    "ready_for_terminal": False,
}
PAYMENT_STATUS = {
    **PAYMENT_CREATED,
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
    "funds_source": "debit",
}
SUBSCRIPTION_CREATED = {
    "subscription_id": "sub-1",
    "redirect_url": "https://khipu.com/pac/redirect/sub-1",
}
SUBSCRIPTION_STATUS = {
    "subscription_id": "sub-1",
    "status": "ENABLED",
    "developer": False,
    "service_reference": "ref-1",
}
CHARGE_CREATED = {"payment_id": "charge-1"}

ROUTES: dict[tuple[str, str], tuple[int, Any]] = {
    ("POST", "/v3/payments"): (200, PAYMENT_CREATED),
    ("GET", f"/v3/payments/{PAYMENT_ID}"): (200, PAYMENT_STATUS),
    ("POST", "/v1/automatic-payment/subscription"): (200, SUBSCRIPTION_CREATED),
    ("GET", "/v1/automatic-payment/subscription/sub-1"): (200, SUBSCRIPTION_STATUS),
    ("POST", "/v1/automatic-payment/charge-intent"): (201, CHARGE_CREATED),
}


class FakeNetwork:
    """Records what the real httpx stack hands to the transport layer."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.pools_built = 0
        self.pool_closes = 0
        self.transport_closes = 0
        self.failure: Optional[Exception] = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        status, body = ROUTES[(request.method, request.url.path)]
        return httpx.Response(status, json=body, request=request)


@pytest.fixture
def network(monkeypatch) -> FakeNetwork:
    fake = FakeNetwork()
    real_transport_close = httpx.HTTPTransport.close
    real_client_init = httpx.Client.__init__
    real_client_close = httpx.Client.close

    def handle_request(transport: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        return fake.handle_request(request)

    def transport_close(transport: httpx.HTTPTransport) -> None:
        fake.transport_closes += 1
        real_transport_close(transport)

    def client_init(client: httpx.Client, *args: Any, **kwargs: Any) -> None:
        fake.pools_built += 1
        real_client_init(client, *args, **kwargs)

    def client_close(client: httpx.Client) -> None:
        fake.pool_closes += 1
        real_client_close(client)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle_request)
    monkeypatch.setattr(httpx.HTTPTransport, "close", transport_close)
    monkeypatch.setattr(httpx.Client, "__init__", client_init)
    monkeypatch.setattr(httpx.Client, "close", client_close)
    return fake


@pytest.fixture
def client() -> KhipuClient:
    return KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL, timeout=7.5))


def instant_pool(client: KhipuClient) -> Optional[httpx.Client]:
    return client._instant._client


def pac_pool(client: KhipuClient) -> Optional[httpx.Client]:
    return client._automatic._client


def use_instant(client: KhipuClient) -> None:
    client.get_instant_payment(payment_id=PAYMENT_ID)


def use_pac(client: KhipuClient) -> None:
    client.get_subscription(subscription_id="sub-1")


#: Every public operation, with arguments that would otherwise succeed.
OPERATIONS: dict[str, Callable[[KhipuClient], Any]] = {
    "create_instant_payment": lambda c: c.create_instant_payment(
        amount=Decimal("10000"), currency="CLP", subject="Aporte", transaction_id="ORDER-1"
    ),
    "get_instant_payment": use_instant,
    "create_subscription": lambda c: c.create_subscription(
        name="Jane Doe",
        email="jane@example.com",
        max_amount=Decimal("50000"),
        max_amount_per_charge=Decimal("20000"),
        currency="CLP",
        notify_url="https://example.com/pac/notify",
        return_url="https://example.com/pac/return",
        cancel_url="https://example.com/pac/cancel",
    ),
    "get_subscription": use_pac,
    "create_charge": lambda c: c.create_charge(
        subscription_id="sub-1",
        amount=Decimal("20000"),
        subject="Monthly fee",
        error_response_url="https://example.com/pac/error",
        notify_url="https://example.com/pac/notify",
    ),
}

#: Arguments the SDK would reject locally; a closed client must say "closed" first.
INVALID_OPERATIONS: dict[str, Callable[[KhipuClient], Any]] = {
    "create_instant_payment": lambda c: c.create_instant_payment(
        amount=Decimal("10000.5"), currency="CLP", subject="Aporte", transaction_id="ORDER-1"
    ),
    "create_subscription": lambda c: c.create_subscription(
        name="Jane Doe",
        email="jane@example.com",
        max_amount=Decimal("1"),
        max_amount_per_charge=Decimal("1"),
        currency="XXX",
        notify_url="https://example.com/pac/notify",
        return_url="https://example.com/pac/return",
        cancel_url="https://example.com/pac/cancel",
    ),
    "create_charge": lambda c: c.create_charge(
        subscription_id="sub-1",
        amount=Decimal("0.5"),
        currency="CLP",
        subject="Monthly fee",
        error_response_url="https://example.com/pac/error",
        notify_url="https://example.com/pac/notify",
    ),
}


def fail_close_after_closing(
    monkeypatch, pool: httpx.Client, exc: Exception
) -> list[httpx.Client]:
    """Make ``pool.close()`` release its connections and then raise ``exc``."""
    calls: list[httpx.Client] = []
    real_close = pool.close

    def close() -> None:
        calls.append(pool)
        real_close()
        raise exc

    monkeypatch.setattr(pool, "close", close)
    return calls


# ----------------------------------------------------------------------
# Behaviour before close is unchanged
# ----------------------------------------------------------------------


class TestBeforeClose:
    def test_no_pool_exists_until_an_api_is_used(self, network, client):
        assert instant_pool(client) is None
        assert pac_pool(client) is None
        assert network.pools_built == 0

    @pytest.mark.parametrize("name", sorted(OPERATIONS))
    def test_each_operation_sends_one_request_with_key_and_timeout(self, network, client, name):
        OPERATIONS[name](client)

        (request,) = network.requests
        assert str(request.url).startswith(BASE_URL)
        assert request.headers["x-api-key"] == API_KEY
        assert request.extensions["timeout"] == httpx.Timeout(7.5).as_dict()

    def test_each_api_reuses_its_own_pool(self, network, client):
        use_instant(client)
        use_instant(client)
        use_pac(client)
        use_pac(client)

        assert network.pools_built == 2
        assert instant_pool(client) is not pac_pool(client)
        assert not instant_pool(client).is_closed
        assert not pac_pool(client).is_closed
        assert len(network.requests) == 4

    def test_results_are_parsed_as_before(self, network, client):
        created = OPERATIONS["create_instant_payment"](client)
        status = client.get_instant_payment(payment_id=PAYMENT_ID)
        charge = OPERATIONS["create_charge"](client)

        assert created.payment_id == PAYMENT_ID
        assert status.amount == Decimal("10000")
        assert charge.payment_id == "charge-1"

    def test_timeout_mapping_is_unchanged(self, network, client):
        network.failure = httpx.ReadTimeout("synthetic read timeout")

        with pytest.raises(KhipuTimeoutError) as caught:
            OPERATIONS["create_instant_payment"](client)

        assert caught.value.request_may_have_been_delivered is True
        assert len(network.requests) == 1

    def test_repr_is_unchanged_and_keyless(self, client):
        assert repr(client) == f"KhipuClient(base_url={BASE_URL!r})"
        client.close()
        assert repr(client) == f"KhipuClient(base_url={BASE_URL!r})"
        assert API_KEY not in repr(client)


# ----------------------------------------------------------------------
# close()
# ----------------------------------------------------------------------


class TestClose:
    def test_close_before_first_use_builds_no_pool(self, network, client):
        client.close()

        assert instant_pool(client) is None
        assert pac_pool(client) is None
        assert network.pools_built == 0
        assert network.pool_closes == 0
        assert network.transport_closes == 0
        assert network.requests == []

    def test_close_with_only_the_instant_pool(self, network, client):
        use_instant(client)
        pool = instant_pool(client)

        client.close()

        assert pool.is_closed
        assert pac_pool(client) is None
        assert network.pools_built == 1
        assert network.pool_closes == 1
        assert network.transport_closes >= 1, "the pool's transport must be released"

    def test_close_with_only_the_pac_pool(self, network, client):
        use_pac(client)
        pool = pac_pool(client)

        client.close()

        assert pool.is_closed
        assert instant_pool(client) is None
        assert network.pools_built == 1
        assert network.pool_closes == 1

    def test_close_with_both_pools(self, network, client):
        use_instant(client)
        use_pac(client)
        instant, pac = instant_pool(client), pac_pool(client)

        client.close()

        assert instant.is_closed
        assert pac.is_closed
        assert network.pools_built == 2
        assert network.pool_closes == 2

    def test_close_returns_none(self, client):
        assert client.close() is None

    def test_repeated_close_is_a_no_op(self, network, client):
        use_instant(client)
        use_pac(client)

        client.close()
        client.close()
        client.close()

        assert network.pool_closes == 2
        assert network.pools_built == 2

    def test_repeated_close_before_use_still_builds_nothing(self, network, client):
        client.close()
        client.close()

        assert network.pools_built == 0

    def test_close_sends_no_request(self, network, client):
        use_instant(client)
        use_pac(client)
        sent = len(network.requests)

        client.close()

        assert len(network.requests) == sent

    def test_config_stays_readable_after_close(self, client):
        client.close()

        assert client.config.base_url == BASE_URL


# ----------------------------------------------------------------------
# Operations after close
# ----------------------------------------------------------------------


class TestAfterClose:
    @pytest.mark.parametrize("name", sorted(OPERATIONS))
    def test_unused_client_rejects_every_operation_without_building_a_pool(
        self, network, client, name
    ):
        client.close()

        with pytest.raises(KhipuConfigurationError, match="closed"):
            OPERATIONS[name](client)

        assert network.requests == []
        assert network.pools_built == 0
        assert instant_pool(client) is None
        assert pac_pool(client) is None

    @pytest.mark.parametrize("name", sorted(OPERATIONS))
    def test_used_client_rejects_every_operation_without_sending(self, network, client, name):
        use_instant(client)
        use_pac(client)
        pools = (instant_pool(client), pac_pool(client))
        client.close()
        sent = len(network.requests)

        with pytest.raises(KhipuConfigurationError, match="closed"):
            OPERATIONS[name](client)

        assert len(network.requests) == sent
        assert (instant_pool(client), pac_pool(client)) == pools
        assert all(pool.is_closed for pool in pools)
        assert network.pools_built == 2

    @pytest.mark.parametrize("name", sorted(INVALID_OPERATIONS))
    def test_closed_is_reported_before_input_validation(self, network, client, name):
        client.close()

        with pytest.raises(KhipuConfigurationError, match="closed"):
            INVALID_OPERATIONS[name](client)

        assert network.requests == []

    def test_after_a_failed_close_operations_are_still_rejected(
        self, monkeypatch, network, client
    ):
        use_instant(client)
        fail_close_after_closing(monkeypatch, instant_pool(client), OSError("synthetic"))
        with pytest.raises(OSError):
            client.close()
        sent = len(network.requests)

        with pytest.raises(KhipuConfigurationError, match="closed"):
            use_pac(client)

        assert len(network.requests) == sent
        assert pac_pool(client) is None

    def test_the_client_is_closed_even_if_cleanup_is_interrupted(
        self, monkeypatch, network, client
    ):
        # The closed flag is set before any pool is touched, so not even a
        # BaseException escaping from httpx can leave a usable client behind.
        use_instant(client)
        fail_close_after_closing(monkeypatch, instant_pool(client), KeyboardInterrupt())
        with pytest.raises(KeyboardInterrupt):
            client.close()

        with pytest.raises(KhipuConfigurationError, match="closed"):
            use_pac(client)

        assert pac_pool(client) is None

    def test_the_closed_error_is_an_sdk_error_without_secrets(self, client):
        client.close()

        with pytest.raises(KhipuConfigurationError) as caught:
            use_instant(client)

        error = caught.value
        assert isinstance(error, KhipuError)
        assert isinstance(error, ValueError)
        assert API_KEY not in str(error)
        assert API_KEY not in repr(error)
        assert error.__cause__ is None
        assert error.__context__ is None
        assert "No request was sent" in str(error)

    def test_the_closed_error_survives_pickling(self, client):
        client.close()
        with pytest.raises(KhipuConfigurationError) as caught:
            use_pac(client)

        clone = pickle.loads(pickle.dumps(caught.value))

        assert type(clone) is KhipuConfigurationError
        assert str(clone) == str(caught.value)


# ----------------------------------------------------------------------
# Context manager
# ----------------------------------------------------------------------


class TestContextManager:
    def test_enter_returns_the_client_and_builds_no_pool(self, network, client):
        with client as entered:
            assert entered is client
            assert network.pools_built == 0

    def test_normal_exit_closes_every_created_pool(self, network, client):
        with client:
            use_instant(client)
            use_pac(client)
            instant, pac = instant_pool(client), pac_pool(client)

        assert instant.is_closed
        assert pac.is_closed
        with pytest.raises(KhipuConfigurationError, match="closed"):
            use_instant(client)

    def test_constructor_in_with_statement(self, network):
        with KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL)) as client:
            use_instant(client)
            pool = instant_pool(client)

        assert pool.is_closed
        assert pac_pool(client) is None
        assert network.pools_built == 1

    def test_exit_after_an_sdk_exception_closes_and_reraises_it(self, network, client):
        network.failure = httpx.ReadTimeout("synthetic read timeout")

        with pytest.raises(KhipuTimeoutError) as caught:
            with client:
                OPERATIONS["create_instant_payment"](client)

        assert caught.value.request_may_have_been_delivered is True
        assert instant_pool(client).is_closed
        assert pac_pool(client) is None

    def test_exit_after_an_arbitrary_exception_closes_and_reraises_it(self, network, client):
        marker = RuntimeError("application failure")

        with pytest.raises(RuntimeError) as caught:
            with client:
                use_pac(client)
                raise marker

        assert caught.value is marker
        assert pac_pool(client).is_closed

    def test_exit_does_not_suppress_exceptions(self, client):
        assert client.__exit__(None, None, None) is None

    def test_a_cleanup_failure_never_replaces_the_body_exception(
        self, monkeypatch, network, client, caplog
    ):
        marker = RuntimeError("application failure")

        with caplog.at_level(logging.WARNING, logger="khipu_sdk.client"):
            with pytest.raises(RuntimeError) as caught:
                with client:
                    use_instant(client)
                    use_pac(client)
                    fail_close_after_closing(
                        monkeypatch, instant_pool(client), OSError("synthetic close failure")
                    )
                    raise marker

        assert caught.value is marker
        assert pac_pool(client).is_closed, "the second pool must still be closed"
        assert "Instant Payments" in caplog.text
        assert "OSError" in caplog.text

    def test_a_cleanup_failure_after_a_clean_body_propagates(self, monkeypatch, network, client):
        failure = OSError("synthetic close failure")

        with pytest.raises(OSError) as caught:
            with client:
                use_instant(client)
                fail_close_after_closing(monkeypatch, instant_pool(client), failure)

        assert caught.value is failure

    def test_entering_a_closed_client_is_rejected(self, network, client):
        client.close()

        with pytest.raises(KhipuConfigurationError, match="closed"):
            with client:
                pass  # pragma: no cover - never entered

        assert network.pools_built == 0

    def test_nested_with_blocks_close_on_the_inner_exit(self, network, client):
        with client:
            with client:
                use_instant(client)
            with pytest.raises(KhipuConfigurationError, match="closed"):
                use_instant(client)

        assert network.pool_closes == 1

    def test_explicit_close_inside_a_with_block(self, network, client):
        with client:
            use_instant(client)
            client.close()

        assert network.pool_closes == 1


# ----------------------------------------------------------------------
# Cleanup failures
# ----------------------------------------------------------------------


class TestCleanupFailures:
    def test_instant_failure_still_closes_pac_and_is_reraised(self, monkeypatch, network, client):
        use_instant(client)
        use_pac(client)
        failure = OSError("synthetic close failure")
        fail_close_after_closing(monkeypatch, instant_pool(client), failure)

        with pytest.raises(OSError) as caught:
            client.close()

        assert caught.value is failure
        assert pac_pool(client).is_closed

    def test_pac_failure_is_reraised_after_instant_is_closed(self, monkeypatch, network, client):
        use_instant(client)
        use_pac(client)
        failure = OSError("synthetic close failure")
        fail_close_after_closing(monkeypatch, pac_pool(client), failure)

        with pytest.raises(OSError) as caught:
            client.close()

        assert caught.value is failure
        assert instant_pool(client).is_closed

    def test_when_both_fail_the_first_is_raised_and_both_are_logged(
        self, monkeypatch, network, client, caplog
    ):
        use_instant(client)
        use_pac(client)
        first = OSError("first synthetic failure")
        second = RuntimeError("second synthetic failure")
        instant_calls = fail_close_after_closing(monkeypatch, instant_pool(client), first)
        pac_calls = fail_close_after_closing(monkeypatch, pac_pool(client), second)

        with caplog.at_level(logging.WARNING, logger="khipu_sdk.client"):
            with pytest.raises(OSError) as caught:
                client.close()

        assert caught.value is first
        assert len(instant_calls) == len(pac_calls) == 1
        messages = [record.getMessage() for record in caplog.records]
        assert messages == [
            "Closing the Instant Payments HTTP connection pool failed (OSError)",
            "Closing the Automatic Payments HTTP connection pool failed (RuntimeError)",
        ]

    def test_cleanup_logs_carry_no_secret_or_exception_message(
        self, monkeypatch, network, client, caplog
    ):
        use_instant(client)
        fail_close_after_closing(
            monkeypatch, instant_pool(client), OSError(f"leaky message {API_KEY}")
        )

        with caplog.at_level(logging.DEBUG, logger="khipu_sdk"):
            with pytest.raises(OSError):
                client.close()

        assert API_KEY not in caplog.text
        assert "leaky message" not in caplog.text

    def test_the_raised_failure_has_no_unrelated_context(self, monkeypatch, network, client):
        use_instant(client)
        use_pac(client)
        first = OSError("first")
        fail_close_after_closing(monkeypatch, instant_pool(client), first)
        fail_close_after_closing(monkeypatch, pac_pool(client), RuntimeError("second"))

        with pytest.raises(OSError) as caught:
            client.close()

        assert caught.value.__context__ is None

    def test_close_after_a_failed_close_is_a_no_op(self, monkeypatch, network, client):
        use_instant(client)
        calls = fail_close_after_closing(monkeypatch, instant_pool(client), OSError("synthetic"))
        with pytest.raises(OSError):
            client.close()

        client.close()

        assert len(calls) == 1
        assert instant_pool(client).is_closed
