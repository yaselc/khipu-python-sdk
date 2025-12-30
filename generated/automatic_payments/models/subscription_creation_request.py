from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SubscriptionCreationRequest")


@_attrs_define
class SubscriptionCreationRequest:
    """Objeto para solicitar una nueva suscripción de Pago Automático (PAC).

    Attributes:
        name (str): Nombre para identificar la suscripción. Example: Service XYZ Id 11.222.333-0.
        email (str): El correo electrónico del cliente que se suscribe al servicio. Example: personal.email@gmail.com.
        max_amount (float): Monto máximo que se puede cobrar mensualmente al cliente. Example: 1000.
        currency (str): El código de moneda en el estándar ISO 4217. Example: CLP.
        notify_url (str): La URL que se llamará cuando el cliente complete el proceso de firma con el banco. Se enviará
            un mensaje JSON a través de POST con la información de la suscripción con la siguiente estructura (`status`
            puede ser __"enabled"__ o __"disabled"__): ```json
              {
                "subscription_id": string,
                "status": "enabled"
              }
            ``` Example: https://my-domain.biz/subscription-notify-api.
        return_url (str): URL a la que redirigir al cliente cuando el proceso de firma se haya completado. Example:
            https://my-domain.biz/subscription-result.
        cancel_url (str): URL a la que redirigir al cliente si el proceso de firma no se pudo completar. Example:
            https://my-domain.biz/subscription-cancel.
        service_reference (str | Unset): Valor a asociar con la suscripción. Puede ser útil cuando no quieres que tu
            cliente sea identificado con un string único aleatorio en el formulario de suscripción de mandato del banco.
            Example: 12345678K.
        image_url (str | Unset): URL de la imagen asociada a la suscripción. Example: https://my-
            domain.biz/subscription-image.png.
        description (str | Unset): Descripción detallada de la suscripción PAC (Pago Automático) realizada en bancos
            para productos. Example: Suscripción PAC para el servicio XYZ..
    """

    name: str
    email: str
    max_amount: float
    currency: str
    notify_url: str
    return_url: str
    cancel_url: str
    service_reference: str | Unset = UNSET
    image_url: str | Unset = UNSET
    description: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        email = self.email

        max_amount = self.max_amount

        currency = self.currency

        notify_url = self.notify_url

        return_url = self.return_url

        cancel_url = self.cancel_url

        service_reference = self.service_reference

        image_url = self.image_url

        description = self.description

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "email": email,
                "max_amount": max_amount,
                "currency": currency,
                "notify_url": notify_url,
                "return_url": return_url,
                "cancel_url": cancel_url,
            }
        )
        if service_reference is not UNSET:
            field_dict["service_reference"] = service_reference
        if image_url is not UNSET:
            field_dict["image_url"] = image_url
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        email = d.pop("email")

        max_amount = d.pop("max_amount")

        currency = d.pop("currency")

        notify_url = d.pop("notify_url")

        return_url = d.pop("return_url")

        cancel_url = d.pop("cancel_url")

        service_reference = d.pop("service_reference", UNSET)

        image_url = d.pop("image_url", UNSET)

        description = d.pop("description", UNSET)

        subscription_creation_request = cls(
            name=name,
            email=email,
            max_amount=max_amount,
            currency=currency,
            notify_url=notify_url,
            return_url=return_url,
            cancel_url=cancel_url,
            service_reference=service_reference,
            image_url=image_url,
            description=description,
        )

        subscription_creation_request.additional_properties = d
        return subscription_creation_request

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
