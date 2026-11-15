from pathlib import Path
from sqlalchemy import create_engine, event
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
    Base.metadata.create_all(bind=motor)