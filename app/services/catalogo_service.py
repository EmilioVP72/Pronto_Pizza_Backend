from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida
from app.schemas.catalogo import ProductoRead, CategoriaProductoRead, UnidadMedidaRead

class CatalogoService:
    @staticmethod
    async def listar_productos(db: AsyncSession, skip: int = 0, limit: int = 100):
        result = await db.execute(select(Producto).where(Producto.activo == True).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def listar_categorias(db: AsyncSession):
        result = await db.execute(select(CategoriaProducto).order_by(CategoriaProducto.nombre))
        return result.scalars().all()

    @staticmethod
    async def listar_unidades(db: AsyncSession):
        result = await db.execute(select(UnidadMedida).order_by(UnidadMedida.nombre))
        return result.scalars().all()
