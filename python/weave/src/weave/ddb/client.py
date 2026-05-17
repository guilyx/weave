import logging
import time
from typing import Any

import httpx

from weave.ddb.campaign import DdbRosterEntry, parse_campaign_roster
from weave.ddb.models import CharacterSheet
from weave.ddb.normalize import normalize_legacy, normalize_v5

logger = logging.getLogger(__name__)

V5_URL = "https://character-service.dndbeyond.com/character/v5/character"
LEGACY_URL = "https://www.dndbeyond.com/character"
COBALT_TOKEN_URL = "https://auth-service.dndbeyond.com/v1/cobalt-token"
CAMPAIGN_CHARACTERS_URL = "https://www.dndbeyond.com/api/campaign/stt/active-characters"


class DdbError(Exception):
    pass


class DdbNotFound(DdbError):
    pass


class DdbAuthRequired(DdbError):
    pass


class DdbClient:
    def __init__(self, cobalt_session: str | None = None) -> None:
        raw = (cobalt_session or "").strip().strip('"').strip("'")
        self._cobalt = raw or None
        self._cached_bearer: str | None = None
        self._bearer_expires_at: float = 0.0
        self._http = httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; Weave/0.2; +https://github.com/weave-dnd)"
                ),
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    def _cookies(self) -> dict[str, str] | None:
        if self._cobalt:
            return {"CobaltSession": self._cobalt}
        return None

    async def _fetch_bearer_token(self) -> str:
        if not self._cobalt:
            raise DdbAuthRequired(
                "DDB_COBALT_SESSION required to read D&D Beyond campaigns"
            )
        now = time.time()
        if self._cached_bearer and now < self._bearer_expires_at:
            return self._cached_bearer
        resp = await self._http.post(
            COBALT_TOKEN_URL,
            cookies={"CobaltSession": self._cobalt},
            headers={
                "Origin": "https://www.dndbeyond.com",
                "Referer": "https://www.dndbeyond.com/",
            },
            content=b"",
        )
        if resp.status_code >= 400:
            raise DdbAuthRequired(
                f"could not obtain D&D Beyond token (HTTP {resp.status_code})"
            )
        try:
            data = resp.json()
        except Exception as exc:
            raise DdbError(f"cobalt-token invalid JSON: {resp.text[:120]}") from exc
        token = data.get("token") or data.get("access_token")
        if not token:
            raise DdbError("cobalt-token response missing token field")
        try:
            ttl = int(data.get("ttl", 300))
        except (TypeError, ValueError):
            ttl = 300
        self._cached_bearer = str(token)
        self._bearer_expires_at = now + max(ttl - 30, 60)
        return self._cached_bearer

    async def _character_headers(self, character_id: int) -> dict[str, str]:
        headers = {
            "Origin": "https://www.dndbeyond.com",
            "Referer": f"https://www.dndbeyond.com/characters/{character_id}",
        }
        if self._cobalt:
            try:
                token = await self._fetch_bearer_token()
                headers["Authorization"] = f"Bearer {token}"
            except DdbAuthRequired:
                logger.warning("cobalt token exchange failed; using cookies only")
        return headers

    async def fetch_campaign_roster(self, ddb_campaign_id: int) -> list[DdbRosterEntry]:
        token = await self._fetch_bearer_token()
        url = f"{CAMPAIGN_CHARACTERS_URL}/{ddb_campaign_id}"
        resp = await self._http.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "https://www.dndbeyond.com",
                "Referer": "https://www.dndbeyond.com/",
            },
            cookies=self._cookies(),
        )
        if resp.status_code == 404:
            raise DdbNotFound(f"campaign {ddb_campaign_id}")
        if resp.status_code in (401, 403):
            raise DdbAuthRequired("invalid or expired DDB_COBALT_SESSION")
        if resp.status_code >= 400:
            raise DdbError(f"campaign API {resp.status_code}: {resp.text[:200]}")
        roster = parse_campaign_roster(resp.json())
        if not roster:
            raise DdbError(
                "no characters found in campaign roster (check campaign ID and access)"
            )
        return roster

    async def fetch_character(self, character_id: int) -> CharacterSheet:
        if not self._cobalt:
            raise DdbAuthRequired(
                "DDB_COBALT_SESSION required to import characters from D&D Beyond"
            )

        last_error: DdbError | None = None
        try:
            return await self._fetch_v5(character_id)
        except DdbAuthRequired:
            raise
        except DdbNotFound as exc:
            last_error = exc
            logger.debug("v5 not found for %s, trying legacy", character_id)
        except DdbError as exc:
            last_error = exc
            logger.debug("v5 failed for %s: %s", character_id, exc)

        try:
            return await self._fetch_legacy(character_id)
        except DdbAuthRequired:
            raise
        except DdbNotFound as exc:
            last_error = exc
        except DdbError as exc:
            last_error = exc

        if last_error:
            raise last_error
        raise DdbNotFound(f"character {character_id}")

    async def fetch_portrait_bytes(
        self,
        character_id: int,
        *,
        kind: str = "avatar",
    ) -> tuple[bytes, str]:
        """Download portrait image bytes (uses Cobalt session when configured)."""
        sheet = await self.fetch_character(character_id)
        url = sheet.avatar_url
        if kind == "frame":
            url = sheet.frame_avatar_url or url
        elif kind == "backdrop":
            url = sheet.large_backdrop_avatar_url or sheet.small_backdrop_avatar_url or url
        if not url:
            raise DdbNotFound(f"no portrait for character {character_id}")
        resp = await self._http.get(
            url,
            cookies=self._cookies(),
            headers=await self._character_headers(character_id),
        )
        if resp.status_code == 404:
            raise DdbNotFound(f"portrait not found for character {character_id}")
        if resp.status_code in (401, 403):
            raise DdbAuthRequired("invalid or expired DDB_COBALT_SESSION")
        if resp.status_code >= 400:
            raise DdbError(f"portrait fetch {resp.status_code}")
        media_type = resp.headers.get("content-type") or "image/png"
        return resp.content, media_type

    async def _fetch_v5(self, character_id: int) -> CharacterSheet:
        url = f"{V5_URL}/{character_id}"
        resp = await self._http.get(
            url,
            params={"includeCustomItems": "true"},
            cookies=self._cookies(),
            headers=await self._character_headers(character_id),
        )
        if resp.status_code == 404:
            raise DdbNotFound(f"character {character_id}")
        if resp.status_code in (401, 403):
            raise DdbAuthRequired("invalid or expired DDB_COBALT_SESSION")
        if resp.status_code >= 400:
            raise DdbError(f"v5 API {resp.status_code}: {resp.text[:200]}")
        data = self._parse_json_response(resp, "v5")
        return normalize_v5(character_id, data)

    async def _fetch_legacy(self, character_id: int) -> CharacterSheet:
        url = f"{LEGACY_URL}/{character_id}/json"
        resp = await self._http.get(
            url,
            cookies=self._cookies(),
            headers=await self._character_headers(character_id),
        )
        if resp.status_code == 404:
            raise DdbNotFound(f"character {character_id}")
        if resp.status_code in (401, 403):
            raise DdbAuthRequired("invalid or expired DDB_COBALT_SESSION")
        if resp.status_code >= 400:
            raise DdbError(f"legacy API {resp.status_code}: {resp.text[:120]}")
        data = self._parse_json_response(resp, "legacy")
        return normalize_legacy(character_id, data)

    @staticmethod
    def _parse_json_response(resp: httpx.Response, source: str) -> dict[str, Any]:
        try:
            payload = resp.json()
        except Exception as exc:
            raise DdbError(
                f"{source} API returned non-JSON (HTTP {resp.status_code})"
            ) from exc
        if not isinstance(payload, dict):
            raise DdbError(f"{source} API response was not a JSON object")
        return payload
