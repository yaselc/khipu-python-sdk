"""Guards on the Instant Payments compatibility overlay (#15).

``GET /v3/payments/{id}`` returns ``payment_method: "direct_debit"`` for an
Automatic Payments (PAC) charge -- observed live in parle-cl/telemaco#377 --
while Khipu's published Instant Payments document declares only
``regular_transfer``, ``simplified_transfer`` and ``not_available``.

``openapi/khipu-instant-payments.yaml`` stays Khipu's document verbatim.
``tools/spec_compat.py`` adds the one missing value to a derived copy at
generation time. These tests pin that the overlay is exactly that narrow, that
it is reflected in ``generated/``, and that it announces its own removal: once
Khipu publishes ``direct_debit``, the upstream guard below fails, and so does
``make generate-all``, until the overlay entry is deleted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from generated.instant_payments.models.payment_get_payment_payment_method import (
    PaymentGetPaymentPaymentMethod,
)

REPO = Path(__file__).resolve().parents[2]
UPSTREAM_SPEC = REPO / "openapi" / "khipu-instant-payments.yaml"

_spec = importlib.util.spec_from_file_location(
    "spec_compat", REPO / "tools" / "spec_compat.py"
)
assert _spec is not None and _spec.loader is not None
spec_compat = importlib.util.module_from_spec(_spec)
# dataclasses resolves the module through sys.modules while the class is built.
sys.modules[_spec.name] = spec_compat
_spec.loader.exec_module(spec_compat)

(ENTRY,) = spec_compat.INSTANT_PAYMENTS
PUBLISHED = ("regular_transfer", "simplified_transfer", "not_available")

SYNTHETIC = """\
openapi: 3.0.0
components:
  schemas:
    other-schema:
      type: object
      properties:
        payment_method:
          type: string
          enum:
            - untouched
    payment-get-payment:
      type: object
      required:
        - payment_method
      properties:
        payment_method:
          type: string
          enum:
{items}
          description: text
        funds_source:
          type: string
          enum:
            - debit
"""


def synthetic(*values: str) -> str:
    return SYNTHETIC.format(items="\n".join(f"            - {v}" for v in values))


def upstream_text() -> str:
    return UPSTREAM_SPEC.read_text(encoding="utf-8")


class TestOverlayScope:
    def test_there_is_exactly_one_entry_and_it_is_the_one_from_15(self):
        assert ENTRY.schema == "payment-get-payment"
        assert ENTRY.property == "payment_method"
        assert ENTRY.added == ("direct_debit",)
        assert ENTRY.published == PUBLISHED
        assert "#15" in ENTRY.reason

    def test_it_adds_exactly_one_line_to_the_committed_spec(self):
        before = upstream_text().splitlines()
        after = spec_compat.apply(upstream_text(), spec_compat.INSTANT_PAYMENTS).splitlines()

        assert len(after) == len(before) + 1
        inserted = [line for line in after if line not in before]
        assert [line.strip() for line in inserted] == ["- direct_debit"]
        remaining = list(after)
        remaining.remove(inserted[0])
        assert remaining == before

    def test_it_is_deterministic(self):
        text = upstream_text()
        first = spec_compat.apply(text, spec_compat.INSTANT_PAYMENTS)
        second = spec_compat.apply(text, spec_compat.INSTANT_PAYMENTS)

        assert first == second

    def test_it_touches_only_the_named_schema(self):
        derived = spec_compat.apply(synthetic(*PUBLISHED), spec_compat.INSTANT_PAYMENTS)

        assert derived.count("- direct_debit") == 1
        assert "            - untouched\n" in derived
        assert derived.index("- direct_debit") > derived.index("payment-get-payment:")
        assert derived.index("- direct_debit") < derived.index("funds_source:")


class TestOverlayRefusesToDrift:
    def test_it_refuses_once_khipu_publishes_the_value_itself(self):
        with pytest.raises(spec_compat.OverlayError, match="obsolete"):
            spec_compat.apply(
                synthetic(*PUBLISHED, "direct_debit"), spec_compat.INSTANT_PAYMENTS
            )

    def test_it_refuses_when_the_upstream_enum_changes_any_other_way(self):
        with pytest.raises(spec_compat.OverlayError, match="Reconcile"):
            spec_compat.apply(
                synthetic(*PUBLISHED, "card"), spec_compat.INSTANT_PAYMENTS
            )

    def test_it_refuses_when_the_property_disappears(self):
        text = synthetic(*PUBLISHED).replace(
            "        payment_method:\n          type: string\n          enum:\n            - regular",
            "        renamed_method:\n          type: string\n          enum:\n            - regular",
        )
        with pytest.raises(spec_compat.OverlayError, match="not found"):
            spec_compat.apply(text, spec_compat.INSTANT_PAYMENTS)

    def test_check_mode_reports_obsolescence_as_a_failure(self, tmp_path, capsys):
        spec = tmp_path / "spec.yaml"
        spec.write_text(synthetic(*PUBLISHED, "direct_debit"), encoding="utf-8")

        assert spec_compat.main(["--check", str(spec)]) == 1
        assert "obsolete" in capsys.readouterr().err


class TestUpstreamStillOmitsDirectDebit:
    """The removal trigger for the overlay.

    When this fails, Khipu has published ``direct_debit`` (or otherwise changed
    the enum). Delete the entry from ``tools/spec_compat.py``, run
    ``make generate-all``, and drop this class: the value is then upstream's.
    """

    def test_the_committed_upstream_enum_is_exactly_the_published_three(self):
        _, values = spec_compat._locate_enum(upstream_text().splitlines(keepends=True), ENTRY)

        assert tuple(values) == PUBLISHED, (
            "Khipu's Instant Payments document changed payment_method; if it now "
            "declares direct_debit, remove the #15 overlay entry"
        )


class TestGeneratedClientCarriesTheOverlay:
    def test_generated_enum_is_upstream_plus_direct_debit_and_nothing_else(self):
        """Fails if generated/ was produced from the raw spec, bypassing the overlay."""
        assert {member.value for member in PaymentGetPaymentPaymentMethod} == {
            *PUBLISHED,
            "direct_debit",
        }
