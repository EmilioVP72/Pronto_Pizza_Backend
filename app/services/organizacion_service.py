from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.organizacion import Empresa, Sucursal, Rol, Usuario
from app.schemas.organizacion import UsuarioCreate, UsuarioUpdate, SucursalCreate, SucursalUpdate, RolCreate, RolUpdate
from fastapi import HTTPException, status
from supabase import create_client, Client
from app.core.config import settings
import uuid
class OrganizacionService:

    @staticmethod
    async def listar_empresas(db: AsyncSession) -> list[Empresa]:
        result = await db.execute(select(Empresa).where(Empresa.activo == True))
        return list(result.scalars().all())

    @staticmethod
    async def listar_sucursales(db: AsyncSession) -> list[Sucursal]:
        result = await db.execute(select(Sucursal).where(Sucursal.activo == True))
        return list(result.scalars().all())

    @staticmethod
    async def crear_sucursal(db: AsyncSession, data: SucursalCreate) -> Sucursal:
        nueva_sucursal = Sucursal(**data.model_dump())
        db.add(nueva_sucursal)
        await db.commit()
        await db.refresh(nueva_sucursal)
        return nueva_sucursal

    @staticmethod
    async def actualizar_sucursal(db: AsyncSession, sucursal_id: uuid.UUID, data: SucursalUpdate) -> Sucursal:
        result = await db.execute(select(Sucursal).where(Sucursal.id == sucursal_id))
        sucursal = result.scalar_one_or_none()
        if not sucursal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
            
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(sucursal, key, value)
            
        await db.commit()
        await db.refresh(sucursal)
        return sucursal

    @staticmethod
    async def eliminar_sucursal(db: AsyncSession, sucursal_id: uuid.UUID):
        result = await db.execute(select(Sucursal).where(Sucursal.id == sucursal_id))
        sucursal = result.scalar_one_or_none()
        if not sucursal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
            
        sucursal.activo = False
        await db.commit()
        return {"detail": "Sucursal eliminada (soft delete)"}

    @staticmethod
    async def listar_roles(db: AsyncSession) -> list[Rol]:
        result = await db.execute(select(Rol))
        return list(result.scalars().all())

    @staticmethod
    async def crear_rol(db: AsyncSession, data: RolCreate) -> Rol:
        nuevo_rol = Rol(**data.model_dump())
        db.add(nuevo_rol)
        await db.commit()
        await db.refresh(nuevo_rol)
        return nuevo_rol

    @staticmethod
    async def actualizar_rol(db: AsyncSession, rol_id: int, data: RolUpdate) -> Rol:
        result = await db.execute(select(Rol).where(Rol.id == rol_id))
        rol = result.scalar_one_or_none()
        if not rol:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
            
        CORE_ROLES = ["administrador", "encargado_sucursal", "almacenista"]
        if rol.nombre in CORE_ROLES and data.nombre and data.nombre != rol.nombre:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede cambiar el nombre de un rol base del sistema")
            
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rol, key, value)
            
        await db.commit()
        await db.refresh(rol)
        return rol

    @staticmethod
    async def eliminar_rol(db: AsyncSession, rol_id: int):
        result = await db.execute(select(Rol).where(Rol.id == rol_id))
        rol = result.scalar_one_or_none()
        if not rol:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
            
        CORE_ROLES = ["administrador", "encargado_sucursal", "almacenista"]
        if rol.nombre in CORE_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede eliminar un rol base del sistema")
            
        await db.delete(rol)
        await db.commit()
        return {"detail": "Rol eliminado"}

    @staticmethod
    async def listar_usuarios(db: AsyncSession) -> list[Usuario]:
        result = await db.execute(
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.sucursal))
            .where(Usuario.activo == True)
            .order_by(Usuario.creado_en.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def crear_usuario(db: AsyncSession, data: UsuarioCreate) -> Usuario:
        if not settings.supabase_service_role_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SUPABASE_SERVICE_ROLE_KEY no está configurada")
        
        supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        
        try:
            auth_response = supabase.auth.admin.create_user({
                "email": data.email,
                "password": data.password,
                "email_confirm": True
            })
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error creando usuario en Supabase: {str(e)}")
        
        user_id = auth_response.user.id
        
        nuevo_usuario = Usuario(
            auth_user_id=uuid.UUID(user_id),
            nombre_completo=data.nombre_completo,
            email=data.email,
            rol_id=data.rol_id,
            sucursal_id=data.sucursal_id
        )
        db.add(nuevo_usuario)
        await db.commit()
        await db.refresh(nuevo_usuario)
        
        result = await db.execute(
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.sucursal))
            .where(Usuario.id == nuevo_usuario.id)
        )
        return result.scalar_one()

    @staticmethod
    async def actualizar_usuario(db: AsyncSession, usuario_id: uuid.UUID, data: UsuarioUpdate) -> Usuario:
        if not settings.supabase_service_role_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SUPABASE_SERVICE_ROLE_KEY no configurada")
        
        result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()
        
        if not usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
            
        # Update Supabase if email or password provided
        if data.email or data.password:
            supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
            update_data = {}
            if data.email: update_data["email"] = data.email
            if data.password: update_data["password"] = data.password
            try:
                supabase.auth.admin.update_user_by_id(
                    str(usuario.auth_user_id),
                    update_data
                )
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error actualizando en Supabase: {str(e)}")
                
        # Update local DB
        if data.nombre_completo: usuario.nombre_completo = data.nombre_completo
        if data.email: usuario.email = data.email
        if data.rol_id: usuario.rol_id = data.rol_id
        if data.sucursal_id: usuario.sucursal_id = data.sucursal_id
        
        await db.commit()
        await db.refresh(usuario)
        
        # Reload to get relationships
        result = await db.execute(
            select(Usuario)
            .options(selectinload(Usuario.rol), selectinload(Usuario.sucursal))
            .where(Usuario.id == usuario_id)
        )
        return result.scalar_one()

    @staticmethod
    async def eliminar_usuario(db: AsyncSession, usuario_id: uuid.UUID):
        if not settings.supabase_service_role_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SUPABASE_SERVICE_ROLE_KEY no configurada")
            
        result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()
        
        if not usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
            
        # Delete from Supabase Auth
        supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        try:
            supabase.auth.admin.delete_user(str(usuario.auth_user_id))
        except Exception as e:
            # If it fails, maybe it was already deleted, but we shouldn't fail local deletion.
            print(f"Error borrando de Supabase: {str(e)}")
            
        # Soft delete in local DB
        usuario.activo = False
        await db.commit()
        return {"detail": "Usuario eliminado exitosamente"}
