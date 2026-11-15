from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from persistencia.conexion import Base

from sqlalchemy.orm import relationship

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id = Column(Integer, primary_key=True)
    patente = Column(String, unique=True, nullable=False)
    nombre_responsable = Column(String, nullable=False)
    telefono = Column(String)
    correo = Column(String)
    estadias = relationship("Estadia", back_populates="vehiculo")
    suscripciones = relationship("Suscripcion", back_populates="vehiculo")

class Estadia(Base):
    __tablename__ = "estadias"
    id = Column(Integer, primary_key=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    fecha_ingreso = Column(DateTime, nullable=False)
    fecha_salida = Column(DateTime)
    modalidad = Column(String, nullable=False)
    suscripcion_id = Column(Integer, ForeignKey("suscripciones.id"))
    vehiculo = relationship("Vehiculo", back_populates="estadias")
    suscripcion = relationship("Suscripcion", back_populates="estadias")
    pago = relationship("Pago", back_populates="estadia", uselist=False)

class Suscripcion(Base):
    __tablename__ = "suscripciones"
    id = Column(Integer, primary_key=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_termino = Column(DateTime, nullable=False)
    vehiculo = relationship("Vehiculo", back_populates="suscripciones")
    estadias = relationship("Estadia", back_populates="suscripcion")
    pago = relationship("Pago", back_populates="suscripcion", uselist=False)

class Pago(Base):
    __tablename__ = "pagos"

    __table_args__ = (
        CheckConstraint(
            "(estadia_id IS NOT NULL AND suscripcion_id IS NULL) OR "
            "(estadia_id IS NULL AND suscripcion_id IS NOT NULL)",
            name="pago_un_solo_origen",
        ),
        CheckConstraint("monto > 0", name="pago_monto_positivo"),
    )

    id = Column(Integer, primary_key=True)
    monto = Column(Integer, nullable=False)
    fecha_pago = Column(DateTime, nullable=False)
    modalidad = Column(String, nullable=False)
    estadia_id = Column(Integer, ForeignKey("estadias.id"), unique=True)
    suscripcion_id = Column(Integer, ForeignKey("suscripciones.id"), unique=True)
    estadia = relationship("Estadia", back_populates="pago")
    suscripcion = relationship("Suscripcion", back_populates="pago")