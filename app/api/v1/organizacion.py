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
