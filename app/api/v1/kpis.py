from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_db
from app.services.kpi_service import KpiService
from app.core.security import get_current_user
from app.models.organizacion import Usuario

router = APIRouter(tags=["KPIs"])

@router.get("/kpis/dashboard")
async def obtener_dashboard_kpis(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    valor_inventario = await KpiService.obtener_valor_inventario(db)
    sla = await KpiService.obtener_tiempos_sla(db)
    rotacion = await KpiService.obtener_rotacion(db)
    
    return {
        "volumen_inventario_por_sucursal": valor_inventario,
        "sla_procesamiento": sla,
        "rotacion_top_5": rotacion
    }
