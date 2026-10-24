from enum import Enum


class RefundPostRefundType(str, Enum):
    FULL = "full"
    PARTIAL = "partial"

    def __str__(self) -> str:
        return str(self.value)
