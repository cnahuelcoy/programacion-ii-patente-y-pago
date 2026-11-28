from sqlalchemy import func, select

from persistencia.conexion import sesion_local
from persistencia.modelos import Estadia, Pago, Suscripcion, Vehiculo
from persistencia.validaciones import validar_fecha
from persistencia.vehiculos import _buscar_vehiculo_por_patente, _limpiar_texto


def listar_vehiculos_presentes():
    consulta = (
        select(
            Estadia.id.label("estadia_id"),
            Vehiculo.id.label("vehiculo_id"),
            Vehiculo.patente,
            Vehiculo.nombre_responsable,
            Estadia.fecha_ingreso,
            Estadia.modalidad,
            Estadia.suscripcion_id,
        )
        .join(Vehiculo, Estadia.vehiculo_id == Vehiculo.id)
        .where(Estadia.fecha_salida.is_(None))
        .order_by(Estadia.fecha_ingreso, Estadia.id)
    )
    with sesion_local() as sesion:
        return [dict(fila) for fila in sesion.execute(consulta).mappings()]


def _validar_filtros(patente, fecha_desde, fecha_hasta, modalidad):
    patente = _limpiar_texto(patente, "La patente").upper()
    modalidad = _limpiar_texto(modalidad, "La modalidad").lower()
    if modalidad and modalidad not in ("minuto", "diaria", "mensual"):
        raise ValueError("La modalidad debe ser minuto, diaria o mensual.")
    if fecha_desde is not None:
        validar_fecha(fecha_desde, "La fecha desde")
    if fecha_hasta is not None:
        validar_fecha(fecha_hasta, "La fecha hasta")
    if fecha_desde is not None and fecha_hasta is not None and fecha_hasta <= fecha_desde:
        raise ValueError("La fecha hasta debe ser posterior a la fecha desde.")
    return patente, modalidad


def _filtrar_periodo(consulta, columna_fecha, columna_modalidad, desde, hasta, modalidad):
    if desde is not None:
        consulta = consulta.where(columna_fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(columna_fecha < hasta)
    if modalidad:
        consulta = consulta.where(columna_modalidad == modalidad)
    return consulta


def _filtrar_patente(sesion, consulta, patente, columna_vehiculo):
    if not patente:
        return consulta
    vehiculo = _buscar_vehiculo_por_patente(sesion, patente)
    if vehiculo is None:
        return None
    return consulta.where(columna_vehiculo == vehiculo.id)


def listar_historial_estadias(patente=None, fecha_desde=None, fecha_hasta=None, modalidad=None):
    patente, modalidad = _validar_filtros(patente, fecha_desde, fecha_hasta, modalidad)
    consulta = (
        select(
            Estadia.id.label("estadia_id"),
            Vehiculo.id.label("vehiculo_id"),
            Vehiculo.patente,
            Vehiculo.nombre_responsable,
            Estadia.fecha_ingreso,
            Estadia.fecha_salida,
            Estadia.modalidad,
            Estadia.suscripcion_id,
            Pago.id.label("pago_id"),
            Pago.monto,
            Pago.fecha_pago,
        )
        .join(Vehiculo, Estadia.vehiculo_id == Vehiculo.id)
        .outerjoin(Pago, Pago.estadia_id == Estadia.id)
        .order_by(Estadia.fecha_ingreso.desc(), Estadia.id.desc())
    )
    consulta = _filtrar_periodo(
        consulta, Estadia.fecha_ingreso, Estadia.modalidad, fecha_desde, fecha_hasta, modalidad
    )
    with sesion_local() as sesion:
        consulta = _filtrar_patente(sesion, consulta, patente, Estadia.vehiculo_id)
        if consulta is None:
            return []
        resultados = []
        for fila in sesion.execute(consulta).mappings():
            registro = dict(fila)
            registro["duracion_segundos"] = None
            if registro["fecha_salida"] is not None:
                registro["duracion_segundos"] = (
                    registro["fecha_salida"] - registro["fecha_ingreso"]
                ).total_seconds()
            if registro["modalidad"] == "mensual" and registro["pago_id"] is None:
                registro["monto"] = 0
            resultados.append(registro)
        return resultados


def listar_pagos(patente=None, fecha_desde=None, fecha_hasta=None, modalidad=None):
    patente, modalidad = _validar_filtros(patente, fecha_desde, fecha_hasta, modalidad)
    vehiculo_origen = func.coalesce(Estadia.vehiculo_id, Suscripcion.vehiculo_id)
    consulta = (
        select(
            Pago.id.label("pago_id"),
            Vehiculo.id.label("vehiculo_id"),
            Vehiculo.patente,
            Vehiculo.nombre_responsable,
            Pago.fecha_pago,
            Pago.modalidad,
            Pago.monto,
            Pago.estadia_id,
            Pago.suscripcion_id,
        )
        .select_from(Pago)
        .outerjoin(Estadia, Pago.estadia_id == Estadia.id)
        .outerjoin(Suscripcion, Pago.suscripcion_id == Suscripcion.id)
        .join(Vehiculo, Vehiculo.id == vehiculo_origen)
        .order_by(Pago.fecha_pago.desc(), Pago.id.desc())
    )
    consulta = _filtrar_periodo(
        consulta, Pago.fecha_pago, Pago.modalidad, fecha_desde, fecha_hasta, modalidad
    )
    with sesion_local() as sesion:
        consulta = _filtrar_patente(sesion, consulta, patente, vehiculo_origen)
        if consulta is None:
            return []
        return [dict(fila) for fila in sesion.execute(consulta).mappings()]
