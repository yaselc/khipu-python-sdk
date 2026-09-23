from enum import Enum


class SubscriptionStatusStatus(str, Enum):
    DISABLED = "DISABLED"
    DISCARDED = "DISCARDED"
    ENABLED = "ENABLED"
    PENDING = "PENDING"
    SIGNED = "SIGNED"

    def __str__(self) -> str:
        return str(self.value)
