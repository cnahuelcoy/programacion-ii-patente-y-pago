from datetime import datetime, timedelta


def _validar_datetime(fecha: datetime, nombre: str) -> None:
    if not isinstance(fecha, datetime):
        raise TypeError(f"{nombre} debe ser un objeto datetime.")
    if fecha.utcoffset() is not None:
        raise ValueError(f"{nombre} debe ser un datetime sin zona horaria.")


def _validar_periodo(inicio: datetime, termino: datetime) -> None:
    _validar_datetime(inicio, "El inicio")
    _validar_datetime(termino, "El término")
    if termino <= inicio:
        raise ValueError("El término debe ser posterior al inicio.")


def calcular_termino_suscripcion(inicio: datetime) -> datetime:
    """Calcula el término, 30 días consecutivos después del inicio."""
    _validar_datetime(inicio, "El inicio")
    return inicio + timedelta(days=30)


def suscripcion_vigente(
    inicio: datetime, termino: datetime, fecha: datetime
) -> bool:
    """Comprueba vigencia incluyendo el inicio y excluyendo el término."""
    _validar_periodo(inicio, termino)
    _validar_datetime(fecha, "La fecha de consulta")
    return inicio <= fecha < termino


def hay_superposicion(
    inicio_a: datetime,
    termino_a: datetime,
    inicio_b: datetime,
    termino_b: datetime,
) -> bool:
    """Comprueba si dos períodos [inicio, término) comparten tiempo."""
    _validar_periodo(inicio_a, termino_a)
    _validar_periodo(inicio_b, termino_b)
    return inicio_a < termino_b and inicio_b < termino_a


def estadia_cubierta(
    inicio_suscripcion: datetime,
    termino_suscripcion: datetime,
    ingreso: datetime,
    salida: datetime,
) -> bool:
    """Determina cobertura al ingresar, aunque la suscripción venza al salir."""
    _validar_datetime(ingreso, "El ingreso")
    _validar_datetime(salida, "La salida")
    if salida < ingreso:
        raise ValueError("La salida debe ser igual o posterior al ingreso.")
    return suscripcion_vigente(inicio_suscripcion, termino_suscripcion, ingreso)
