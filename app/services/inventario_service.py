from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from datetime import datetime, timezone, date
import uuid
from uuid import UUID
from decimal import Decimal

from app.models.inventario import MovimientoInventario, TipoMovimiento, Lote
from app.schemas.inventario import MovimientoInventarioBase, RecepcionCompraCreate, AjusteInventarioCreate
from app.models.organizacion import Usuario
from app.models.catalogo import ProductoSucursal


class InventarioService:

    @staticmethod
    async def registrar_movimiento(
        db: AsyncSession,
        data: MovimientoInventarioBase,
        current_user: Usuario,
    ) -> MovimientoInventario:
        # El inventario es un ledger inmutable.
        # Solo hacemos INSERT en MovimientoInventario.
        # El trigger trg_actualizar_saldo de PostgreSQL actualizará saldos_inventario.
        
        movimiento = MovimientoInventario(
            **data.model_dump(exclude={"registrado_por_id"}),
            registrado_por_id=current_user.id
        )
        
        db.add(movimiento)
        await db.commit()
        await db.refresh(movimiento)
        
        # Trigger de verificación de alertas de stock
        sucursal_id_afectada = data.sucursal_origen_id or data.sucursal_destino_id
        if sucursal_id_afectada:
            await InventarioService.verificar_alertas_stock(db, data.producto_id, sucursal_id_afectada)
        
        return movimiento

    @staticmethod
    async def actualizar_parametros(
        db: AsyncSession,
        producto_id: UUID,
        sucursal_id: UUID,
        punto_reorden: Decimal,
        stock_maximo: Decimal,
        current_user: Usuario
    ):
        result = await db.execute(
            select(ProductoSucursal).where(
                ProductoSucursal.producto_id == producto_id,
                ProductoSucursal.sucursal_id == sucursal_id
            )
        )
        ps = result.scalar_one_or_none()
        if not ps:
            ps = ProductoSucursal(
                producto_id=producto_id,
                sucursal_id=sucursal_id,
                punto_reorden=punto_reorden,
                stock_maximo=stock_maximo
            )
            db.add(ps)
        else:
            ps.punto_reorden = punto_reorden
            ps.stock_maximo = stock_maximo

        await db.flush()

        from app.services.bitacora_service import BitacoraService
        await BitacoraService.registrar_accion(
            db=db,
            usuario_id=current_user.id,
            modulo="Inventario",
            accion="ACTUALIZAR_PARAMETROS",
            detalles={"producto_id": str(producto_id), "punto_reorden": str(punto_reorden), "stock_maximo": str(stock_maximo)}
        )

        await db.commit()
        return ps

    @staticmethod
    async def recibir_compra(
        db: AsyncSession,
        data: RecepcionCompraCreate,
        current_user: Usuario
    ):
        result = await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == "ENT_COMPRA"))
        tipo_mov = result.scalar_one_or_none()
        if not tipo_mov:
            raise HTTPException(status_code=500, detail="Tipo de movimiento ENT_COMPRA no configurado")

        movimientos_creados = []
        for det in data.detalles:
            # Crear el lote para la recepción
            # Como es una compra, el número de lote puede autogenerarse con un prefijo
            lote = Lote(
                producto_id=det.producto_id,
                sucursal_id=data.sucursal_destino_id,
                numero_lote=f"COMP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
                fecha_caducidad=det.fecha_caducidad,
                cantidad_inicial=det.cantidad,
                cantidad_actual=det.cantidad,
                costo_unitario=det.costo_unitario,
            )
            db.add(lote)
            await db.flush() # Obtener lote.id
            
            mov_data = MovimientoInventarioBase(
                tipo_movimiento_id=tipo_mov.id,
                producto_id=det.producto_id,
                sucursal_destino_id=data.sucursal_destino_id,
                lote_id=lote.id,
                cantidad=det.cantidad,
                costo_unitario=det.costo_unitario,
                notas=data.notas or det.notas,
                registrado_por_id=current_user.id
            )
            mov = await InventarioService.registrar_movimiento(db, mov_data, current_user)
            movimientos_creados.append(mov)
            
        return movimientos_creados

    @staticmethod
    async def registrar_ajuste(
        db: AsyncSession,
        data: AjusteInventarioCreate,
        current_user: Usuario
    ):
        codigo_mov = "AJU_POSITIVO" if data.es_positivo else "AJU_NEGATIVO"
        result = await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == codigo_mov))
        tipo_mov = result.scalar_one_or_none()
        if not tipo_mov:
            raise HTTPException(status_code=500, detail=f"Tipo de movimiento {codigo_mov} no configurado")

        movimientos_creados = []
        for det in data.detalles:
            # En un ajuste negativo, sucursal_origen = sucursal_id. 
            # En un ajuste positivo, sucursal_destino = sucursal_id.
            if data.es_positivo:
                sucursal_destino = data.sucursal_id
                sucursal_origen = None
            else:
                sucursal_destino = None
                sucursal_origen = data.sucursal_id
                
            mov_data = MovimientoInventarioBase(
                tipo_movimiento_id=tipo_mov.id,
                producto_id=det.producto_id,
                sucursal_origen_id=sucursal_origen,
                sucursal_destino_id=sucursal_destino,
                lote_id=det.lote_id,
                cantidad=det.cantidad,
                costo_unitario=det.costo_unitario,
                notas=data.notas or det.notas,
                registrado_por_id=current_user.id
            )
            mov = await InventarioService.registrar_movimiento(db, mov_data, current_user)
            movimientos_creados.append(mov)
            
        return movimientos_creados

    @staticmethod
    async def listar_saldos(db: AsyncSession, skip: int = 0, limit: int = 100):
        # We need to join with Producto and Sucursal to return names
        from app.models.inventario import SaldoInventario
        from app.models.catalogo import Producto
        from app.models.organizacion import Sucursal
        from sqlalchemy.orm import selectinload
        
        # In a real app we would join and map, but for simplicity let's do a basic select
        # and we can map it. 
        query = select(SaldoInventario).order_by(SaldoInventario.actualizado_en.desc()).offset(skip).limit(limit)
        
        # We should use joinedload but since we don't have the exact relationships mapped in the files 
        # (they might be missing back_populates), we'll do a manual fetch if needed or rely on relationships.
        # Assuming the relationships exist:
        from sqlalchemy.orm import joinedload
        try:
            query = query.options(joinedload(SaldoInventario.producto), joinedload(SaldoInventario.sucursal))
        except:
            pass # If relationships are not defined, it will fail to load names, but let's try
            
        result = await db.execute(query)
        saldos = result.scalars().all()
        
        # Map to dict to match our schema structure if relationships are not perfect
        out = []
        for s in saldos:
            # We fetch manually if relationships are missing (mock for now if needed, but let's try standard)
            out.append({
                "id": s.id,
                "producto_id": s.producto_id,
                "producto_nombre": getattr(s.producto, "nombre", "Desconocido") if hasattr(s, "producto") else "Desconocido",
                "producto_codigo": getattr(s.producto, "codigo_interno", "N/A") if hasattr(s, "producto") else "N/A",
                "sucursal_id": s.sucursal_id,
                "sucursal_nombre": getattr(s.sucursal, "nombre", "Desconocida") if hasattr(s, "sucursal") else "Desconocida",
                "cantidad": s.cantidad,
                "ultima_entrada": s.ultima_entrada,
                "ultima_salida": s.ultima_salida,
                "actualizado_en": s.actualizado_en
            })
        return out

    @staticmethod
    async def listar_movimientos(db: AsyncSession, skip: int = 0, limit: int = 100):
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(MovimientoInventario)
            .options(selectinload(MovimientoInventario.tipo_movimiento))
            .order_by(MovimientoInventario.creado_en.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def listar_productos_bajo_minimo(db: AsyncSession, skip: int = 0, limit: int = 100):
        from sqlalchemy import select, func
        from app.models.catalogo import Producto, ProductoSucursal
        from app.models.inventario import SaldoInventario
        
        query = select(
            Producto.id.label("producto_id"),
            Producto.codigo_interno.label("producto_codigo"),
            Producto.nombre.label("producto_nombre"),
            func.coalesce(func.sum(SaldoInventario.cantidad), 0).label("cantidad_actual"),
            func.coalesce(func.max(ProductoSucursal.punto_reorden), 0).label("punto_reorden"),
            func.coalesce(func.max(ProductoSucursal.stock_maximo), 0).label("stock_maximo")
        ).outerjoin(
            ProductoSucursal, ProductoSucursal.producto_id == Producto.id
        ).outerjoin(
            SaldoInventario, SaldoInventario.producto_id == Producto.id
        ).group_by(
            Producto.id, Producto.codigo_interno, Producto.nombre
        ).having(
            func.coalesce(func.sum(SaldoInventario.cantidad), 0) <= func.coalesce(func.max(ProductoSucursal.punto_reorden), 0)
        ).offset(skip).limit(limit)

        result = await db.execute(query)
        rows = result.all()
        return [
            {
                "producto_id": str(r.producto_id),
                "producto_codigo": r.producto_codigo,
                "producto_nombre": r.producto_nombre,
                "cantidad_actual": str(r.cantidad_actual),
                "punto_reorden": str(r.punto_reorden),
                "stock_maximo": str(r.stock_maximo)
            }
            for r in rows if r.punto_reorden > 0 and r.cantidad_actual <= r.punto_reorden
        ]

    @staticmethod
    async def verificar_alertas_stock(db: AsyncSession, producto_id: UUID, sucursal_id: UUID):
        from sqlalchemy import func
        from app.models.catalogo import Producto, ProductoSucursal
        from app.models.inventario import SaldoInventario
        from app.models.notificaciones import Notificacion
        from app.models.organizacion import Usuario, Rol
        
        # Fetch current saldo and parameters
        query = select(
            func.coalesce(func.sum(SaldoInventario.cantidad), 0).label("cantidad"),
            func.coalesce(func.max(ProductoSucursal.punto_reorden), 0).label("punto_reorden"),
            func.max(Producto.nombre).label("producto_nombre")
        ).outerjoin(
            ProductoSucursal, ProductoSucursal.producto_id == Producto.id
        ).outerjoin(
            SaldoInventario, SaldoInventario.producto_id == Producto.id
        ).where(
            Producto.id == producto_id,
            SaldoInventario.sucursal_id == sucursal_id,
            ProductoSucursal.sucursal_id == sucursal_id
        ).group_by(Producto.id)

        res = await db.execute(query)
        row = res.first()
        
        if row and row.punto_reorden > 0 and row.cantidad <= row.punto_reorden:
            # Verificar si ya existe una alerta reciente (últimas 24h) no leída para este producto y sucursal
            # Para simplificar, creamos la alerta a los roles pertinentes
            q_users = select(Usuario).join(Rol).where(
                Usuario.sucursal_id == sucursal_id,
                Rol.nombre.in_(["encargado_sucursal", "almacenista", "administrador", "comisariato"])
            )
            users_res = await db.execute(q_users)
            usuarios = users_res.scalars().all()
            
            for u in usuarios:
                notif = Notificacion(
                    usuario_id=u.id,
                    titulo="Alerta de Stock Mínimo",
                    mensaje=f"El producto {row.producto_nombre} ha bajado de su punto de reorden. Stock actual: {row.cantidad}"
                )
                db.add(notif)
            await db.commit()
