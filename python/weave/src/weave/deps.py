from typing import Annotated

import asyncpg
import redis.asyncio as redis
from fastapi import Header, HTTPException, Request

from weave.config import settings
from weave.ddb.client import DdbClient


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def get_redis(request: Request) -> redis.Redis:
    return request.app.state.redis


def get_ddb(request: Request) -> DdbClient:
    return request.app.state.ddb


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="unauthorized")
