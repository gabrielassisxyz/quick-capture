"""Tests for Karakeep HTTP client module."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from quick_capture.db import init_captures_db
from quick_capture.karakeep import (
    _URL_PATTERN,
    dispatch_reference_to_karakeep,
    sync_reference_to_karakeep,
)

FAKE_API_URL = "http://karakeep.test"
FAKE_API_KEY = "kk_test_key_12345"


class TestURLPattern:
    """Tests for _URL_PATTERN regex."""

    def test_detects_https(self):
        assert _URL_PATTERN.search("Check https://example.com out") is not None

    def test_detects_http(self):
        assert _URL_PATTERN.search("Visit http://example.com") is not None

    def test_no_url(self):
        assert _URL_PATTERN.search("Just some text") is None

    def test_match_returns_url(self):
        match = _URL_PATTERN.search("See https://example.com/path for details")
        assert match is not None
        assert match.group(0) == "https://example.com/path"


class TestDispatchTextBookmark:
    """dispatch_reference_to_karakeep with plain text (no URL)."""

    @patch("quick_capture.karakeep.httpx.post")
    def test_sends_text_type(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm1"}, raise_for_status=MagicMock()
        )
        result = dispatch_reference_to_karakeep(
            text="A thought about AI",
            enriched_text="Expanded thought",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        assert result == {"id": "bm1"}
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["type"] == "text"
        assert payload["title"] == "A thought about AI"
        assert payload["note"] == "Expanded thought"
        assert payload["source"] == "api"
        assert "url" not in payload

    @patch("quick_capture.karakeep.httpx.post")
    def test_truncates_long_title(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm2"}, raise_for_status=MagicMock()
        )
        long_text = "x" * 300
        dispatch_reference_to_karakeep(
            text=long_text,
            enriched_text="short",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        payload = mock_post.call_args.kwargs["json"]
        assert len(payload["title"]) == 200
        assert payload["title"] == long_text[:200]


class TestDispatchLinkBookmark:
    """dispatch_reference_to_karakeep with URL in text → type=link."""

    @patch("quick_capture.karakeep.httpx.post")
    def test_sends_link_type(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm3"}, raise_for_status=MagicMock()
        )
        dispatch_reference_to_karakeep(
            text="Read https://example.com/article",
            enriched_text="Article notes",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["type"] == "link"
        assert payload["url"] == "https://example.com/article"

    @patch("quick_capture.karakeep.httpx.post")
    def test_includes_tags(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm4"}, raise_for_status=MagicMock()
        )
        dispatch_reference_to_karakeep(
            text="A link https://example.com",
            enriched_text="Notes",
            tags=["ai", "research"],
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["tags"] == ["ai", "research"]

    @patch("quick_capture.karakeep.httpx.post")
    def test_no_tags_key_when_empty(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm5"}, raise_for_status=MagicMock()
        )
        dispatch_reference_to_karakeep(
            text="No tags here",
            enriched_text="Notes",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        payload = mock_post.call_args.kwargs["json"]
        assert "tags" not in payload


class TestDispatchAuthAndRequest:
    """dispatch_reference_to_karakeep auth header and request details."""

    @patch("quick_capture.karakeep.httpx.post")
    def test_bearer_token_auth(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm6"}, raise_for_status=MagicMock()
        )
        dispatch_reference_to_karakeep(
            text="Text",
            enriched_text="Notes",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == f"Bearer {FAKE_API_KEY}"

    @patch("quick_capture.karakeep.httpx.post")
    def test_posts_to_bookmarks_endpoint(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm7"}, raise_for_status=MagicMock()
        )
        dispatch_reference_to_karakeep(
            text="Text",
            enriched_text="Notes",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        url = mock_post.call_args.args[0]
        assert url == f"{FAKE_API_URL}/api/v1/bookmarks"

    @patch("quick_capture.karakeep.httpx.post")
    def test_timeout_30(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm8"}, raise_for_status=MagicMock()
        )
        dispatch_reference_to_karakeep(
            text="Text",
            enriched_text="Notes",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        assert mock_post.call_args.kwargs["timeout"] == 30.0


class TestDispatchMissingKey:
    """dispatch_reference_to_karakeep raises ValueError when API key is not configured."""

    def test_raises_when_no_key(self):
        with patch("quick_capture.karakeep.KARAKEEP_API_KEY", ""), \
             pytest.raises(ValueError, match="KARAKEEP_API_KEY not configured"):
            dispatch_reference_to_karakeep(
                text="Text",
                enriched_text="Notes",
                api_url=FAKE_API_URL,
                api_key=None,
            )

    def test_raises_when_empty_key(self):
        with patch("quick_capture.karakeep.KARAKEEP_API_KEY", ""), \
             pytest.raises(ValueError, match="KARAKEEP_API_KEY not configured"):
            dispatch_reference_to_karakeep(
                text="Text",
                enriched_text="Notes",
                api_url=FAKE_API_URL,
                api_key="",
            )


class TestDispatchHTTPError:
    """dispatch_reference_to_karakeep propagates HTTP errors."""

    @patch("quick_capture.karakeep.httpx.post")
    def test_raises_http_status_error(self, mock_post):
        request = httpx.Request("POST", f"{FAKE_API_URL}/api/v1/bookmarks")
        mock_post.return_value = httpx.Response(
            status_code=500,
            request=request,
            json={"error": "internal"},
        )
        with pytest.raises(httpx.HTTPStatusError):
            dispatch_reference_to_karakeep(
                text="Text",
                enriched_text="Notes",
                api_url=FAKE_API_URL,
                api_key=FAKE_API_KEY,
            )


class TestDispatchEnvVarDefaults:
    """dispatch_reference_to_karakeep uses env-var defaults when explicit args are None."""

    @patch("quick_capture.karakeep.httpx.post")
    def test_uses_env_api_url(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm9"}, raise_for_status=MagicMock()
        )
        with patch("quick_capture.karakeep.KARAKEEP_API_URL", "http://env-karakeep.test"), \
             patch("quick_capture.karakeep.KARAKEEP_API_KEY", "env_key"):
            dispatch_reference_to_karakeep(text="Text", enriched_text="Notes")
            url = mock_post.call_args.args[0]
            assert url == "http://env-karakeep.test/api/v1/bookmarks"

    @patch("quick_capture.karakeep.httpx.post")
    def test_uses_env_api_key(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm10"}, raise_for_status=MagicMock()
        )
        with patch("quick_capture.karakeep.KARAKEEP_API_KEY", "env_key_xyz"), \
             patch("quick_capture.karakeep.KARAKEEP_API_URL", "http://env.test"):
            dispatch_reference_to_karakeep(text="Text", enriched_text="Notes")
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer env_key_xyz"

    @patch("quick_capture.karakeep.httpx.post")
    def test_explicit_args_override_env(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm11"}, raise_for_status=MagicMock()
        )
        with patch("quick_capture.karakeep.KARAKEEP_API_URL", "http://env.test"), \
             patch("quick_capture.karakeep.KARAKEEP_API_KEY", "env_key"):
            dispatch_reference_to_karakeep(
                text="Text",
                enriched_text="Notes",
                api_url=FAKE_API_URL,
                api_key=FAKE_API_KEY,
            )
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Authorization"] == f"Bearer {FAKE_API_KEY}"


class TestAPIKeyNotInLogs:
    """Verify that the API key is never logged or exposed in error messages."""

    def test_api_key_never_in_logged_error(self):
        """When sync fails, API key must not appear in any log message."""
        secret_value = "super-secret-key-do-not-log"  # noqa: S105
        with (
            patch("quick_capture.karakeep.httpx.post", side_effect=httpx.ConnectError("refused")),
            patch("quick_capture.karakeep.logger") as mock_logger,
        ):
            result = sync_reference_to_karakeep(
                capture_id="test-id",
                text="Text",
                enriched_text="Notes",
                api_url=FAKE_API_URL,
                api_key=secret_value,
            )
            assert result is None

        for call in mock_logger.exception.call_args_list:
            logged_msg = call[0][0] if call[0] else ""
            logged_args = call[0][1:] if len(call[0]) > 1 else ()
            full_log = logged_msg % logged_args if logged_args else logged_msg
            assert secret_value not in full_log

    def test_value_error_does_not_expose_key(self):
        """When API key is missing, ValueError message does not contain any real key value."""
        with patch("quick_capture.karakeep.KARAKEEP_API_KEY", ""), \
             pytest.raises(ValueError, match="KARAKEEP_API_KEY not configured") as exc_info:
            dispatch_reference_to_karakeep(
                text="Text",
                enriched_text="Notes",
                api_url=FAKE_API_URL,
            )
        msg = str(exc_info.value)
        assert "secret" not in msg.lower()
        assert "KARAKEEP_API_KEY" in msg


class TestSyncReferenceToKarakeep:
    """sync_reference_to_karakeep wraps dispatch with graceful degradation."""

    @patch("quick_capture.karakeep.httpx.post")
    def test_success_calls_log_sync(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm_sync"}, raise_for_status=MagicMock()
        )
        conn = init_captures_db(":memory:")
        try:
            with patch("quick_capture.karakeep.log_sync") as mock_log_sync:
                result = sync_reference_to_karakeep(
                    "cap-1",
                    "Text",
                    "Enriched",
                    tags=["test"],
                    api_url=FAKE_API_URL,
                    api_key=FAKE_API_KEY,
                    conn=conn,
                )
            assert result == {"id": "bm_sync"}
            mock_log_sync.assert_called_once_with("cap-1", "karakeep", conn=conn)
        finally:
            conn.close()

    @patch("quick_capture.karakeep.httpx.post")
    def test_returns_none_on_http_status_error(self, mock_post):
        request = httpx.Request("POST", f"{FAKE_API_URL}/api/v1/bookmarks")
        mock_post.return_value = httpx.Response(
            status_code=500,
            request=request,
            json={"error": "internal"},
        )
        result = sync_reference_to_karakeep(
            "cap-2",
            "Text",
            "Note",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        assert result is None

    @patch("quick_capture.karakeep.httpx.post")
    def test_returns_none_on_connect_error(self, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        result = sync_reference_to_karakeep(
            "cap-3",
            "Text",
            "Note",
            api_url=FAKE_API_URL,
            api_key=FAKE_API_KEY,
        )
        assert result is None

    def test_returns_none_on_missing_key(self):
        with patch("quick_capture.karakeep.KARAKEEP_API_KEY", ""):
            result = sync_reference_to_karakeep(
                "cap-4",
                "Text",
                "Note",
                api_url=FAKE_API_URL,
            )
            assert result is None

    @patch("quick_capture.karakeep.httpx.post")
    def test_tags_passed_through(self, mock_post):
        mock_post.return_value = MagicMock(
            json=lambda: {"id": "bm11"}, raise_for_status=MagicMock()
        )
        conn = init_captures_db(":memory:")
        try:
            with patch("quick_capture.karakeep.log_sync"):
                sync_reference_to_karakeep(
                    "cap-6",
                    "Text",
                    "Note",
                    tags=["python", "ai"],
                    api_url=FAKE_API_URL,
                    api_key=FAKE_API_KEY,
                    conn=conn,
                )
            payload = mock_post.call_args.kwargs["json"]
            assert payload["tags"] == ["python", "ai"]
        finally:
            conn.close()
