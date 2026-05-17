import base64
import io
import logging

from weave.config import settings

logger = logging.getLogger(__name__)


def synthesize_speech(text: str) -> tuple[bytes, str]:
    """Return audio bytes and mime type."""
    if settings.openai_api_key:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text[:4096],
        )
        return response.content, "audio/mpeg"

    try:
        import edge_tts
        import asyncio

        async def _run() -> bytes:
            communicate = edge_tts.Communicate(text[:4096], voice="en-US-GuyNeural")
            buf = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            return buf.getvalue()

        audio = asyncio.run(_run())
        return audio, "audio/mpeg"
    except Exception as exc:
        logger.warning("TTS fallback failed: %s", exc)
        return b"", "text/plain"
