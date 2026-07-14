from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class SaldoInventarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    producto_id: UUID
    producto_nombre: str
    producto_codigo: str
    sucursal_id: UUID
    sucursal_nombre: str
    cantidad: Decimal
    ultima_entrada: datetime | None = None
    ultima_salida: datetime | None = None
    actualizado_en: datetime
