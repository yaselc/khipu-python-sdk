"""Guards on the Automatic Payments provider contract as Khipu publishes it.

``openapi/khipu-automatic-payments.yaml`` is the document Khipu serves,
committed verbatim and pinned by sha256 in ``OPENAPI_SPECS.lock.json``. These
tests assert on the *generated* models, which CI rebuilds from that committed
spec, so a silent regeneration drift fails the suite instead of reaching a
caller as a parse error against the live API.

The lifecycle facts encoded here were first observed against the live
developer-mode API in parle-cl/telemaco#377 and are now documented by Khipu
itself: ``PENDING`` before the customer signs, ``DISCARDED`` once the
subscription is unsubscribed, and no ``customer_bank_code`` field at all.
"""

from __future__ import annotations

import pytest

from generated.automatic_payments.models.subscription_creation_request import (
    SubscriptionCreationRequest,
)
from generated.automatic_payments.models.subscription_status import SubscriptionStatus
from generated.automatic_payments.models.subscription_status_status import (
    SubscriptionStatusStatus,
)

#: The complete published vocabulary. ``PENDING`` and ``DISCARDED`` were added
#: by Khipu after the 2026-08-28 document this repository previously pinned.
PUBLISHED_STATUS_VOCABULARY = {
    "PENDING",
    "DISABLED",
    "SIGNED",
    "ENABLED",
    "DISCARDED",
}


def status_body(**overrides):
    body = {
        "subscription_id": "7Kp2R9xTmQ4b",
        "status": "ENABLED",
        "developer": True,
        "service_reference": "synthetic-reference",
    }
    body.update(overrides)
    return body


class TestStatusVocabulary:
    def test_covers_every_published_value(self):
        assert {
            member.value for member in SubscriptionStatusStatus
        } == PUBLISHED_STATUS_VOCABULARY

    @pytest.mark.parametrize("value", sorted(PUBLISHED_STATUS_VOCABULARY))
    def test_each_published_status_parses(self, value):
        parsed = SubscriptionStatus.from_dict(status_body(status=value))
        assert parsed.status.value == value


class TestSubscriptionStatusShape:
    def test_customer_bank_code_is_not_part_of_the_schema(self):
        """Khipu removed the field; it must not reappear as a model attribute."""
        assert not hasattr(SubscriptionStatus, "customer_bank_code")
        assert "customer_bank_code" not in SubscriptionStatus.from_dict(
            status_body()
        ).to_dict()

    def test_a_customer_bank_code_khipu_still_sent_lands_in_additional_properties(self):
        """An unknown key is kept, not dropped and not promoted."""
        parsed = SubscriptionStatus.from_dict(status_body(customer_bank_code="8"))
        assert parsed.additional_properties["customer_bank_code"] == "8"

    def test_service_reference_is_required(self):
        """Khipu documents it as present but empty before signing, never absent."""
        with pytest.raises(KeyError):
            SubscriptionStatus.from_dict(
                {
                    "subscription_id": "7Kp2R9xTmQ4b",
                    "status": "PENDING",
                    "developer": True,
                }
            )

    def test_an_empty_service_reference_is_preserved_as_an_empty_string(self):
        parsed = SubscriptionStatus.from_dict(status_body(service_reference=""))
        assert parsed.service_reference == ""

    def test_subscription_id_and_status_remain_required(self):
        with pytest.raises(KeyError):
            SubscriptionStatus.from_dict(
                {"status": "ENABLED", "developer": True, "service_reference": "x"}
            )
        with pytest.raises(KeyError):
            SubscriptionStatus.from_dict(
                {
                    "subscription_id": "7Kp2R9xTmQ4b",
                    "developer": True,
                    "service_reference": "x",
                }
            )

    def test_subscription_id_is_an_opaque_string_with_no_uuid_parsing(self):
        parsed = SubscriptionStatus.from_dict(status_body(status="PENDING"))
        assert parsed.subscription_id == "7Kp2R9xTmQ4b"
        assert type(parsed.subscription_id) is str


class TestSubscriptionCreationRequest:
    def test_max_amount_per_charge_is_a_required_field(self):
        """Khipu added it to the required list; #9."""
        assert "max_amount_per_charge" in SubscriptionCreationRequest.from_dict(
            {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "max_amount": 50000,
                "max_amount_per_charge": 20000,
                "currency": "CLP",
                "notify_url": "https://example.com/pac/notify",
                "return_url": "https://example.com/pac/return",
                "cancel_url": "https://example.com/pac/cancel",
            }
        ).to_dict()

        with pytest.raises(KeyError):
            SubscriptionCreationRequest.from_dict(
                {
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "max_amount": 50000,
                    "currency": "CLP",
                    "notify_url": "https://example.com/pac/notify",
                    "return_url": "https://example.com/pac/return",
                    "cancel_url": "https://example.com/pac/cancel",
                }
            )
