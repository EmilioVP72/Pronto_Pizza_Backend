from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
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

        # Buscar despachos en el periodo
        query = select(Despacho).where(
            func.date(Despacho.fecha_despacho) >= data.periodo_inicio,
            func.date(Despacho.fecha_despacho) <= data.periodo_fin,
            Despacho.estatus == "completado"
        )
        result = await db.execute(query)
        despachos = result.scalars().all()

        lineas = []
        # Generar líneas de ejemplo
        for d in despachos:
            linea = LineaContpaqi(
                exportacion_id=exportacion.id,
                despacho_id=d.id,
                cuenta_contable="1150-001-000", # Cuenta ejemplo
                concepto=f"Despacho {d.folio_documento}",
                referencia=d.folio_documento,
                importe=0.0, # Aqui se sumaría el costo
                tipo_poliza="DIARIO"
            )
            lineas.append(linea)

        if lineas:
            db.add_all(lineas)
            exportacion.total_registros = len(lineas)
            exportacion.estatus = "generada"
            exportacion.archivo_nombre = f"CONTPAQI_{data.periodo_inicio}_{data.periodo_fin}.txt"
            await db.commit()

        return exportacion

    @staticmethod
    async def listar_exportaciones(db: AsyncSession):
        result = await db.execute(select(ExportacionContpaqi).order_by(ExportacionContpaqi.creado_en.desc()))
        return result.scalars().all()

    @staticmethod
    async def descargar_exportacion(db: AsyncSession, exportacion_id: str):
        result = await db.execute(select(LineaContpaqi).where(LineaContpaqi.exportacion_id == exportacion_id))
        lineas = result.scalars().all()
        
        # Formato plano de contpaqi (ejemplo simplificado)
        content = ""
        for L in lineas:
            content += f"{L.tipo_poliza},{L.cuenta_contable},{L.referencia},{L.concepto},{L.importe}\n"
        
        return content
