from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    rfc: Mapped[str] = mapped_column(String(13), nullable=False, unique=True)
    direccion_fiscal: Mapped[str | None] = mapped_column(Text)
    es_matriz: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sucursales = relationship("Sucursal", back_populates="empresa")

class Sucursal(Base):
    __tablename__ = "sucursales"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    direccion: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(String(20))
    es_comisariato: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    empresa = relationship("Empresa", back_populates="sucursales")
    usuarios = relationship("Usuario", back_populates="sucursal")

class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)

    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursales.id"), nullable=False, index=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    auth_user_id: Mapped[UUID | None] = mapped_column(unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sucursal = relationship("Sucursal", back_populates="usuarios")
    rol = relationship("Rol", back_populates="usuarios")
