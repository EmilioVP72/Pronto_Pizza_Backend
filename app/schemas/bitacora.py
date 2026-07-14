from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.organizacion import UsuarioRead

class BitacoraAccionRead(BaseModel):
    id: UUID
    usuario_id: UUID
    modulo: str
    accion: str
    detalles: str | None = None
    ip_address: str | None = None
    creado_en: datetime
    
    usuario: UsuarioRead | None = None

    class Config:
        from_attributes = True
