import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from o365.auth import O365Auth
from o365.calendar import O365CalendarClient
from o365.tasks import O365TasksClient


class TestO365Auth:
    def test_is_configured_true(self):
        auth = O365Auth("tenant", "client", "secret")
        assert auth.is_configured("tenant", "client", "secret") is True

    def test_is_configured_false_empty(self):
        auth = O365Auth("", "", "")
        assert auth.is_configured("", "", "") is False

    def test_is_configured_false_partial(self):
        auth = O365Auth("t", "", "s")
        assert auth.is_configured("t", "", "s") is False


class TestO365CalendarClient:
    def _make_auth(self):
        auth = MagicMock(spec=O365Auth)
        auth.get_token = MagicMock(return_value="fake_token")
        return auth

    def test_headers_include_bearer_token(self):
        auth = self._make_auth()
        client = O365CalendarClient(auth, "group@test.de")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer fake_token"

    def test_create_event_calls_graph(self):
        auth = self._make_auth()
        client = O365CalendarClient(auth, "group@test.de")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"value": [{"id": "group_id_123"}]})
        mock_resp.raise_for_status = MagicMock()

        mock_create_resp = MagicMock()
        mock_create_resp.status_code = 201
        mock_create_resp.json = MagicMock(return_value={"id": "event_id_456"})
        mock_create_resp.raise_for_status = MagicMock()

        async def mock_get(*args, **kwargs):
            return mock_resp

        async def mock_post(*args, **kwargs):
            return mock_create_resp

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.get = AsyncMock(return_value=mock_resp)
            mock_session.post = AsyncMock(return_value=mock_create_resp)
            mock_httpx.return_value = mock_session

            result = asyncio.get_event_loop().run_until_complete(
                client.create_event(
                    title="Test Termin",
                    start=datetime(2025, 6, 15, 10, 0),
                )
            )
            assert result == "event_id_456"


class TestO365TasksClient:
    def _make_auth(self):
        auth = MagicMock(spec=O365Auth)
        auth.get_token = MagicMock(return_value="fake_token")
        return auth

    def test_headers_correct(self):
        auth = self._make_auth()
        client = O365TasksClient(auth, "plan_123", "group@test.de")
        headers = client._headers()
        assert "Bearer" in headers["Authorization"]

    def test_create_task_no_bucket_returns_none(self):
        auth = self._make_auth()
        client = O365TasksClient(auth, "plan_123", "group@test.de")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(return_value={"value": []})  # No buckets
            mock_resp.raise_for_status = MagicMock()
            mock_session.get = AsyncMock(return_value=mock_resp)
            mock_httpx.return_value = mock_session

            result = asyncio.get_event_loop().run_until_complete(
                client.create_task("Test Task")
            )
            assert result is None
