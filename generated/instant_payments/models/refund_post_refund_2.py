from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="RefundPostRefund2")


@_attrs_define
class RefundPostRefund2:
    """Resultado de la reversa.

    Attributes:
        id (str): Identificador único de la reversa. Example: b31bd9aa-273b-4aed-9516-85866d47a931.
        payment_id (str): Identificador del pago reversado. Example: xsthgfkmvyvb.
        refunded_amount (str): Monto reversado en esta operación. Sin separador de miles, usando '.' como separador de
            decimales y siempre con 4 decimales. Example: 1000.0000.
        total_refunded (str): Monto total reversado del pago, sumando todas las reversas. Example: 1000.0000.
        remaining (str): Saldo del pago aún disponible para reversar. Example: 2000.0000.
        currency (str): Código de la moneda de los montos. Example: CLP.
        message (str | Unset): Mensaje informativo opcional sobre el estado de la billetera de reversas; por ejemplo,
            cuando su saldo es insuficiente para concretar las reversas del día.
    """

    id: str
    payment_id: str
    refunded_amount: str
    total_refunded: str
    remaining: str
    currency: str
    message: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        payment_id = self.payment_id

        refunded_amount = self.refunded_amount

        total_refunded = self.total_refunded

        remaining = self.remaining

        currency = self.currency

        message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "payment_id": payment_id,
                "refunded_amount": refunded_amount,
                "total_refunded": total_refunded,
                "remaining": remaining,
                "currency": currency,
            }
        )
        if message is not UNSET:
            field_dict["message"] = message

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        payment_id = d.pop("payment_id")

        refunded_amount = d.pop("refunded_amount")

        total_refunded = d.pop("total_refunded")

        remaining = d.pop("remaining")

        currency = d.pop("currency")

        message = d.pop("message", UNSET)

        refund_post_refund_2 = cls(
            id=id,
            payment_id=payment_id,
            refunded_amount=refunded_amount,
            total_refunded=total_refunded,
            remaining=remaining,
            currency=currency,
            message=message,
        )

        refund_post_refund_2.additional_properties = d
        return refund_post_refund_2

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
