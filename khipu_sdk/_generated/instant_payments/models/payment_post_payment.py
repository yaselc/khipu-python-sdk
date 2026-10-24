from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.payment_post_payment_currency import PaymentPostPaymentCurrency
from ..types import UNSET, Unset

T = TypeVar("T", bound="PaymentPostPayment")


@_attrs_define
class PaymentPostPayment:
    """Crea un pago en Khipu y obtiene las URLs para redirección al usuario para que complete el pago.

    Attributes:
        amount (float): El monto del cobro. Sin separador de miles y usando '.' como separador de decimales. Hasta 4
            lugares decimales, dependiendo de la moneda. Example: 1000.
        currency (PaymentPostPaymentCurrency): El código de moneda en formato ISO-4217. Example: CLP.
        subject (str): Motivo. Example: Cobro de prueba.
        transaction_id (str | Unset): Identificador propio de la transacción. Ej: número de factura u orden de compra.
            Example: zwo3wqz6uulcvajt.
        custom (str | Unset): Parámetro para enviar información personalizada de la transacción. Ej: documento XML con
            el detalle del carro de compra. Example: <xml>...</xml>.
        body (str | Unset): Descripción del cobro. Example: Cobro de orden de compra #123-abcdef.
        bank_id (str | Unset): Identificador del banco para usar en el pago. Example: SDdGj.
        return_url (str | Unset): La dirección URL a donde enviar al cliente mientras el pago está siendo verificado.
            Example: https://micomercio.com/order/return_url.
        cancel_url (str | Unset): La dirección URL a donde enviar al cliente si decide no hacer hacer la transacción.
            Example: https://micomercio.com/order/cancel_url.
        picture_url (str | Unset): Una dirección URL de una foto de tu producto o servicio. Example:
            https://micomercio.com/picture_url.
        notify_url (str | Unset): La dirección del web-service que utilizará khipu para notificar cuando el pago esté
            conciliado. Example: https://micomercio.com/webhook/notify_url.
        contract_url (str | Unset): La dirección URL del archivo PDF con el contrato a firmar mediante este pago. El
            cobrador debe estar habilitado para este servicio y el campo `fixed_payer_personal_identifier` es obligatorio.
            Example: https://micomercio.com/contract_url.
        notify_api_version (str | Unset): Versión de la API de notificaciones para recibir avisos por web-service.
            Example: 3.0.
        expires_date (datetime.datetime | Unset): Fecha máxima para ejecutar el pago (en formato ISO-8601). El cliente
            podrá realizar varios intentos de pago hasta dicha fecha. Cada intento tiene un plazo individual de 3 horas para
            su ejecución. Example: 2023-12-31T15:45:00-04:00.
        send_email (bool | Unset): Si es `true`, se enviará una solicitud de cobro al correo especificado en
            `payer_email`.
        payer_name (str | Unset): Nombre del pagador. Es obligatorio cuando `send_email` es `true`. Example: Nombre
            Pagador.
        payer_email (str | Unset): Correo del pagador. Es obligatorio cuando `send_email` es `true`. Example:
            pagador@email.com.
        send_reminders (bool | Unset): Si es `true`, se enviarán recordatorios de cobro. Example: True.
        responsible_user_email (str | Unset): Correo electrónico del responsable de este cobro, debe corresponder a un
            usuario Khipu con permisos para cobrar usando esta cuenta de cobro. Example: responsible@email.com.
        fixed_payer_personal_identifier (str | Unset): Identificador personal. Si se especifica, solo podrá ser pagado
            usando ese identificador. Example: 11.000.111-9.
        integrator_fee (str | Unset): Comisión para el integrador. Sólo es válido si la cuenta de cobro tiene una cuenta
            de integrador asociada. Example: 100.
        collect_account_uuid (str | Unset): Para cuentas de cobro con más cuenta propia. Permite elegir la cuenta donde
            debe ocurrir la transferencia. Example: 007367340234.
        confirm_timeout_date (datetime.datetime | Unset): Fecha de rendición del cobro. Es también la fecha final para
            poder reembolsar el cobro. Formato ISO-8601. Example: 2017-03-01T13:00:00Z.
        mandatory_payment_method (str | Unset): El cobro sólo se podrá pagar utilizando el medio de pago especificado.
            Los posibles valores para este campo se encuentran en el campo `id` de la respuesta del endpoint
            `/v3/merchants/{id}/paymentMethods`. Example: SIMPLIFIED_TRANSFER.
        psp_client_merchant_name (str | Unset): Nombre del comercio final para quien un proveedor de servicios de pago
            procesa un pago. Requerido para transacciones de clientes PSP; no aplicable para otros. En caso de tratarse de
            un PSP de PSP, estos deben ingresarse separados por '->'. Example: PSP 1->PSP 2->Client Name.
        psp_client_merchant_logo_url (str | Unset): URL del logo del comercio final al que corresponde el pago procesado
            por el proveedor de servicios de pago. Opcional para transacciones de clientes PSP; no aplicable para otros.
            Example: https://micomercio.com/logo.png.
    """

    amount: float
    currency: PaymentPostPaymentCurrency
    subject: str
    transaction_id: str | Unset = UNSET
    custom: str | Unset = UNSET
    body: str | Unset = UNSET
    bank_id: str | Unset = UNSET
    return_url: str | Unset = UNSET
    cancel_url: str | Unset = UNSET
    picture_url: str | Unset = UNSET
    notify_url: str | Unset = UNSET
    contract_url: str | Unset = UNSET
    notify_api_version: str | Unset = UNSET
    expires_date: datetime.datetime | Unset = UNSET
    send_email: bool | Unset = UNSET
    payer_name: str | Unset = UNSET
    payer_email: str | Unset = UNSET
    send_reminders: bool | Unset = UNSET
    responsible_user_email: str | Unset = UNSET
    fixed_payer_personal_identifier: str | Unset = UNSET
    integrator_fee: str | Unset = UNSET
    collect_account_uuid: str | Unset = UNSET
    confirm_timeout_date: datetime.datetime | Unset = UNSET
    mandatory_payment_method: str | Unset = UNSET
    psp_client_merchant_name: str | Unset = UNSET
    psp_client_merchant_logo_url: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        amount = self.amount

        currency = self.currency.value

        subject = self.subject

        transaction_id = self.transaction_id

        custom = self.custom

        body = self.body

        bank_id = self.bank_id

        return_url = self.return_url

        cancel_url = self.cancel_url

        picture_url = self.picture_url

        notify_url = self.notify_url

        contract_url = self.contract_url

        notify_api_version = self.notify_api_version

        expires_date: str | Unset = UNSET
        if not isinstance(self.expires_date, Unset):
            expires_date = self.expires_date.isoformat()

        send_email = self.send_email

        payer_name = self.payer_name

        payer_email = self.payer_email

        send_reminders = self.send_reminders

        responsible_user_email = self.responsible_user_email

        fixed_payer_personal_identifier = self.fixed_payer_personal_identifier

        integrator_fee = self.integrator_fee

        collect_account_uuid = self.collect_account_uuid

        confirm_timeout_date: str | Unset = UNSET
        if not isinstance(self.confirm_timeout_date, Unset):
            confirm_timeout_date = self.confirm_timeout_date.isoformat()

        mandatory_payment_method = self.mandatory_payment_method

        psp_client_merchant_name = self.psp_client_merchant_name

        psp_client_merchant_logo_url = self.psp_client_merchant_logo_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "amount": amount,
                "currency": currency,
                "subject": subject,
            }
        )
        if transaction_id is not UNSET:
            field_dict["transaction_id"] = transaction_id
        if custom is not UNSET:
            field_dict["custom"] = custom
        if body is not UNSET:
            field_dict["body"] = body
        if bank_id is not UNSET:
            field_dict["bank_id"] = bank_id
        if return_url is not UNSET:
            field_dict["return_url"] = return_url
        if cancel_url is not UNSET:
            field_dict["cancel_url"] = cancel_url
        if picture_url is not UNSET:
            field_dict["picture_url"] = picture_url
        if notify_url is not UNSET:
            field_dict["notify_url"] = notify_url
        if contract_url is not UNSET:
            field_dict["contract_url"] = contract_url
        if notify_api_version is not UNSET:
            field_dict["notify_api_version"] = notify_api_version
        if expires_date is not UNSET:
            field_dict["expires_date"] = expires_date
        if send_email is not UNSET:
            field_dict["send_email"] = send_email
        if payer_name is not UNSET:
            field_dict["payer_name"] = payer_name
        if payer_email is not UNSET:
            field_dict["payer_email"] = payer_email
        if send_reminders is not UNSET:
            field_dict["send_reminders"] = send_reminders
        if responsible_user_email is not UNSET:
            field_dict["responsible_user_email"] = responsible_user_email
        if fixed_payer_personal_identifier is not UNSET:
            field_dict["fixed_payer_personal_identifier"] = (
                fixed_payer_personal_identifier
            )
        if integrator_fee is not UNSET:
            field_dict["integrator_fee"] = integrator_fee
        if collect_account_uuid is not UNSET:
            field_dict["collect_account_uuid"] = collect_account_uuid
        if confirm_timeout_date is not UNSET:
            field_dict["confirm_timeout_date"] = confirm_timeout_date
        if mandatory_payment_method is not UNSET:
            field_dict["mandatory_payment_method"] = mandatory_payment_method
        if psp_client_merchant_name is not UNSET:
            field_dict["psp_client_merchant_name"] = psp_client_merchant_name
        if psp_client_merchant_logo_url is not UNSET:
            field_dict["psp_client_merchant_logo_url"] = psp_client_merchant_logo_url

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        amount = d.pop("amount")

        currency = PaymentPostPaymentCurrency(d.pop("currency"))

        subject = d.pop("subject")

        transaction_id = d.pop("transaction_id", UNSET)

        custom = d.pop("custom", UNSET)

        body = d.pop("body", UNSET)

        bank_id = d.pop("bank_id", UNSET)

        return_url = d.pop("return_url", UNSET)

        cancel_url = d.pop("cancel_url", UNSET)

        picture_url = d.pop("picture_url", UNSET)

        notify_url = d.pop("notify_url", UNSET)

        contract_url = d.pop("contract_url", UNSET)

        notify_api_version = d.pop("notify_api_version", UNSET)

        _expires_date = d.pop("expires_date", UNSET)
        expires_date: datetime.datetime | Unset
        if isinstance(_expires_date, Unset):
            expires_date = UNSET
        else:
            expires_date = isoparse(_expires_date)

        send_email = d.pop("send_email", UNSET)

        payer_name = d.pop("payer_name", UNSET)

        payer_email = d.pop("payer_email", UNSET)

        send_reminders = d.pop("send_reminders", UNSET)

        responsible_user_email = d.pop("responsible_user_email", UNSET)

        fixed_payer_personal_identifier = d.pop(
            "fixed_payer_personal_identifier", UNSET
        )

        integrator_fee = d.pop("integrator_fee", UNSET)

        collect_account_uuid = d.pop("collect_account_uuid", UNSET)

        _confirm_timeout_date = d.pop("confirm_timeout_date", UNSET)
        confirm_timeout_date: datetime.datetime | Unset
        if isinstance(_confirm_timeout_date, Unset):
            confirm_timeout_date = UNSET
        else:
            confirm_timeout_date = isoparse(_confirm_timeout_date)

        mandatory_payment_method = d.pop("mandatory_payment_method", UNSET)

        psp_client_merchant_name = d.pop("psp_client_merchant_name", UNSET)

        psp_client_merchant_logo_url = d.pop("psp_client_merchant_logo_url", UNSET)

        payment_post_payment = cls(
            amount=amount,
            currency=currency,
            subject=subject,
            transaction_id=transaction_id,
            custom=custom,
            body=body,
            bank_id=bank_id,
            return_url=return_url,
            cancel_url=cancel_url,
            picture_url=picture_url,
            notify_url=notify_url,
            contract_url=contract_url,
            notify_api_version=notify_api_version,
            expires_date=expires_date,
            send_email=send_email,
            payer_name=payer_name,
            payer_email=payer_email,
            send_reminders=send_reminders,
            responsible_user_email=responsible_user_email,
            fixed_payer_personal_identifier=fixed_payer_personal_identifier,
            integrator_fee=integrator_fee,
            collect_account_uuid=collect_account_uuid,
            confirm_timeout_date=confirm_timeout_date,
            mandatory_payment_method=mandatory_payment_method,
            psp_client_merchant_name=psp_client_merchant_name,
            psp_client_merchant_logo_url=psp_client_merchant_logo_url,
        )

        payment_post_payment.additional_properties = d
        return payment_post_payment

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
