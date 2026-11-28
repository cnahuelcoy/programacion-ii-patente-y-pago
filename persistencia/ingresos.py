from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from persistencia.conexion import sesion_local
from persistencia.modelos import Estadia, Suscripcion
from persistencia.vehiculos import _buscar_vehiculo_por_patente, _normalizar_patente


def registrar_ingreso(patente, fecha_ingreso, modalidad):
    patente = _normalizar_patente(patente)
    if not isinstance(fecha_ingreso, datetime) or fecha_ingreso.tzinfo is not None:
        raise ValueError("La fecha de ingreso debe ser un datetime sin zona horaria.")
    if modalidad not in ("minuto", "diaria"):
        raise ValueError("La modalidad solicitada debe ser minuto o diaria.")

    sesion = sesion_local()
    try:
        vehiculo = _buscar_vehiculo_por_patente(sesion, patente)
        if vehiculo is None:
            raise ValueError(f"No existe un vehículo con la patente {patente}.")

        consulta_activa = select(Estadia.id).where(
            Estadia.vehiculo_id == vehiculo.id,
            Estadia.fecha_salida.is_(None),
        )
        if sesion.scalar(consulta_activa) is not None:
            raise ValueError(f"El vehículo {patente} ya tiene una estadía activa.")

        consulta_suscripciones = select(Suscripcion).where(
            Suscripcion.vehiculo_id == vehiculo.id,
            Suscripcion.fecha_inicio <= fecha_ingreso,
            Suscripcion.fecha_termino > fecha_ingreso,
        )
        suscripciones = sesion.scalars(consulta_suscripciones.limit(2)).all()
        if len(suscripciones) > 1:
            raise ValueError(f"El vehículo {patente} tiene suscripciones superpuestas.")

        estadia = Estadia(
            vehiculo=vehiculo,
            fecha_ingreso=fecha_ingreso,
            modalidad=modalidad,
        )
        if suscripciones:
            estadia.modalidad = "mensual"
            estadia.suscripcion = suscripciones[0]

        sesion.add(estadia)
        sesion.flush()
        resultado = {
            "id": estadia.id,
            "vehiculo_id": vehiculo.id,
            "patente": vehiculo.patente,
            "fecha_ingreso": estadia.fecha_ingreso,
            "fecha_salida": estadia.fecha_salida,
            "modalidad": estadia.modalidad,
            "suscripcion_id": estadia.suscripcion_id,
        }
        sesion.commit()
        return resultado
    except IntegrityError as error:
        sesion.rollback()
        if "UNIQUE constraint failed: estadias.vehiculo_id" in str(error.orig):
            raise ValueError(f"El vehículo {patente} ya tiene una estadía activa.") from error
        raise
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
