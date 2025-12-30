from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PaymentPostPayment2")


@_attrs_define
class PaymentPostPayment2:
    """Crea un pago en Khipu y obtiene las URLs para redirección al usuario para que complete el pago.

    Attributes:
        payment_id (str): Identificador único del pago, es una cadena alfanumérica de 12 caracteres. Como este
            identificador es único, se puede usar, por ejemplo, para evitar procesar una notificación repetida. (Khipu
            espera un código 200 al notificar un pago, si esto no ocurre se reintenta hasta por dos días). Example:
            gqzdy6chjne9.
        payment_url (str): URL principal del pago, si el usuario no ha elegido previamente un método de pago se le
            muestran las opciones. Example: https://khipu.com/payment/info/gqzdy6chjne9.
        simplified_transfer_url (str): URL de pago simplificado. Example:
            https://app.khipu.com/payment/simplified/gqzdy6chjne9.
        transfer_url (str): URL de pago normal. Example: https://khipu.com/payment/manual/gqzdy6chjne9.
        app_url (str): URL para invocar el pago desde un dispositivo móvil usando la APP de Khipu. Example:
            khipu:///pos/gqzdy6chjne9.
        ready_for_terminal (bool): Es `true` si el pago ya cuenta con todos los datos necesarios para abrir directamente
            la aplicación de pagos Khipu.
    """

    payment_id: str
    payment_url: str
    simplified_transfer_url: str
    transfer_url: str
    app_url: str
    ready_for_terminal: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payment_id = self.payment_id

        payment_url = self.payment_url

        simplified_transfer_url = self.simplified_transfer_url

        transfer_url = self.transfer_url

        app_url = self.app_url

        ready_for_terminal = self.ready_for_terminal

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "payment_id": payment_id,
                "payment_url": payment_url,
                "simplified_transfer_url": simplified_transfer_url,
                "transfer_url": transfer_url,
                "app_url": app_url,
                "ready_for_terminal": ready_for_terminal,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        payment_id = d.pop("payment_id")

        payment_url = d.pop("payment_url")

        simplified_transfer_url = d.pop("simplified_transfer_url")

        transfer_url = d.pop("transfer_url")

        app_url = d.pop("app_url")

        ready_for_terminal = d.pop("ready_for_terminal")

        payment_post_payment_2 = cls(
            payment_id=payment_id,
            payment_url=payment_url,
            simplified_transfer_url=simplified_transfer_url,
            transfer_url=transfer_url,
            app_url=app_url,
            ready_for_terminal=ready_for_terminal,
        )

        payment_post_payment_2.additional_properties = d
        return payment_post_payment_2

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
