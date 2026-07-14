from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timezone

from app.models.despachos import Despacho, DespachoDetalle, TipoDocumentoSalida
from app.models.organizacion import Sucursal, Usuario
from app.schemas.despachos import DespachoCreate
from app.services.inventario_service import InventarioService
from app.schemas.inventario import MovimientoInventarioBase
from app.services.requisicion_service import RequisicionService

class DespachoService:

    @staticmethod
    async def determinar_tipo_documento(
        db: AsyncSession,
        sucursal_origen_id: UUID,
        sucursal_destino_id: UUID,
    ) -> TipoDocumentoSalida:
        origen = await db.get(Sucursal, sucursal_origen_id)
        destino = await db.get(Sucursal, sucursal_destino_id)
        
        if not origen or not destino:
            raise HTTPException(status_code=404, detail="Sucursal origen o destino no encontrada")
            
        codigo_doc = "NOTA_TRASLADO" if origen.empresa_id == destino.empresa_id else "FACTURA"
        
        result = await db.execute(select(TipoDocumentoSalida).where(TipoDocumentoSalida.codigo == codigo_doc))
        tipo_doc = result.scalar_one_or_none()
        
        if not tipo_doc:
            raise HTTPException(status_code=500, detail=f"Tipo de documento {codigo_doc} no configurado en BD")
            
        return tipo_doc

    @staticmethod
    async def crear(
        db: AsyncSession,
        data: DespachoCreate,
        current_user: Usuario,
    ) -> Despacho:
        # El origen siempre es el comisariato donde está el almacenista
        # (o la sucursal del current_user)
        sucursal_origen_id = current_user.sucursal_id
        
        tipo_doc = await DespachoService.determinar_tipo_documento(db, sucursal_origen_id, data.sucursal_destino_id)
        
        despacho = Despacho(
            requisicion_id=data.requisicion_id,
            sucursal_origen_id=sucursal_origen_id,
            sucursal_destino_id=data.sucursal_destino_id,
            tipo_documento_id=tipo_doc.id,
            estatus="pendiente",
            despachado_por_id=current_user.id,
            notas=data.notas
        )
        db.add(despacho)
        await db.flush()

        for det in data.detalles:
            detalle = DespachoDetalle(
                despacho_id=despacho.id,
                producto_id=det.producto_id,
                lote_id=det.lote_id,
                cantidad=det.cantidad,
                costo_unitario=det.costo_unitario,
                notas=det.notas
            )
            db.add(detalle)
        from app.services.bitacora_service import BitacoraService
        await BitacoraService.registrar_accion(
            db=db,
            usuario_id=current_user.id,
            modulo="Despachos",
            accion="CREAR_DESPACHO",
            detalles={"despacho_id": str(despacho.id)}
        )

        await db.commit()
        
        result_despacho = await db.execute(
            select(Despacho)
            .options(selectinload(Despacho.detalles))
            .where(Despacho.id == despacho.id)
        )
        return result_despacho.scalar_one()

    @staticmethod
    async def listar(db: AsyncSession, current_user: Usuario) -> list[Despacho]:
        result = await db.execute(
            select(Despacho)
            .options(selectinload(Despacho.detalles))
            .order_by(Despacho.creado_en.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def completar_despacho(
        db: AsyncSession,
        despacho_id: UUID,
        current_user: Usuario
    ) -> Despacho:
        despacho = await db.get(Despacho, despacho_id)
        if not despacho:
            raise HTTPException(status_code=404, detail="Despacho no encontrado")
            
        if despacho.estatus != "pendiente" and despacho.estatus != "en_proceso":
            raise HTTPException(status_code=400, detail=f"No se puede completar un despacho en estado {despacho.estatus}")
            
        # Actualizar estado a completado
        despacho.estatus = "completado"
        despacho.fecha_despacho = datetime.now(timezone.utc)
        
        # Para cada detalle del despacho, registrar el movimiento de salida
        # Necesitamos el ID del TipoMovimiento SAL_REQUISICION o salida general
        # En el caso de despachos a sucursales usaremos 'SAL_REQUISICION' o un genérico
        from app.models.inventario import TipoMovimiento
        result = await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == "SAL_REQUISICION"))
        tipo_mov_salida = result.scalar_one_or_none()
        
        if not tipo_mov_salida:
            raise HTTPException(status_code=500, detail="Tipo de movimiento SAL_REQUISICION no configurado")

        # Necesitamos cargar los detalles del despacho
        from sqlalchemy.orm import selectinload
        result_despacho = await db.execute(
            select(Despacho).options(selectinload(Despacho.detalles)).where(Despacho.id == despacho_id)
        )
        despacho_completo = result_despacho.scalar_one()

        for det in despacho_completo.detalles:
            mov_data = MovimientoInventarioBase(
                tipo_movimiento_id=tipo_mov_salida.id,
                producto_id=det.producto_id,
                sucursal_origen_id=despacho_completo.sucursal_origen_id,
                sucursal_destino_id=despacho_completo.sucursal_destino_id,
                lote_id=det.lote_id,
                requisicion_id=despacho_completo.requisicion_id,
                despacho_id=despacho_completo.id,
                cantidad=det.cantidad,
                costo_unitario=det.costo_unitario,
                notas="Salida automática por completar despacho",
                registrado_por_id=current_user.id
            )
            await InventarioService.registrar_movimiento(db, mov_data, current_user)

        # Si hay requisición ligada, actualizar a 'surtida'
        if despacho_completo.requisicion_id:
            await RequisicionService.transicionar_estado(
                db, 
                despacho_completo.requisicion_id, 
                "surtida", 
                current_user
            )
            
        from app.services.bitacora_service import BitacoraService
        await BitacoraService.registrar_accion(
            db=db,
            usuario_id=current_user.id,
            modulo="Despachos",
            accion="COMPLETAR_DESPACHO",
            detalles={"despacho_id": str(despacho_completo.id), "folio": despacho_completo.folio}
        )

        await db.commit()
        
        result_final = await db.execute(
            select(Despacho)
            .options(selectinload(Despacho.detalles))
            .where(Despacho.id == despacho_completo.id)
        )
        return result_final.scalar_one()
