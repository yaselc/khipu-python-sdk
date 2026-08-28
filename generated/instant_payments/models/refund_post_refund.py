from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.refund_post_refund_type import RefundPostRefundType
from ..types import UNSET, Unset

T = TypeVar("T", bound="RefundPostRefund")


@_attrs_define
class RefundPostRefund:
    """Datos para reversar un pago.

    Attributes:
        type_ (RefundPostRefundType): Tipo de reversa. `full` reversa el monto completo reversable del pago; `partial`
            reversa el monto indicado en `amount`. Example: partial.
        payment_id (str): Identificador del pago a reversar. Example: xsthgfkmvyvb.
        amount (str | Unset): El monto a reversar. Obligatorio cuando `type` es `partial`; no puede ser utilizado cuando
            `type` es `full`. Sin separador de miles y usando '.' como separador de decimales. Hasta el número de decimales
            que admita la moneda. No puede superar el saldo reversable del pago. Example: 1000.
    """

    type_: RefundPostRefundType
    payment_id: str
    amount: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        payment_id = self.payment_id

        amount = self.amount

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "payment_id": payment_id,
            }
        )
        if amount is not UNSET:
            field_dict["amount"] = amount

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = RefundPostRefundType(d.pop("type"))

        payment_id = d.pop("payment_id")

        amount = d.pop("amount", UNSET)

        refund_post_refund = cls(
            type_=type_,
            payment_id=payment_id,
            amount=amount,
        )

        refund_post_refund.additional_properties = d
        return refund_post_refund

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
