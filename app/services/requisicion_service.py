from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime

from app.models.requisiciones import Requisicion, RequisicionDetalle
from app.models.organizacion import Usuario
from app.schemas.requisiciones import RequisicionCreate

class RequisicionService:

    @staticmethod
    async def listar(db: AsyncSession, current_user: Usuario) -> list[Requisicion]:
        result = await db.execute(
            select(Requisicion)
            .options(selectinload(Requisicion.detalles))
            .order_by(Requisicion.creado_en.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def obtener_por_id(db: AsyncSession, requisicion_id: UUID) -> Requisicion:
        result = await db.execute(
            select(Requisicion)
            .options(selectinload(Requisicion.detalles))
            .where(Requisicion.id == requisicion_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def crear(
        db: AsyncSession,
        data: RequisicionCreate,
        current_user: Usuario,
    ) -> Requisicion:
        # El folio real se genera por un trigger en BD. Asignamos un placeholder o None
        requisicion = Requisicion(
            sucursal_id=current_user.sucursal_id,
            folio="", # El trigger `trg_folio_requisicion` llenará esto antes del INSERT
            estatus="borrador",
            creado_por_id=current_user.id,
            fecha_requerida=data.fecha_requerida,
            notas=data.notas
        )
        db.add(requisicion)
        await db.flush() # Para obtener el ID de la requisición

        for det in data.detalles:
            detalle = RequisicionDetalle(
                requisicion_id=requisicion.id,
                producto_id=det.producto_id,
                cantidad_solicitada=det.cantidad_solicitada,
                notas=det.notas
            )
            db.add(detalle)
        from app.services.bitacora_service import BitacoraService
        await BitacoraService.registrar_accion(
            db=db,
            usuario_id=current_user.id,
            modulo="Requisiciones",
            accion="CREAR_REQUISICION",
            detalles={"requisicion_id": str(requisicion.id), "cantidad_productos": len(data.detalles)}
        )
        
        await db.commit()
        
        result_req = await db.execute(
            select(Requisicion)
            .options(selectinload(Requisicion.detalles))
            .where(Requisicion.id == requisicion.id)
        )
        return result_req.scalar_one()

    @staticmethod
    async def transicionar_estado(
        db: AsyncSession,
        requisicion_id: UUID,
        nuevo_estatus: str,
        current_user: Usuario
    ) -> Requisicion:
        result = await db.execute(
            select(Requisicion)
            .options(selectinload(Requisicion.detalles))
            .where(Requisicion.id == requisicion_id)
        )
        requisicion = result.scalar_one_or_none()
        if not requisicion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requisición no encontrada")

        estatus_actual = requisicion.estatus
        if estatus_actual == nuevo_estatus:
            return requisicion
            
        rol = current_user.rol.nombre

        # Validaciones de transición permitida
        transiciones_validas = {
            "borrador": {"enviada": ["encargado_sucursal", "almacenista", "administrador"]},
            "enviada": {
                "aprobada": ["almacenista", "administrador"],
                "rechazada": ["almacenista", "administrador"]
            },
            "aprobada": {
                "surtida": ["almacenista", "administrador"],
                "rechazada": ["almacenista", "administrador"]
            },
            "surtida": {"cerrada": ["encargado_sucursal", "administrador"]}
        }

        if estatus_actual not in transiciones_validas or nuevo_estatus not in transiciones_validas[estatus_actual]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No se puede transicionar de '{estatus_actual}' a '{nuevo_estatus}'")

        roles_permitidos = transiciones_validas[estatus_actual][nuevo_estatus]
        if rol not in roles_permitidos:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para realizar esta acción")

        requisicion.estatus = nuevo_estatus
        
        if nuevo_estatus == "aprobada":
            from datetime import timezone
            requisicion.aprobado_por_id = current_user.id
            requisicion.fecha_aprobacion = datetime.now(timezone.utc)
            
        from app.services.bitacora_service import BitacoraService
        await BitacoraService.registrar_accion(
            db=db,
            usuario_id=current_user.id,
            modulo="Requisiciones",
            accion=f"TRANSICION_{nuevo_estatus.upper()}",
            detalles={"requisicion_id": str(requisicion.id), "folio": requisicion.folio}
        )

        if nuevo_estatus == "surtida":
            from app.schemas.despachos import DespachoCreate, DespachoDetalleBase
            from app.services.despacho_service import DespachoService
            
            detalles_despacho = []
            for det in requisicion.detalles:
                cantidad = det.cantidad_aprobada if det.cantidad_aprobada is not None else det.cantidad_solicitada
                detalles_despacho.append(DespachoDetalleBase(
                    producto_id=det.producto_id,
                    lote_id=None,
                    cantidad=cantidad,
                    costo_unitario=None,
                    notas="Autogenerado desde requisición"
                ))
                
            despacho_data = DespachoCreate(
                requisicion_id=requisicion.id,
                sucursal_destino_id=requisicion.sucursal_id,
                notas=f"Despacho automático para requisición {requisicion.folio}",
                detalles=detalles_despacho
            )
            
            # This calls commit internally
            await DespachoService.crear(db, despacho_data, current_user)
        else:
            await db.commit()
        
        result_req = await db.execute(
            select(Requisicion)
            .options(selectinload(Requisicion.detalles))
            .where(Requisicion.id == requisicion.id)
        )
        return result_req.scalar_one()
