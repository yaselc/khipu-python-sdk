from enum import Enum


class PaymentGetPaymentStatusDetail(str, Enum):
    MARKED_AS_ABUSE = "marked-as-abuse"
    MARKED_PAID_BY_RECEIVER = "marked-paid-by-receiver"
    NORMAL = "normal"
    PENDING = "pending"
    REJECTED_BY_PAYER = "rejected-by-payer"
    REVERSED = "reversed"

    def __str__(self) -> str:
        return str(self.value)
