import asyncio
from app.core.database import engine
from app.models.base import Base
# Import all models to ensure they are registered with Base.metadata
from app.models import organizacion, catalogo, inventario, produccion, despachos, requisiciones, contabilidad

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tablas actualizadas exitosamente.")

if __name__ == "__main__":
    asyncio.run(create_tables())
