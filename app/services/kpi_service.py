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
        # Valor del inventario por sucursal
        # Aproximación: cantidad * un costo referencial o si tuviéramos un costo_promedio en Saldo
        # En nuestro diseño actual, el SaldoInventario tiene cantidad. Asumiremos que tenemos el costo del lote
        # o usamos un valor referencial. Para el KPI simple, haremos sum(cantidad) y simularemos un valor.
        query = select(
            Sucursal.nombre.label("sucursal_nombre"),
            func.coalesce(func.sum(SaldoInventario.cantidad), 0).label("cantidad_total")
        ).outerjoin(
            SaldoInventario, SaldoInventario.sucursal_id == Sucursal.id
        ).where(
            Sucursal.es_comisariato == False # O mostrar todas
        ).group_by(Sucursal.id)
        
        res = await db.execute(query)
        rows = res.all()
        # Retornamos el volumen (cantidad total de artículos) en lugar de un valor monetario ficticio.
        return [{"sucursal": r.sucursal_nombre, "valor": float(r.cantidad_total)} for r in rows]

    @staticmethod
    async def obtener_tiempos_sla(db: AsyncSession):
        # Medir el tiempo (SLA) desde que se solicita (creado_en) hasta que se aprueba/surte
        # Calcularemos el promedio en horas de requisiciones que tienen fecha_aprobacion
        query = select(
            func.avg(
                func.extract('epoch', Requisicion.fecha_aprobacion) - func.extract('epoch', Requisicion.creado_en)
            ).label("promedio_segundos")
        ).where(
            Requisicion.fecha_aprobacion.isnot(None)
        )
        res = await db.execute(query)
        promedio = res.scalar() or 0
        horas = promedio / 3600
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
            Producto.id
        ).order_by(
            func.sum(MovimientoInventario.cantidad).desc()
        ).limit(5)
        
        res = await db.execute(query)
        rows = res.all()
        return [{"producto": r.producto, "cantidad": float(r.cantidad_salida)} for r in rows]
