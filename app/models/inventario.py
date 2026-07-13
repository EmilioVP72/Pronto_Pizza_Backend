from datetime import datetime, date
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, Date, CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from decimal import Decimal
from app.models.base import Base

class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursales.id"), nullable=False, index=True)
    numero_lote: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_elaboracion: Mapped[date | None] = mapped_column(Date)
    fecha_caducidad: Mapped[date | None] = mapped_column(Date, index=True)
    elaborado_por_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    cantidad_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    cantidad_actual: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    producto = relationship("Producto")
    sucursal = relationship("Sucursal")
    elaborado_por = relationship("Usuario")

class SaldoInventario(Base):
    __tablename__ = "saldos_inventario"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursales.id"), nullable=False, index=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False)
    ultima_entrada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultima_salida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    producto = relationship("Producto")
    sucursal = relationship("Sucursal")

class TipoMovimiento(Base):
    __tablename__ = "tipos_movimiento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    direccion: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    afecta_costo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tipo_movimiento_id: Mapped[int] = mapped_column(ForeignKey("tipos_movimiento.id"), nullable=False, index=True)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    sucursal_origen_id: Mapped[UUID | None] = mapped_column(ForeignKey("sucursales.id"), index=True)
    sucursal_destino_id: Mapped[UUID | None] = mapped_column(ForeignKey("sucursales.id"), index=True)
    lote_id: Mapped[UUID | None] = mapped_column(ForeignKey("lotes.id"))
    requisicion_id: Mapped[UUID | None] = mapped_column(ForeignKey("requisiciones.id"))
    despacho_id: Mapped[UUID | None] = mapped_column(ForeignKey("despachos.id"))

    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    notas: Mapped[str | None] = mapped_column(Text)
    registrado_por_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    tipo_movimiento = relationship("TipoMovimiento")
    producto = relationship("Producto")
    sucursal_origen = relationship("Sucursal", foreign_keys=[sucursal_origen_id])
    sucursal_destino = relationship("Sucursal", foreign_keys=[sucursal_destino_id])
    lote = relationship("Lote")
    registrado_por = relationship("Usuario")
    requisicion = relationship("Requisicion")
    despacho = relationship("Despacho")

