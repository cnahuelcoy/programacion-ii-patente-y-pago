from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from persistencia.conexion import sesion_local
from persistencia.modelos import Vehiculo


def _limpiar_texto(valor, campo):
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ValueError(f"{campo} debe ser texto.")
    return valor.strip()


def _normalizar_patente(patente):
    patente = _limpiar_texto(patente, "La patente").upper()
    if not patente:
        raise ValueError("La patente no puede estar vacía.")
    return patente


def _buscar_vehiculo_por_patente(sesion, patente):
    consulta = select(Vehiculo).order_by(Vehiculo.id)
    coincidencias = [
        vehiculo
        for vehiculo in sesion.scalars(consulta)
        if vehiculo.patente.strip().upper() == patente
    ]
    if len(coincidencias) > 1:
        raise ValueError(
            f"La patente {patente} identifica varios vehículos en registros anteriores. "
            "Revisa esos registros antes de continuar."
        )
    return coincidencias[0] if coincidencias else None


def _vehiculo_a_diccionario(vehiculo):
    return {
        "id": vehiculo.id,
        "patente": vehiculo.patente,
        "nombre_responsable": vehiculo.nombre_responsable,
        "telefono": vehiculo.telefono or "",
        "correo": vehiculo.correo or "",
    }


def registrar_vehiculo(patente, nombre_responsable, telefono, correo):
    patente = _normalizar_patente(patente)
    nombre_responsable = _limpiar_texto(nombre_responsable, "El nombre del responsable")
    telefono = _limpiar_texto(telefono, "El teléfono")
    correo = _limpiar_texto(correo, "El correo")

    if not nombre_responsable:
        raise ValueError("El nombre del responsable no puede estar vacío.")
    if not telefono and not correo:
        raise ValueError("Debes indicar al menos un teléfono o un correo de contacto.")

    sesion = sesion_local()
    try:
        if _buscar_vehiculo_por_patente(sesion, patente) is not None:
            raise ValueError(f"Ya existe un vehículo con la patente {patente}.")

        vehiculo = Vehiculo(
            patente=patente,
            nombre_responsable=nombre_responsable,
            telefono=telefono or None,
            correo=correo or None,
        )
        sesion.add(vehiculo)
        sesion.flush()
        resultado = _vehiculo_a_diccionario(vehiculo)
        sesion.commit()
        return resultado
    except IntegrityError as error:
        sesion.rollback()
        if "UNIQUE constraint failed: vehiculos.patente" in str(error.orig):
            raise ValueError(f"Ya existe un vehículo con la patente {patente}.") from error
        raise
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()


def listar_vehiculos():
    with sesion_local() as sesion:
        consulta = select(Vehiculo).order_by(Vehiculo.id)
        vehiculos = sesion.scalars(consulta).all()

        return [_vehiculo_a_diccionario(vehiculo) for vehiculo in vehiculos]
