from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timezone
import uuid

from app.models.produccion import Receta, RecetaIngrediente, OrdenProduccion
from app.schemas.produccion import RecetaCreate, OrdenProduccionCreate, OrdenProduccionCompletar
from app.models.inventario import TipoMovimiento, Lote
from app.schemas.inventario import MovimientoInventarioBase
from app.services.inventario_service import InventarioService
from app.models.organizacion import Usuario


class ProduccionService:
    
    @staticmethod
    async def crear_receta(
        db: AsyncSession,
        data: RecetaCreate,
        current_user: Usuario
    ) -> Receta:
        receta = Receta(
            producto_id=data.producto_id,
            nombre=data.nombre,
            rendimiento=data.rendimiento,
            unidad_medida_id=data.unidad_medida_id,
            version=data.version,
            activo=data.activo
        )
        db.add(receta)
        await db.flush()
        
        for ing in data.ingredientes:
            db.add(RecetaIngrediente(
                receta_id=receta.id,
                insumo_id=ing.insumo_id,
                cantidad=ing.cantidad,
                unidad_medida_id=ing.unidad_medida_id
            ))
            
        await db.commit()
        
        result_receta = await db.execute(
            select(Receta)
            .options(selectinload(Receta.ingredientes))
            .where(Receta.id == receta.id)
        )
        return result_receta.scalar_one()

    @staticmethod
    async def obtener_recetas(db: AsyncSession) -> list[Receta]:
        result = await db.execute(
            select(Receta)
            .options(selectinload(Receta.ingredientes))
        )
        return list(result.scalars().all())

    @staticmethod
    async def listar_ordenes(db: AsyncSession) -> list[OrdenProduccion]:
        result = await db.execute(
            select(OrdenProduccion)
            .order_by(OrdenProduccion.creado_en.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def crear_orden_produccion(
        db: AsyncSession,
        data: OrdenProduccionCreate,
        current_user: Usuario
    ) -> OrdenProduccion:
        # Generar un folio simple
        count_op = await db.execute(select(OrdenProduccion))
        total_ops = len(count_op.scalars().all()) + 1
        folio = f"OP-{datetime.now().strftime('%Y%m%d')}-{total_ops:03d}"
        
        orden = OrdenProduccion(
            receta_id=data.receta_id,
            sucursal_id=data.sucursal_id,
            folio=folio,
            tandas=data.tandas,
            estatus="programada",
            notas=data.notas
        )
        db.add(orden)
        await db.commit()
        await db.refresh(orden)
        return orden

    @staticmethod
    async def completar_orden_produccion(
        db: AsyncSession,
        orden_id: UUID,
        data: OrdenProduccionCompletar,
        current_user: Usuario
    ) -> OrdenProduccion:
        result = await db.execute(
            select(OrdenProduccion)
            .where(OrdenProduccion.id == orden_id)
        )
        orden = result.scalar_one_or_none()
        
        if not orden:
            raise HTTPException(status_code=404, detail="Orden de producción no encontrada")
            
        if orden.estatus == "completada":
            raise HTTPException(status_code=400, detail="La orden ya ha sido completada")
            
        # 1. Obtener la receta para descontar insumos
        res_receta = await db.execute(
            select(Receta)
            .options(selectinload(Receta.ingredientes))
            .where(Receta.id == orden.receta_id)
        )
        receta = res_receta.scalar_one()
        
        # 2. Registrar Salidas de Producción
        # Buscamos o creamos un tipo_movimiento de salida de producción si no existe o usamos SAL_MUESTRA como fallback en db si el trigger no existe
        res_tipo_salida = await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == "SAL_PRODUCCION"))
        tipo_salida = res_tipo_salida.scalar_one_or_none()
        if not tipo_salida:
            # Create it dynamically if missing
            tipo_salida = TipoMovimiento(
                codigo="SAL_PRODUCCION",
                nombre="Salida por Producción",
                direccion="S",
                afecta_costo=True
            )
            db.add(tipo_salida)
            await db.flush()
            
        for ing in receta.ingredientes:
            # Calcular cantidad a descontar = (cantidad por tanda) * (tandas totales en orden)
            cantidad_consumir = ing.cantidad * orden.tandas
            
            mov_salida = MovimientoInventarioBase(
                tipo_movimiento_id=tipo_salida.id,
                producto_id=ing.insumo_id,
                sucursal_origen_id=orden.sucursal_id, # Se consume del comisariato/sucursal que produce
                sucursal_destino_id=None,
                cantidad=cantidad_consumir,
                costo_unitario=None, # El ledger calculará el costo si aplica PEPS/Promedio
                notas=f"Consumo automático para {orden.folio}",
                registrado_por_id=current_user.id
            )
            await InventarioService.registrar_movimiento(db, mov_salida, current_user)
            
        # 3. Registrar Entrada del Producto Preparado
        res_tipo_entrada = await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == "ENT_PRODUCCION"))
        tipo_entrada = res_tipo_entrada.scalar_one_or_none()
        if not tipo_entrada:
            raise HTTPException(status_code=500, detail="Tipo ENT_PRODUCCION no encontrado")
            
        lote_generado = Lote(
            producto_id=receta.producto_id,
            sucursal_id=orden.sucursal_id,
            numero_lote=f"PROD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
            elaborado_por_id=current_user.id,
            cantidad_inicial=data.cantidad_real,
            cantidad_actual=data.cantidad_real,
            # costo_unitario: se debería calcular según el costo de los insumos consumidos. Por simplicidad aquí lo dejamos en None o 0
        )
        db.add(lote_generado)
        await db.flush()
        
        mov_entrada = MovimientoInventarioBase(
            tipo_movimiento_id=tipo_entrada.id,
            producto_id=receta.producto_id,
            sucursal_origen_id=None,
            sucursal_destino_id=orden.sucursal_id,
            lote_id=lote_generado.id,
            cantidad=data.cantidad_real,
            costo_unitario=None,
            notas=data.notas or f"Entrada automática de {orden.folio}",
            registrado_por_id=current_user.id
        )
        await InventarioService.registrar_movimiento(db, mov_entrada, current_user)
        
        # 4. Actualizar Orden
        orden.estatus = "completada"
        orden.cantidad_real = data.cantidad_real
        orden.lote_resultado_id = lote_generado.id
        orden.elaborado_por_id = current_user.id
        orden.fecha_produccion = datetime.now(timezone.utc)
        
        if data.notas:
            orden.notas = f"{orden.notas or ''} | {data.notas}"
            
        await db.commit()
        await db.refresh(orden)
        
        return orden
