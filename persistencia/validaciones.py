from datetime import datetime


def validar_fecha(fecha, nombre):
    if not isinstance(fecha, datetime) or fecha.tzinfo is not None:
        raise ValueError(f"{nombre} debe ser un datetime sin zona horaria.")


def validar_monto(monto, permitir_cero=False):
    if isinstance(monto, bool) or not isinstance(monto, int):
        raise ValueError("El monto debe ser un entero en pesos chilenos.")
    if monto < 0:
        raise ValueError("El monto no puede ser negativo.")
    if monto == 0 and not permitir_cero:
        raise ValueError("El monto debe ser positivo.")
    if monto > 2**63 - 1:
        raise ValueError("El monto es demasiado grande.")


def obtener_fecha_pago(fecha_pago):
    if fecha_pago is None:
        return datetime.now()
    validar_fecha(fecha_pago, "La fecha del pago")
    return fecha_pago
