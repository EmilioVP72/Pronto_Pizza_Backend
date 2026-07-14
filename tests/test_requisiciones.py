import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from uuid import uuid4

from app.models.catalogo import Producto, CategoriaProducto, UnidadMedida
from app.models.organizacion import Rol, Usuario

@pytest.fixture
async def test_data_requisiciones(db_session: AsyncSession, auth_data: dict):
    # Crear producto
    categoria = CategoriaProducto(nombre="Insumos Req")
    db_session.add(categoria)
    unidad = UnidadMedida(nombre="Pieza Req", abreviatura="pzr")
    db_session.add(unidad)
    await db_session.flush()

    producto = Producto(
        categoria_id=categoria.id,
        unidad_medida_id=unidad.id,
        codigo_interno="REQ-01",
        nombre="Producto Req Test"
    )
    db_session.add(producto)
    await db_session.commit()
    return {"producto": producto}

@pytest.mark.asyncio
async def test_crear_requisicion_success(async_client: AsyncClient, auth_data: dict, test_data_requisiciones: dict):
    token = auth_data["token"]
    producto = test_data_requisiciones["producto"]
    
    payload = {
        "notas": "Requisicion urgente",
        "detalles": [
            {
                "producto_id": str(producto.id),
                "cantidad_solicitada": "5.0000",
                "notas": "Por favor enviar rápido"
            }
        ]
    }
    
    response = await async_client.post(
        "/api/v1/requisiciones/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["estatus"] == "borrador"
    assert len(data["detalles"]) == 1

@pytest.mark.asyncio
async def test_transicionar_requisicion_flujo_feliz(async_client: AsyncClient, auth_data: dict, test_data_requisiciones: dict):
    token = auth_data["token"]
    producto = test_data_requisiciones["producto"]
    
    # 1. Crear
    res_crear = await async_client.post(
        "/api/v1/requisiciones/",
        headers={"Authorization": f"Bearer {token}"},
        json={"detalles": [{"producto_id": str(producto.id), "cantidad_solicitada": "5.0000"}]}
    )
    req_id = res_crear.json()["id"]

    # 2. Enviar
    res_enviar = await async_client.patch(
        f"/api/v1/requisiciones/{req_id}/enviar",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_enviar.status_code == 200
    assert res_enviar.json()["estatus"] == "enviada"

    # 3. Aprobar
    res_aprobar = await async_client.patch(
        f"/api/v1/requisiciones/{req_id}/aprobar",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_aprobar.status_code == 200
    assert res_aprobar.json()["estatus"] == "aprobada"

@pytest.mark.asyncio
async def test_transicionar_invalida(async_client: AsyncClient, auth_data: dict, test_data_requisiciones: dict):
    token = auth_data["token"]
    producto = test_data_requisiciones["producto"]
    
    # Crear en borrador
    res_crear = await async_client.post(
        "/api/v1/requisiciones/",
        headers={"Authorization": f"Bearer {token}"},
        json={"detalles": [{"producto_id": str(producto.id), "cantidad_solicitada": "5.0000"}]}
    )
    req_id = res_crear.json()["id"]

    # Intentar aprobar directo desde borrador (debe fallar)
    res_aprobar = await async_client.patch(
        f"/api/v1/requisiciones/{req_id}/aprobar",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_aprobar.status_code == 400
    assert "No se puede transicionar de 'borrador' a 'aprobada'" in res_aprobar.json()["detail"]
