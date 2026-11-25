from sqlalchemy import select

from persistencia.conexion import sesion_local
from persistencia.modelos import Estadia, Vehiculo


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
