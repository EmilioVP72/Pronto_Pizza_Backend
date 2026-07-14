import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida
from app.models.despachos import TipoDocumentoSalida
from app.models.inventario import MovimientoInventario, TipoMovimiento

@pytest.fixture
async def test_data_despachos(db_session: AsyncSession, auth_data: dict):
    # Tipos Documento y Movimiento
    tipo_doc = TipoDocumentoSalida(codigo="NOTA_TRASLADO", nombre="Nota de Traslado")
    db_session.add(tipo_doc)
    
    tipo_mov = TipoMovimiento(codigo="SAL_REQUISICION", nombre="Salida por Requisicion", direccion="S", afecta_costo=True)
    db_session.add(tipo_mov)
    
    # Producto
    categoria = CategoriaProducto(nombre="Insumos Despacho")
    db_session.add(categoria)
    unidad = UnidadMedida(nombre="Kg", abreviatura="kg")
    db_session.add(unidad)
    await db_session.flush()

    producto = Producto(
        categoria_id=categoria.id,
        unidad_medida_id=unidad.id,
        codigo_interno="DESP-01",
        nombre="Producto Despacho"
    )
    db_session.add(producto)
    await db_session.commit()
    return {"producto": producto}

@pytest.mark.asyncio
async def test_flujo_completo_despacho(async_client: AsyncClient, auth_data: dict, test_data_despachos: dict, db_session: AsyncSession):
    token = auth_data["token"]
    producto = test_data_despachos["producto"]
    sucursal = auth_data["sucursal"]
    
    # Crear un despacho
    payload = {
        "sucursal_destino_id": str(sucursal.id),
        "notas": "Despacho de prueba",
        "detalles": [
            {
                "producto_id": str(producto.id),
                "cantidad": "20.0000",
                "costo_unitario": "15.5000"
            }
        ]
    }
    
    # 1. POST para crear el despacho en estado pendiente
    res_crear = await async_client.post(
        "/api/v1/despachos/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert res_crear.status_code == 201
    data = res_crear.json()
    assert data["estatus"] == "pendiente"
    despacho_id = data["id"]
    
    # 2. PATCH para completar el despacho
    res_completar = await async_client.patch(
        f"/api/v1/despachos/{despacho_id}/completar",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_completar.status_code == 200
    assert res_completar.json()["estatus"] == "completado"
    
    # 3. Verificar que se creó el movimiento de inventario (ledger inmutable)
    result = await db_session.execute(
        select(MovimientoInventario).where(MovimientoInventario.despacho_id == UUID(despacho_id))
    )
    movimientos = result.scalars().all()
    assert len(movimientos) == 1
    assert movimientos[0].cantidad == Decimal("20.0000")
    assert movimientos[0].costo_unitario == Decimal("15.5000")
    assert movimientos[0].producto_id == producto.id
