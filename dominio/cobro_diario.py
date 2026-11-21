from datetime import datetime, timedelta

from dominio.modalidad_cobro import ModalidadCobro


class CobroDiario(ModalidadCobro):
    """Cobra cada bloque iniciado de 24 horas, con un mínimo de un día."""

    def __init__(self, tarifa: int):
        self.tarifa = tarifa

    @property
    def tarifa(self) -> int:
        """Precio de un bloque de 24 horas en pesos chilenos."""
        return self.__tarifa

    @tarifa.setter
    def tarifa(self, valor: int) -> None:
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
        dias, resto = divmod(duracion, timedelta(days=1))
        if resto > timedelta(0):
            dias += 1
        dias = max(1, dias)
        return dias * self.tarifa
