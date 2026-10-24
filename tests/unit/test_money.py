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
        from khipu_sdk._generated.instant_payments.models.payment_post_payment_currency import (
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


class TestWireExactness:
    """F3 of #41: a non-integral amount is sent with exactly its value or rejected.

    The JSON encoder writes a float as ``repr(float)``, so the decimal value on
    the wire is ``Decimal(repr(amount_to_wire(x)))``.
    """

    @pytest.mark.parametrize(
        "value",
        [
            "0.1",  # no exact binary form, but still emitted as 0.1
            "0.01",
            "10.50",  # trailing zero: same value as 10.5
            "1.2345",  # CLF, four decimals
            "19.99",  # USD, two decimals
            "9999999999999.99",  # 15 significant digits
            "123456789012.3457",  # 16 significant digits that survive
            "0.30000000000000004",  # 17 significant digits that survive
            "1E-300",
        ],
    )
    def test_representable_amount_keeps_its_decimal_value(self, value):
        wire = amount_to_wire(Decimal(value))
        assert isinstance(wire, float)
        assert Decimal(repr(wire)) == Decimal(value)

    @pytest.mark.parametrize(
        "value",
        [
            "1234567890123.4567",  # CLF example from the audit
            "1234567890123456.78",  # USD example from the audit
            "0.12345678901234567891",
            "9007199254740993.5",
        ],
    )
    def test_lossy_amount_is_rejected_not_rounded(self, value):
        with pytest.raises(KhipuValidationError, match="not rounded automatically"):
            amount_to_wire(Decimal(value))

    def test_amount_overflowing_float_is_rejected(self):
        with pytest.raises(KhipuValidationError):
            amount_to_wire(Decimal("1" + "0" * 400 + ".5"))

    def test_amount_underflowing_float_is_rejected(self):
        with pytest.raises(KhipuValidationError):
            amount_to_wire(Decimal("1E-400"))

    @pytest.mark.parametrize(
        "value",
        [
            "9007199254740993",  # 2**53 + 1: not a float, but exact as int
            "123456789012345678901234567890",
            "1E+400",
            "9007199254740993.0000",
        ],
    )
    def test_integral_amount_stays_exact_at_any_size(self, value):
        wire = amount_to_wire(Decimal(value))
        assert type(wire) is int
        assert wire == Decimal(value)

    def test_validated_amounts_reach_the_wire_unchanged(self):
        """normalize_amount() and amount_to_wire() together, per currency."""
        assert amount_to_wire(normalize_amount(Decimal("10000"), "CLP")) == 10000
        assert amount_to_wire(normalize_amount(Decimal("1.2345"), "CLF")) == 1.2345
        assert amount_to_wire(normalize_amount(Decimal("12.30"), "USD")) == 12.3
        assert amount_to_wire(normalize_amount("0.5", None)) == 0.5

    def test_float_input_keeps_the_callers_float_value(self):
        """The SDK adds no float error, but cannot remove the caller's own."""
        amount = normalize_amount(0.1 + 0.2, None)
        assert amount == Decimal("0.30000000000000004")
        assert amount_to_wire(amount) == 0.1 + 0.2

    def test_from_wire_uses_str_to_avoid_binary_float_noise(self):
        assert amount_from_wire(0.1) == Decimal("0.1")
        assert amount_from_wire(10000) == Decimal("10000")

    def test_from_wire_passes_none_through(self):
        assert amount_from_wire(None) is None
