# weave

Unified Python backend for Weave (API, worker, DDB, STT, agent, TTS).

```bash
uv sync --extra dev
uv run uvicorn weave.main:app --host 0.0.0.0 --port 8080
```

From the repo root, `make weave` runs the same. Postgres and Redis must be up (`make infra` or Docker).
