from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from jose import JWTError, jwt
from uuid import UUID

from app.core.config import settings
from app.core.database import get_db
from app.models.organizacion import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    if token.startswith("dummy-dev-token") and settings.app_env == "development":
        email = "admin@prontopizza.com"
        if "|" in token:
            email = token.split("|")[1]
            
        result = await db.execute(
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.sucursal))
            .where(Usuario.email == email)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bypass fallido: admin no encontrado")

    try:
        payload = jwt.decode(
            token, 
            settings.supabase_jwt_secret, 
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        auth_user_id: str | None = payload.get("sub")
        if auth_user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: falta sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

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
