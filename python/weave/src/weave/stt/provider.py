import base64
import io
import logging
import tempfile
from dataclasses import dataclass

from weave.config import settings

logger = logging.getLogger(__name__)

_local_model = None


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    provider: str


def transcribe_audio(audio_base64: str, content_type: str = "audio/webm") -> TranscriptionResult:
    audio_bytes = base64.b64decode(audio_base64)
    provider = _resolve_provider()

    if provider == "local":
        try:
            return _transcribe_local(audio_bytes, content_type)
        except Exception as exc:
            logger.warning("local STT failed: %s", exc)
            if settings.stt_provider == "auto" and settings.openai_api_key:
                return _transcribe_cloud(audio_bytes, content_type)
            raise

    if provider == "cloud":
        return _transcribe_cloud(audio_bytes, content_type)

    # auto: try local first
    try:
        return _transcribe_local(audio_bytes, content_type)
    except Exception as exc:
        logger.warning("local STT unavailable: %s", exc)
        if settings.openai_api_key:
            return _transcribe_cloud(audio_bytes, content_type)
        logger.warning(
            "STT skipped: set OPENAI_API_KEY for cloud transcription or STT_PROVIDER=local with faster-whisper"
        )
        return TranscriptionResult(text="", confidence=0.0, provider="stub")


def _resolve_provider() -> str:
    mode = settings.stt_provider.lower()
    if mode in ("local", "cloud", "auto"):
        return mode
    return "auto"


def _transcribe_local(audio_bytes: bytes, content_type: str) -> TranscriptionResult:
    from faster_whisper import WhisperModel

    global _local_model
    if _local_model is None:
        _local_model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")

    suffix = ".webm" if "webm" in content_type else ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        segments, _info = _local_model.transcribe(tmp.name, beam_size=1)
        text = " ".join(seg.text.strip() for seg in segments).strip()

    return TranscriptionResult(text=text, confidence=0.85, provider="local")


def _transcribe_cloud(audio_bytes: bytes, content_type: str) -> TranscriptionResult:
    from openai import OpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY required for cloud STT")

    client = OpenAI(api_key=settings.openai_api_key)
    suffix = ".webm" if "webm" in content_type else ".wav"
    buf = io.BytesIO(audio_bytes)
    buf.name = f"chunk{suffix}"
    response = client.audio.transcriptions.create(model="whisper-1", file=buf)
    text = (response.text or "").strip()
    return TranscriptionResult(text=text, confidence=0.9, provider="cloud")
