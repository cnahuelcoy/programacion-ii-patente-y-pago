from datetime import datetime, timedelta

from dominio.modalidad_cobro import ModalidadCobro


class CobroPorMinuto(ModalidadCobro):
    """Cobra cada minuto iniciado, con un mínimo de un minuto."""

    def __init__(self, tarifa: int):
        self.tarifa = tarifa

    @property
    def tarifa(self) -> int:
        """Precio de un minuto en pesos chilenos enteros."""
        return self.__tarifa

    @tarifa.setter
    def tarifa(self, valor: int) -> None:
        # bool hereda de int, pero no representa una tarifa válida.
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise TypeError("La tarifa debe ser un entero en pesos chilenos.")
        if valor <= 0:
            raise ValueError("La tarifa debe ser positiva.")
        self.__tarifa = valor

    def calcular_importe(self, ingreso: datetime, salida: datetime) -> int:
        if not isinstance(ingreso, datetime) or not isinstance(salida, datetime):
            raise TypeError("El ingreso y la salida deben ser objetos datetime.")
        if salida < ingreso:
            raise ValueError("La salida debe ser igual o posterior al ingreso.")

        duracion = salida - ingreso
        # Dividir timedeltas conserva exactamente las fracciones de minuto.
        minutos, resto = divmod(duracion, timedelta(minutes=1))
        if resto > timedelta(0):
            minutos += 1
        minutos = max(1, minutos)
        return minutos * self.tarifa
