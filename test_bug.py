import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services.requisicion_service import RequisicionService
from app.services.pdf_service import PDFService
from sqlalchemy import select
from app.models.requisiciones import Requisicion
from app.models.notificaciones import Notificacion

async def test_pdf():
    async with SessionLocal() as db:
        result = await db.execute(select(Requisicion).limit(1))
        req = result.scalar_one_or_none()
        if req:
            print("Testing PDF for Requisicion ID:", req.id)
            try:
                # Need to load with detalles
                req_loaded = await RequisicionService.obtener_por_id(db, req.id)
                PDFService.generar_pdf_requisicion(req_loaded)
                print("PDF Requisicion OK")
            except Exception as e:
                import traceback
                traceback.print_exc()

async def test_notif():
    async with SessionLocal() as db:
        print("Testing Notificaciones...")
        try:
            result = await db.execute(select(Notificacion).limit(1))
            notifs = result.scalars().all()
            print("Notificaciones OK", len(notifs))
        except Exception as e:
            import traceback
            traceback.print_exc()

async def main():
    await test_pdf()
    await test_notif()

if __name__ == "__main__":
    asyncio.run(main())
