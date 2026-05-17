# Weave

Live D&D session assistant: captures table audio, transcribes narrative, maintains a rolling recap, and offers suggestions grounded in your campaign characters and lore.

## Architecture

Single Python service (**weave**) on FastAPI:

- REST + WebSocket API, Postgres, Redis job queue
- Background worker (STT, debounced agent ticks, DDB refresh)
- D&D Beyond character fetch (v5 API + legacy fallback)
- Hybrid STT, Cursor/LangGraph agent, TTS
- **web** (React/Vite) — campaigns, characters, live session UI

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python 3.11+
- Node 20+ for the web UI
- Docker (optional full stack)

## Quick start (Docker — full stack)

```bash
cp .env.example .env
# Set CURSOR_API_KEY (and DDB_COBALT_SESSION if needed) in .env

make up
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Web UI (nginx → API) |
| http://localhost:8080 | API directly |

Logs: `docker compose logs -f weave`

**Cursor agent in Docker:** The `agent` CLI is not inside the image by default. Mount the CLI or run `make weave` on the host with `AGENT_BACKEND=cursor` for ask-mode recaps.

**STT in Docker:** Defaults to `STT_PROVIDER=cloud` (needs `OPENAI_API_KEY`) unless you use local dev with `faster-whisper` (`uv sync --extra stt`).

## Quick start (native dev)

```bash
cp .env.example .env
make infra

make weave   # terminal 1 — http://localhost:8080
make web     # terminal 2 — http://localhost:5173
```

## D&D Beyond characters

**Recommended:** On the campaign **Party** tab, use **Import from D&D Beyond campaign** — paste your DDB campaign ID (from the campaign URL), load the roster, check the characters to import, and select **My character**. Requires `DDB_COBALT_SESSION` in `.env`.

**Manual:** Link individual character IDs from `dndbeyond.com/characters/{id}` (works for public sheets without the campaign import).

1. Set `DDB_COBALT_SESSION` in `.env` (browser cookie from dndbeyond.com) for private sheets and campaign rosters.
2. Campaign ID is the number in your D&D Beyond campaign URL.

**Note:** Automated access may conflict with D&D Beyond terms of service. Use only for your own games and data.

## Configuration

See [.env.example](.env.example). Key variables:

| Variable | Purpose |
|----------|---------|
| `CURSOR_API_KEY` | Session agent (recap, chat, suggestions) via Cursor CLI ask mode |
| `AGENT_BACKEND` | `cursor` (default), `langgraph`, or `stub` |
| `CURSOR_AGENT_MODE` | `ask` (read-only, default) or `plan` |
| `OPENAI_API_KEY` | Optional: cloud STT/TTS, or `AGENT_BACKEND=langgraph` |
| `STT_PROVIDER` | `auto`, `local`, or `cloud` |
| `DDB_COBALT_SESSION` | Optional private character access |
| `WEAVE_API_KEY` | Optional `x-api-key` on API routes (leave empty locally) |

The agent uses the [`agent` CLI](https://cursor.com/docs/cli/using) (`agent --print --mode ask`). Install via Cursor; ensure `agent` is on your `PATH`.

## License

MIT
