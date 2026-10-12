from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.predict_get_predict_all_banks_item import (
        PredictGetPredictAllBanksItem,
    )


T = TypeVar("T", bound="PredictGetPredictAll")


@_attrs_define
class PredictGetPredictAll:
    """Predicción acerca del resultado de un pago para cada banco disponible para la cuenta de cobro.

    Attributes:
        banks (list[PredictGetPredictAllBanksItem]): Arreglo con la predicción para cada banco, en el mismo orden que
            `GET /v3/banks`. Puede venir vacío si no hay bancos disponibles.
    """

    banks: list[PredictGetPredictAllBanksItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        banks = []
        for banks_item_data in self.banks:
            banks_item = banks_item_data.to_dict()
            banks.append(banks_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "banks": banks,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.predict_get_predict_all_banks_item import (
            PredictGetPredictAllBanksItem,
        )

        d = dict(src_dict)
        banks = []
        _banks = d.pop("banks")
        for banks_item_data in _banks:
            banks_item = PredictGetPredictAllBanksItem.from_dict(banks_item_data)

            banks.append(banks_item)

        predict_get_predict_all = cls(
            banks=banks,
        )

        predict_get_predict_all.additional_properties = d
        return predict_get_predict_all

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
