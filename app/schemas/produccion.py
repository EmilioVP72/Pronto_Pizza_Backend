from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class RecetaIngredienteBase(BaseModel):
    insumo_id: UUID
    cantidad: Decimal
    unidad_medida_id: int

class RecetaIngredienteCreate(RecetaIngredienteBase):
    pass

class RecetaIngredienteRead(RecetaIngredienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    receta_id: UUID

class RecetaBase(BaseModel):
    producto_id: UUID
    nombre: str
    rendimiento: Decimal
    unidad_medida_id: int
    version: int = 1
    activo: bool = True

class RecetaCreate(RecetaBase):
    ingredientes: list[RecetaIngredienteCreate]

class RecetaRead(RecetaBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    creado_en: datetime
    ingredientes: list[RecetaIngredienteRead]

class OrdenProduccionBase(BaseModel):
    receta_id: UUID
    sucursal_id: UUID
    tandas: Decimal
    notas: str | None = None

class OrdenProduccionCreate(OrdenProduccionBase):
    pass

class OrdenProduccionRead(OrdenProduccionBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    folio: str
    cantidad_real: Decimal | None = None
    estatus: str
    lote_resultado_id: UUID | None = None
    elaborado_por_id: UUID | None = None
    fecha_produccion: datetime | None = None
    creado_en: datetime
    actualizado_en: datetime

class OrdenProduccionCompletar(BaseModel):
    cantidad_real: Decimal
    notas: str | None = None
