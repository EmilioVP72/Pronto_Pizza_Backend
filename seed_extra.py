import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from decimal import Decimal
from app.core.database import SessionLocal
from app.models.catalogo import Producto, ProductoSucursal, CategoriaProducto, UnidadMedida
from app.models.organizacion import Usuario, Sucursal
from app.models.produccion import OrdenProduccion, Receta, RecetaIngrediente
from app.models.inventario import SaldoInventario

async def run_seed():
    async with SessionLocal() as db:
        # Get references
        sucursal = (await db.execute(select(Sucursal).limit(1))).scalars().first()
        admin = (await db.execute(select(Usuario).where(Usuario.email == "admin@prontopizza.com"))).scalars().first()
        
        # Ensure we have a product
        harina = (await db.execute(select(Producto).where(Producto.nombre == "Harina"))).scalars().first()
        if not harina:
            # create it
            cat = (await db.execute(select(CategoriaProducto).limit(1))).scalars().first()
            um = (await db.execute(select(UnidadMedida).limit(1))).scalars().first()
            harina = Producto(categoria_id=cat.id, unidad_medida_id=um.id, codigo_interno="INS-001", nombre="Harina")
            db.add(harina)
            await db.commit()
            await db.refresh(harina)
            
        # 1. Configurar Producto Sucursal para Bajo Minimo
        ps = (await db.execute(select(ProductoSucursal).where(ProductoSucursal.producto_id == harina.id))).scalars().first()
        if not ps:
            ps = ProductoSucursal(producto_id=harina.id, sucursal_id=sucursal.id, stock_minimo=Decimal("10"), stock_maximo=Decimal("100"), punto_reorden=Decimal("50"))
            db.add(ps)
        else:
            ps.punto_reorden = Decimal("50")
            
        # Asegurar Saldo actual menor al punto de reorden
        saldo = (await db.execute(select(SaldoInventario).where(SaldoInventario.producto_id == harina.id))).scalars().first()
        if not saldo:
            saldo = SaldoInventario(sucursal_id=sucursal.id, producto_id=harina.id, cantidad=Decimal("5"))
            db.add(saldo)
        else:
            saldo.cantidad = Decimal("5")
            
        # 2. Configurar Orden Producción
        receta = (await db.execute(select(Receta).where(Receta.nombre == "Masa de Pizza"))).scalars().first()
        if not receta:
            receta = Receta(producto_id=harina.id, nombre="Masa de Pizza", rendimiento=Decimal("1"), unidad_medida_id=1)
            db.add(receta)
            await db.flush()
            db.add(RecetaIngrediente(receta_id=receta.id, insumo_id=harina.id, cantidad=Decimal("0.5"), unidad_medida_id=1))
            await db.commit()
            await db.refresh(receta)
            
        orden = (await db.execute(select(OrdenProduccion).limit(1))).scalars().first()
        if not orden:
            orden = OrdenProduccion(receta_id=receta.id, sucursal_id=sucursal.id, folio="OP-TEST-001", tandas=Decimal("1"), estatus="programada", notas="Orden generada automaticamente")
            db.add(orden)
            
        await db.commit()
        print("Datos Sembrados!")

if __name__ == "__main__":
    asyncio.run(run_seed())
