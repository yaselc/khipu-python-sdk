"""PAC subscription lifecycle, exercised over the real HTTP boundary.

Every fixture here is a **sanitised synthetic** body whose shape mirrors what
Khipu's Automatic Payments API returns. No live Khipu call happens here or in
CI.

The lifecycle these tests pin was first observed in parle-cl/telemaco#377
against the live developer-mode API, and is now documented by Khipu itself:

* a GET issued immediately after creation returns ``PENDING`` -- the customer
  has not signed the bank mandate yet;
* the ``subscription_id`` Khipu issues is a short mixed-case alphanumeric
  token, not the UUID its schema example implies. The ids used below are
  synthetic but preserve that shape;
* ``customer_bank_code`` is not part of the response at all. #377 saw a valid
  post-signing body without it, and Khipu has since removed the field from the
  published schema;
* ``service_reference`` is always present and comes back **empty** until the
  customer signs;
* ``DISCARDED`` reports a subscription that was unsubscribed.
"""

from __future__ import annotations

import pytest

from khipu_sdk import KhipuClient, KhipuConfig

BASE_URL = "https://payment-api.khipu.com"
SUBSCRIPTION_URL = f"{BASE_URL}/v1/automatic-payment/subscription"
API_KEY = "unit-test-api-key"

#: Synthetic, but the same shape as the id Khipu actually issued in #377:
#: twelve mixed-case alphanumeric characters, emphatically not a UUID.
OPAQUE_SUBSCRIPTION_ID = "7Kp2R9xTmQ4b"


@pytest.fixture
def client() -> KhipuClient:
    return KhipuClient(KhipuConfig(api_key=API_KEY, base_url=BASE_URL))


def body(**overrides):
    payload = {
        "subscription_id": OPAQUE_SUBSCRIPTION_ID,
        "status": "ENABLED",
        "developer": True,
        "service_reference": "synthetic-reference",
    }
    payload.update(overrides)
    return payload


def fetch(client: KhipuClient, httpx_mock, payload):
    httpx_mock.add_response(
        url=f"{SUBSCRIPTION_URL}/{OPAQUE_SUBSCRIPTION_ID}", json=payload
    )
    return client.get_subscription(subscription_id=OPAQUE_SUBSCRIPTION_ID)


class TestLifecycle:
    @pytest.mark.parametrize(
        "provider_status", ["PENDING", "DISABLED", "SIGNED", "ENABLED", "DISCARDED"]
    )
    def test_every_published_status_parses_through_the_public_facade(
        self, client, httpx_mock, provider_status
    ):
        status = fetch(client, httpx_mock, body(status=provider_status))

        assert status.status == provider_status
        assert type(status.status) is str, "facade must not leak the generated enum type"

    def test_pending_is_the_pre_signing_state_that_used_to_raise(
        self, client, httpx_mock
    ):
        """#377: this exact body raised ValueError out of the generated enum."""
        status = fetch(
            client, httpx_mock, body(status="PENDING", service_reference="")
        )

        assert status.status == "PENDING"
        assert status.service_reference == ""

    def test_discarded_reports_an_unsubscribed_mandate(self, client, httpx_mock):
        status = fetch(client, httpx_mock, body(status="DISCARDED"))

        assert status.status == "DISCARDED"


class TestOpaqueIdentifiers:
    def test_non_uuid_subscription_id_is_returned_unchanged(self, client, httpx_mock):
        status = fetch(client, httpx_mock, body(status="PENDING"))

        assert status.subscription_id == OPAQUE_SUBSCRIPTION_ID
        assert type(status.subscription_id) is str


class TestResponseFields:
    def test_post_signing_response_without_customer_bank_code_parses(
        self, client, httpx_mock
    ):
        """OBSERVED in #377, and now the published shape: the field is gone."""
        status = fetch(client, httpx_mock, body(status="ENABLED"))

        assert status.status == "ENABLED"
        assert not hasattr(status, "customer_bank_code")

    def test_an_empty_service_reference_is_not_turned_into_none(
        self, client, httpx_mock
    ):
        """Khipu sends ``""`` before signing. Empty is a value, not absence."""
        status = fetch(client, httpx_mock, body(service_reference=""))

        assert status.service_reference == ""
        assert status.service_reference is not None

    def test_a_service_reference_khipu_sent_is_preserved_verbatim(
        self, client, httpx_mock
    ):
        status = fetch(client, httpx_mock, body(service_reference="mi-comercio"))

        assert status.service_reference == "mi-comercio"

    def test_developer_flag_is_promoted_onto_the_result(self, client, httpx_mock):
        """#377 ran in developer mode; callers must be able to see that."""
        assert fetch(client, httpx_mock, body(developer=True)).developer is True
        assert fetch(client, httpx_mock, body(developer=False)).developer is False

    def test_an_unknown_key_khipu_adds_later_does_not_break_parsing(
        self, client, httpx_mock
    ):
        status = fetch(client, httpx_mock, body(some_future_field="x"))

        assert status.status == "ENABLED"
        assert status.raw.additional_properties["some_future_field"] == "x"
