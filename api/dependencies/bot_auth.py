import hmac

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings

# auto_error=False: missing/invalid headers are answered with our own 401
bot_bearer = HTTPBearer(auto_error=False)


async def require_bot_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bot_bearer),
) -> None:
    """Machine-to-machine auth for /bot/*: `Authorization: Bearer <BOT_API_KEY>`.

    Fails closed: with BOT_API_KEY unset every bot request is rejected (503).
    """
    expected = settings.BOT_API_KEY
    if not expected:
        raise HTTPException(status_code=503, detail="bot integration disabled")

    provided = credentials.credentials if credentials else ""
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="Clave de bot inválida",
            headers={"WWW-Authenticate": "Bearer"},
        )
