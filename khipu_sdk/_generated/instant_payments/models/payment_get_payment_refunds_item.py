from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.payment_get_payment_refunds_item_status import (
    PaymentGetPaymentRefundsItemStatus,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="PaymentGetPaymentRefundsItem")


@_attrs_define
class PaymentGetPaymentRefundsItem:
    """
    Attributes:
        id (str): Identificador único de la devolución, el mismo que entrega la respuesta de `POST /v3/refunds`.
            Example: b31bd9aa-273b-4aed-9516-85866d47a931.
        status (PaymentGetPaymentRefundsItemStatus): Estado de la devolución:
            `pending` (solicitada, aún sin confirmar),
            `authorized` (Khipu se hace responsable de la devolución),
            `paid` (los fondos fueron entregados al pagador, confirmado por la conciliación bancaria), y
            `expired` (la devolución no se confirmó dentro de 15 días hábiles y ya no se realizará). Example: paid.
        amount (str): Monto de la devolución. Example: 5000.0000.
        currency (str): El código de moneda en formato ISO-4217. Example: CLP.
        request_date (datetime.datetime): Fecha y hora en que se solicitó la devolución. Formato ISO-8601. Example:
            2026-08-28T14:03:22.000Z.
        authorization_date (datetime.datetime | Unset): Fecha y hora en que la devolución quedó autorizada. Solo aparece
            cuando ya fue autorizada. Formato ISO-8601. Example: 2026-08-28T14:05:12.000Z.
        payout_date (datetime.datetime | Unset): Fecha y hora en que los fondos fueron entregados al pagador. Solo
            aparece cuando la devolución ya fue pagada. Formato ISO-8601. Example: 2026-09-01T09:30:00.000Z.
        expiration_date (datetime.datetime | Unset): Fecha y hora en que la devolución expiró. Solo aparece cuando la
            devolución expiró. Formato ISO-8601. Example: 2026-08-31T03:00:00.000Z.
    """

    id: str
    status: PaymentGetPaymentRefundsItemStatus
    amount: str
    currency: str
    request_date: datetime.datetime
    authorization_date: datetime.datetime | Unset = UNSET
    payout_date: datetime.datetime | Unset = UNSET
    expiration_date: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        status = self.status.value

        amount = self.amount

        currency = self.currency

        request_date = self.request_date.isoformat()

        authorization_date: str | Unset = UNSET
        if not isinstance(self.authorization_date, Unset):
            authorization_date = self.authorization_date.isoformat()

        payout_date: str | Unset = UNSET
        if not isinstance(self.payout_date, Unset):
            payout_date = self.payout_date.isoformat()

        expiration_date: str | Unset = UNSET
        if not isinstance(self.expiration_date, Unset):
            expiration_date = self.expiration_date.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "status": status,
                "amount": amount,
                "currency": currency,
                "request_date": request_date,
            }
        )
        if authorization_date is not UNSET:
            field_dict["authorization_date"] = authorization_date
        if payout_date is not UNSET:
            field_dict["payout_date"] = payout_date
        if expiration_date is not UNSET:
            field_dict["expiration_date"] = expiration_date

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        status = PaymentGetPaymentRefundsItemStatus(d.pop("status"))

        amount = d.pop("amount")

        currency = d.pop("currency")

        request_date = isoparse(d.pop("request_date"))

        _authorization_date = d.pop("authorization_date", UNSET)
        authorization_date: datetime.datetime | Unset
        if isinstance(_authorization_date, Unset):
            authorization_date = UNSET
        else:
            authorization_date = isoparse(_authorization_date)

        _payout_date = d.pop("payout_date", UNSET)
        payout_date: datetime.datetime | Unset
        if isinstance(_payout_date, Unset):
            payout_date = UNSET
        else:
            payout_date = isoparse(_payout_date)

        _expiration_date = d.pop("expiration_date", UNSET)
        expiration_date: datetime.datetime | Unset
        if isinstance(_expiration_date, Unset):
            expiration_date = UNSET
        else:
            expiration_date = isoparse(_expiration_date)

        payment_get_payment_refunds_item = cls(
            id=id,
            status=status,
            amount=amount,
            currency=currency,
            request_date=request_date,
            authorization_date=authorization_date,
            payout_date=payout_date,
            expiration_date=expiration_date,
        )

        payment_get_payment_refunds_item.additional_properties = d
        return payment_get_payment_refunds_item

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
