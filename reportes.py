from collections.abc import Iterable
from datetime import datetime
from functools import reduce


_MODALIDADES = ("minuto", "diaria", "mensual")


def _validar_fecha(fecha: datetime | None, nombre: str) -> None:
    if fecha is not None and (
        not isinstance(fecha, datetime) or fecha.tzinfo is not None
    ):
        raise ValueError(f"{nombre} debe ser un datetime sin zona horaria.")


def _validar_filtros(
    fecha_desde: datetime | None,
    fecha_hasta: datetime | None,
    modalidad: str | None,
) -> str | None:
    _validar_fecha(fecha_desde, "La fecha desde")
    _validar_fecha(fecha_hasta, "La fecha hasta")
    if fecha_desde is not None and fecha_hasta is not None:
        if fecha_hasta <= fecha_desde:
            raise ValueError("La fecha hasta debe ser posterior a la fecha desde.")

    if modalidad is None:
        return None
    if not isinstance(modalidad, str):
        raise ValueError("La modalidad debe ser texto.")
    if not modalidad.strip():
        return None
    modalidad = modalidad.strip().lower()
    if modalidad not in _MODALIDADES:
        raise ValueError("La modalidad debe ser minuto, diaria o mensual.")
    return modalidad


def _pagos_unicos(pagos: Iterable[dict]) -> list[dict]:
    pagos_por_id = {}
    for pago in pagos:
        pagos_por_id.setdefault(pago["pago_id"], pago)
    return list(pagos_por_id.values())


def filtrar_pagos(
    pagos: list[dict],
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    modalidad: str | None = None,
) -> list[dict]:
    """Filtra pagos por fecha_pago y modalidad, sin cambiar la lista recibida."""
    modalidad = _validar_filtros(fecha_desde, fecha_hasta, modalidad)

    def coincide(pago: dict) -> bool:
        fecha_pago = pago["fecha_pago"]
        _validar_fecha(fecha_pago, "La fecha del pago")
        return (
            (fecha_desde is None or fecha_pago >= fecha_desde)
            and (fecha_hasta is None or fecha_pago < fecha_hasta)
            and (modalidad is None or pago["modalidad"].lower() == modalidad)
        )

    return _pagos_unicos(list(filter(lambda pago: coincide(pago), pagos)))


def calcular_total_recaudado(pagos: Iterable[dict]) -> int:
    """Suma los pagos únicos; devuelve cero si la lista está vacía."""
    montos = map(lambda pago: pago["monto"], _pagos_unicos(pagos))
    return reduce(lambda total, monto: total + monto, montos, 0)


def calcular_totales_por_modalidad(pagos: list[dict]) -> dict[str, int]:
    """Devuelve el total general y los subtotales por modalidad."""
    pagos = _pagos_unicos(pagos)
    return {
        "total": calcular_total_recaudado(pagos),
        "minuto": calcular_total_recaudado(
            filter(lambda pago: pago["modalidad"] == "minuto", pagos)
        ),
        "diaria": calcular_total_recaudado(
            filter(lambda pago: pago["modalidad"] == "diaria", pagos)
        ),
        "mensual": calcular_total_recaudado(
            filter(lambda pago: pago["modalidad"] == "mensual", pagos)
        ),
    }


def generar_reporte_recaudacion(
    pagos: list[dict],
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    modalidad: str | None = None,
) -> dict[str, int]:
    """Filtra pagos opcionalmente y devuelve el total y su distribución."""
    pagos_filtrados = filtrar_pagos(pagos, fecha_desde, fecha_hasta, modalidad)
    return calcular_totales_por_modalidad(pagos_filtrados)
