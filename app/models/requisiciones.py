from datetime import datetime, date
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from decimal import Decimal
from app.models.base import Base

class Requisicion(Base):
    __tablename__ = "requisiciones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursales.id"), nullable=False, index=True)
    folio: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    estatus: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False, index=True)
    fecha_requerida: Mapped[date | None] = mapped_column(Date)
    notas: Mapped[str | None] = mapped_column(Text)
    creado_por_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    aprobado_por_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sucursal = relationship("Sucursal")
    creado_por = relationship("Usuario", foreign_keys=[creado_por_id])
    aprobado_por = relationship("Usuario", foreign_keys=[aprobado_por_id])
    detalles = relationship("RequisicionDetalle", back_populates="requisicion", cascade="all, delete-orphan")

class RequisicionDetalle(Base):
    __tablename__ = "requisicion_detalles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    requisicion_id: Mapped[UUID] = mapped_column(ForeignKey("requisiciones.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    cantidad_solicitada: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    cantidad_aprobada: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    cantidad_surtida: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    notas: Mapped[str | None] = mapped_column(Text)

    requisicion = relationship("Requisicion", back_populates="detalles")
    producto = relationship("Producto")
