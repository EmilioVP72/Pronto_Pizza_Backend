from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.organizacion import Usuario
from app.schemas.bitacora import BitacoraAccionRead
from app.services.bitacora_service import BitacoraService
from app.api.v1.utils import paginate_response

router = APIRouter(prefix="/bitacora", tags=["Bitácora"])

@router.get("/", dependencies=[Depends(require_role("administrador"))])
async def obtener_bitacora(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    skip = (page - 1) * size
    acciones = await BitacoraService.listar_bitacora(db, skip=skip, limit=size)
    total = await BitacoraService.contar_bitacora(db)
    
    # We must format it to dict for the paginator
    items = []
    for a in acciones:
        items.append({
            "id": str(a.id),
            "usuario_id": str(a.usuario_id),
            "modulo": a.modulo,
            "accion": a.accion,
            "detalles": a.detalles,
            "ip_address": a.ip_address,
            "creado_en": a.creado_en.isoformat(),
            "usuario": {
                "id": str(a.usuario.id),
                "nombre_completo": a.usuario.nombre_completo,
                "email": a.usuario.email,
                "rol": {"nombre": a.usuario.rol.nombre} if a.usuario.rol else None
            } if a.usuario else None
        })
        
    return paginate_response(items, total, page, size)
