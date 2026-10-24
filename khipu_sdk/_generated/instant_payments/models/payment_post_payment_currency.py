from enum import Enum


class PaymentPostPaymentCurrency(str, Enum):
    ARS = "ARS"
    BOB = "BOB"
    CLF = "CLF"
    CLP = "CLP"
    COP = "COP"
    EUR = "EUR"
    MXN = "MXN"
    PEN = "PEN"
    USD = "USD"

    def __str__(self) -> str:
        return str(self.value)
