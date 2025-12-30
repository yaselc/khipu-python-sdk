from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.predict_get_predict_result import PredictGetPredictResult

T = TypeVar("T", bound="PredictGetPredict")


@_attrs_define
class PredictGetPredict:
    """Predicción acerca del resultado de un pago, si podrá o no funcionar. Información adicional como máximo posible de
    transferir a un nuevo destinatario.

        Attributes:
            result (PredictGetPredictResult): El resultado de la predicción. Example: ok.
            max_amount (float): El monto máximo posible para transferir. Example: 5000000.
            cool_down_date (str): Fecha de término para la restricción de monto en formato ISO-8601 Example:
                2024-06-21T11:23:09.123Z.
            new_destinatary_max_amount (float): Monto máximo para transferir a un nuevo destinatario. Example: 100000.
    """

    result: PredictGetPredictResult
    max_amount: float
    cool_down_date: str
    new_destinatary_max_amount: float
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = self.result.value

        max_amount = self.max_amount

        cool_down_date = self.cool_down_date

        new_destinatary_max_amount = self.new_destinatary_max_amount

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "result": result,
                "max_amount": max_amount,
                "cool_down_date": cool_down_date,
                "new_destinatary_max_amount": new_destinatary_max_amount,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        result = PredictGetPredictResult(d.pop("result"))

        max_amount = d.pop("max_amount")

        cool_down_date = d.pop("cool_down_date")

        new_destinatary_max_amount = d.pop("new_destinatary_max_amount")

        predict_get_predict = cls(
            result=result,
            max_amount=max_amount,
            cool_down_date=cool_down_date,
            new_destinatary_max_amount=new_destinatary_max_amount,
        )

        predict_get_predict.additional_properties = d
        return predict_get_predict

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
