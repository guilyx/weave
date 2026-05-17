import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    if env_root := os.environ.get("WEAVE_ROOT"):
        return Path(env_root).resolve()
    here = Path(__file__).resolve().parent
    for parent in (here, *here.parents):
        if (parent / "migrations").is_dir():
            return parent
    return here.parents[2]


def _find_env_file() -> Path | None:
    if env_root := os.environ.get("WEAVE_ROOT"):
        candidate = Path(env_root) / ".env"
        if candidate.is_file():
            return candidate
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


_REPO_ROOT = _find_repo_root()
_ENV_FILE = _find_env_file()

_settings_config: dict = {"extra": "ignore", "env_file_encoding": "utf-8"}
if _ENV_FILE is not None:
    _settings_config["env_file"] = str(_ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(**_settings_config)

    database_url: str = "postgres://weave:weave@localhost:5432/weave"
    redis_url: str = "redis://127.0.0.1:6379"
    api_bind: str = "0.0.0.0:8080"
    api_key: str | None = None
    data_dir: str = "./data"

    ddb_cobalt_session: str | None = None

    stt_provider: str = "auto"
    whisper_model: str = "small"
    openai_api_key: str | None = None

    agent_backend: str = "cursor"
    agent_model: str = "gpt-4o-mini"
    cursor_api_key: str | None = None
    cursor_agent_bin: str = "agent"
    cursor_agent_mode: str = "ask"
    cursor_model: str | None = None
    cursor_workspace: str = ""
    cursor_timeout_seconds: int = 300

    worker_concurrency: int = 4
    agent_debounce_sec: int = 25
    chronicle_stt_per_chapter: int = 30

    migrations_path: str | None = None

    @property
    def migrations_dir(self) -> Path:
        if self.migrations_path:
            return Path(self.migrations_path)
        return _REPO_ROOT / "migrations"


def load_settings() -> Settings:
    data = Settings()
    if not data.cursor_workspace:
        data.cursor_workspace = str(_REPO_ROOT)
    if not data.cursor_api_key:
        data.cursor_api_key = os.environ.get("CURSOR_API_KEY") or None
    if data.api_key is not None and data.api_key == "":
        data.api_key = None
    if data.ddb_cobalt_session is not None:
        stripped = data.ddb_cobalt_session.strip().strip('"').strip("'")
        data.ddb_cobalt_session = stripped or None
    return data


settings = load_settings()
