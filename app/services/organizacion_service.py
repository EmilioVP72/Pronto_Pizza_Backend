from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.organizacion import Empresa, Sucursal, Rol, Usuario

class OrganizacionService:

    @staticmethod
    async def listar_empresas(db: AsyncSession) -> list[Empresa]:
        result = await db.execute(select(Empresa).where(Empresa.activo == True))
        return list(result.scalars().all())

    @staticmethod
    async def listar_sucursales(db: AsyncSession) -> list[Sucursal]:
        result = await db.execute(select(Sucursal).where(Sucursal.activo == True))
        return list(result.scalars().all())

    @staticmethod
    async def listar_roles(db: AsyncSession) -> list[Rol]:
        result = await db.execute(select(Rol))
        return list(result.scalars().all())

    @staticmethod
    async def listar_usuarios(db: AsyncSession) -> list[Usuario]:
        result = await db.execute(
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.sucursal))
            .where(Usuario.activo == True)
            .order_by(Usuario.creado_en.desc())
        )
        return list(result.scalars().all())
