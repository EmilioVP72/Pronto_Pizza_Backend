import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from app.main import app
from app.core.security import get_current_user, require_role
from app.schemas.organizacion import UsuarioRead
from app.models.organizacion import Usuario

# Dummy routers para testing
test_router = APIRouter(prefix="/test")

@test_router.get("/me", response_model=UsuarioRead)
async def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user

@test_router.get("/admin-only", response_model=dict)
async def get_admin_only(current_user: Usuario = Depends(require_role("administrador"))):
    return {"message": "Admin area"}

@test_router.get("/almacenista-only", response_model=dict)
async def get_almacenista_only(current_user: Usuario = Depends(require_role("almacenista"))):
    return {"message": "Almacenista area"}

app.include_router(test_router)

@pytest.mark.asyncio
async def test_get_current_user_success(async_client: AsyncClient, auth_data: dict):
    token = auth_data["token"]
    response = await async_client.get("/test/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["rol"]["nombre"] == "administrador"
    assert data["sucursal"]["codigo"] == "MTZ"

@pytest.mark.asyncio
async def test_require_role_success(async_client: AsyncClient, auth_data: dict):
    token = auth_data["token"]
    response = await async_client.get("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Admin area"}

@pytest.mark.asyncio
async def test_require_role_forbidden(async_client: AsyncClient, auth_data: dict):
    token = auth_data["token"]
    # Admin tries to access almacenista route
    response = await async_client.get("/test/almacenista-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Permisos insuficientes"

@pytest.mark.asyncio
async def test_invalid_token(async_client: AsyncClient):
    response = await async_client.get("/test/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
    assert "Token inválido" in response.json()["detail"]
