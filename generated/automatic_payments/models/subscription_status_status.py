from enum import Enum


class SubscriptionStatusStatus(str, Enum):
    DISABLED = "DISABLED"
    ENABLED = "ENABLED"
    SIGNED = "SIGNED"

    def __str__(self) -> str:
        return str(self.value)
