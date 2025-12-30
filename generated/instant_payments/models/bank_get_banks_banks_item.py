from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.bank_get_banks_banks_item_type import BankGetBanksBanksItemType
from ..types import UNSET, Unset

T = TypeVar("T", bound="BankGetBanksBanksItem")


@_attrs_define
class BankGetBanksBanksItem:
    """Datos de banco.

    Attributes:
        bank_id (str): Identificador del banco. Example: SDdGj.
        name (str): Nombre del banco. Example: Banco Estado.
        message (str): Mensaje con particularidades del banco. Example: Tarifa de $300 de transferencia a otros bancos,
            usando CuentaRUT..
        min_amount (float): Monto mínimo que acepta el banco en un pago. Example: 1000.
        type_ (BankGetBanksBanksItemType): Tipo de banco. Example: Persona.
        parent (str): Identificador del banco padre (si un banco tiene banca personas y empresas, el primero será el
            padre del segundo).
        logo_url (str | Unset): URL del logo del banco. Example:
            https://s3.amazonaws.com/static.khipu.com/logos/bancos/chile/estado-icon.png.
    """

    bank_id: str
    name: str
    message: str
    min_amount: float
    type_: BankGetBanksBanksItemType
    parent: str
    logo_url: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bank_id = self.bank_id

        name = self.name

        message = self.message

        min_amount = self.min_amount

        type_ = self.type_.value

        parent = self.parent

        logo_url = self.logo_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bank_id": bank_id,
                "name": name,
                "message": message,
                "min_amount": min_amount,
                "type": type_,
                "parent": parent,
            }
        )
        if logo_url is not UNSET:
            field_dict["logo_url"] = logo_url

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        bank_id = d.pop("bank_id")

        name = d.pop("name")

        message = d.pop("message")

        min_amount = d.pop("min_amount")

        type_ = BankGetBanksBanksItemType(d.pop("type"))

        parent = d.pop("parent")

        logo_url = d.pop("logo_url", UNSET)

        bank_get_banks_banks_item = cls(
            bank_id=bank_id,
            name=name,
            message=message,
            min_amount=min_amount,
            type_=type_,
            parent=parent,
            logo_url=logo_url,
        )

        bank_get_banks_banks_item.additional_properties = d
        return bank_get_banks_banks_item

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
