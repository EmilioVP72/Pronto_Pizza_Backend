from sqlalchemy import Column, String, Numeric, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid

from app.models.base import Base


class Receta(Base):
    __tablename__ = "recetas"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    producto_id = Column(PGUUID(as_uuid=True), ForeignKey("productos.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    rendimiento = Column(Numeric(12, 4), nullable=False)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relaciones
    producto = relationship("Producto", foreign_keys=[producto_id])
    unidad_medida = relationship("UnidadMedida")
    ingredientes = relationship("RecetaIngrediente", back_populates="receta", cascade="all, delete-orphan")


class RecetaIngrediente(Base):
    __tablename__ = "receta_ingredientes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receta_id = Column(PGUUID(as_uuid=True), ForeignKey("recetas.id", ondelete="CASCADE"), nullable=False)
    insumo_id = Column(PGUUID(as_uuid=True), ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Numeric(12, 4), nullable=False)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=False)

    # Relaciones
    receta = relationship("Receta", back_populates="ingredientes")
    insumo = relationship("Producto", foreign_keys=[insumo_id])
    unidad_medida = relationship("UnidadMedida")


class OrdenProduccion(Base):
    __tablename__ = "ordenes_produccion"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receta_id = Column(PGUUID(as_uuid=True), ForeignKey("recetas.id"), nullable=False)
    sucursal_id = Column(PGUUID(as_uuid=True), ForeignKey("sucursales.id"), nullable=False)
    folio = Column(String(20), nullable=False, unique=True)
    tandas = Column(Numeric(8, 2), nullable=False, default=1)
    cantidad_real = Column(Numeric(12, 4))
    estatus = Column(String(20), nullable=False, default="programada") # programada, en_proceso, completada, cancelada
    lote_resultado_id = Column(PGUUID(as_uuid=True), ForeignKey("lotes.id"))
    elaborado_por_id = Column(PGUUID(as_uuid=True), ForeignKey("usuarios.id"))
    fecha_produccion = Column(DateTime(timezone=True))
    notas = Column(String)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relaciones
    receta = relationship("Receta")
    sucursal = relationship("Sucursal")
    lote_resultado = relationship("Lote")
    elaborado_por = relationship("Usuario")
