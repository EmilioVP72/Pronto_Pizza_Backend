import asyncio
from app.core.database import engine
from app.models.base import Base
# Make sure all models are imported so they are registered with Base.metadata
import app.models.organizacion
import app.models.catalogo
import app.models.inventario
import app.models.despachos
import app.models.requisiciones
import app.models.produccion
import app.models.notificaciones


async def create_tables():
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully.")

if __name__ == "__main__":
    asyncio.run(create_tables())
