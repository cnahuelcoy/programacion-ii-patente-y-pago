"""Funciones de ejemplo en memoria, SOLO para probar la interfaz.

Tienen las mismas firmas que las funciones reales que entregará la capa de
persistencia y de negocio, así que reemplazarlas es cambiar los imports en
main.py. Cuando se integre todo, este archivo se puede borrar.

IMPORTANTE: las tarifas y los cálculos de cobro de este archivo son DATOS DE
PRUEBA. Las tarifas y fórmulas oficiales las define el equipo en el dominio.
"""

import math
from datetime import datetime, timedelta

from interfaz.formato import formatear_fecha

# --- DATOS DE PRUEBA (no son las tarifas reales del proyecto) ---
TARIFA_MINUTO_DEMO = 50        # pesos por minuto
TARIFA_DIARIA_DEMO = 5000      # pesos por bloque de 24 horas
PATENTES_MENSUALES_DEMO = {"MENS01"}  # simulan una suscripción vigente
TARIFA_MENSUAL_DEMO = 30000    # pesos por suscripción de 30 días

DIAS_SUSCRIPCION = 30

MODALIDADES_VALIDAS = ("minuto", "diaria")

_vehiculos = []
_siguiente_id = 1
_estadias = []
_suscripciones = []
_siguiente_estadia_id = 1
_siguiente_suscripcion_id = 1


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


def _buscar_vehiculo(patente):
    for vehiculo in _vehiculos:
        if vehiculo["patente"] == patente:
            return vehiculo
    return None


def _buscar_suscripcion_vigente(patente, fecha):
    for suscripcion in _suscripciones:
        if suscripcion["patente"] == patente and suscripcion["fecha_inicio"] <= fecha < suscripcion["fecha_termino"]:
            return suscripcion
    return None


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
    global _siguiente_estadia_id

    vehiculo = _buscar_vehiculo(patente)
    if vehiculo is None:
        raise ValueError(
            f"El vehículo {patente} no está registrado. Regístralo primero en la pestaña Vehículos."
        )
    if _buscar_estadia_activa(patente) is not None:
        raise ValueError(f"El vehículo {patente} ya tiene una estadía activa.")

    suscripcion = _buscar_suscripcion_vigente(patente, fecha_ingreso)
    if suscripcion is not None:
        modalidad = "mensual"

    # DATO DE PRUEBA: la cobertura mensual real depende de las suscripciones.
    if patente in PATENTES_MENSUALES_DEMO:
        modalidad = "mensual"

    _estadias.append(
        {
            "estadia_id": _siguiente_estadia_id,
            "vehiculo_id": vehiculo["id"],
            "patente": patente,
            "fecha_ingreso": fecha_ingreso,
            "fecha_salida": None,
            "modalidad": modalidad,
            "suscripcion_id": suscripcion["id"] if suscripcion is not None else None,
        }
    )
    _siguiente_estadia_id += 1
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


def contratar_suscripcion(patente, fecha_inicio):
    global _siguiente_suscripcion_id

    patente = patente.strip().upper()
    if not patente:
        raise ValueError("La patente no puede estar vacía.")
    if not isinstance(fecha_inicio, datetime):
        raise ValueError("La fecha de inicio no es válida.")
    if _buscar_vehiculo(patente) is None:
        raise ValueError(
            f"El vehículo {patente} no está registrado. Regístralo primero en la pestaña Vehículos."
        )

    fecha_termino = fecha_inicio + timedelta(days=DIAS_SUSCRIPCION)
    for existente in _suscripciones:
        if (
            existente["patente"] == patente
            and fecha_inicio < existente["fecha_termino"]
            and fecha_termino > existente["fecha_inicio"]
        ):
            raise ValueError(
                f"El vehículo {patente} ya tiene una suscripción entre "
                f"{formatear_fecha(existente['fecha_inicio'])} y {formatear_fecha(existente['fecha_termino'])}."
            )

    fecha_pago = datetime.now().replace(microsecond=0)
    _suscripciones.append(
        {
            "id": _siguiente_suscripcion_id,
            "patente": patente,
            "fecha_inicio": fecha_inicio,
            "fecha_termino": fecha_termino,
        }
    )
    _siguiente_suscripcion_id += 1
    return {
        "patente": patente,
        "fecha_inicio": fecha_inicio,
        "fecha_termino": fecha_termino,
        "monto": TARIFA_MENSUAL_DEMO,
        "fecha_pago": fecha_pago,
    }


def listar_vehiculos_presentes():
    presentes = [e for e in _estadias if e["fecha_salida"] is None]
    return [
        {
            "estadia_id": e["estadia_id"],
            "vehiculo_id": e["vehiculo_id"],
            "patente": e["patente"],
            "nombre_responsable": _buscar_vehiculo(e["patente"])["nombre_responsable"],
            "fecha_ingreso": e["fecha_ingreso"],
            "modalidad": e["modalidad"],
            "suscripcion_id": e["suscripcion_id"],
        }
        for e in sorted(presentes, key=lambda e: e["fecha_ingreso"])
    ]


def reiniciar_demo():
    """Vacía los datos de ejemplo (útil para las pruebas)."""
    global _siguiente_id, _siguiente_estadia_id, _siguiente_suscripcion_id
    _vehiculos.clear()
    _estadias.clear()
    _suscripciones.clear()
    _siguiente_id = 1
    _siguiente_estadia_id = 1
    _siguiente_suscripcion_id = 1
