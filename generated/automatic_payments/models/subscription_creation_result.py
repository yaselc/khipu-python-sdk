from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="SubscriptionCreationResult")


@_attrs_define
class SubscriptionCreationResult:
    """Objeto con el resultado de una solicitud de creación de suscripción a Pago Automático.

    Attributes:
        subscription_id (str): Identificador único de la suscripción, que se asociará al servicio adquirido por el
            cliente. Posteriormente, este valor puede ser usado para consultar el estado de la suscripción. Example:
            13a0f1aa-5e47-4894-aa8b-282dd19593ec.
        redirect_url (str): La URL donde el comercio debe redirigir al usuario para que firme la suscripción con su
            banco personal. Utiliza el id de la suscripción como parámetro de la URL. Example: https://khipu.com/pac-
            manager/13a0f1aa-5e47-4894-aa8b-282dd19593ec.
    """

    subscription_id: str
    redirect_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subscription_id = self.subscription_id

        redirect_url = self.redirect_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "subscription_id": subscription_id,
                "redirect_url": redirect_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        subscription_id = d.pop("subscription_id")

        redirect_url = d.pop("redirect_url")

        subscription_creation_result = cls(
            subscription_id=subscription_id,
            redirect_url=redirect_url,
        )

        subscription_creation_result.additional_properties = d
        return subscription_creation_result

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
