from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.organizacion import Usuario
from app.schemas.organizacion import (
    EmpresaRead,
    SucursalRead,
    UsuarioRead,
    RolRead,
    UsuarioCreate,
    UsuarioUpdate
)
from app.services.organizacion_service import OrganizacionService

router = APIRouter(prefix="/organizacion", tags=["Organizacion"])

@router.post("/usuarios", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("administrador")),
):
    return await OrganizacionService.crear_usuario(db, data)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioRead)
async def actualizar_usuario(
    usuario_id: UUID,
    data: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("administrador")),
):
    return await OrganizacionService.actualizar_usuario(db, usuario_id, data)


@router.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    usuario_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("administrador")),
):
    await OrganizacionService.eliminar_usuario(db, usuario_id)


@router.get("/usuarios/me", response_model=UsuarioRead)
async def obtener_usuario_actual(
    current_user: Usuario = Depends(get_current_user)
):
    return current_user


@router.get("/empresas", response_model=list[EmpresaRead])
async def listar_empresas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await OrganizacionService.listar_empresas(db)


@router.get("/sucursales", response_model=list[SucursalRead])
async def listar_sucursales(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await OrganizacionService.listar_sucursales(db)


@router.get("/roles", response_model=list[RolRead])
async def listar_roles(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("administrador")),
):
    return await OrganizacionService.listar_roles(db)


from app.api.v1.utils import paginate_response

@router.get("/usuarios", response_model=dict)
async def listar_usuarios(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("administrador")),
):
    items = await OrganizacionService.listar_usuarios(db)
    return paginate_response([UsuarioRead.model_validate(i).model_dump(mode="json") for i in items], page, size)
