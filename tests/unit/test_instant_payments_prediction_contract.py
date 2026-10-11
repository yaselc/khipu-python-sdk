"""Guards on the Instant Payments prediction contract as Khipu publishes it.

The Instant Payments document adopted in #20 (sha256 ``fed2ea62...``) changed
``predict-get-predict.result`` from lowercase wire values (``ok``,
``max_amount_exceeded``, ...) to uppercase ones (``OK``,
``MAX_AMOUNT_EXCEEDED``, ...), and added ``GET /v3/predict/all``
(``getPredictAll``), which returns the same prediction per bank.

Prediction is not part of the supported ``KhipuClient`` facade; it is reachable
only through ``generated.instant_payments``. These tests pin that the generated
parser follows the published wire vocabulary exactly -- no lowercase aliases --
so a regeneration that drifts from the committed spec fails here, and that the
facade still does not expose prediction.
"""

from __future__ import annotations

import httpx
import pytest

from generated.instant_payments.api.default import get_predict_all
from generated.instant_payments.client import AuthenticatedClient
from generated.instant_payments.models.predict_get_predict import PredictGetPredict
from generated.instant_payments.models.predict_get_predict_all import (
    PredictGetPredictAll,
)
from generated.instant_payments.models.predict_get_predict_result import (
    PredictGetPredictResult,
)
from khipu_sdk import KhipuClient

#: The complete published vocabulary, uppercase since the #20 adoption.
PUBLISHED_RESULT_VOCABULARY = {
    "OK",
    "NEW_DESTINATARY_AMOUNT_EXCEEDED",
    "MAX_AMOUNT_EXCEEDED",
    "NEW_DESTINATARY_COOL_DOWN",
    "NOT_AVAILABLE_ACCOUNT",
}

#: What the previously pinned document published. Khipu no longer declares it.
RETIRED_LOWERCASE_VOCABULARY = {value.lower() for value in PUBLISHED_RESULT_VOCABULARY}


def prediction_body(**overrides):
    body = {
        "result": "OK",
        "max_amount": 5000000,
        "cool_down_date": "2024-06-21T11:23:09.123Z",
        "new_destinatary_max_amount": 100000,
    }
    body.update(overrides)
    return body


def bank_body(**overrides):
    body = {"bank_id": "Bawdf", "name": "Banco Ejemplo", **prediction_body()}
    body.update(overrides)
    return body


class TestResultVocabulary:
    def test_covers_exactly_the_published_values(self):
        assert {
            member.value for member in PredictGetPredictResult
        } == PUBLISHED_RESULT_VOCABULARY

    @pytest.mark.parametrize("value", sorted(PUBLISHED_RESULT_VOCABULARY))
    def test_each_published_result_parses(self, value):
        parsed = PredictGetPredict.from_dict(prediction_body(result=value))
        assert parsed.result.value == value

    @pytest.mark.parametrize("value", sorted(RETIRED_LOWERCASE_VOCABULARY))
    def test_retired_lowercase_values_are_rejected(self, value):
        """No compatibility aliases without evidence Khipu still sends them."""
        with pytest.raises(ValueError):
            PredictGetPredict.from_dict(prediction_body(result=value))


class TestPredictAll:
    def test_parses_one_prediction_per_bank_in_order(self):
        parsed = PredictGetPredictAll.from_dict(
            {
                "banks": [
                    bank_body(bank_id="Bawdf", result="OK"),
                    bank_body(bank_id="Xk12z", name="Otro", result="NOT_AVAILABLE_ACCOUNT"),
                ]
            }
        )

        assert [bank.bank_id for bank in parsed.banks] == ["Bawdf", "Xk12z"]
        assert [bank.result for bank in parsed.banks] == [
            PredictGetPredictResult.OK,
            PredictGetPredictResult.NOT_AVAILABLE_ACCOUNT,
        ]
        assert parsed.banks[1].name == "Otro"

    def test_an_empty_bank_list_is_valid(self):
        assert PredictGetPredictAll.from_dict({"banks": []}).banks == []

    @pytest.mark.parametrize("missing", ["bank_id", "name", "result"])
    def test_each_required_bank_field_is_enforced(self, missing):
        item = bank_body()
        del item[missing]
        with pytest.raises(KeyError):
            PredictGetPredictAll.from_dict({"banks": [item]})

    def test_banks_is_required(self):
        with pytest.raises(KeyError):
            PredictGetPredictAll.from_dict({})

    def test_items_share_the_uppercase_result_vocabulary(self):
        with pytest.raises(ValueError):
            PredictGetPredictAll.from_dict({"banks": [bank_body(result="ok")]})

    def test_operation_sends_the_published_query_without_bank_id(self):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"banks": [bank_body()]})

        client = AuthenticatedClient(
            base_url="https://payment-api.khipu.com",
            token="synthetic",
            prefix="",
            auth_header_name="x-api-key",
        ).set_httpx_client(
            httpx.Client(
                base_url="https://payment-api.khipu.com",
                transport=httpx.MockTransport(handler),
            )
        )

        parsed = get_predict_all.sync(
            client=client, payer_email="payer@example.com", amount="1000", currency="CLP"
        )

        (request,) = seen
        assert request.method == "GET"
        assert request.url.path == "/v3/predict/all"
        assert dict(request.url.params) == {
            "payer_email": "payer@example.com",
            "amount": "1000",
            "currency": "CLP",
        }
        assert isinstance(parsed, PredictGetPredictAll)
        assert parsed.banks[0].result is PredictGetPredictResult.OK


class TestFacadeDoesNotExposePrediction:
    def test_khipu_client_has_no_prediction_operation(self):
        assert not [name for name in dir(KhipuClient) if "predict" in name.lower()]
