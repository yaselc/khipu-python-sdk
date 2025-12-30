from enum import Enum


class PaymentGetPaymentFundsSource(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    NOT_AVAILABLE = "not-available"
    PREPAID = "prepaid"
    VALUE_4 = ""

    def __str__(self) -> str:
        return str(self.value)
