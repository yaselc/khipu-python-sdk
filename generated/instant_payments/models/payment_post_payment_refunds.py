from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PaymentPostPaymentRefunds")


@_attrs_define
class PaymentPostPaymentRefunds:
    """Reembolsa total o parcialmente el monto de un pago. Esta operación solo se puede realizar en los comercios que
    recauden en cuenta Khipu y antes de la rendición de los fondos correspondientes.

        Attributes:
            amount (float | Unset): El monto a devolver. Sin separador de miles y usando '.' como separador de decimales.
                Hasta 4 lugares decimales, dependiendo de la moneda. Si se omite el reembolso se hará por el total del monto del
                pago. Example: 1000.
    """

    amount: float | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        amount = self.amount

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if amount is not UNSET:
            field_dict["amount"] = amount

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        amount = d.pop("amount", UNSET)

        payment_post_payment_refunds = cls(
            amount=amount,
        )

        payment_post_payment_refunds.additional_properties = d
        return payment_post_payment_refunds

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
