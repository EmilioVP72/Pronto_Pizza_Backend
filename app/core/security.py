from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
import jwt as pyjwt

from app.core.config import settings
from app.core.database import get_db
from app.models.organizacion import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Cache JWKS keys so we don't fetch them on every request
_jwks_client = None

def get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        # Supabase exposes JWKS at /.well-known/jwks.json, NOT at /jwks
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = pyjwt.PyJWKClient(jwks_url, headers={"apikey": settings.supabase_anon_key})
    return _jwks_client


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    if token.startswith("dummy-dev-token") and settings.app_env == "development":
        email = "admin@prontopizza.com"
        
        result = await db.execute(
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.sucursal))
            .where(Usuario.email == email)
        )
        user = result.scalar_one_or_none()
        if user and user.rol.nombre == "administrador":
            return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bypass fallido: admin no encontrado o no es administrador")

    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "HS256"],
            options={"verify_aud": False}
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except pyjwt.PyJWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token inválido: {str(e)}")
    except Exception as e:
        print(f"JWKS Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Error validando token")

    auth_user_id: str | None = payload.get("sub")
    if not auth_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: falta sub")

    try:
        auth_uuid = UUID(auth_user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: sub no es UUID")

    result = await db.execute(
        select(Usuario)
        .options(selectinload(Usuario.rol), selectinload(Usuario.sucursal))
        .where(Usuario.auth_user_id == auth_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")
        
    return user

def require_role(*roles: str):
    async def dependency(current_user: Usuario = Depends(get_current_user)):
        if current_user.rol.nombre not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
        return current_user
    return dependency
