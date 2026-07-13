from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_role
from app.models.organizacion import Usuario
from app.schemas.inventario import (
    RecepcionCompraCreate, 
    AjusteInventarioCreate, 
    MovimientoInventarioRead
)
from app.schemas.saldos import SaldoInventarioRead
from app.services.inventario_service import InventarioService
from math import ceil

router = APIRouter(prefix="/inventario", tags=["Inventario"])

@router.get("/saldos", response_model=dict)
async def listar_saldos(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * size
    saldos = await InventarioService.listar_saldos(db, skip=skip, limit=size)
    return {
        "items": saldos,
        "total": 100,
        "page": page,
        "size": size,
        "pages": ceil(100 / size)
    }

from app.api.v1.utils import paginate_response

@router.get("/movimientos", response_model=dict)
async def listar_movimientos(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * size
    movs = await InventarioService.listar_movimientos(db, skip=skip, limit=size)
    # the frontend expects a specific format, we can just use paginate_response with model dump if available
    # Actually MovimientoInventarioRead requires dumping
    return paginate_response([MovimientoInventarioRead.model_validate(m).model_dump(mode="json") for m in movs], page, size)

@router.get("/productos-bajo-minimo", response_model=dict)
async def listar_productos_bajo_minimo(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * size
    prods = await InventarioService.listar_productos_bajo_minimo(db, skip=skip, limit=size)
    return paginate_response(prods, page, size)

@router.post("/recepciones-compra", response_model=list[MovimientoInventarioRead], status_code=status.HTTP_201_CREATED)
async def recibir_compra(
    data: RecepcionCompraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    """
    Registra la entrada de una compra de insumos.
    Crea lotes automáticamente y genera movimientos de inventario de entrada.
    """
    return await InventarioService.recibir_compra(db, data, current_user)


@router.post("/ajustes", response_model=list[MovimientoInventarioRead], status_code=status.HTTP_201_CREATED)
async def registrar_ajuste(
    data: AjusteInventarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    """
    Registra un ajuste de inventario (merma o sobrante).
    Crea un movimiento de salida (si es negativo) o de entrada (si es positivo).
    """
    return await InventarioService.registrar_ajuste(db, data, current_user)
