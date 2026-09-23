from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ChargeError")


@_attrs_define
class ChargeError:
    """Objeto con el motivo del rechazo de una intención de cobro.

    Attributes:
        error_code (str): Código del motivo del rechazo. Los valores posibles son `MAX_AMOUNT_PER_CHARGE_EXCEEDED`,
            `MAX_MONTHLY_AMOUNT_EXCEEDED`, `SUBSCRIPTION_NOT_CHARGEABLE`, `CURRENCY_MISMATCH`, `INVALID_AMOUNT`,
            `IDEMPOTENCY_KEY_REUSED`, `INVALID_PAYLOAD` y `MERCHANT_ID_NOT_RESOLVED`. Example:
            MAX_AMOUNT_PER_CHARGE_EXCEEDED.
        error_message (str): Descripción del motivo del rechazo. Example: amount exceeds the maximum allowed per charge
            for this subscription.
    """

    error_code: str
    error_message: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        error_code = self.error_code

        error_message = self.error_message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "error_code": error_code,
                "error_message": error_message,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        error_code = d.pop("error_code")

        error_message = d.pop("error_message")

        charge_error = cls(
            error_code=error_code,
            error_message=error_message,
        )

        charge_error.additional_properties = d
        return charge_error

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
