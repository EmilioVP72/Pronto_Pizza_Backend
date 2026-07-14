from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from decimal import Decimal
from app.models.base import Base

class TipoDocumentoSalida(Base):
    __tablename__ = "tipos_documento_salida"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)

class Despacho(Base):
    __tablename__ = "despachos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requisicion_id: Mapped[UUID | None] = mapped_column(ForeignKey("requisiciones.id"), index=True)
    sucursal_origen_id: Mapped[UUID] = mapped_column(ForeignKey("sucursales.id"), nullable=False, index=True)
    sucursal_destino_id: Mapped[UUID] = mapped_column(ForeignKey("sucursales.id"), nullable=False, index=True)
    tipo_documento_id: Mapped[int] = mapped_column(ForeignKey("tipos_documento_salida.id"), nullable=False)
    folio_documento: Mapped[str | None] = mapped_column(String(30))
    folio_fiscal: Mapped[str | None] = mapped_column(String(50))
    estatus: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False, index=True)
    fecha_despacho: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    notas: Mapped[str | None] = mapped_column(Text)
    despachado_por_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    recibido_por_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    fecha_recepcion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    requisicion = relationship("Requisicion")
    sucursal_origen = relationship("Sucursal", foreign_keys=[sucursal_origen_id])
    sucursal_destino = relationship("Sucursal", foreign_keys=[sucursal_destino_id])
    tipo_documento = relationship("TipoDocumentoSalida")
    despachado_por = relationship("Usuario", foreign_keys=[despachado_por_id])
    recibido_por = relationship("Usuario", foreign_keys=[recibido_por_id])
    detalles = relationship("DespachoDetalle", back_populates="despacho", cascade="all, delete-orphan")

class DespachoDetalle(Base):
    __tablename__ = "despacho_detalles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    despacho_id: Mapped[UUID] = mapped_column(ForeignKey("despachos.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    lote_id: Mapped[UUID | None] = mapped_column(ForeignKey("lotes.id"), index=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    notas: Mapped[str | None] = mapped_column(Text)

    despacho = relationship("Despacho", back_populates="detalles")
    producto = relationship("Producto")
    lote = relationship("Lote")
