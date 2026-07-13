from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from decimal import Decimal
from app.models.base import Base

class CategoriaProducto(Base):
    __tablename__ = "categorias_producto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)

    productos = relationship("Producto", back_populates="categoria")

class UnidadMedida(Base):
    __tablename__ = "unidades_medida"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(40), nullable=False)
    abreviatura: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)

    productos = relationship("Producto", foreign_keys="[Producto.unidad_medida_id]", back_populates="unidad_medida")
    productos_compra = relationship("Producto", foreign_keys="[Producto.unidad_compra_id]", back_populates="unidad_compra")

class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias_producto.id"), nullable=False, index=True)
    unidad_medida_id: Mapped[int] = mapped_column(ForeignKey("unidades_medida.id"), nullable=False)
    unidad_compra_id: Mapped[int | None] = mapped_column(ForeignKey("unidades_medida.id"))
    factor_conversion: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("1.0000"))
    codigo_interno: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    tipo_producto: Mapped[str] = mapped_column(String(15), default="insumo", nullable=False, index=True)
    precio_referencia: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    clave_contpaqi: Mapped[str | None] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    categoria = relationship("CategoriaProducto", back_populates="productos")
    unidad_medida = relationship("UnidadMedida", foreign_keys=[unidad_medida_id], back_populates="productos")
    unidad_compra = relationship("UnidadMedida", foreign_keys=[unidad_compra_id], back_populates="productos_compra")
    configuraciones_sucursal = relationship("ProductoSucursal", back_populates="producto")

class ProductoSucursal(Base):
    __tablename__ = "productos_sucursal"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursales.id"), nullable=False, index=True)
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False)
    stock_maximo: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False)
    punto_reorden: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    producto = relationship("Producto", back_populates="configuraciones_sucursal")
    sucursal = relationship("Sucursal")
