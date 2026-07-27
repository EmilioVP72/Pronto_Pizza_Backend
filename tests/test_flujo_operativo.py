import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from uuid import uuid4, UUID
from datetime import datetime, timezone
from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida
from app.models.organizacion import Empresa, Sucursal
from app.models.despachos import TipoDocumentoSalida, Despacho
from app.models.inventario import TipoMovimiento, MovimientoInventario
from app.models.contabilidad import ExportacionContpaqi

@pytest.fixture
async def test_data_flujo(db_session: AsyncSession, auth_data: dict):
    matriz_emp = auth_data["empresa"]
    matriz_suc = auth_data["sucursal"] # Comisariato
    
    # 1. Crear Sucursal Héroes (Misma empresa)
    heroes_suc = Sucursal(empresa_id=matriz_emp.id, nombre="Héroes", codigo="HER", es_comisariato=False)
    db_session.add(heroes_suc)
    
    # 2. Crear Empresa Franquicia y Sucursal Externa
    franq_emp = Empresa(razon_social="Franquicia 1", rfc="FRA101010AAA", es_matriz=False)
    db_session.add(franq_emp)
    await db_session.flush()
    
    externa_suc = Sucursal(empresa_id=franq_emp.id, nombre="San Luis Rey", codigo="SLR", es_comisariato=False)
    db_session.add(externa_suc)
    
    # 3. Tipos Documento y Movimiento
    tipo_doc_nt = TipoDocumentoSalida(codigo="NOTA_TRASLADO", nombre="Nota de Traslado")
    tipo_doc_fac = TipoDocumentoSalida(codigo="FACTURA", nombre="Factura")
    db_session.add(tipo_doc_nt)
    db_session.add(tipo_doc_fac)
    
    tipo_mov = TipoMovimiento(codigo="SAL_REQUISICION", nombre="Salida por Requisicion", direccion="S", afecta_costo=True)
    db_session.add(tipo_mov)
    
    # 4. Producto
    categoria = CategoriaProducto(nombre="Insumos")
    db_session.add(categoria)
    unidad = UnidadMedida(nombre="Kg", abreviatura="kg")
    db_session.add(unidad)
    await db_session.flush()

    producto = Producto(
        categoria_id=categoria.id,
        unidad_medida_id=unidad.id,
        codigo_interno="INS-01",
        nombre="Masa Pizza"
    )
    db_session.add(producto)
    await db_session.commit()
    
    return {
        "heroes": heroes_suc,
        "externa": externa_suc,
        "producto": producto,
        "comisariato": matriz_suc
    }

