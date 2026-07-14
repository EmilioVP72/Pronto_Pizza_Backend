from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.organizacion import Usuario
from app.schemas.requisiciones import RequisicionCreate, RequisicionRead, RequisicionUpdate
from app.services.requisicion_service import RequisicionService

router = APIRouter(prefix="/requisiciones", tags=["Requisiciones"])

@router.get("/", response_model=list[RequisicionRead])
async def listar_requisiciones(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await RequisicionService.listar(db, current_user)

@router.post("/", response_model=RequisicionRead, status_code=status.HTTP_201_CREATED)
async def crear_requisicion(
    data: RequisicionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("encargado_sucursal", "almacenista", "administrador")),
):
    return await RequisicionService.crear(db, data, current_user)

@router.patch("/{requisicion_id}/enviar", response_model=RequisicionRead)
async def enviar_requisicion(
    requisicion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("encargado_sucursal", "almacenista", "administrador")),
):
    return await RequisicionService.transicionar_estado(db, requisicion_id, "enviada", current_user)

@router.patch("/{requisicion_id}/aprobar", response_model=RequisicionRead)
async def aprobar_requisicion(
    requisicion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    return await RequisicionService.transicionar_estado(db, requisicion_id, "aprobada", current_user)

@router.patch("/{requisicion_id}/rechazar", response_model=RequisicionRead)
async def rechazar_requisicion(
    requisicion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    return await RequisicionService.transicionar_estado(db, requisicion_id, "rechazada", current_user)
