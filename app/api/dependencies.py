from hmac import compare_digest
from typing import Annotated

from fastapi import (
    HTTPException,
    Security,
    status,
)
from fastapi.security import APIKeyHeader

from app.core.config import settings

API_KEY = APIKeyHeader(
    name='X-API-Key',
    auto_error=False,
)


async def require_api_key(
    api_key: Annotated[str | None, Security(API_KEY)],
):
    excepted = settings.API_KEY.get_secret_value()
    if api_key is None or not compare_digest(api_key, excepted):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )
