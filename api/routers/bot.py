"""Chatbot (chatv2) contract. Separate from the user-JWT routers.

Every endpoint requires `Authorization: Bearer <BOT_API_KEY>`. Business outcomes
are HTTP 200: success bodies carry `"ok": true`, failures are
`{"ok": false, "reason": "<code>", "message": "<es text>"}`. 422 only for malformed bodies.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.bot_auth import require_bot_key
from schemas.bot import (
    BotAvailabilityRequest,
    BotAvailabilityResponse,
    BotFailure,
    BotHealthResponse,
    BotHoldRequest,
    BotHoldResponse,
    BotQuoteRequest,
    BotQuoteResponse,
)
from services.bot_service import BotService

router = APIRouter(prefix="/bot", tags=["bot"], dependencies=[Depends(require_bot_key)])


@router.get("/health", response_model=BotHealthResponse)
async def bot_health():
    """Lets the bot operator check that the key is configured and accepted."""
    return BotHealthResponse()


@router.post("/availability", response_model=BotAvailabilityResponse | BotFailure)
async def search_availability(req: BotAvailabilityRequest, db: AsyncSession = Depends(get_db)):
    """Active cabins free for [check_in, check_out) that fit `guests`, each with its quote."""
    return await BotService(db).search_availability(req)


@router.post("/quote", response_model=BotQuoteResponse | BotFailure)
async def quote(req: BotQuoteRequest, db: AsyncSession = Depends(get_db)):
    """Quote one cabin for a stay and say whether the dates are free."""
    return await BotService(db).quote(req)


@router.post("/holds", response_model=BotHoldResponse | BotFailure)
async def create_hold(req: BotHoldRequest, db: AsyncSession = Depends(get_db)):
    """Pre-reserve a cabin for a lead; a human confirms it from the panel before it expires."""
    return await BotService(db).create_hold(req)
