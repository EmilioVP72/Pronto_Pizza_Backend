from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class TipoDocumentoSalidaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    descripcion: str | None = None

class DespachoDetalleBase(BaseModel):
    producto_id: UUID
    lote_id: UUID | None = None
    cantidad: Decimal
    costo_unitario: Decimal | None = None
    notas: str | None = None

class DespachoDetalleRead(DespachoDetalleBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    despacho_id: UUID

class DespachoCreate(BaseModel):
    requisicion_id: UUID | None = None
    sucursal_destino_id: UUID
    notas: str | None = None
    detalles: list[DespachoDetalleBase]

class DespachoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    requisicion_id: UUID | None
    sucursal_origen_id: UUID
    sucursal_destino_id: UUID
    tipo_documento_id: int
    folio_documento: str | None
    folio_fiscal: str | None
    estatus: str
    fecha_despacho: datetime | None
    notas: str | None
    despachado_por_id: UUID
    recibido_por_id: UUID | None
    fecha_recepcion: datetime | None
    creado_en: datetime
    actualizado_en: datetime
    detalles: list[DespachoDetalleRead]
