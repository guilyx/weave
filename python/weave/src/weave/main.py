import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from weave import __version__
from weave.api.router import router
from weave.config import settings
from weave.db import create_pool, migrate
from weave.ddb.client import DdbClient
from weave.worker import worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir, "audio").mkdir(parents=True, exist_ok=True)
    pool = await create_pool()
    await migrate(pool)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    ddb = DdbClient(settings.ddb_cobalt_session)

    app.state.pool = pool
    app.state.redis = redis_client
    app.state.ddb = ddb

    worker_task = asyncio.create_task(worker_loop(pool, redis_client, ddb))
    yield

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await ddb.aclose()
    await redis_client.aclose()
    await pool.close()


app = FastAPI(title="Weave", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "weave"}


@app.websocket("/api/v1/sessions/{session_id}/live")
async def live_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    redis_client = websocket.app.state.redis
    channel = f"session:{session_id}:live"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    async def reader() -> None:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode()
            await websocket.send_text(data)

    task = asyncio.create_task(reader())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


app.include_router(router)


def run() -> None:
    import uvicorn

    host, _, port_s = settings.api_bind.partition(":")
    uvicorn.run(
        "weave.main:app",
        host=host or "0.0.0.0",
        port=int(port_s or "8080"),
        reload=False,
    )


if __name__ == "__main__":
    run()
