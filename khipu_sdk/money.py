"""Money handling for the Khipu SDK.

Design rules:

* :class:`~decimal.Decimal` is the canonical SDK-facing representation. The SDK
  never performs financial arithmetic in binary floating point.
* Amounts are validated against the currency's minor-unit scale *before* any
  HTTP request is made, so an invalid fractional CLP amount can never reach
  Khipu.
* Conversion to ``float``/``int`` happens only at the very last step, when
  handing the value to the OpenAPI-generated model, whose ``amount`` field is
  typed ``float`` by the generator. That boundary is
  :func:`amount_to_wire`, and it is the only place in the SDK where a
  non-``Decimal`` numeric type is produced.
* Values decoded from JSON arrive as ``float``/``int``; they are converted back
  with ``Decimal(str(value))`` (see :func:`amount_from_wire`) so no additional
  binary floating-point error is introduced.
"""

from __future__ import annotations

from decimal import Decimal, DecimalException
from typing import Mapping, Optional, Union

from .errors import KhipuValidationError

__all__ = [
    "CURRENCY_MINOR_UNITS",
    "SUPPORTED_CURRENCIES",
    "AmountInput",
    "validate_currency",
    "normalize_amount",
    "amount_to_wire",
    "amount_from_wire",
]

#: Number of decimal places each currency admits, per ISO-4217 minor units.
#:
#: Khipu's spec says only "hasta 4 lugares decimales, dependiendo de la moneda",
#: without enumerating per-currency scales, so these come from ISO-4217 rather
#: than from the vendored spec. The keys must stay in sync with the currency
#: enum of the Instant Payments spec; ``tests/unit/test_money.py`` asserts that.
#:
#: Note CLP (Chilean peso) has no minor unit, and CLF (Unidad de Fomento) has
#: four. Nothing here assumes a default of two decimals.
CURRENCY_MINOR_UNITS: Mapping[str, int] = {
    "ARS": 2,
    "BOB": 2,
    "CLF": 4,
    "CLP": 0,
    "COP": 2,
    "EUR": 2,
    "MXN": 2,
    "PEN": 2,
    "USD": 2,
}

SUPPORTED_CURRENCIES = frozenset(CURRENCY_MINOR_UNITS)

#: Accepted input types for a monetary amount. ``Decimal`` is preferred; ``int``
#: and ``str`` are exact. ``float`` is accepted for convenience and converted
#: through ``str`` so the SDK adds no binary floating-point error, but any
#: imprecision already present in the caller's float is preserved -- pass
#: ``Decimal`` if exactness matters.
AmountInput = Union[Decimal, int, str, float]


def validate_currency(currency: str) -> str:
    """Return ``currency`` if the SDK supports it, else raise."""
    if not isinstance(currency, str) or currency not in SUPPORTED_CURRENCIES:
        supported = ", ".join(sorted(SUPPORTED_CURRENCIES))
        raise KhipuValidationError(
            f"Unsupported currency {currency!r}. Supported currencies: {supported}."
        )
    return currency


def _to_decimal(amount: AmountInput) -> Decimal:
    if isinstance(amount, Decimal):
        return amount
    if isinstance(amount, bool):  # bool is an int subclass; reject it explicitly
        raise KhipuValidationError(f"Invalid amount {amount!r}: expected a number.")
    if isinstance(amount, int):
        return Decimal(amount)
    if isinstance(amount, float):
        # str() first: never Decimal(float), which would capture binary noise.
        return Decimal(str(amount))
    if isinstance(amount, str):
        try:
            return Decimal(amount)
        except DecimalException as exc:
            raise KhipuValidationError(
                f"Invalid amount {amount!r}: not a valid decimal number."
            ) from exc
    raise KhipuValidationError(
        f"Invalid amount of type {type(amount).__name__!r}: "
        "expected Decimal, int, str or float."
    )


def normalize_amount(amount: AmountInput, currency: Optional[str] = None) -> Decimal:
    """Validate ``amount`` and return it as a ``Decimal``.

    Raises :class:`KhipuValidationError` if the currency is unsupported, or the
    amount is not finite, not strictly positive, or has more decimal places than
    the currency admits. Amounts are never silently rounded.

    ``currency`` may be ``None`` for requests whose Khipu payload carries no
    currency field (the Automatic Payments charge intent inherits its currency
    from the subscription). Minor-unit validation is then impossible and is
    skipped -- the finite/positive checks still apply.
    """
    if currency is not None:
        validate_currency(currency)
    value = _to_decimal(amount)

    if not value.is_finite():
        raise KhipuValidationError(f"Invalid amount {value!r}: must be a finite number.")
    if value <= 0:
        raise KhipuValidationError(f"Invalid amount {value}: must be greater than zero.")

    if currency is None:
        return value

    scale = CURRENCY_MINOR_UNITS[currency]
    # normalize() strips trailing zeros, so Decimal("10000.0000") is treated as
    # the integral 1E+4 and accepted for CLP, while Decimal("1000.5") is not.
    exponent = value.normalize().as_tuple().exponent
    assert isinstance(exponent, int)  # finite Decimal always has an int exponent
    if exponent < -scale:
        raise KhipuValidationError(
            f"Invalid amount {value} for {currency}: {currency} admits "
            f"{scale} decimal place(s). Amounts are not rounded automatically."
        )
    return value


def amount_to_wire(amount: Decimal) -> Union[int, float]:
    """Convert a validated ``Decimal`` to the numeric type the generated model wants.

    This is the single boundary where the SDK leaves ``Decimal``. Integral
    amounts become ``int`` so that e.g. CLP serialises as ``10000`` rather than
    ``10000.0``.
    """
    if amount == amount.to_integral_value():
        return int(amount)
    return float(amount)


def amount_from_wire(value: Union[int, float, str, None]) -> Optional[Decimal]:
    """Convert a JSON-decoded amount back to ``Decimal`` without adding float error."""
    if value is None:
        return None
    return Decimal(str(value))
