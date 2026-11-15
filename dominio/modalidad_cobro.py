from abc import ABC, abstractmethod
from datetime import datetime


class ModalidadCobro(ABC):
    """Contrato común para calcular el cobro de una estadía."""

    @abstractmethod
    def calcular_importe(self, ingreso: datetime, salida: datetime) -> int:
        """Devuelve el importe de la estadía en pesos chilenos enteros."""
        pass
