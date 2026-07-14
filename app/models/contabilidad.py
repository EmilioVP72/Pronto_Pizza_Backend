from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, Date, Integer, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

class ExportacionContpaqi(Base):
    __tablename__ = "exportaciones_contpaqi"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fin: Mapped[date] = mapped_column(Date, nullable=False)
    estatus: Mapped[str] = mapped_column(String(20), default='pendiente', nullable=False)
    archivo_nombre: Mapped[str | None] = mapped_column(String(200))
    total_registros: Mapped[int | None] = mapped_column(Integer)
    generado_por_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notas: Mapped[str | None] = mapped_column(Text)

    generado_por = relationship("Usuario")
    lineas = relationship("LineaContpaqi", back_populates="exportacion")

class LineaContpaqi(Base):
    __tablename__ = "lineas_contpaqi"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    exportacion_id: Mapped[UUID] = mapped_column(ForeignKey("exportaciones_contpaqi.id"), nullable=False, index=True)
    movimiento_id: Mapped[UUID | None] = mapped_column(ForeignKey("movimientos_inventario.id"))
    despacho_id: Mapped[UUID | None] = mapped_column(ForeignKey("despachos.id"))
    cuenta_contable: Mapped[str] = mapped_column(String(20), nullable=False)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(50))
    importe: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    tipo_poliza: Mapped[str | None] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    exportacion = relationship("ExportacionContpaqi", back_populates="lineas")
