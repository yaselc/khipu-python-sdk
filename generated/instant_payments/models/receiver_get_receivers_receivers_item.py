from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="ReceiverGetReceiversReceiversItem")


@_attrs_define
class ReceiverGetReceiversReceiversItem:
    """
    Attributes:
        id (int): Identificador único de la cuenta de cobro. Example: 302026.
        name (str): Nombre de la cuenta de cobro. Example: Cobrador 20260311115756.
        date_created (datetime.datetime): Fecha de creación de la cuenta de cobro. Example: 2026-03-11T14:57:56Z.
        disabled (bool): Indica si la cuenta de cobro está deshabilitada.
        can_collect (bool): Indica si la cuenta de cobro puede recibir pagos. Example: True.
    """

    id: int
    name: str
    date_created: datetime.datetime
    disabled: bool
    can_collect: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        date_created = self.date_created.isoformat()

        disabled = self.disabled

        can_collect = self.can_collect

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "date_created": date_created,
                "disabled": disabled,
                "can_collect": can_collect,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        date_created = isoparse(d.pop("date_created"))

        disabled = d.pop("disabled")

        can_collect = d.pop("can_collect")

        receiver_get_receivers_receivers_item = cls(
            id=id,
            name=name,
            date_created=date_created,
            disabled=disabled,
            can_collect=can_collect,
        )

        receiver_get_receivers_receivers_item.additional_properties = d
        return receiver_get_receivers_receivers_item

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
