"""Chatbot (chatv2) contract. Separate from the user-JWT routers.

Every endpoint requires `Authorization: Bearer <BOT_API_KEY>`. Business outcomes
are HTTP 200: success bodies carry `"ok": true`, failures are
`{"ok": false, "reason": "<code>", "message": "<es text>"}`. Malformed bodies are the
`invalid_input` failure (HTTP 200 too), but only for callers with a valid key.
"""
import logging
from typing import Callable

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.bot_auth import bot_bearer, require_bot_key
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
from services.bot_outcomes import invalid_input_failure
from services.bot_service import BotService

logger = logging.getLogger(__name__)


class BotRoute(APIRoute):
    """Turns request validation errors into the `invalid_input` business outcome (HTTP 200).

    Scoped to this router, so every other router keeps the standard 422. FastAPI runs the
    router dependencies (bot auth) before it raises field errors, but a body that is not
    valid JSON fails before any dependency runs, so the key is checked again here: an
    unauthenticated caller always gets 401/503, never a 200 that reveals the schema.
    """

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def bot_route_handler(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as exc:
                await require_bot_key(await bot_bearer(request))
                # Log locations only: the inputs may carry lead personal data
                locations = [e.get("loc") for e in exc.errors()]
                logger.warning(f"[BOT] {request.url.path}: invalid input at {locations}")
                failure = invalid_input_failure(exc.errors())
                return JSONResponse(status_code=200, content=failure.model_dump(mode="json"))

        return bot_route_handler


router = APIRouter(
    prefix="/bot", tags=["bot"], dependencies=[Depends(require_bot_key)], route_class=BotRoute,
)


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
