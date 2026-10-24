from enum import Enum


class PaymentGetPaymentRefundsItemStatus(str, Enum):
    AUTHORIZED = "authorized"
    EXPIRED = "expired"
    PAID = "paid"
    PENDING = "pending"

    def __str__(self) -> str:
        return str(self.value)
