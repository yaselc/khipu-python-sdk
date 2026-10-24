from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.payment_get_payment_funds_source import PaymentGetPaymentFundsSource
from ..models.payment_get_payment_payment_method import PaymentGetPaymentPaymentMethod
from ..models.payment_get_payment_status import PaymentGetPaymentStatus
from ..models.payment_get_payment_status_detail import PaymentGetPaymentStatusDetail
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.payment_get_payment_refunds_item import PaymentGetPaymentRefundsItem


T = TypeVar("T", bound="PaymentGetPayment")


@_attrs_define
class PaymentGetPayment:
    """Información completa del pago. Datos con los que fue creado y el estado actual del pago.

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
        notification_token (str): Cadena de caracteres alfanuméricos que identifican unicamente al pago, es el
            identificador que el servidor de Khipu enviará al servidor del comercio cuando notifique que un pago está
            conciliado. Example: 9dec8aa176c5223026919b3b5579a4776923e646ff3be686b9e6b62ec042e91f.
        receiver_id (int): Identificador único de una cuenta de cobro. Example: 985101.
        conciliation_date (datetime.datetime): Fecha y hora de conciliación del pago. Formato ISO-8601. Example:
            2017-03-01T13:00:00.000Z.
        subject (str): Motivo del pago. Example: Test.
        amount (str): El monto del cobro. Example: 1000.0000.
        currency (str): El código de moneda en formato ISO-4217. Example: CLP.
        status (PaymentGetPaymentStatus): Estado del pago, puede ser `pending` (el pagador aún no comienza a pagar),
            `verifying` (se está verificando el pago) o `done`, cuando el pago ya está confirmado. Example: done.
        status_detail (PaymentGetPaymentStatusDetail): Detalle del estado del pago:
            `pending` (el pagador aún no comienza a pagar),
            `normal` (el pago fue verificado y fue cancelado por algún medio de pago estándar),
            `marked-paid-by-receiver` (el cobrador marcó el cobro como pagado por otro medio),
            `rejected-by-payer` (el pagador declaró que no pagará),
            `marked-as-abuse` (el pagador declaró que no pagará y que el cobro fue no solicitado),
            `reversed` (el pago fue anulado por el comercio y el monto quedó marcado para devolución al pagador),
            `partially-refunded` (una parte del monto del pago quedó marcada para devolución al pagador mediante
            devoluciones parciales), y
            `fully-refunded` (el monto total del pago quedó marcado para devolución al pagador mediante una o más
            devoluciones). Example: normal.
        body (str): Detalle del cobro. Example: Test.
        picture_url (str): URL con imagen del cobro. Example: https://micomercio.com/picture_url.
        receipt_url (str): URL del comprobante de pago. Example: https://micomercio.com/order/receipt_url.
        return_url (str): URL donde se redirige al pagador luego que termina el pago. Example:
            https://micomercio.com/order/return_url.
        cancel_url (str): URL donde se redirige al pagador luego de que desiste hacer el pago. Example:
            https://micomercio.com/order/cancel_url.
        notify_url (str): URL del webservice donde se notificará el pago. Example:
            https://micomercio.com/webhook/notify_url.
        notify_api_version (str): Versión de la API de notificación. Example: 3.0.
        expires_date (datetime.datetime): Fecha máxima para ejecutar el pago (en formato ISO-8601). El cliente podrá
            realizar varios intentos de pago hasta dicha fecha. Cada intento tiene un plazo individual de 3 horas para su
            ejecución. Example: 2023-12-31T15:45:00-04:00.
        attachment_urls (list[str]): Arreglo de URLs de archivos adjuntos al pago.
        bank (str): Nombre del banco seleccionado por el pagador. Example: Banco de Chile (Edwards Citi).
        bank_id (str): Identificador del banco seleccionado por el pagador. Example: dfFbF.
        payer_name (str): Nombre del pagador. Example: Nombre Pagador.
        payer_email (str): Correo electrónico del pagador. Example: pagador@email.com.
        personal_identifier (str): Identificador personal del pagador. Example: 11.000.111-9.
        bank_account_number (str): Número de cuenta bancaria del pagador. Example: 001120490689.
        out_of_date_conciliation (bool): Es `true` si la conciliación del pago fue hecha luego de la fecha de
            expiración. Example: True.
        transaction_id (str): Identificador del pago asignado por el cobrador. Example: zwo3wqz6uulcvajt.
        custom (str): Campo genérico que asigna el cobrador al momento de hacer el pago. Example: <xml>...</xml>.
        responsible_user_email (str): Correo electrónico de la persona responsable del pago. Example:
            responsible@email.com.
        send_reminders (bool): Es `true` cuando este es un cobro por correo electrónico y Khipu enviará recordatorios.
            Example: True.
        send_email (bool): Es `true` cuando Khipu enviará el cobro por correo electrónico. Example: True.
        payment_method (PaymentGetPaymentPaymentMethod): Método de pago usado por el pagador, puede ser
            `regular_transfer` (transferencia normal) o `simplified_transfer` (transferencia simplificada). Example:
            simplified_transfer.
        funds_source (PaymentGetPaymentFundsSource): Origen de fondos usado por el pagador, puede ser `debit` para pago
            con débito, `prepaid` para pago con prepago, `credit` para pago con crédito, o vacío en el caso de que se haya
            pagado mediante transferencia bancaria. Example: debit.
        authorizer_operation_code (str | Unset): Identificador único de la transacción otorgado por el organismo
            autorizador de la operación. Example: AUT-20240418-0001.
        discount (str | Unset): Monto a descontar del valor pagado. Example: 0.0000.
        third_party_authorization_details (str | Unset): Ignorar este campo.
        refunds (list[PaymentGetPaymentRefundsItem] | Unset): Devoluciones solicitadas sobre este pago, de la más
            antigua a la más reciente. Solo aparece cuando el pago tiene devoluciones. Un pago anulado no admite
            devoluciones: esa operación se informa con `void_payout_date`.
        total_refunded (str | Unset): Monto total devuelto al pagador en este pago. Solo aparece cuando el pago tiene
            devoluciones. Las devoluciones expiradas no se suman. Example: 5000.0000.
        void_payout_date (datetime.datetime | Unset): Fecha y hora en que los fondos de la anulación fueron entregados
            al pagador. Solo aparece en pagos anulados (`status_detail: reversed`) cuya anulación ya fue pagada al pagador.
            Formato ISO-8601. Example: 2026-09-02T09:30:00.000Z.
    """

    payment_id: str
    payment_url: str
    simplified_transfer_url: str
    transfer_url: str
    app_url: str
    ready_for_terminal: bool
    notification_token: str
    receiver_id: int
    conciliation_date: datetime.datetime
    subject: str
    amount: str
    currency: str
    status: PaymentGetPaymentStatus
    status_detail: PaymentGetPaymentStatusDetail
    body: str
    picture_url: str
    receipt_url: str
    return_url: str
    cancel_url: str
    notify_url: str
    notify_api_version: str
    expires_date: datetime.datetime
    attachment_urls: list[str]
    bank: str
    bank_id: str
    payer_name: str
    payer_email: str
    personal_identifier: str
    bank_account_number: str
    out_of_date_conciliation: bool
    transaction_id: str
    custom: str
    responsible_user_email: str
    send_reminders: bool
    send_email: bool
    payment_method: PaymentGetPaymentPaymentMethod
    funds_source: PaymentGetPaymentFundsSource
    authorizer_operation_code: str | Unset = UNSET
    discount: str | Unset = UNSET
    third_party_authorization_details: str | Unset = UNSET
    refunds: list[PaymentGetPaymentRefundsItem] | Unset = UNSET
    total_refunded: str | Unset = UNSET
    void_payout_date: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payment_id = self.payment_id

        payment_url = self.payment_url

        simplified_transfer_url = self.simplified_transfer_url

        transfer_url = self.transfer_url

        app_url = self.app_url

        ready_for_terminal = self.ready_for_terminal

        notification_token = self.notification_token

        receiver_id = self.receiver_id

        conciliation_date = self.conciliation_date.isoformat()

        subject = self.subject

        amount = self.amount

        currency = self.currency

        status = self.status.value

        status_detail = self.status_detail.value

        body = self.body

        picture_url = self.picture_url

        receipt_url = self.receipt_url

        return_url = self.return_url

        cancel_url = self.cancel_url

        notify_url = self.notify_url

        notify_api_version = self.notify_api_version

        expires_date = self.expires_date.isoformat()

        attachment_urls = self.attachment_urls

        bank = self.bank

        bank_id = self.bank_id

        payer_name = self.payer_name

        payer_email = self.payer_email

        personal_identifier = self.personal_identifier

        bank_account_number = self.bank_account_number

        out_of_date_conciliation = self.out_of_date_conciliation

        transaction_id = self.transaction_id

        custom = self.custom

        responsible_user_email = self.responsible_user_email

        send_reminders = self.send_reminders

        send_email = self.send_email

        payment_method = self.payment_method.value

        funds_source = self.funds_source.value

        authorizer_operation_code = self.authorizer_operation_code

        discount = self.discount

        third_party_authorization_details = self.third_party_authorization_details

        refunds: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.refunds, Unset):
            refunds = []
            for refunds_item_data in self.refunds:
                refunds_item = refunds_item_data.to_dict()
                refunds.append(refunds_item)

        total_refunded = self.total_refunded

        void_payout_date: str | Unset = UNSET
        if not isinstance(self.void_payout_date, Unset):
            void_payout_date = self.void_payout_date.isoformat()

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
                "notification_token": notification_token,
                "receiver_id": receiver_id,
                "conciliation_date": conciliation_date,
                "subject": subject,
                "amount": amount,
                "currency": currency,
                "status": status,
                "status_detail": status_detail,
                "body": body,
                "picture_url": picture_url,
                "receipt_url": receipt_url,
                "return_url": return_url,
                "cancel_url": cancel_url,
                "notify_url": notify_url,
                "notify_api_version": notify_api_version,
                "expires_date": expires_date,
                "attachment_urls": attachment_urls,
                "bank": bank,
                "bank_id": bank_id,
                "payer_name": payer_name,
                "payer_email": payer_email,
                "personal_identifier": personal_identifier,
                "bank_account_number": bank_account_number,
                "out_of_date_conciliation": out_of_date_conciliation,
                "transaction_id": transaction_id,
                "custom": custom,
                "responsible_user_email": responsible_user_email,
                "send_reminders": send_reminders,
                "send_email": send_email,
                "payment_method": payment_method,
                "funds_source": funds_source,
            }
        )
        if authorizer_operation_code is not UNSET:
            field_dict["authorizer_operation_code"] = authorizer_operation_code
        if discount is not UNSET:
            field_dict["discount"] = discount
        if third_party_authorization_details is not UNSET:
            field_dict["third_party_authorization_details"] = (
                third_party_authorization_details
            )
        if refunds is not UNSET:
            field_dict["refunds"] = refunds
        if total_refunded is not UNSET:
            field_dict["total_refunded"] = total_refunded
        if void_payout_date is not UNSET:
            field_dict["void_payout_date"] = void_payout_date

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.payment_get_payment_refunds_item import (
            PaymentGetPaymentRefundsItem,
        )

        d = dict(src_dict)
        payment_id = d.pop("payment_id")

        payment_url = d.pop("payment_url")

        simplified_transfer_url = d.pop("simplified_transfer_url")

        transfer_url = d.pop("transfer_url")

        app_url = d.pop("app_url")

        ready_for_terminal = d.pop("ready_for_terminal")

        notification_token = d.pop("notification_token")

        receiver_id = d.pop("receiver_id")

        conciliation_date = isoparse(d.pop("conciliation_date"))

        subject = d.pop("subject")

        amount = d.pop("amount")

        currency = d.pop("currency")

        status = PaymentGetPaymentStatus(d.pop("status"))

        status_detail = PaymentGetPaymentStatusDetail(d.pop("status_detail"))

        body = d.pop("body")

        picture_url = d.pop("picture_url")

        receipt_url = d.pop("receipt_url")

        return_url = d.pop("return_url")

        cancel_url = d.pop("cancel_url")

        notify_url = d.pop("notify_url")

        notify_api_version = d.pop("notify_api_version")

        expires_date = isoparse(d.pop("expires_date"))

        attachment_urls = cast(list[str], d.pop("attachment_urls"))

        bank = d.pop("bank")

        bank_id = d.pop("bank_id")

        payer_name = d.pop("payer_name")

        payer_email = d.pop("payer_email")

        personal_identifier = d.pop("personal_identifier")

        bank_account_number = d.pop("bank_account_number")

        out_of_date_conciliation = d.pop("out_of_date_conciliation")

        transaction_id = d.pop("transaction_id")

        custom = d.pop("custom")

        responsible_user_email = d.pop("responsible_user_email")

        send_reminders = d.pop("send_reminders")

        send_email = d.pop("send_email")

        payment_method = PaymentGetPaymentPaymentMethod(d.pop("payment_method"))

        funds_source = PaymentGetPaymentFundsSource(d.pop("funds_source"))

        authorizer_operation_code = d.pop("authorizer_operation_code", UNSET)

        discount = d.pop("discount", UNSET)

        third_party_authorization_details = d.pop(
            "third_party_authorization_details", UNSET
        )

        _refunds = d.pop("refunds", UNSET)
        refunds: list[PaymentGetPaymentRefundsItem] | Unset = UNSET
        if _refunds is not UNSET:
            refunds = []
            for refunds_item_data in _refunds:
                refunds_item = PaymentGetPaymentRefundsItem.from_dict(refunds_item_data)

                refunds.append(refunds_item)

        total_refunded = d.pop("total_refunded", UNSET)

        _void_payout_date = d.pop("void_payout_date", UNSET)
        void_payout_date: datetime.datetime | Unset
        if isinstance(_void_payout_date, Unset):
            void_payout_date = UNSET
        else:
            void_payout_date = isoparse(_void_payout_date)

        payment_get_payment = cls(
            payment_id=payment_id,
            payment_url=payment_url,
            simplified_transfer_url=simplified_transfer_url,
            transfer_url=transfer_url,
            app_url=app_url,
            ready_for_terminal=ready_for_terminal,
            notification_token=notification_token,
            receiver_id=receiver_id,
            conciliation_date=conciliation_date,
            subject=subject,
            amount=amount,
            currency=currency,
            status=status,
            status_detail=status_detail,
            body=body,
            picture_url=picture_url,
            receipt_url=receipt_url,
            return_url=return_url,
            cancel_url=cancel_url,
            notify_url=notify_url,
            notify_api_version=notify_api_version,
            expires_date=expires_date,
            attachment_urls=attachment_urls,
            bank=bank,
            bank_id=bank_id,
            payer_name=payer_name,
            payer_email=payer_email,
            personal_identifier=personal_identifier,
            bank_account_number=bank_account_number,
            out_of_date_conciliation=out_of_date_conciliation,
            transaction_id=transaction_id,
            custom=custom,
            responsible_user_email=responsible_user_email,
            send_reminders=send_reminders,
            send_email=send_email,
            payment_method=payment_method,
            funds_source=funds_source,
            authorizer_operation_code=authorizer_operation_code,
            discount=discount,
            third_party_authorization_details=third_party_authorization_details,
            refunds=refunds,
            total_refunded=total_refunded,
            void_payout_date=void_payout_date,
        )

        payment_get_payment.additional_properties = d
        return payment_get_payment

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
