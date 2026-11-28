"""Funciones puras de formato para la interfaz: fechas y montos.

Son funciones puras: su resultado depende solo de sus argumentos y no tocan
la base de datos ni los widgets. Por eso son fáciles de probar.
"""

from datetime import datetime

FORMATO_CON_SEGUNDOS = "%d/%m/%Y %H:%M:%S"
FORMATO_SIN_SEGUNDOS = "%d/%m/%Y %H:%M"

MENSAJE_FECHA_INVALIDA = (
    "La fecha y hora no es válida. Usa el formato dd/mm/aaaa HH:MM "
    "o dd/mm/aaaa HH:MM:SS, por ejemplo 15/11/2026 13:30:00."
)


def parsear_fecha(texto):
    """Convierte un texto en un datetime SIN zona horaria.

    Acepta "dd/mm/aaaa HH:MM" y "dd/mm/aaaa HH:MM:SS".
    Lanza ValueError con un mensaje comprensible si el texto no es válido.
    """
    texto = texto.strip()
    if not texto:
        raise ValueError("Debes ingresar la fecha y hora.")

    for formato in (FORMATO_CON_SEGUNDOS, FORMATO_SIN_SEGUNDOS):
        try:
            # strptime devuelve un datetime "naive" (sin zona horaria).
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    raise ValueError(MENSAJE_FECHA_INVALIDA)


def formatear_fecha(fecha):
    """Convierte un datetime en texto "dd/mm/aaaa HH:MM:SS"."""
    return fecha.strftime(FORMATO_CON_SEGUNDOS)


def formatear_pesos(monto):
    """Da formato de pesos chilenos: 5000 -> "$5.000"."""
    return "$" + f"{monto:,}".replace(",", ".")
