from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

class RequisicionDetalleBase(BaseModel):
    producto_id: UUID
    cantidad_solicitada: Decimal
    notas: str | None = None

class RequisicionDetalleUpdate(BaseModel):
    cantidad_aprobada: Decimal | None = None
    cantidad_surtida: Decimal | None = None
    notas: str | None = None

class RequisicionDetalleRead(RequisicionDetalleBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    requisicion_id: UUID
    cantidad_aprobada: Decimal | None
    cantidad_surtida: Decimal | None

class RequisicionCreate(BaseModel):
    fecha_requerida: date | None = None
    notas: str | None = None
    detalles: list[RequisicionDetalleBase]

class RequisicionUpdate(BaseModel):
    fecha_requerida: date | None = None
    notas: str | None = None

class RequisicionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sucursal_id: UUID
    folio: str
    estatus: str
    fecha_requerida: date | None
    notas: str | None
    creado_por_id: UUID
    aprobado_por_id: UUID | None
    fecha_aprobacion: datetime | None
    creado_en: datetime
    actualizado_en: datetime
    detalles: list[RequisicionDetalleRead]
