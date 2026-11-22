"""Funciones de ejemplo en memoria, SOLO para probar la interfaz.

Tienen las mismas firmas que las funciones reales que entregará la capa de
persistencia y de negocio, así que reemplazarlas es cambiar los imports en
main.py. Cuando se integre todo, este archivo se puede borrar.

IMPORTANTE: las tarifas y los cálculos de cobro de este archivo son DATOS DE
PRUEBA. Las tarifas y fórmulas oficiales las define el equipo en el dominio.
"""

import math
from datetime import datetime

# --- DATOS DE PRUEBA (no son las tarifas reales del proyecto) ---
TARIFA_MINUTO_DEMO = 50        # pesos por minuto
TARIFA_DIARIA_DEMO = 5000      # pesos por bloque de 24 horas
PATENTES_MENSUALES_DEMO = {"MENS01"}  # simulan una suscripción vigente

MODALIDADES_VALIDAS = ("minuto", "diaria")

_vehiculos = []
_siguiente_id = 1
_estadias = []


def registrar_vehiculo(patente, nombre_responsable, telefono, correo):
    """Registra un vehículo y lo devuelve como diccionario.

    Lanza ValueError con un mensaje claro si los datos no son válidos.
    """
    global _siguiente_id

    patente = patente.strip().upper()
    if not patente:
        raise ValueError("La patente no puede estar vacía.")
    if any(v["patente"] == patente for v in _vehiculos):
        raise ValueError(f"Ya existe un vehículo con la patente {patente}.")

    vehiculo = {
        "id": _siguiente_id,
        "patente": patente,
        "nombre_responsable": nombre_responsable.strip(),
        "telefono": telefono.strip(),
        "correo": correo.strip(),
    }
    _vehiculos.append(vehiculo)
    _siguiente_id += 1
    return dict(vehiculo)


def listar_vehiculos():
    """Devuelve la lista de vehículos como diccionarios."""
    return [dict(v) for v in _vehiculos]


def _buscar_estadia_activa(patente):
    for estadia in _estadias:
        if estadia["patente"] == patente and estadia["fecha_salida"] is None:
            return estadia
    return None


def registrar_ingreso(patente, fecha_ingreso, modalidad):
    """Registra el ingreso de un vehículo y devuelve un diccionario.

    Devuelve patente, fecha_ingreso y modalidad. La modalidad devuelta es
    "mensual" si el vehículo tiene cobertura (en la demo: PATENTES_MENSUALES_DEMO).
    Lanza ValueError con un mensaje claro si el ingreso no es válido.
    """
    patente = patente.strip().upper()
    if not patente:
        raise ValueError("La patente no puede estar vacía.")
    if not isinstance(fecha_ingreso, datetime):
        raise ValueError("La fecha de ingreso no es válida.")
    if modalidad not in MODALIDADES_VALIDAS:
        raise ValueError("La modalidad debe ser \"minuto\" o \"diaria\".")
    if not any(v["patente"] == patente for v in _vehiculos):
        raise ValueError(
            f"El vehículo {patente} no está registrado. Regístralo primero en la pestaña Vehículos."
        )
    if _buscar_estadia_activa(patente) is not None:
        raise ValueError(f"El vehículo {patente} ya tiene una estadía activa.")

    # DATO DE PRUEBA: la cobertura mensual real depende de las suscripciones.
    if patente in PATENTES_MENSUALES_DEMO:
        modalidad = "mensual"

    _estadias.append(
        {"patente": patente, "fecha_ingreso": fecha_ingreso, "fecha_salida": None, "modalidad": modalidad}
    )
    return {"patente": patente, "fecha_ingreso": fecha_ingreso, "modalidad": modalidad}


def _calcular_monto_demo(modalidad, fecha_ingreso, fecha_salida):
    """CÁLCULO DE PRUEBA con tarifas de prueba (el real vive en el dominio)."""
    segundos = (fecha_salida - fecha_ingreso).total_seconds()
    if modalidad == "minuto":
        return max(1, math.ceil(segundos / 60)) * TARIFA_MINUTO_DEMO
    if modalidad == "diaria":
        return max(1, math.ceil(segundos / 86400)) * TARIFA_DIARIA_DEMO
    return 0  # mensual: estadía cubierta, cobro adicional de $0


def registrar_salida(patente, fecha_salida):
    """Registra la salida de un vehículo y devuelve un diccionario.

    Devuelve patente, fecha_ingreso, fecha_salida, modalidad y monto (en
    pesos). Lanza ValueError con un mensaje claro si la salida no es válida.
    """
    patente = patente.strip().upper()
    if not patente:
        raise ValueError("La patente no puede estar vacía.")
    if not isinstance(fecha_salida, datetime):
        raise ValueError("La fecha de salida no es válida.")

    estadia = _buscar_estadia_activa(patente)
    if estadia is None:
        raise ValueError(f"El vehículo {patente} no tiene una estadía activa.")
    if fecha_salida < estadia["fecha_ingreso"]:
        raise ValueError("La fecha de salida no puede ser anterior a la fecha de ingreso.")

    monto = _calcular_monto_demo(estadia["modalidad"], estadia["fecha_ingreso"], fecha_salida)
    estadia["fecha_salida"] = fecha_salida
    return {
        "patente": patente,
        "fecha_ingreso": estadia["fecha_ingreso"],
        "fecha_salida": fecha_salida,
        "modalidad": estadia["modalidad"],
        "monto": monto,
    }


def reiniciar_demo():
    """Vacía los datos de ejemplo (útil para las pruebas)."""
    global _siguiente_id
    _vehiculos.clear()
    _estadias.clear()
    _siguiente_id = 1
