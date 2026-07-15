from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.catalogo import ProductoRead, CategoriaProductoRead, UnidadMedidaRead, ProductoCreate, ProductoUpdate
from app.services.catalogo_service import CatalogoService
from math import ceil
from uuid import UUID

router = APIRouter(prefix="/productos", tags=["Catálogo"])

@router.get("/", response_model=dict)
async def listar_productos(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * size
    productos = await CatalogoService.listar_productos(db, skip=skip, limit=size)
    total_count = await CatalogoService.contar_productos(db)
    # Simple pagination wrapper to match frontend PaginatedResponse
    return {
        "items": [ProductoRead.model_validate(p).model_dump() for p in productos],
        "total": total_count,
        "page": page,
        "size": size,
        "pages": ceil(total_count / size) if total_count > 0 else 1
    }

@router.post("/", response_model=ProductoRead, status_code=201)
async def crear_producto(data: ProductoCreate, db: AsyncSession = Depends(get_db)):
    return await CatalogoService.crear_producto(db, data)

@router.patch("/{producto_id}", response_model=ProductoRead)
async def actualizar_producto(producto_id: UUID, data: ProductoUpdate, db: AsyncSession = Depends(get_db)):
    return await CatalogoService.actualizar_producto(db, producto_id, data)

@router.delete("/{producto_id}", status_code=204)
async def eliminar_producto(producto_id: UUID, db: AsyncSession = Depends(get_db)):
    await CatalogoService.eliminar_producto(db, producto_id)

@router.get("/categorias", response_model=list[CategoriaProductoRead])
async def listar_categorias(db: AsyncSession = Depends(get_db)):
    return await CatalogoService.listar_categorias(db)

@router.get("/unidades", response_model=list[UnidadMedidaRead])
async def listar_unidades(db: AsyncSession = Depends(get_db)):
    return await CatalogoService.listar_unidades(db)

@router.get("/base", response_model=list[dict])
async def listar_productos_base(db: AsyncSession = Depends(get_db)):
    # Used for Selects (only id, nombre, codigo_interno)
    productos = await CatalogoService.listar_productos(db, skip=0, limit=1000)
    return [{"id": str(p.id), "nombre": p.nombre, "codigo_interno": p.codigo_interno} for p in productos]
