# Docker

## Full stack

From the repo root:

```bash
docker compose up --build -d
```

Open **http://localhost:3000** (web). Postgres and Redis are also published on `5432` / `6379` for debugging.

## Services

| Service | Role |
|---------|------|
| `postgres` | Database |
| `redis` | Job queue + live pub/sub |
| `weave` | Python API + background worker + STT/agent/TTS |
| `web` | Built React app + nginx proxy to API |

Shared volume `weave_data` stores uploaded audio chunks (`/data` in `weave`).

## Environment

Compose overrides `DATABASE_URL` and `REDIS_URL` to use Docker service names. Other values come from your `.env` via `env_file`.

## Cursor agent inside Docker

The `weave` image installs the [Cursor Agent CLI](https://cursor.com/docs/cli/installation) at build time (`agent` on `PATH`). No host mount required.

In `.env`:

```env
AGENT_BACKEND=cursor
CURSOR_API_KEY=crsr_...
CURSOR_AGENT_MODE=ask
```

Compose sets `CURSOR_WORKSPACE=/app/repo` (repo mounted read-only for campaign context). If the CLI fails and `OPENAI_API_KEY` is set, ticks fall back to `langgraph`.

Use `AGENT_BACKEND=langgraph` to skip Cursor and use OpenAI only.

## Infra only

```bash
docker compose up -d postgres redis
```

Then use `make weave` and `make web` locally.
