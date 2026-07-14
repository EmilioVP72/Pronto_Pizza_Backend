from pydantic import BaseModel, ConfigDict, EmailStr
from uuid import UUID
from datetime import datetime

class EmpresaBase(BaseModel):
    razon_social: str
    rfc: str
    direccion_fiscal: str | None = None
    es_matriz: bool = False

class EmpresaRead(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

class SucursalBase(BaseModel):
    empresa_id: UUID
    nombre: str
    codigo: str
    direccion: str | None = None
    telefono: str | None = None
    es_comisariato: bool = False

class SucursalRead(SucursalBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

class RolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    descripcion: str | None = None

class UsuarioBase(BaseModel):
    sucursal_id: UUID
    rol_id: int
    nombre_completo: str
    email: EmailStr

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioUpdate(BaseModel):
    sucursal_id: UUID | None = None
    rol_id: int | None = None
    nombre_completo: str | None = None
    email: EmailStr | None = None
    password: str | None = None

class UsuarioRead(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    auth_user_id: UUID | None
    activo: bool
    creado_en: datetime
    actualizado_en: datetime
    rol: RolRead | None = None
    sucursal: SucursalRead | None = None
