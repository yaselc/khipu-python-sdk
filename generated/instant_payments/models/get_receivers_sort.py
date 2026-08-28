from enum import Enum


class GetReceiversSort(str, Enum):
    DATE_CREATED = "date_created"
    ID = "id"
    NAME = "name"

    def __str__(self) -> str:
        return str(self.value)
