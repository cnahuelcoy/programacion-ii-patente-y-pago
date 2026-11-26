import argparse
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from dominio.cobro_diario import CobroDiario
from dominio.cobro_mensual import CobroMensual
from dominio.cobro_por_minuto import CobroPorMinuto
from dominio.suscripciones import calcular_termino_suscripcion, suscripcion_vigente
from persistencia.conexion import Base, RUTA_BASE_DATOS, activar_claves_foraneas
from persistencia.modelos import Estadia, Pago, Suscripcion, Vehiculo


def _cargar_ejemplos(sesion):
    referencia = datetime(2026, 11, 25, 10)
    modalidades = {
        "minuto": CobroPorMinuto(50),
        "diaria": CobroDiario(5000),
        "mensual": CobroMensual(30000),
    }
    vehiculos = []
    for numero in range(1, 7):
        vehiculo = Vehiculo(
            patente=f"DEMO{numero:02d}",
            nombre_responsable=f"Persona de ejemplo {numero}",
            telefono=f"+569000000{numero:02d}",
            correo=f"demo{numero}@example.com",
        )
        sesion.add(vehiculo)
        vehiculos.append(vehiculo)

    def agregar_estadia(vehiculo, ingreso, salida, modalidad, suscripcion=None):
        estadia = Estadia(
            vehiculo=vehiculo,
            fecha_ingreso=ingreso,
            fecha_salida=salida,
            modalidad=modalidad,
            suscripcion=suscripcion,
        )
        sesion.add(estadia)
        if salida is not None:
            monto = modalidades[modalidad].calcular_importe(ingreso, salida)
            if monto > 0:
                estadia.pago = Pago(monto=monto, fecha_pago=salida, modalidad=modalidad)

    def agregar_suscripcion(vehiculo, inicio):
        suscripcion = Suscripcion(
            vehiculo=vehiculo,
            fecha_inicio=inicio,
            fecha_termino=calcular_termino_suscripcion(inicio),
            pago=Pago(
                monto=modalidades["mensual"].calcular_importe_contratacion(),
                fecha_pago=inicio,
                modalidad="mensual",
            ),
        )
        sesion.add(suscripcion)
        return suscripcion

    agregar_estadia(vehiculos[0], referencia, referencia + timedelta(minutes=1, seconds=10), "minuto")
    agregar_estadia(vehiculos[1], referencia - timedelta(days=1), referencia, "diaria")
    agregar_estadia(vehiculos[2], referencia - timedelta(days=1, minutes=1), referencia, "diaria")

    vigente = agregar_suscripcion(vehiculos[3], referencia - timedelta(days=1))
    agregar_estadia(vehiculos[3], referencia - timedelta(hours=4), referencia - timedelta(hours=3), "mensual", vigente)
    agregar_estadia(vehiculos[3], referencia - timedelta(hours=2), referencia - timedelta(hours=1), "mensual", vigente)
    agregar_estadia(vehiculos[3], referencia, None, "mensual", vigente)

    vencida = agregar_suscripcion(vehiculos[4], referencia - timedelta(days=31))
    modalidad = "mensual" if suscripcion_vigente(vencida.fecha_inicio, vencida.fecha_termino, referencia) else "minuto"
    agregar_estadia(vehiculos[4], referencia, None, modalidad)
    agregar_estadia(vehiculos[5], referencia, None, "diaria")


def generar_datos_ejemplo(ruta_base=None):
    ruta = Path(ruta_base if ruta_base is not None else RUTA_BASE_DATOS).resolve()
    try:
        with ruta.open("xb"):
            pass
    except FileExistsError as error:
        raise ValueError("La base ya existe. Usa una copia nueva del proyecto o indica otro archivo con --base.") from error

    motor = None
    try:
        motor = create_engine(f"sqlite:///{ruta.as_posix()}")
        event.listen(motor, "connect", activar_claves_foraneas)
        Base.metadata.create_all(bind=motor)
        sesiones = sessionmaker(bind=motor)
        with sesiones() as sesion, sesion.begin():
            _cargar_ejemplos(sesion)
            sesion.flush()
            cantidades = {
                "vehiculos": sesion.scalar(select(func.count()).select_from(Vehiculo)),
                "estadias": sesion.scalar(select(func.count()).select_from(Estadia)),
                "suscripciones": sesion.scalar(select(func.count()).select_from(Suscripcion)),
                "pagos": sesion.scalar(select(func.count()).select_from(Pago)),
            }
        return {"ruta": str(ruta), **cantidades}
    except Exception:
        if motor is not None:
            motor.dispose()
        ruta.unlink()
        raise
    finally:
        if motor is not None:
            motor.dispose()


def main():
    parser = argparse.ArgumentParser(description="Crea una base nueva con datos de ejemplo.")
    parser.add_argument("--base", type=Path, default=RUTA_BASE_DATOS)
    argumentos = parser.parse_args()
    try:
        resultado = generar_datos_ejemplo(argumentos.base)
    except (ValueError, OSError) as error:
        parser.exit(1, f"No se generaron los ejemplos: {error}\n")
    print(f"Base creada: {resultado['ruta']}")
    print(f"Vehículos: {resultado['vehiculos']}; estadías: {resultado['estadias']}; suscripciones: {resultado['suscripciones']}; pagos: {resultado['pagos']}.")
    print("Fechas de ejemplo: 25/11/2026. Tarifas de prueba: $50/minuto, $5.000/día y $30.000/mensual.")


if __name__ == "__main__":
    main()
