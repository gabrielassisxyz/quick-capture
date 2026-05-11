"""Karakeep sync — dispatch enriched references as bookmarks to Karakeep."""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

import httpx

from quick_capture.db import log_sync

if TYPE_CHECKING:
    import sqlite3

logger = logging.getLogger(__name__)

KARAKEEP_API_URL = os.environ.get("KARAKEEP_API_URL", "http://localhost:3000")
KARAKEEP_API_KEY = os.environ.get("KARAKEEP_API_KEY", "")
KARAKEEP_TIMEOUT = 30.0

_URL_PATTERN = re.compile(r"https?://\S+")


def dispatch_reference_to_karakeep(
    text: str,
    enriched_text: str,
    tags: list[str] | None = None,
    *,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Post a bookmark to Karakeep.

    Detects URLs in text to determine bookmark type:
    - text with URL → type=link
    - text without URL → type=text

    Args:
        text: Original capture text (used for title and URL detection).
        enriched_text: Enriched text (used as note content).
        tags: Optional tags to attach to the bookmark.
        api_url: Override for Karakeep API URL (defaults to env var).
        api_key: Override for Karakeep API key (defaults to env var).

    Returns:
        Response JSON from Karakeep API.

    Raises:
        ValueError: If KARAKEEP_API_KEY is not configured.
        httpx.HTTPStatusError: On non-2xx HTTP responses.
        httpx.ConnectError: If the server is unreachable.
    """
    key = api_key if api_key is not None else KARAKEEP_API_KEY
    url = api_url if api_url is not None else KARAKEEP_API_URL

    if not key:
        msg = "KARAKEEP_API_KEY not configured"
        raise ValueError(msg)

    match = _URL_PATTERN.search(text)
    bookmark_type = "link" if match else "text"

    payload: dict[str, Any] = {
        "type": bookmark_type,
        "title": text[:200],
        "note": enriched_text,
        "source": "api",
    }

    if match:
        payload["url"] = match.group(0)

    if tags:
        payload["tags"] = tags

    response = httpx.post(
        f"{url}/api/v1/bookmarks",
        json=payload,
        headers={"Authorization": f"Bearer {key}"},
        timeout=KARAKEEP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def sync_reference_to_karakeep(  # noqa: PLR0913
    capture_id: str,
    text: str,
    enriched_text: str,
    tags: list[str] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Sync an enriched reference to Karakeep with graceful error handling.

    Wraps dispatch_reference_to_karakeep in try/except. On success, logs the
    sync via log_sync. On failure, logs the error and returns None without
    crashing.

    Args:
        capture_id: ID of the capture to log sync for.
        text: Original capture text.
        enriched_text: Enriched text content.
        tags: Optional tags for the bookmark.
        conn: Optional database connection.
        api_url: Override for Karakeep API URL.
        api_key: Override for Karakeep API key.

    Returns:
        Response dict on success, None on failure.
    """
    try:
        result = dispatch_reference_to_karakeep(
            text=text,
            enriched_text=enriched_text,
            tags=tags,
            api_url=api_url,
            api_key=api_key,
        )
        log_sync(capture_id, "karakeep", conn=conn)
    except (httpx.HTTPStatusError, httpx.ConnectError, ValueError):
        logger.exception("Failed to sync capture %s to Karakeep", capture_id)
        return None
    else:
        return result
