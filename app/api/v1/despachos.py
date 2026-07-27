from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.organizacion import Usuario
from app.schemas.despachos import DespachoCreate, DespachoRead
from app.services.despacho_service import DespachoService

from app.api.v1.utils import paginate_response

router = APIRouter(prefix="/despachos", tags=["Despachos"])

@router.get("/", response_model=dict)
async def listar_despachos(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    items = await DespachoService.listar(db, current_user)
    return paginate_response([DespachoRead.model_validate(i).model_dump(mode="json") for i in items], page, size)

@router.get("/{despacho_id}", response_model=DespachoRead)
async def obtener_despacho(
    despacho_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    despacho = await DespachoService.obtener_por_id(db, despacho_id)
    if not despacho:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despacho no encontrado")
    return despacho

@router.get("/{despacho_id}/pdf")
async def descargar_pdf_despacho(
    despacho_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    despacho = await DespachoService.obtener_por_id(db, despacho_id)
    if not despacho:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despacho no encontrado")
        
    from app.services.pdf_service import PDFService
    pdf_buffer = PDFService.generar_pdf_despacho(despacho)
    
    filename = f"Despacho_{despacho.folio_documento or despacho.id}.pdf"
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

@router.post("/", response_model=DespachoRead, status_code=status.HTTP_201_CREATED)
async def crear_despacho(
    data: DespachoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    return await DespachoService.crear(db, data, current_user)

@router.patch("/{despacho_id}/completar", response_model=DespachoRead)
async def completar_despacho(
    despacho_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("almacenista", "administrador")),
):
    return await DespachoService.completar_despacho(db, despacho_id, current_user)
