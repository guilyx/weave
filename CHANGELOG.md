# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed

- Session **chat**: Markdown rendering (headings, lists, bold, code); full message thread; backend strips JSON/code-fence wrappers from agent replies
- Chronicle **chapters** group ~30 STT transcript lines each (agent passages merge into the current chapter; chapter 2 starts at STT 31). Compact chapter nav (dropdown when many chapters)
- Player viewpoint: “Ideas for your character” suggestions prompts explicitly target the **player**, not the DM (system prompt, tick extras, JSON `suggestions_audience` field)

### Fixed

- Chronicle: worker `UPDATE` used unused SQL params (`IndeterminateDatatypeError` on `$2`); chapters merge on extend again
- Migration `010` consolidates legacy one-tick-per-row journals into ~30-STT chapters; chapter nav back to wrap buttons (no dropdown)
- Web build: `SessionChatPanel` uses `api.listMessages` and typed `SessionMessage` (was `getMessages` / implicit `any`)
- Cursor agent: large session prompts passed via stdin instead of argv (fixes `Argument list too long` / E2BIG in Docker); compact context payload for Cursor ticks
- Agent tick JSON: extract JSON from prose/markdown wrappers; Cursor ticks get stricter JSON instructions and stub fallback when parse fails
- Worker crash: `log_activity()` accepts optional `activity_id` for stable chronicle/memory feed ids
- Docker image installs `faster-whisper` (`--extra stt`) for local STT; compose default remains `STT_PROVIDER=cloud` when `OPENAI_API_KEY` is set

### Changed

- Docker `weave` image installs Cursor Agent CLI (`curl cursor.com/install`); auth via `CURSOR_API_KEY` — no host binary mount. Default `AGENT_BACKEND=cursor` in Compose

### Added

- D&D Beyond **game log** sync: rolls and events from `game-log-rest-live.dndbeyond.com` stored per campaign (`campaign_game_log_entries`), surfaced in Debug activity feed and agent context (`ddb_game_log_recent`); sync on session start and during live play (requires `DDB_COBALT_SESSION` + `ddb_campaign_id`)
- `GET/POST /api/v1/campaigns/{id}/game-log` and `sync-game-log`
- Session chronicle UI: chapter navigation (`Ch. 1`, `Ch. 2`, …), full-scroll vs single-chapter view
- `session_memory` table for condensed agent beats (migration `005_session_memory.sql`)
- `sessions.story` column: cumulative narrative from speech-to-text and recap updates (migration `004_session_story.sql`)
- D&D Beyond character portraits: `avatar_url` (and frame/backdrop) on sheets; `GET /api/v1/ddb/characters/{id}/avatar` proxy for private images
- Live session **activity log**: unified feed for audio chunks, transcripts, notes, AI recap/suggestions, and chat (filters + WebSocket updates)
- Campaign **AI brief** (persistent summary) on campaign page; included in every agent tick and session chat
- Unified agent context: campaign brief, lore docs, party sheets, past session recaps, current recap, transcript, notes
- Rich character sheet panels: abilities, combat stats, equipped gear, inventory, features, and spells
- Party roster accordion on live sessions; full sheet preview in character-selection carousel
- DDB API: `GET /ddb/characters/{id}/sheet` and batch `POST /ddb/characters/sheets` for previews before import
- Web UI overhaul: Tailwind v4, D&D-themed layout, campaign wizard with party character recaps
- Character cards (abilities, HP, AC, DDB link); add any player's D&D Beyond ID to a campaign
- Import full party from a D&D Beyond campaign ID (`DDB_COBALT_SESSION`); carousel to pick your character
- Campaign wizard: DDB campaign ID on step 1 (no manual character IDs)

### Changed

