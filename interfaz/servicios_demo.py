"""Funciones de ejemplo en memoria, SOLO para probar la interfaz.

Tienen las mismas firmas que las funciones reales que entregará la capa de
persistencia, así que reemplazarlas es cambiar dos líneas en main.py.
Cuando se integre todo, este archivo se puede borrar.
"""

_vehiculos = []
_siguiente_id = 1


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


def reiniciar_demo():
    """Vacía los datos de ejemplo (útil para las pruebas)."""
    global _siguiente_id
    _vehiculos.clear()
    _siguiente_id = 1
