from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ChargeResult")


@_attrs_define
class ChargeResult:
    """Objeto con el resultado de una solicitud de creación de intención de cobro.

    Attributes:
        payment_id (str): Identificador único del cobro. Representa el id de pago automático que se usará para rastrear
            la solicitud de cobro a la cuenta del cliente. Example: v67prof2ugg3.
    """

    payment_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payment_id = self.payment_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "payment_id": payment_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        payment_id = d.pop("payment_id")

        charge_result = cls(
            payment_id=payment_id,
        )

        charge_result.additional_properties = d
        return charge_result

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
