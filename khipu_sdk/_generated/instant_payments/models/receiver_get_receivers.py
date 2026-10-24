from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.receiver_get_receivers_receivers_item import (
        ReceiverGetReceiversReceiversItem,
    )


T = TypeVar("T", bound="ReceiverGetReceivers")


@_attrs_define
class ReceiverGetReceivers:
    """Objeto para respuesta de listado de cuentas de cobro asociadas a un integrador.

    Attributes:
        total (int): Cantidad total de cuentas de cobro asociadas al integrador. Example: 150.
        receivers (list[ReceiverGetReceiversReceiversItem]): Lista de cuentas de cobro asociadas al integrador.
    """

    total: int
    receivers: list[ReceiverGetReceiversReceiversItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        total = self.total

        receivers = []
        for receivers_item_data in self.receivers:
            receivers_item = receivers_item_data.to_dict()
            receivers.append(receivers_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "total": total,
                "receivers": receivers,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.receiver_get_receivers_receivers_item import (
            ReceiverGetReceiversReceiversItem,
        )

        d = dict(src_dict)
        total = d.pop("total")

        receivers = []
        _receivers = d.pop("receivers")
        for receivers_item_data in _receivers:
            receivers_item = ReceiverGetReceiversReceiversItem.from_dict(
                receivers_item_data
            )

            receivers.append(receivers_item)

        receiver_get_receivers = cls(
            total=total,
            receivers=receivers,
        )

        receiver_get_receivers.additional_properties = d
        return receiver_get_receivers

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
