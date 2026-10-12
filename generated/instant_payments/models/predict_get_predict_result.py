from enum import Enum


class PredictGetPredictResult(str, Enum):
    MAX_AMOUNT_EXCEEDED = "MAX_AMOUNT_EXCEEDED"
    NEW_DESTINATARY_AMOUNT_EXCEEDED = "NEW_DESTINATARY_AMOUNT_EXCEEDED"
    NEW_DESTINATARY_COOL_DOWN = "NEW_DESTINATARY_COOL_DOWN"
    NOT_AVAILABLE_ACCOUNT = "NOT_AVAILABLE_ACCOUNT"
    OK = "OK"

    def __str__(self) -> str:
        return str(self.value)
