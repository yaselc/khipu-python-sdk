from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ReceiverPostReceiver2")


@_attrs_define
class ReceiverPostReceiver2:
    """Objeto para respuesta de creación de cuenta de cobro.

    Attributes:
        receiver_id (str): Identificador único de la cuenta de cobro. Example: 934568.
        secret (str): Llave secreta de la cuenta de cobro, se usa para firmar todas las peticiones. Example:
            b2025dc47a29a04592fa3c1191110370db0e208c.
        api_key (str | Unset): API key de la cuenta de cobro creada. Example: d6ec59c7-e299-4704-840d-300442546982.
    """

    receiver_id: str
    secret: str
    api_key: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        receiver_id = self.receiver_id

        secret = self.secret

        api_key = self.api_key

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "receiver_id": receiver_id,
                "secret": secret,
            }
        )
        if api_key is not UNSET:
            field_dict["api_key"] = api_key

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        receiver_id = d.pop("receiver_id")

        secret = d.pop("secret")

        api_key = d.pop("api_key", UNSET)

        receiver_post_receiver_2 = cls(
            receiver_id=receiver_id,
            secret=secret,
            api_key=api_key,
        )

        receiver_post_receiver_2.additional_properties = d
        return receiver_post_receiver_2

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
