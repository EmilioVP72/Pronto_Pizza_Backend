from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import require_role
from app.models.organizacion import Usuario
from app.schemas.produccion import (
    RecetaCreate, RecetaRead,
    OrdenProduccionCreate, OrdenProduccionRead, OrdenProduccionCompletar
)
from app.services.produccion_service import ProduccionService

router = APIRouter(prefix="/produccion", tags=["Producción"])

@router.post("/recetas", response_model=RecetaRead, status_code=status.HTTP_201_CREATED)
async def crear_receta(
    data: RecetaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    """
    Crea una receta para un producto procesado.
    """
    return await ProduccionService.crear_receta(db, data, current_user)

@router.get("/recetas", response_model=list[RecetaRead])
async def obtener_recetas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador", "encargado_sucursal", "solo_lectura")),
):
    """
    Lista las recetas disponibles.
    """
    return await ProduccionService.obtener_recetas(db)


from app.api.v1.utils import paginate_response

@router.get("/ordenes", response_model=dict)
async def listar_ordenes(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador", "encargado_sucursal", "solo_lectura")),
):
    items = await ProduccionService.listar_ordenes(db)
    return paginate_response([OrdenProduccionRead.model_validate(i).model_dump(mode="json") for i in items], page, size)


@router.post("/ordenes", response_model=OrdenProduccionRead, status_code=status.HTTP_201_CREATED)
async def crear_orden_produccion(
    data: OrdenProduccionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    """
    Programa una nueva orden de producción en el comisariato.
    """
    return await ProduccionService.crear_orden_produccion(db, data, current_user)


@router.patch("/ordenes/{orden_id}/completar", response_model=OrdenProduccionRead)
async def completar_orden_produccion(
    orden_id: UUID,
    data: OrdenProduccionCompletar,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    """
    Completa la orden de producción. Esto descuenta los insumos y agrega el producto resultante al inventario.
    """
    return await ProduccionService.completar_orden_produccion(db, orden_id, data, current_user)
