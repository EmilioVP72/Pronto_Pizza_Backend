from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.organizacion import Usuario
from app.schemas.contabilidad import ExportacionCreate, ExportacionRead
from app.services.contabilidad_service import ContabilidadService

router = APIRouter(prefix="/contabilidad", tags=["Contabilidad"])

@router.post("/exportar", response_model=ExportacionRead, status_code=status.HTTP_201_CREATED)
async def generar_exportacion(
    data: ExportacionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("contador", "administrador")),
):
    return await ContabilidadService.generar_exportacion(db, data, current_user)

@router.get("/exportaciones", response_model=list[ExportacionRead])
async def listar_exportaciones(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("contador", "administrador")),
):
    return await ContabilidadService.listar_exportaciones(db)

@router.get("/exportaciones/{exportacion_id}/descargar", response_class=PlainTextResponse)
async def descargar_exportacion(
    exportacion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("contador", "administrador")),
):
    content = await ContabilidadService.descargar_exportacion(db, str(exportacion_id))
    return content
