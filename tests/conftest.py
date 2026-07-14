import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from jose import jwt
import uuid

from app.main import app
from app.core.database import get_db
from app.core.config import settings
from app.models.base import Base
from app.models.organizacion import Empresa, Sucursal, Rol, Usuario

# Base de datos en memoria para pruebas
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest.fixture
async def auth_data(db_session: AsyncSession):
    empresa = Empresa(razon_social="Pronto Pizza Test", rfc="PPT200101XYZ", es_matriz=True)
    db_session.add(empresa)
    await db_session.flush()

    sucursal = Sucursal(empresa_id=empresa.id, nombre="Matriz", codigo="MTZ", es_comisariato=True)
    db_session.add(sucursal)
    
    rol_admin = Rol(nombre="administrador")
    rol_almacenista = Rol(nombre="almacenista")
    db_session.add(rol_admin)
    db_session.add(rol_almacenista)
    await db_session.flush()
    
    auth_user_id = uuid.uuid4()
    admin_user = Usuario(
        sucursal_id=sucursal.id, 
        rol_id=rol_admin.id, 
        nombre_completo="Admin Test", 
        email="admin@test.com", 
        auth_user_id=auth_user_id
    )
    db_session.add(admin_user)
    await db_session.commit()
    
    # Generate token
    token = jwt.encode({"sub": str(auth_user_id)}, settings.supabase_jwt_secret, algorithm="HS256")
    
    return {"user": admin_user, "token": token, "sucursal": sucursal, "empresa": empresa}
