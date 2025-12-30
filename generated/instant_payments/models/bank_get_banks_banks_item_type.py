from enum import Enum


class BankGetBanksBanksItemType(str, Enum):
    EMPRESA = "Empresa"
    PERSONA = "Persona"

    def __str__(self) -> str:
        return str(self.value)
