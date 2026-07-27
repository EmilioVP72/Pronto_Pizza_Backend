import asyncio
from sqlalchemy import select
from decimal import Decimal
from datetime import datetime, timezone
import uuid

from app.core.database import SessionLocal
from app.models.inventario import MovimientoInventario, Lote, SaldoInventario, TipoMovimiento
from app.models.despachos import Despacho, TipoDocumentoSalida, DespachoDetalle
from app.models.produccion import OrdenProduccion, Receta
from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida, ProductoSucursal
from app.models.organizacion import Sucursal, Usuario
from app.models.requisiciones import Requisicion, RequisicionDetalle

async def check_and_seed():
    async with SessionLocal() as db:
        # Check current data
        movs = await db.execute(select(MovimientoInventario))
        desps = await db.execute(select(Despacho))
        prods = await db.execute(select(OrdenProduccion))
        reqs = await db.execute(select(Requisicion))
        saldos = await db.execute(select(SaldoInventario))
        
        movs_count = len(movs.scalars().all())
        desps_count = len(desps.scalars().all())
        prods_count = len(prods.scalars().all())
        reqs_count = len(reqs.scalars().all())
        saldos_count = len(saldos.scalars().all())
        
        print(f"Data found: Movimientos={movs_count}, Despachos={desps_count}, Ordenes={prods_count}, Requisiciones={reqs_count}, Saldos={saldos_count}")
        
        if movs_count == 0 and desps_count == 0:
            print("Database operational tables are empty. Seeding some basic data...")
            
            # Fetch base data
            sucursal = (await db.execute(select(Sucursal).limit(1))).scalar_one_or_none()
            sucursal_destino = None
            if sucursal:
                sucursal_destino = (await db.execute(select(Sucursal).where(Sucursal.id != sucursal.id).limit(1))).scalar_one_or_none()
            user = (await db.execute(select(Usuario).limit(1))).scalar_one_or_none()
            producto = (await db.execute(select(Producto).limit(1))).scalar_one_or_none()
            tipo_mov = (await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == 'ENT_COMPRA').limit(1))).scalar_one_or_none()
            tipo_mov_sal = (await db.execute(select(TipoMovimiento).where(TipoMovimiento.codigo == 'SAL_TRASLADO').limit(1))).scalar_one_or_none()
            tipo_doc = (await db.execute(select(TipoDocumentoSalida).limit(1))).scalar_one_or_none()

            if not tipo_mov:
                tipo_mov = TipoMovimiento(codigo='ENT_COMPRA', nombre='Entrada por Compra', direccion='E', afecta_costo=True)
                tipo_mov_sal = TipoMovimiento(codigo='SAL_TRASLADO', nombre='Salida por Traslado', direccion='S', afecta_costo=True)
                db.add_all([tipo_mov, tipo_mov_sal])
                await db.flush()

            if not sucursal:
                from app.models.organizacion import Empresa, Rol
                empresa = Empresa(razon_social='Pronto Pizza Matriz', rfc='PPM123456789', es_matriz=True)
                db.add(empresa)
                await db.flush()
                sucursal = Sucursal(empresa_id=empresa.id, nombre='Matriz', codigo='MTZ', es_comisariato=True)
                sucursal_destino = Sucursal(empresa_id=empresa.id, nombre='Héroes', codigo='HER', es_comisariato=False)
                db.add_all([sucursal, sucursal_destino])
                await db.flush()
                
                rol = Rol(nombre='administrador', descripcion='Admin')
                db.add(rol)
                await db.flush()

                user = Usuario(sucursal_id=sucursal.id, rol_id=rol.id, nombre_completo='Admin', email='admin@prontopizza.com', auth_user_id=uuid.uuid4())
                db.add(user)
                await db.flush()

            if not producto:
                categoria = CategoriaProducto(nombre='Insumos')
                unidad = UnidadMedida(nombre='Kilogramo', abreviatura='kg')
                db.add_all([categoria, unidad])
                await db.flush()
                producto = Producto(categoria_id=categoria.id, unidad_medida_id=unidad.id, unidad_compra_id=unidad.id, factor_conversion=Decimal("1.0"), codigo_interno='INS-001', nombre='Masa Pizza')
                db.add(producto)
                await db.flush()

            if not tipo_doc:
                tipo_doc = TipoDocumentoSalida(codigo='NOTA_TRASLADO', nombre='Nota de Traslado')
                db.add(tipo_doc)
                await db.flush()

            if not sucursal_destino:
                sucursal_destino = sucursal

            # 1. Seed Requisición
            req = Requisicion(
                sucursal_id=sucursal_destino.id,
                folio="REQ-2026-001",
                estatus="aprobada",
                creado_por_id=user.id,
                aprobado_por_id=user.id,
                fecha_requerida=datetime.now(timezone.utc).date()
            )
            db.add(req)
            await db.flush()

            db.add(RequisicionDetalle(
                requisicion_id=req.id,
                producto_id=producto.id,
                cantidad_solicitada=Decimal("150.0")
            ))
            await db.flush()

            # 2. Seed Lote & Entrada
            lote = Lote(
                producto_id=producto.id,
                sucursal_id=sucursal.id,
                numero_lote="LOTE-TEST-2026",
                cantidad_inicial=Decimal("500.0"),
                cantidad_actual=Decimal("350.0"),
                costo_unitario=Decimal("25.0")
            )
            db.add(lote)
            await db.flush()

            db.add(MovimientoInventario(
                tipo_movimiento_id=tipo_mov.id,
                producto_id=producto.id,
                sucursal_destino_id=sucursal.id,
                lote_id=lote.id,
                cantidad=Decimal("500.0"),
                costo_unitario=Decimal("25.0"),
                registrado_por_id=user.id,
                notas="Entrada simulada"
            ))

            # 3. Seed Despacho & Salida
            if tipo_doc:
                desp = Despacho(
                    requisicion_id=req.id,
                    sucursal_origen_id=sucursal.id,
                    sucursal_destino_id=sucursal_destino.id,
                    tipo_documento_id=tipo_doc.id,
                    folio_documento="DESP-2026-001",
                    estatus="completado",
                    despachado_por_id=user.id
                )
                db.add(desp)
                await db.flush()

                db.add(DespachoDetalle(
                    despacho_id=desp.id,
                    producto_id=producto.id,
                    lote_id=lote.id,
                    cantidad=Decimal("150.0"),
                    costo_unitario=Decimal("25.0")
                ))
                
                if tipo_mov_sal:
                    db.add(MovimientoInventario(
                        tipo_movimiento_id=tipo_mov_sal.id,
                        producto_id=producto.id,
                        sucursal_origen_id=sucursal.id,
                        lote_id=lote.id,
                        cantidad=Decimal("150.0"),
                        costo_unitario=Decimal("25.0"),
                        despacho_id=desp.id,
                        registrado_por_id=user.id,
                        notas="Salida por despacho simulado"
                    ))

            await db.commit()
            print("Successfully seeded Requisicion, Lote, Movimiento, Despacho.")
        else:
            print("Operational data already exists. No seeding required.")

if __name__ == "__main__":
    asyncio.run(check_and_seed())
