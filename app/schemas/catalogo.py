from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class CategoriaProductoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    descripcion: str | None = None

class UnidadMedidaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    abreviatura: str

class ProductoBase(BaseModel):
    categoria_id: int
    unidad_medida_id: int
    unidad_compra_id: int | None = None
    factor_conversion: Decimal = Decimal("1.0000")
    codigo_interno: str
    nombre: str
    descripcion: str | None = None
    tipo_producto: str = "insumo"
    precio_referencia: Decimal | None = None
    clave_contpaqi: str | None = None

class ProductoRead(ProductoBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

class ProductoSucursalBase(BaseModel):
    producto_id: UUID
    sucursal_id: UUID
    stock_minimo: Decimal = Decimal("0.0000")
    stock_maximo: Decimal = Decimal("0.0000")
    punto_reorden: Decimal = Decimal("0.0000")

class ProductoSucursalRead(ProductoSucursalBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    activo: bool
    actualizado_en: datetime
