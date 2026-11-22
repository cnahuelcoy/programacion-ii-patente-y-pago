from datetime import datetime

from dominio.modalidad_cobro import ModalidadCobro


class CobroMensual(ModalidadCobro):
    """Representa una suscripción mensual que cubre la estadía."""

    def __init__(self, tarifa: int):
        self.tarifa = tarifa

    @property
    def tarifa(self) -> int:
        """Precio de contratación de la suscripción, en pesos chilenos."""
        return self.__tarifa

    @tarifa.setter
    def tarifa(self, valor: int) -> None:
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise TypeError("La tarifa debe ser un entero en pesos chilenos.")
        if valor <= 0:
            raise ValueError("La tarifa debe ser positiva.")
        self.__tarifa = valor

    def calcular_importe(self, ingreso: datetime, salida: datetime) -> int:
        """Devuelve cero porque esta estadía está cubierta por la suscripción."""
        if not isinstance(ingreso, datetime) or not isinstance(salida, datetime):
            raise TypeError("El ingreso y la salida deben ser objetos datetime.")
        if salida < ingreso:
            raise ValueError("La salida debe ser igual o posterior al ingreso.")
        return 0

    def calcular_importe_contratacion(self) -> int:
        """Devuelve el precio a pagar al contratar la suscripción mensual."""
        return self.tarifa
