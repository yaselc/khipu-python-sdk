from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.subscription_status_status import SubscriptionStatusStatus

T = TypeVar("T", bound="SubscriptionStatus")


@_attrs_define
class SubscriptionStatus:
    """Objeto con el estado de una suscripción de pago automático.

    Attributes:
        subscription_id (str): Identificador único de la suscripción. Example: 13a0f1aa-5e47-4894-aa8b-282dd19593ec.
        status (SubscriptionStatusStatus): El estado actual de la suscripción. Un intento de cobro solo se puede
            realizar si el estado es `ENABLED`. `PENDING` indica que el cliente todavía no ha firmado con su banco, y
            `DISCARDED` que la suscripción fue dada de baja. Example: SIGNED.
        developer (bool): Indica si la suscripción fue creada usando el entorno de pruebas. Un valor `false` significa
            que es una suscripción de producción.
        service_reference (str): El alias utilizado para identificar la suscripción. Viene vacío mientras el cliente no
            haya firmado con su banco. Example: Nombre de mi comercio.
    """

    subscription_id: str
    status: SubscriptionStatusStatus
    developer: bool
    service_reference: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subscription_id = self.subscription_id

        status = self.status.value

        developer = self.developer

        service_reference = self.service_reference

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "subscription_id": subscription_id,
                "status": status,
                "developer": developer,
                "service_reference": service_reference,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        subscription_id = d.pop("subscription_id")

        status = SubscriptionStatusStatus(d.pop("status"))

        developer = d.pop("developer")

        service_reference = d.pop("service_reference")

        subscription_status = cls(
            subscription_id=subscription_id,
            status=status,
            developer=developer,
            service_reference=service_reference,
        )

        subscription_status.additional_properties = d
        return subscription_status

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
