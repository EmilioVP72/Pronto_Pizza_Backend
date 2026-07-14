from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID
from typing import List, Optional

class ExportacionBase(BaseModel):
    periodo_inicio: date
    periodo_fin: date
    notas: Optional[str] = None

class ExportacionCreate(ExportacionBase):
    pass

class ExportacionRead(ExportacionBase):
    id: UUID
    estatus: str
    archivo_nombre: Optional[str]
    total_registros: Optional[int]
    generado_por_id: UUID
    creado_en: datetime

    class Config:
        from_attributes = True

class LineaContpaqiRead(BaseModel):
    id: UUID
    cuenta_contable: str
    concepto: str
    referencia: Optional[str]
    importe: float
    tipo_poliza: Optional[str]

    class Config:
        from_attributes = True
