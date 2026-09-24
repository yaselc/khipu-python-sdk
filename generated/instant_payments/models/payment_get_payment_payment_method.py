from enum import Enum


class PaymentGetPaymentPaymentMethod(str, Enum):
    DIRECT_DEBIT = "direct_debit"
    NOT_AVAILABLE = "not_available"
    REGULAR_TRANSFER = "regular_transfer"
    SIMPLIFIED_TRANSFER = "simplified_transfer"

    def __str__(self) -> str:
        return str(self.value)
