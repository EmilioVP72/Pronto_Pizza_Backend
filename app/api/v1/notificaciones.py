from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.organizacion import Usuario
from app.models.notificaciones import Notificacion
from app.schemas.notificaciones import NotificacionRead
from app.core.security import get_current_user

router = APIRouter(tags=["Notificaciones"])

@router.get("/notificaciones", response_model=List[NotificacionRead])
async def obtener_notificaciones(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(Notificacion)
        .where(Notificacion.usuario_id == current_user.id)
        .order_by(Notificacion.creado_en.desc())
        .limit(50)
    )
    return result.scalars().all()

@router.patch("/notificaciones/{notificacion_id}/leer", response_model=NotificacionRead)
async def marcar_notificacion_leida(
    notificacion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(Notificacion).where(
            Notificacion.id == notificacion_id,
            Notificacion.usuario_id == current_user.id
        )
    )
    notificacion = result.scalar_one_or_none()
    
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
        
    notificacion.leida = True
    await db.commit()
    await db.refresh(notificacion)
    
    return notificacion

@router.patch("/notificaciones/leer-todas")
async def marcar_todas_leidas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    await db.execute(
        update(Notificacion)
        .where(Notificacion.usuario_id == current_user.id)
        .where(Notificacion.leida == False)
        .values(leida=True)
    )
    await db.commit()
    return {"status": "ok"}
