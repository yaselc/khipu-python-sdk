from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.merchant_get_payment_methods_payment_methods_item import (
        MerchantGetPaymentMethodsPaymentMethodsItem,
    )


T = TypeVar("T", bound="MerchantGetPaymentMethods")


@_attrs_define
class MerchantGetPaymentMethods:
    """
    Attributes:
        payment_methods (list[MerchantGetPaymentMethodsPaymentMethodsItem]): Arreglo con métodos de pago disponibles.
    """

    payment_methods: list[MerchantGetPaymentMethodsPaymentMethodsItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payment_methods = []
        for payment_methods_item_data in self.payment_methods:
            payment_methods_item = payment_methods_item_data.to_dict()
            payment_methods.append(payment_methods_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "paymentMethods": payment_methods,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.merchant_get_payment_methods_payment_methods_item import (
            MerchantGetPaymentMethodsPaymentMethodsItem,
        )

        d = dict(src_dict)
        payment_methods = []
        _payment_methods = d.pop("paymentMethods")
        for payment_methods_item_data in _payment_methods:
            payment_methods_item = (
                MerchantGetPaymentMethodsPaymentMethodsItem.from_dict(
                    payment_methods_item_data
                )
            )

            payment_methods.append(payment_methods_item)

        merchant_get_payment_methods = cls(
            payment_methods=payment_methods,
        )

        merchant_get_payment_methods.additional_properties = d
        return merchant_get_payment_methods

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
