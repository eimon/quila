from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.catalog_service import CatalogService

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/catalog", response_class=PlainTextResponse)
async def get_catalog(db: AsyncSession = Depends(get_db)):
    """Public markdown catalog of active properties (no auth, used for chatbot RAG ingestion)."""
    content = await CatalogService(db).build_markdown()
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")
