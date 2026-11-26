"""Chatbot (chatv2) contract. Separate from the user-JWT routers.

Every endpoint requires `Authorization: Bearer <BOT_API_KEY>`. Business outcomes
are HTTP 200: success bodies carry `"ok": true`, failures are
`{"ok": false, "reason": "<code>", "message": "<es text>"}`. 422 only for malformed bodies.
"""
from fastapi import APIRouter, Depends

from dependencies.bot_auth import require_bot_key
from schemas.bot import BotHealthResponse

router = APIRouter(prefix="/bot", tags=["bot"], dependencies=[Depends(require_bot_key)])


@router.get("/health", response_model=BotHealthResponse)
async def bot_health():
    """Lets the bot operator check that the key is configured and accepted."""
    return BotHealthResponse()
