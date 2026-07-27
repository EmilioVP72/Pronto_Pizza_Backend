from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida
from app.schemas.catalogo import ProductoRead, CategoriaProductoRead, UnidadMedidaRead, ProductoCreate, ProductoUpdate
from fastapi import HTTPException
from sqlalchemy import func
from uuid import UUID

class CatalogoService:
    @staticmethod
    async def listar_productos(db: AsyncSession, skip: int = 0, limit: int = 100):
        result = await db.execute(select(Producto).where(Producto.activo == True).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def contar_productos(db: AsyncSession):
        result = await db.execute(select(func.count(Producto.id)).where(Producto.activo == True))
        return result.scalar_one()

    @staticmethod
    async def crear_producto(db: AsyncSession, data: ProductoCreate) -> Producto:
        existing = await db.execute(select(Producto).where(Producto.codigo_interno == data.codigo_interno))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="El código de producto ya existe")
            
        prod = Producto(**data.model_dump())
        db.add(prod)
        await db.commit()
        await db.refresh(prod)
        return prod

    @staticmethod
    async def actualizar_producto(db: AsyncSession, producto_id: UUID, data: ProductoUpdate) -> Producto:
        result = await db.execute(select(Producto).where(Producto.id == producto_id))
        prod = result.scalar_one_or_none()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
            
        update_data = data.model_dump(exclude_unset=True)
        if "codigo_interno" in update_data and update_data["codigo_interno"] != prod.codigo_interno:
            existing = await db.execute(select(Producto).where(Producto.codigo_interno == update_data["codigo_interno"]))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="El código de producto ya existe")
                
        for key, value in update_data.items():
            setattr(prod, key, value)
            
        await db.commit()
        await db.refresh(prod)
        return prod

    @staticmethod
    async def eliminar_producto(db: AsyncSession, producto_id: UUID):
        result = await db.execute(select(Producto).where(Producto.id == producto_id))
        prod = result.scalar_one_or_none()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        prod.activo = False
        await db.commit()

    @staticmethod
    async def listar_categorias(db: AsyncSession):
        result = await db.execute(select(CategoriaProducto).order_by(CategoriaProducto.nombre))
        return result.scalars().all()

    @staticmethod
    async def listar_unidades(db: AsyncSession):
        result = await db.execute(select(UnidadMedida).order_by(UnidadMedida.nombre))
        return result.scalars().all()
