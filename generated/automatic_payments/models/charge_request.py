from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChargeRequest")


@_attrs_define
class ChargeRequest:
    """Objecto para enviar una solicitud de un nuevo cobro asociado a un id de suscripción.

    Attributes:
        subscription_id (str): El ID de la suscripción que se cobrará. Example: 13a0f1aa-5e47-4894-aa8b-282dd19593ec.
        amount (float): Monto que se cobrará. No use separador de miles, y un máximo de 4 decimales. Se asumirá la
            moneda en que el comercio registró su cuenta en Khipu. Example: 10000.
        subject (str): Asunto para identificar el cobro. Example: Cargo por servicio XYZ Id 11.222.333-0.
        error_response_url (str): URL que será llamada si ocurre un error en el proceso de cobro. Se enviará un JSON por
            POST con la siguiente estructura:
            ```json
              {
                "subscription_id": string,
                "transaction_id": string,
                "payment_id": string,
                "error_message": string
              }
            ``` Example: https://my-domain.biz/charge-error-api.
        notify_url (str): URL que será llamada una vez que el proceso de cobro finalice y el pago sea conciliado. Se
            enviará un POST con los parámetros que permiten obtener los detalles del pago, utilizando el mismo flujo de un
            pago normal. Consulte la [documentación](https://docs.khipu.com/en/payment-solutions/instant-payments/payment-
            webhook) para más detalles. Example: https://my-domain.biz/charge-notify-api.
        body (str | Unset): Descripción del cobro. Puede incluir información adicional sobre el cobro, como el servicio
            o producto asociado, fecha, etc. Se recomienda que sea lo más descriptivo posible. Example: Servicio XYZ -
            Noviembre 2022 - Monto: $10.000.
        custom (str | Unset): Éste campo puede ser utilizado para enviar información personalizada sobre el cobro. Puede
            ser en formato texto o un documento codificado en base64. Example: Contenido personalizado del cobro en formato
            texto o base64..
        transaction_id (str | Unset): El identificador único del comercio para esta operación. Por ejemplo, el número de
            factura. Example: INVOICE-23ffcfbe1e4a4d1c9dc631fe70bddaa0.
        notify_api_version (str | Unset): Version of the API used for the notification. This is useful to ensure
            compatibility with future changes in the API. Example: 1.3.
    """

    subscription_id: str
    amount: float
    subject: str
    error_response_url: str
    notify_url: str
    body: str | Unset = UNSET
    custom: str | Unset = UNSET
    transaction_id: str | Unset = UNSET
    notify_api_version: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subscription_id = self.subscription_id

        amount = self.amount

        subject = self.subject

        error_response_url = self.error_response_url

        notify_url = self.notify_url

        body = self.body

        custom = self.custom

        transaction_id = self.transaction_id

        notify_api_version = self.notify_api_version

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "subscription_id": subscription_id,
                "amount": amount,
                "subject": subject,
                "error_response_url": error_response_url,
                "notify_url": notify_url,
            }
        )
        if body is not UNSET:
            field_dict["body"] = body
        if custom is not UNSET:
            field_dict["custom"] = custom
        if transaction_id is not UNSET:
            field_dict["transaction_id"] = transaction_id
        if notify_api_version is not UNSET:
            field_dict["notify_api_version"] = notify_api_version

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        subscription_id = d.pop("subscription_id")

        amount = d.pop("amount")

        subject = d.pop("subject")

        error_response_url = d.pop("error_response_url")

        notify_url = d.pop("notify_url")

        body = d.pop("body", UNSET)

        custom = d.pop("custom", UNSET)

        transaction_id = d.pop("transaction_id", UNSET)

        notify_api_version = d.pop("notify_api_version", UNSET)

        charge_request = cls(
            subscription_id=subscription_id,
            amount=amount,
            subject=subject,
            error_response_url=error_response_url,
            notify_url=notify_url,
            body=body,
            custom=custom,
            transaction_id=transaction_id,
            notify_api_version=notify_api_version,
        )

        charge_request.additional_properties = d
        return charge_request

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
