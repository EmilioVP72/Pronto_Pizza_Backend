import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from httpx import AsyncClient
from decimal import Decimal
from uuid import UUID


from app.services.inventario_service import InventarioService
from app.schemas.inventario import MovimientoInventarioBase
from app.models.inventario import MovimientoInventario, TipoMovimiento, Lote
from app.models.catalogo import CategoriaProducto, UnidadMedida, Producto
from app.models.organizacion import Usuario, Sucursal, Empresa

@pytest.mark.asyncio
async def test_registrar_movimiento_solo_insert(db_session: AsyncSession, auth_data: dict):
    user = auth_data["user"]
    sucursal = auth_data["sucursal"]
    
    # 1. Preparar datos de catálogo mínimos
    categoria = CategoriaProducto(nombre="Insumo Test")
    db_session.add(categoria)
    unidad = UnidadMedida(nombre="Litro", abreviatura="lt")
    db_session.add(unidad)
    await db_session.flush()

    producto = Producto(
        categoria_id=categoria.id,
        unidad_medida_id=unidad.id,
        codigo_interno="TEST-01",
        nombre="Producto Test"
    )
    db_session.add(producto)
    
    tipo_mov = TipoMovimiento(
        codigo="ENT_COMPRA_TEST",
        nombre="Entrada Compra Test",
        direccion="E",
        afecta_costo=True
    )
    db_session.add(tipo_mov)
    await db_session.flush()
    
    # 2. Configurar el payload
    payload = MovimientoInventarioBase(
        tipo_movimiento_id=tipo_mov.id,
        producto_id=producto.id,
        sucursal_destino_id=sucursal.id,
        cantidad=Decimal("10.0000"),
        costo_unitario=Decimal("5.0000"),
        registrado_por_id=user.id,
        notas="Test de inserción"
    )

    # 3. Registrar el movimiento
    movimiento = await InventarioService.registrar_movimiento(db_session, payload, user)
    
    # 4. Verificar que se insertó correctamente
    assert movimiento.id is not None
    assert movimiento.cantidad == Decimal("10.0000")
    assert movimiento.registrado_por_id == user.id
    
    # Verificar que existe en la BD
    result = await db_session.execute(select(MovimientoInventario).where(MovimientoInventario.id == movimiento.id))
    movimiento_db = result.scalar_one()
    assert movimiento_db.notas == "Test de inserción"

@pytest.fixture
async def test_data_inventario(db_session: AsyncSession):
    categoria = CategoriaProducto(nombre="Insumo Inventario")
    db_session.add(categoria)
    unidad = UnidadMedida(nombre="Litro", abreviatura="lt")
    db_session.add(unidad)
    await db_session.flush()

    producto = Producto(
        categoria_id=categoria.id,
        unidad_medida_id=unidad.id,
        codigo_interno="INV-01",
        nombre="Producto Inventario"
    )
    db_session.add(producto)
    
    # Crear los tipos de movimiento requeridos
    tipos = [
        TipoMovimiento(codigo="ENT_COMPRA", nombre="Entrada por Compra", direccion="E", afecta_costo=True),
        TipoMovimiento(codigo="AJU_POSITIVO", nombre="Ajuste Positivo", direccion="A", afecta_costo=True),
        TipoMovimiento(codigo="AJU_NEGATIVO", nombre="Ajuste Negativo", direccion="A", afecta_costo=True)
    ]
    for tm in tipos:
        db_session.add(tm)
    await db_session.commit()
    
    return {"producto": producto}

@pytest.mark.asyncio
async def test_recepcion_compra_api(async_client: AsyncClient, auth_data: dict, test_data_inventario: dict, db_session: AsyncSession):
    token = auth_data["token"]
    producto = test_data_inventario["producto"]
    sucursal = auth_data["sucursal"]
    
    payload = {
        "sucursal_destino_id": str(sucursal.id),
        "notas": "Factura F-100",
        "detalles": [
            {
                "producto_id": str(producto.id),
                "cantidad": "50.0000",
                "costo_unitario": "12.5000",
                "notas": "Recibido bien"
            }
        ]
    }
    
    res = await async_client.post(
        "/api/v1/inventario/recepciones-compra",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    assert data[0]["cantidad"] == "50.0000"
    
    # Verificar que el lote se generó
    mov_id = data[0]["id"]
    result = await db_session.execute(select(MovimientoInventario).where(MovimientoInventario.id == UUID(mov_id)))
    mov = result.scalar_one()
    assert mov.lote_id is not None
    
    result_lote = await db_session.execute(select(Lote).where(Lote.id == mov.lote_id))
    lote = result_lote.scalar_one()
    assert lote.cantidad_inicial == Decimal("50.0000")
    assert "COMP-" in lote.numero_lote

@pytest.mark.asyncio
async def test_ajuste_inventario_api(async_client: AsyncClient, auth_data: dict, test_data_inventario: dict, db_session: AsyncSession):
    token = auth_data["token"]
    producto = test_data_inventario["producto"]
    sucursal = auth_data["sucursal"]
    
    # Ajuste Positivo
    payload_positivo = {
        "sucursal_id": str(sucursal.id),
        "es_positivo": True,
        "notas": "Sobrante en conteo",
        "detalles": [
            {
                "producto_id": str(producto.id),
                "cantidad": "5.0000",
                "costo_unitario": "12.5000"
            }
        ]
    }
    
    res_pos = await async_client.post(
        "/api/v1/inventario/ajustes",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_positivo
    )
    assert res_pos.status_code == 201
    data_pos = res_pos.json()
    assert data_pos[0]["sucursal_destino_id"] == str(sucursal.id)
    assert data_pos[0]["sucursal_origen_id"] is None
    
    # Ajuste Negativo
    payload_negativo = {
        "sucursal_id": str(sucursal.id),
        "es_positivo": False,
        "notas": "Merma por rotura",
        "detalles": [
            {
                "producto_id": str(producto.id),
                "cantidad": "2.0000",
                "costo_unitario": "12.5000"
            }
        ]
    }
    
    res_neg = await async_client.post(
        "/api/v1/inventario/ajustes",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_negativo
    )
    assert res_neg.status_code == 201
    data_neg = res_neg.json()
    assert data_neg[0]["sucursal_origen_id"] == str(sucursal.id)
    assert data_neg[0]["sucursal_destino_id"] is None

