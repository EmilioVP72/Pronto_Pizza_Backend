from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json
from app.models.organizacion import BitacoraAccion
from uuid import UUID

class BitacoraService:
    @staticmethod
    async def registrar_accion(
        db: AsyncSession,
        usuario_id: UUID,
        modulo: str,
        accion: str,
        detalles: dict | None = None,
        ip_address: str | None = None
    ) -> BitacoraAccion:
        from fastapi.encoders import jsonable_encoder
        detalles_encoded = jsonable_encoder(detalles) if detalles else None
        detalles_str = json.dumps(detalles_encoded) if detalles_encoded else None
        
        nueva_accion = BitacoraAccion(
            usuario_id=usuario_id,
            modulo=modulo,
            accion=accion,
            detalles=detalles_str,
            ip_address=ip_address
        )
        db.add(nueva_accion)
        # We don't commit here so that the log is part of the same transaction as the action!
        return nueva_accion

    @staticmethod
    async def listar_bitacora(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(BitacoraAccion).options(
            selectinload(BitacoraAccion.usuario)
        ).order_by(BitacoraAccion.creado_en.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def contar_bitacora(db: AsyncSession) -> int:
        from sqlalchemy import func
        query = select(func.count(BitacoraAccion.id))
        result = await db.execute(query)
        return result.scalar_one()
