import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from weave.ddb.client import DdbClient


async def _test_fetch_bearer_token_caches_without_shadowing_method() -> None:
    """Instance attr must not shadow _fetch_bearer_token (was _bearer_token → TypeError)."""
    client = DdbClient(cobalt_session="test-cobalt")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"token": "jwt-abc", "ttl": 600}

    with patch.object(client._http, "post", new_callable=AsyncMock) as post:
        post.return_value = mock_resp
        first = await client._fetch_bearer_token()
        second = await client._fetch_bearer_token()

    assert first == "jwt-abc"
    assert second == "jwt-abc"
    assert post.await_count == 1
    assert client._cached_bearer == "jwt-abc"


async def _test_fetch_bearer_token_refreshes_after_expiry() -> None:
    client = DdbClient(cobalt_session="test-cobalt")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"token": "jwt-1", "ttl": 60}

    with patch.object(client._http, "post", new_callable=AsyncMock) as post:
        post.return_value = mock_resp
        await client._fetch_bearer_token()
        client._bearer_expires_at = time.time() - 1
        mock_resp.json.return_value = {"token": "jwt-2", "ttl": 60}
        token = await client._fetch_bearer_token()

    assert token == "jwt-2"
    assert post.await_count == 2


def test_fetch_bearer_token_caches_without_shadowing_method() -> None:
    asyncio.run(_test_fetch_bearer_token_caches_without_shadowing_method())


def test_fetch_bearer_token_refreshes_after_expiry() -> None:
    asyncio.run(_test_fetch_bearer_token_refreshes_after_expiry())
