from decimal import Decimal

import pytest

from khipu_sdk.errors import KhipuValidationError
from khipu_sdk.money import (
    CURRENCY_MINOR_UNITS,
    amount_from_wire,
    amount_to_wire,
    normalize_amount,
    validate_currency,
)


class TestCurrencyValidation:
    def test_accepts_supported_currency(self):
        assert validate_currency("CLP") == "CLP"

    def test_rejects_unsupported_currency(self):
        with pytest.raises(KhipuValidationError) as exc:
            validate_currency("XYZ")
        assert "XYZ" in str(exc.value)

    def test_rejects_lowercase_currency_rather_than_guessing(self):
        with pytest.raises(KhipuValidationError):
            validate_currency("clp")

    def test_minor_units_cover_every_currency_the_generated_enum_accepts(self):
        """Guards against spec drift: regeneration must not add an unmapped currency."""
        from generated.instant_payments.models.payment_post_payment_currency import (
            PaymentPostPaymentCurrency,
        )

        assert set(CURRENCY_MINOR_UNITS) == {c.value for c in PaymentPostPaymentCurrency}

    def test_clp_has_zero_minor_units_and_clf_has_four(self):
        assert CURRENCY_MINOR_UNITS["CLP"] == 0
        assert CURRENCY_MINOR_UNITS["CLF"] == 4


class TestNormalizeAmount:
    @pytest.mark.parametrize(
        "value",
        [Decimal("10000"), Decimal("10000.0000"), 10000, "10000"],
    )
    def test_accepts_exact_integral_clp(self, value):
        assert normalize_amount(value, "CLP") == Decimal("10000")

    def test_accepts_float_by_converting_through_str(self):
        # float is accepted but routed through Decimal(str(...)) so no binary
        # floating point noise is introduced by the SDK itself.
        assert normalize_amount(10000.0, "CLP") == Decimal("10000")

    def test_rejects_fractional_clp(self):
        with pytest.raises(KhipuValidationError) as exc:
            normalize_amount(Decimal("1000.5"), "CLP")
        assert "CLP" in str(exc.value)
        assert "0 decimal" in str(exc.value)

    def test_accepts_two_decimals_for_usd(self):
        assert normalize_amount(Decimal("10.50"), "USD") == Decimal("10.50")

    def test_rejects_three_decimals_for_usd(self):
        with pytest.raises(KhipuValidationError):
            normalize_amount(Decimal("10.505"), "USD")

    def test_accepts_four_decimals_for_clf(self):
        assert normalize_amount(Decimal("1.2345"), "CLF") == Decimal("1.2345")

    def test_rejects_five_decimals_for_clf(self):
        with pytest.raises(KhipuValidationError):
            normalize_amount(Decimal("1.23456"), "CLF")

    @pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1000")])
    def test_rejects_non_positive_amounts(self, value):
        with pytest.raises(KhipuValidationError):
            normalize_amount(value, "CLP")

    @pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
    def test_rejects_non_finite_amounts(self, value):
        with pytest.raises(KhipuValidationError):
            normalize_amount(value, "CLP")

    def test_rejects_unparseable_string(self):
        with pytest.raises(KhipuValidationError):
            normalize_amount("not-a-number", "CLP")

    def test_rejects_unsupported_type(self):
        with pytest.raises(KhipuValidationError):
            normalize_amount(object(), "CLP")  # type: ignore[arg-type]


class TestWireConversion:
    def test_integral_amount_serializes_as_int(self):
        assert amount_to_wire(Decimal("10000")) == 10000
        assert isinstance(amount_to_wire(Decimal("10000")), int)

    def test_trailing_zero_integral_amount_serializes_as_int(self):
        assert amount_to_wire(Decimal("10000.0000")) == 10000

    def test_fractional_amount_serializes_as_float(self):
        assert amount_to_wire(Decimal("10.50")) == 10.5

    def test_from_wire_uses_str_to_avoid_binary_float_noise(self):
        assert amount_from_wire(0.1) == Decimal("0.1")
        assert amount_from_wire(10000) == Decimal("10000")

    def test_from_wire_passes_none_through(self):
        assert amount_from_wire(None) is None
