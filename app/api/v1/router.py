from fastapi import APIRouter
from app.api.v1.organizacion import router as organizacion_router
from app.api.v1.requisiciones import router as requisiciones_router
from app.api.v1.despachos import router as despachos_router
from app.api.v1.inventario import router as inventario_router
from app.api.v1.produccion import router as produccion_router
from app.api.v1.contabilidad import router as contabilidad_router

from app.api.v1.catalogo import router as catalogo_router

router = APIRouter(prefix="/api/v1")

router.include_router(catalogo_router)
router.include_router(organizacion_router)
router.include_router(requisiciones_router)
router.include_router(despachos_router)
router.include_router(inventario_router)
router.include_router(produccion_router)
router.include_router(contabilidad_router)
