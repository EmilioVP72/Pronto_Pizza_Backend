from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from decimal import Decimal
from fastapi import HTTPException, status

from app.models.contabilidad import ExportacionContpaqi, LineaContpaqi
from app.models.despachos import Despacho, DespachoDetalle
from app.models.organizacion import Usuario
from app.schemas.contabilidad import ExportacionCreate

class ContabilidadService:
    @staticmethod
    async def generar_exportacion(db: AsyncSession, data: ExportacionCreate, current_user: Usuario):
        # Crear el registro de exportación
        exportacion = ExportacionContpaqi(
            periodo_inicio=data.periodo_inicio,
            periodo_fin=data.periodo_fin,
            notas=data.notas,
            generado_por_id=current_user.id
        )
        db.add(exportacion)
        await db.commit()
        await db.refresh(exportacion)

        # Buscar despachos en el periodo con sus detalles y productos cargados
        query = (
            select(Despacho)
            .options(
                selectinload(Despacho.detalles).selectinload(DespachoDetalle.producto)
            )
            .where(
                func.date(Despacho.fecha_despacho) >= data.periodo_inicio,
                func.date(Despacho.fecha_despacho) <= data.periodo_fin,
                Despacho.estatus == "completado"
            )
        )
        result = await db.execute(query)
        despachos = result.scalars().all()

        lineas = []
        for d in despachos:
            folio = d.folio_documento or str(d.id)[:8]
            if d.detalles:
                for det in d.detalles:
                    prod = det.producto
                    # Determinar el precio o costo unitario
                    costo = float(det.costo_unitario or (prod.precio_referencia if prod else None) or 25.0)
                    importe_total = float(det.cantidad) * costo
                    cuenta = (prod.clave_contpaqi if prod and prod.clave_contpaqi else "1150-001-000")

                    linea = LineaContpaqi(
                        exportacion_id=exportacion.id,
                        despacho_id=d.id,
                        cuenta_contable=cuenta,
                        concepto=f"Despacho {folio} - {prod.nombre if prod else 'Insumo'}",
                        referencia=folio,
                        importe=round(importe_total, 2),
                        tipo_poliza="DIARIO"
                    )
                    lineas.append(linea)
            else:
                # Si el despacho no tiene detalles registrados
                linea = LineaContpaqi(
                    exportacion_id=exportacion.id,
                    despacho_id=d.id,
                    cuenta_contable="1150-001-000",
                    concepto=f"Despacho {folio} (Sin detalle)",
                    referencia=folio,
                    importe=0.0,
                    tipo_poliza="DIARIO"
                )
                lineas.append(linea)

        if lineas:
            db.add_all(lineas)
            exportacion.total_registros = len(lineas)
            exportacion.estatus = "generada"
            exportacion.archivo_nombre = f"CONTPAQI_{data.periodo_inicio}_{data.periodo_fin}.txt"
        else:
            exportacion.total_registros = 0
            exportacion.estatus = "sin_registros"
            exportacion.archivo_nombre = f"CONTPAQI_{data.periodo_inicio}_{data.periodo_fin}_VACIO.txt"

        await db.commit()
        await db.refresh(exportacion)
        return exportacion

    @staticmethod
    async def listar_exportaciones(db: AsyncSession):
        result = await db.execute(select(ExportacionContpaqi).order_by(ExportacionContpaqi.creado_en.desc()))
        return result.scalars().all()

    @staticmethod
    async def descargar_exportacion(db: AsyncSession, exportacion_id: str):
        result = await db.execute(select(LineaContpaqi).where(LineaContpaqi.exportacion_id == exportacion_id))
        lineas = result.scalars().all()
        
        # Formato plano de CONTPAQi: TIPO_POLIZA,FECHA,CUENTA_CONTABLE,REFERENCIA,CONCEPTO,IMPORTE
        content = "TIPO_POLIZA,FECHA,CUENTA_CONTABLE,REFERENCIA,CONCEPTO,IMPORTE\n"
        for L in lineas:
            fecha_str = L.creado_en.strftime("%Y-%m-%d") if L.creado_en else ""
            content += f"{L.tipo_poliza},{fecha_str},{L.cuenta_contable},{L.referencia},{L.concepto},{float(L.importe):.2f}\n"
        
        return content
