from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from persistencia.conexion import sesion_local
from persistencia.modelos import Estadia, Pago
from persistencia.validaciones import obtener_fecha_pago, validar_fecha, validar_monto
from persistencia.vehiculos import _buscar_vehiculo_por_patente, _normalizar_patente


def registrar_salida(patente, fecha_salida, monto, fecha_pago=None):
    patente = _normalizar_patente(patente)
    validar_fecha(fecha_salida, "La fecha de salida")
    validar_monto(monto, permitir_cero=True)
    fecha_registro = obtener_fecha_pago(fecha_pago)

    sesion = sesion_local()
    try:
        sesion.connection().exec_driver_sql("BEGIN IMMEDIATE")
        vehiculo = _buscar_vehiculo_por_patente(sesion, patente)
        if vehiculo is None:
            raise ValueError(f"No existe un vehículo con la patente {patente}.")

        consulta = select(Estadia).where(
            Estadia.vehiculo_id == vehiculo.id,
            Estadia.fecha_salida.is_(None),
        )
        estadias = sesion.scalars(consulta.limit(2)).all()
        if not estadias:
            raise ValueError(f"El vehículo {patente} no tiene una estadía activa.")
        if len(estadias) > 1:
            raise ValueError(f"El vehículo {patente} tiene más de una estadía activa.")

        estadia = estadias[0]
        if fecha_salida < estadia.fecha_ingreso:
            raise ValueError("La salida no puede ser anterior al ingreso.")
        if estadia.modalidad not in ("minuto", "diaria", "mensual"):
            raise ValueError("La modalidad de la estadía no es válida.")
        if estadia.modalidad == "mensual":
            if estadia.suscripcion_id is None:
                raise ValueError("La estadía mensual no tiene una suscripción asociada.")
            if monto != 0:
                raise ValueError("Una estadía cubierta por suscripción debe tener monto cero.")
        elif monto == 0:
            raise ValueError("Una estadía sin cobertura mensual debe tener un monto positivo.")

        consulta_pago = select(Pago.id).where(Pago.estadia_id == estadia.id)
        if sesion.scalar(consulta_pago.limit(1)) is not None:
            raise ValueError("La estadía ya tiene un pago registrado.")

        estadia.fecha_salida = fecha_salida
        pago = None
        if monto > 0:
            pago = Pago(
                estadia_id=estadia.id,
                monto=monto,
                fecha_pago=fecha_registro,
                modalidad=estadia.modalidad,
            )
            sesion.add(pago)
        sesion.flush()
        resultado = {
            "id": estadia.id,
            "vehiculo_id": vehiculo.id,
            "patente": vehiculo.patente,
            "fecha_ingreso": estadia.fecha_ingreso,
            "fecha_salida": fecha_salida,
            "modalidad": estadia.modalidad,
            "suscripcion_id": estadia.suscripcion_id,
            "monto": monto,
            "pago_id": pago.id if pago is not None else None,
            "fecha_pago": fecha_registro if pago is not None else None,
        }
        sesion.commit()
        return resultado
    except IntegrityError as error:
        sesion.rollback()
        raise ValueError("No se pudo guardar la salida y su pago. Revisa los datos.") from error
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
