from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

RUTA_BASE_DATOS = Path(__file__).resolve().parent.parent / "estacionamiento.db"

motor = create_engine(f"sqlite:///{RUTA_BASE_DATOS.as_posix()}")

@event.listens_for(motor, "connect")
def activar_claves_foraneas(conexion, _registro):
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

class Base(DeclarativeBase):
    pass

sesion_local = sessionmaker(bind=motor)

def crear_tablas():
    from persistencia import modelos

    try:
        Base.metadata.create_all(bind=motor)
        for modelo in (modelos.Estadia, modelos.Suscripcion):
            for indice in modelo.__table__.indexes:
                indice.create(bind=motor, checkfirst=True)
    except IntegrityError as error:
        if "UNIQUE constraint failed: estadias.vehiculo_id" in str(error.orig):
            raise ValueError(
                "Hay vehículos con más de una estadía activa. "
                "Corrige esas estadías para completar la actualización de la base de datos."
            ) from error
        raise