- Agent ticks: production recap prompts, OpenAI JSON mode (`langgraph`), cursor→langgraph fallback; stub no longer pastes raw STT into recap/memory; Docker defaults to `langgraph` when using compose
- Session chronicle is an **append-only journal** (`session_chronicle_entries`): timestamped, id’d entries per DM/player viewpoint — no full recap rewrite each tick
- Session **perspective**: choose Dungeon Master or a player character; recaps, tips, and chat prompts adapt (player POV vs DM chronicle — no DM coaching in player mode)
- Session Recap / Chat tabs moved to the top of the center pane (left rail: controls + party only)
- Live session layout: party shown vertically in the left rail (not horizontal strip or center tab); center panel uses full width/height for recap, chat, or selected character sheet
- Session UI readability: larger type, `prose-table` recaps, RPG-themed icons (`IconBox`, empty states), quest-style numbered tips, labeled sidebar controls
- **Recap tab** shows only AI-synthesized session recap (memory beats + suggestions), not raw speech-to-text; mic audio is STT’d then passed to the agent with full session history to produce `session_recap`
- Agent tick prefers `session_recap` (full DM prose) over appending `recap_delta`; raw transcript is no longer written into `sessions.recap`
- Agent context includes chat history and prior suggestions; tips must not repeat generic stub lines
- Wider session workspace: larger left rail, main recap area, and AI journal sidebar
- Docker `AGENT_BACKEND` respects `.env` (was hard-coded to stub)
- Themed scrollbars (thin, gold on hover) across scroll regions
- App shell locked to viewport (`100dvh`); live session uses left rail + main tabs + right AI journal sidebar (no page scroll)
- Campaign page uses same sidebar + main workspace pattern
- Session log defaults to **AI journal** only (memory beats, recap, tips, chat replies); pipeline audio/STT hidden under Debug
- Agent ticks produce `memory_delta` stored in `session_memory`; debounce configurable via `AGENT_DEBOUNCE_SEC` (default 25s)
- Fixed worker crash: `enqueue()` was passed a JSON string instead of `JobEnvelope`
- Live session UX: compact party strip, tabs (Table / Log / Party / Chat), configurable mic chunk interval (`VITE_AUDIO_CHUNK_MS`)
- Session log: smaller rows for audio/agent events; stable activity IDs fix duplicate WebSocket + API entries
- Growing `session_story` in DB from STT and recap deltas; included in agent context for every tick and chat
- Chat supports map/scene/portrait brief requests (text descriptions until image generation exists)
- Imported party UI: compact tile grid with one expandable sheet (fits viewport without page scroll); campaign create, party tab, and live session roster
- Background worker processes multiple jobs in parallel (`WORKER_CONCURRENCY`, default 4); STT and agent run in thread pool so the API stays responsive
- Agent recap runs are serialized per session with automatic re-queue if a tick arrives while one is in flight

### Fixed

- D&D Beyond character import: v5/legacy fetches now send bearer token + cookies (fixes `legacy API 500` after party import)
- Party import continues when individual characters fail; reports per-character errors
- Safer DDB JSON normalization (race/background as string, invalid stat levels)
- D&D Beyond campaign roster 500: cached bearer token attribute shadowed `_bearer_token()` method (`TypeError` on second call)
- Cobalt session trimming in config; clearer DDB auth/parse errors on roster endpoint
- Audio upload returns 404 when session does not exist (stale URL after DB reset); live UI shows clear message
- `config.py` repo root detection in Docker (`/app/src/weave` layout); use `MIGRATIONS_PATH` / `WEAVE_ROOT` instead of hard-coded `parents[4]`
- Migrations tracked in `schema_migrations`; `001_init.sql` idempotent for restarts and partial applies
- Docker Compose forces `AGENT_BACKEND=stub` and `STT_PROVIDER=cloud`; cursor agent falls back to stub when CLI missing

### Added

- Python monolith `python/weave`: API, background worker, DDB client, STT, agent, TTS in one process
- Docker Compose stack: `weave`, `web`, Postgres, Redis (`docker/Dockerfile.weave`)
- DDB normalization tests ported to Python

### Removed

- Rust crates (`weave-api`, `weave-worker`, `weave-ddb`, `weave-core`) and `python/weave-ai` sidecar
- Separate `weave-api` / `weave-worker` / `weave-ai` Docker services

### Changed

- Default session agent remains **Cursor CLI ask mode** (`AGENT_BACKEND=cursor`)
- Web TTS calls `/api/v1/tts/speak` on the unified API
- `make weave` replaces `make api`, `make worker`, and `make ai`
