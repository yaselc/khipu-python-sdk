from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RefundWalletGetBalance")


@_attrs_define
class RefundWalletGetBalance:
    """Saldo de la billetera de devoluciones.

    Attributes:
        balance (str): Saldo disponible de la billetera de devoluciones. Sin separador de miles, usando '.' como
            separador de decimales y siempre con 4 decimales. Example: 5000.0000.
        currency (str): Código de la moneda del saldo. Example: CLP.
        add_funds_url (str): URL para recargar la billetera de devoluciones. Example: https://khipu.com/dashboard/bills.
    """

    balance: str
    currency: str
    add_funds_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        balance = self.balance

        currency = self.currency

        add_funds_url = self.add_funds_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "balance": balance,
                "currency": currency,
                "add_funds_url": add_funds_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        balance = d.pop("balance")

        currency = d.pop("currency")

        add_funds_url = d.pop("add_funds_url")

        refund_wallet_get_balance = cls(
            balance=balance,
            currency=currency,
            add_funds_url=add_funds_url,
        )

        refund_wallet_get_balance.additional_properties = d
        return refund_wallet_get_balance

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
