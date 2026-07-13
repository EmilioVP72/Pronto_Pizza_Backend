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
    RolRead
)
from app.services.organizacion_service import OrganizacionService

router = APIRouter(prefix="/organizacion", tags=["Organizacion"])


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


@router.get("/usuarios", response_model=list[UsuarioRead])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("administrador")),
):
    return await OrganizacionService.listar_usuarios(db)
