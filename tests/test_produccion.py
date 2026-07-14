import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from uuid import UUID

from app.models.produccion import Receta, OrdenProduccion
from app.models.inventario import MovimientoInventario, Lote, TipoMovimiento
from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida

@pytest.fixture
async def test_data_produccion(db_session: AsyncSession):
    categoria = CategoriaProducto(nombre="Preparados Test")
    db_session.add(categoria)
    unidad = UnidadMedida(nombre="Kilogramo", abreviatura="kg")
    db_session.add(unidad)
    await db_session.flush()

    insumo = Producto(
        categoria_id=categoria.id,
        unidad_medida_id=unidad.id,
        codigo_interno="INS-01",
        nombre="Harina Test"
    )
    preparado = Producto(
        categoria_id=categoria.id,
        unidad_medida_id=unidad.id,
        codigo_interno="PREP-01",
        nombre="Masa Test"
    )
    db_session.add(insumo)
    db_session.add(preparado)
    
    # Crear tipos de movimiento
    tm_ent = TipoMovimiento(codigo="ENT_PRODUCCION", nombre="Entrada Produccion", direccion="E", afecta_costo=True)
    tm_sal = TipoMovimiento(codigo="SAL_PRODUCCION", nombre="Salida Produccion", direccion="S", afecta_costo=True)
    db_session.add(tm_ent)
    db_session.add(tm_sal)

    await db_session.commit()
    
    return {"insumo": insumo, "preparado": preparado, "unidad": unidad}

@pytest.mark.asyncio
async def test_flujo_produccion_completo(async_client: AsyncClient, auth_data: dict, test_data_produccion: dict, db_session: AsyncSession):
    token = auth_data["token"]
    sucursal = auth_data["sucursal"]
    insumo = test_data_produccion["insumo"]
    preparado = test_data_produccion["preparado"]
    unidad = test_data_produccion["unidad"]
    
    # 1. Crear Receta
    payload_receta = {
        "producto_id": str(preparado.id),
        "nombre": "Receta Masa Especial",
        "rendimiento": "10.0000",
        "unidad_medida_id": unidad.id,
        "ingredientes": [
            {
                "insumo_id": str(insumo.id),
                "cantidad": "5.0000",
                "unidad_medida_id": unidad.id
            }
        ]
    }
    
    res_receta = await async_client.post(
        "/api/v1/produccion/recetas",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_receta
    )
    assert res_receta.status_code == 201
    receta_id = res_receta.json()["id"]
    
    # 2. Crear Orden de Producción (Programar 2 tandas)
    payload_orden = {
        "receta_id": receta_id,
        "sucursal_id": str(sucursal.id),
        "tandas": "2.00"
    }
    
    res_orden = await async_client.post(
        "/api/v1/produccion/ordenes",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_orden
    )
    assert res_orden.status_code == 201
    orden_id = res_orden.json()["id"]
    
    # 3. Completar Orden de Producción
    # La receta dice 10 kg de rendimiento, por 2 tandas = 20 kg
    payload_completar = {
        "cantidad_real": "20.0000"
    }
    
    res_completar = await async_client.patch(
        f"/api/v1/produccion/ordenes/{orden_id}/completar",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_completar
    )
    assert res_completar.status_code == 200, res_completar.text
    orden_completada = res_completar.json()
    assert orden_completada["estatus"] == "completada"
    lote_generado_id = orden_completada["lote_resultado_id"]
    assert lote_generado_id is not None
    
    # 4. Validar Inventarios (Movimientos)
    # Debe haber 1 movimiento de entrada por 20.0 (preparado) y 1 de salida por 10.0 (insumo)
    result_mov = await db_session.execute(select(MovimientoInventario))
    movimientos = result_mov.scalars().all()
    
    # Filtrar solo los movimientos creados por este flujo, descartando otros tests si los hay
    movs_flujo = [m for m in movimientos if m.notas and "automátic" in m.notas.lower()]
    assert len(movs_flujo) == 2
    
    # Salida (consumo de insumos)
    mov_salida = next(m for m in movs_flujo if m.sucursal_destino_id is None)
    assert mov_salida.producto_id == insumo.id
    assert mov_salida.cantidad == Decimal("10.0000") # 5.0 * 2 tandas
    
    # Entrada (producto preparado generado)
    mov_entrada = next(m for m in movs_flujo if m.sucursal_origen_id is None)
    assert mov_entrada.producto_id == preparado.id
    assert mov_entrada.cantidad == Decimal("20.0000")
    
    # 5. Validar que el lote fue insertado correctamente
    result_lote = await db_session.execute(select(Lote).where(Lote.id == UUID(lote_generado_id)))
    lote = result_lote.scalar_one()
    assert lote.producto_id == preparado.id
    assert lote.cantidad_inicial == Decimal("20.0000")
