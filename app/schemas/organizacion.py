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

class SucursalCreate(SucursalBase):
    pass

class SucursalUpdate(BaseModel):
    empresa_id: UUID | None = None
    nombre: str | None = None
    codigo: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    es_comisariato: bool | None = None
    activo: bool | None = None

class SucursalRead(SucursalBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

class RolBase(BaseModel):
    nombre: str
    descripcion: str | None = None

class RolCreate(RolBase):
    pass

class RolUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None

class RolRead(RolBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

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
