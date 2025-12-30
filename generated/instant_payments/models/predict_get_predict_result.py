from enum import Enum


class PredictGetPredictResult(str, Enum):
    MAX_AMOUNT_EXCEEDED = "max_amount_exceeded"
    NEW_DESTINATARY_AMOUNT_EXCEEDED = "new_destinatary_amount_exceeded"
    NEW_DESTINATARY_COOL_DOWN = "new_destinatary_cool_down"
    NOT_AVAILABLE_ACCOUNT = "not_available_account"
    OK = "ok"

    def __str__(self) -> str:
        return str(self.value)