@pytest.mark.asyncio
async def test_flujo_matriz_nota_traslado(async_client: AsyncClient, auth_data: dict, test_data_flujo: dict, db_session: AsyncSession):
    # Simula el flujo hacia una sucursal de la misma empresa (Matriz -> Héroes)
    token = auth_data["token"]
    heroes = test_data_flujo["heroes"]
    producto = test_data_flujo["producto"]
    
    # 1. Crear Requisición
    res_req = await async_client.post(
        "/api/v1/requisiciones/",
        headers={"Authorization": f"Bearer {token}"},
        json={"detalles": [{"producto_id": str(producto.id), "cantidad_solicitada": "50.0000"}]}
    )
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]
    
    await async_client.patch(f"/api/v1/requisiciones/{req_id}/enviar", headers={"Authorization": f"Bearer {token}"})
    await async_client.patch(f"/api/v1/requisiciones/{req_id}/aprobar", headers={"Authorization": f"Bearer {token}"})
    
    # 2. Crear Despacho hacia Héroes (Misma empresa)
    payload_despacho = {
        "requisicion_id": req_id,
        "sucursal_destino_id": str(heroes.id),
        "notas": "Despacho a Héroes",
        "detalles": [
            {
                "producto_id": str(producto.id),
                "cantidad": "50.0000",
                "costo_unitario": "10.0000"
            }
        ]
    }
    res_desp = await async_client.post(
        "/api/v1/despachos/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_despacho
    )
    assert res_desp.status_code == 201
    despacho_data = res_desp.json()
    despacho_id = despacho_data["id"]
    
    # 3. Validar Validación Legal: Debe ser NOTA_TRASLADO
    db_despacho = await db_session.get(Despacho, UUID(despacho_id))
    tipo_doc = await db_session.get(TipoDocumentoSalida, db_despacho.tipo_documento_id)
    assert tipo_doc.codigo == "NOTA_TRASLADO"
    
    # 4. Completar Despacho y verificar inventario
    res_completar = await async_client.patch(
        f"/api/v1/despachos/{despacho_id}/completar",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_completar.status_code == 200
    
    res_mov = await db_session.execute(select(MovimientoInventario).where(MovimientoInventario.despacho_id == UUID(despacho_id)))
    movimientos = res_mov.scalars().all()
    assert len(movimientos) == 1
    
    # Validamos que el tipo de movimiento sea SAL_REQUISICION
    tipo_mov = await db_session.get(TipoMovimiento, movimientos[0].tipo_movimiento_id)
    assert tipo_mov.codigo == "SAL_REQUISICION"

@pytest.mark.asyncio
async def test_flujo_externa_factura(async_client: AsyncClient, auth_data: dict, test_data_flujo: dict, db_session: AsyncSession):
    # Simula el flujo hacia una sucursal de otra empresa (Matriz -> San Luis Rey)
    token = auth_data["token"]
    externa = test_data_flujo["externa"]
    producto = test_data_flujo["producto"]
    
    # 1. Crear Requisición
    res_req = await async_client.post(
        "/api/v1/requisiciones/",
        headers={"Authorization": f"Bearer {token}"},
        json={"detalles": [{"producto_id": str(producto.id), "cantidad_solicitada": "30.0000"}]}
    )
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]
    
    await async_client.patch(f"/api/v1/requisiciones/{req_id}/enviar", headers={"Authorization": f"Bearer {token}"})
    await async_client.patch(f"/api/v1/requisiciones/{req_id}/aprobar", headers={"Authorization": f"Bearer {token}"})
    
    # 2. Crear Despacho hacia Externa (Franquicia)
    payload_despacho = {
        "requisicion_id": req_id,
        "sucursal_destino_id": str(externa.id),
        "notas": "Despacho a San Luis Rey",
        "detalles": [
            {
                "producto_id": str(producto.id),
                "cantidad": "30.0000",
                "costo_unitario": "12.0000"
            }
        ]
    }
    res_desp = await async_client.post(
        "/api/v1/despachos/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_despacho
    )
    assert res_desp.status_code == 201
    despacho_id = res_desp.json()["id"]
    
    # 3. Validar Validación Legal: Debe ser FACTURA
    db_despacho = await db_session.get(Despacho, UUID(despacho_id))
    tipo_doc = await db_session.get(TipoDocumentoSalida, db_despacho.tipo_documento_id)
    assert tipo_doc.codigo == "FACTURA"
    
    # 4. Completar
    res_completar = await async_client.patch(
        f"/api/v1/despachos/{despacho_id}/completar",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_completar.status_code == 200
    
    res_mov = await db_session.execute(select(MovimientoInventario).where(MovimientoInventario.despacho_id == UUID(despacho_id)))
    movimientos = res_mov.scalars().all()
    assert len(movimientos) == 1

@pytest.mark.asyncio
async def test_sincronizacion_contable(async_client: AsyncClient, auth_data: dict, test_data_flujo: dict):
    token = auth_data["token"]
    externa = test_data_flujo["externa"]
    producto = test_data_flujo["producto"]
    
    # 1. Crear Requisición y Despacho para tener datos
    res_req = await async_client.post(
        "/api/v1/requisiciones/",
        headers={"Authorization": f"Bearer {token}"},
        json={"detalles": [{"producto_id": str(producto.id), "cantidad_solicitada": "10.00"}]}
    )
    req_id = res_req.json()["id"]
    await async_client.patch(f"/api/v1/requisiciones/{req_id}/enviar", headers={"Authorization": f"Bearer {token}"})
    await async_client.patch(f"/api/v1/requisiciones/{req_id}/aprobar", headers={"Authorization": f"Bearer {token}"})
    
    payload_despacho = {
        "requisicion_id": req_id,
        "sucursal_destino_id": str(externa.id),
        "notas": "Despacho",
        "detalles": [
            {"producto_id": str(producto.id), "cantidad": "10.00", "costo_unitario": "12.00"}
        ]
    }
    res_desp = await async_client.post(
        "/api/v1/despachos/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload_despacho
    )
    despacho_id = res_desp.json()["id"]
    await async_client.patch(f"/api/v1/despachos/{despacho_id}/completar", headers={"Authorization": f"Bearer {token}"})

    # Ejecutamos la exportación contable
    payload = {
        "periodo_inicio": "2020-01-01",
        "periodo_fin": "2030-12-31",
        "notas": "Exportacion de prueba E2E"
    }
    res_export = await async_client.post(
        "/api/v1/contabilidad/exportar",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert res_export.status_code == 201
    data = res_export.json()
    assert data["estatus"] == "generada"
    assert data["total_registros"] > 0
