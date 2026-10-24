from enum import Enum


class PaymentGetPaymentStatus(str, Enum):
    DONE = "done"
    PENDING = "pending"
    VERIFYING = "verifying"

    def __str__(self) -> str:
        return str(self.value)
