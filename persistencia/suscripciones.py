from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from persistencia.conexion import sesion_local
from persistencia.modelos import Pago, Suscripcion
from persistencia.validaciones import obtener_fecha_pago, validar_fecha, validar_monto
from persistencia.vehiculos import _buscar_vehiculo_por_patente, _normalizar_patente


def registrar_suscripcion(patente, fecha_inicio, fecha_termino, monto, fecha_pago=None):
    patente = _normalizar_patente(patente)
    validar_fecha(fecha_inicio, "La fecha de inicio")
    validar_fecha(fecha_termino, "La fecha de término")
    if fecha_termino - fecha_inicio != timedelta(days=30):
        raise ValueError("La suscripción debe cubrir exactamente 30 días consecutivos.")
    validar_monto(monto)
    fecha_registro = obtener_fecha_pago(fecha_pago)

    sesion = sesion_local()
    try:
        sesion.connection().exec_driver_sql("BEGIN IMMEDIATE")
        vehiculo = _buscar_vehiculo_por_patente(sesion, patente)
        if vehiculo is None:
            raise ValueError(f"No existe un vehículo con la patente {patente}.")

        consulta = select(Suscripcion.id).where(
            Suscripcion.vehiculo_id == vehiculo.id,
            Suscripcion.fecha_inicio < fecha_termino,
            Suscripcion.fecha_termino > fecha_inicio,
        )
        if sesion.scalar(consulta.limit(1)) is not None:
            raise ValueError(f"La suscripción se superpone con otra del vehículo {patente}.")

        pago = Pago(monto=monto, fecha_pago=fecha_registro, modalidad="mensual")
        suscripcion = Suscripcion(
            vehiculo_id=vehiculo.id,
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            pago=pago,
        )
        sesion.add(suscripcion)
        sesion.flush()
        resultado = {
            "id": suscripcion.id,
            "vehiculo_id": vehiculo.id,
            "patente": vehiculo.patente,
            "fecha_inicio": fecha_inicio,
            "fecha_termino": fecha_termino,
            "monto": monto,
            "pago_id": pago.id,
            "fecha_pago": fecha_registro,
        }
        sesion.commit()
        return resultado
    except IntegrityError as error:
        sesion.rollback()
        raise ValueError("No se pudo guardar la suscripción y su pago. Revisa los datos.") from error
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
