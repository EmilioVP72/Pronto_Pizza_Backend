import asyncio
from app.core.database import SessionLocal
from app.models.inventario import TipoMovimiento
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        res = await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == "SAL_REQUISICION"))
        tm = res.scalar_one_or_none()
        if not tm:
            tm = TipoMovimiento(codigo="SAL_REQUISICION", nombre="Salida por Requisición", direccion="S", afecta_costo=True)
            db.add(tm)
            await db.commit()
            print("Added SAL_REQUISICION")
        else:
            print("Already exists")

if __name__ == "__main__":
    asyncio.run(main())
