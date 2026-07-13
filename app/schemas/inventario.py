from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

class LoteBase(BaseModel):
    producto_id: UUID
    sucursal_id: UUID
    numero_lote: str
    fecha_elaboracion: date | None = None
    fecha_caducidad: date | None = None
    elaborado_por_id: UUID | None = None
    cantidad_inicial: Decimal
    cantidad_actual: Decimal
    costo_unitario: Decimal | None = None

class LoteRead(LoteBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    activo: bool
    creado_en: datetime

class SaldoInventarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    producto_id: UUID
    sucursal_id: UUID
    cantidad: Decimal
    ultima_entrada: datetime | None = None
    ultima_salida: datetime | None = None
    actualizado_en: datetime

class TipoMovimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    direccion: str
    afecta_costo: bool

class MovimientoInventarioBase(BaseModel):
    tipo_movimiento_id: int
    producto_id: UUID
    sucursal_origen_id: UUID | None = None
    sucursal_destino_id: UUID | None = None
    lote_id: UUID | None = None
    requisicion_id: UUID | None = None
    despacho_id: UUID | None = None
    cantidad: Decimal
    costo_unitario: Decimal | None = None
    notas: str | None = None
    registrado_por_id: UUID

class MovimientoInventarioRead(MovimientoInventarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    creado_en: datetime

class RecepcionCompraDetalleCreate(BaseModel):
    producto_id: UUID
    cantidad: Decimal
    costo_unitario: Decimal
    fecha_caducidad: date | None = None
    notas: str | None = None

class RecepcionCompraCreate(BaseModel):
    sucursal_destino_id: UUID
    notas: str | None = None # Aquí se puede guardar la referencia a la factura
    detalles: list[RecepcionCompraDetalleCreate]

class AjusteInventarioDetalleCreate(BaseModel):
    producto_id: UUID
    lote_id: UUID | None = None
    cantidad: Decimal # Siempre positiva
    costo_unitario: Decimal | None = None
    notas: str | None = None

class AjusteInventarioCreate(BaseModel):
    sucursal_id: UUID
    es_positivo: bool # True para entrada (sobrante), False para salida (merma)
    notas: str | None = None
    detalles: list[AjusteInventarioDetalleCreate]

