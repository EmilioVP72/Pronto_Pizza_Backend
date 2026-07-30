from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from app.models.inventario import SaldoInventario, MovimientoInventario, TipoMovimiento
from app.models.catalogo import Producto
from app.models.organizacion import Sucursal
from app.models.requisiciones import Requisicion

class KpiService:
    @staticmethod
    async def obtener_valor_inventario(db: AsyncSession):
        # Valor del inventario por sucursal calculando cantidad * precio_referencia
        query = select(
            Sucursal.nombre.label("sucursal_nombre"),
            func.coalesce(
                func.sum(SaldoInventario.cantidad * func.coalesce(Producto.precio_referencia, 0.0)),
                0
            ).label("valor_total")
        ).outerjoin(
            SaldoInventario, SaldoInventario.sucursal_id == Sucursal.id
        ).outerjoin(
            Producto, SaldoInventario.producto_id == Producto.id
        ).where(
            Sucursal.es_comisariato == False
        ).group_by(Sucursal.id, Sucursal.nombre)
        
        res = await db.execute(query)
        rows = res.all()
        return [{"sucursal": r.sucursal_nombre, "valor": float(r.valor_total)} for r in rows]

    @staticmethod
    async def obtener_tiempos_sla(db: AsyncSession):
        # Medir el tiempo (SLA) desde que se solicita (creado_en) hasta que se aprueba/surte
        query = select(
            func.avg(
                func.extract('epoch', Requisicion.fecha_aprobacion) - func.extract('epoch', Requisicion.creado_en)
            ).label("promedio_segundos")
        ).where(
            Requisicion.fecha_aprobacion.isnot(None)
        )
        res = await db.execute(query)
        promedio = res.scalar() or 0
        horas = float(promedio) / 3600
        return {"sla_promedio_horas": round(horas, 2)}

    @staticmethod
    async def obtener_rotacion(db: AsyncSession):
        # Top 5 productos con más salidas (SAL_REQUISICION u otros) en los últimos 30 días
        hace_30_dias = datetime.now(timezone.utc) - timedelta(days=30)
        query = select(
            Producto.nombre.label("producto"),
            func.sum(MovimientoInventario.cantidad).label("cantidad_salida")
        ).join(
            MovimientoInventario, MovimientoInventario.producto_id == Producto.id
        ).join(
            TipoMovimiento, TipoMovimiento.id == MovimientoInventario.tipo_movimiento_id
        ).where(
            TipoMovimiento.direccion == "S",
            MovimientoInventario.creado_en >= hace_30_dias
        ).group_by(
            Producto.id, Producto.nombre
        ).order_by(
            func.sum(MovimientoInventario.cantidad).desc()
        ).limit(5)
        
        res = await db.execute(query)
        rows = res.all()
        return [{"producto": r.producto, "cantidad": float(r.cantidad_salida)} for r in rows]
