from typing import Literal

from pydantic import BaseModel

from core.enums import BotFailureReason


class BotFailure(BaseModel):
    """Business failure for the chatbot (always HTTP 200)."""
    ok: Literal[False] = False
    reason: BotFailureReason
    message: str


class BotHealthResponse(BaseModel):
    ok: Literal[True] = True
