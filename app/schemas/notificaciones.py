from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class NotificacionBase(BaseModel):
    titulo: str
    mensaje: str
    leida: bool

class NotificacionCreate(BaseModel):
    usuario_id: UUID
    titulo: str
    mensaje: str

class NotificacionRead(NotificacionBase):
    id: UUID
    creado_en: datetime
    
    class Config:
        from_attributes = True
