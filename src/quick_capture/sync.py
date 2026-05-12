"""Wiki sync — create inbox pages, daily rollups, and weekly rollups."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from contextlib import suppress
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter

from quick_capture.db import get_enrichment, get_unsynced_captures, log_sync
from quick_capture.karakeep import sync_reference_to_karakeep

logger = logging.getLogger(__name__)

VAULT_PATH = Path.home() / "Documents" / "obsidian" / "Akademia" / "wiki"


def _validate_vault_path(page_path: Path, vault_path: Path) -> Path:
    """Ensure page_path resolves to within the vault directory.

    Raises ValueError if path traversal is detected.
    """
    resolved = page_path.resolve()
    vault_root = vault_path.resolve()
    if not str(resolved).startswith(str(vault_root) + os.sep) and resolved != vault_root:
        msg = f"Path traversal detected: {resolved} is outside vault {vault_root}"
        raise ValueError(msg)
    return resolved


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically using temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        Path(tmp_path).replace(path)
    except BaseException:
        with suppress(OSError):
            Path(tmp_path).unlink()
        raise


def create_inbox_page(  # noqa: PLR0913
    capture_id: str,
    original_text: str,
    enriched_text: str,
    bucket: str,
    tags: list[str],
    wikilinks: list[str],
    created_at: str,
    vault_path: Path | None = None,
) -> Path:
    """Create an Obsidian wiki page for an enriched capture.

    Idempotent: if a page with the same capture_id already exists, returns its path.
    Uses capture_id[:8] in filename for deterministic deduplication.
    """
    vault = vault_path or VAULT_PATH
    page_date = date.fromisoformat(created_at[:10])
    short_id = capture_id[:8]
    filename = f"{page_date.isoformat()}-quick-capture-{short_id}.md"
    page_path = vault / "inbox" / filename

    # Validate path stays within vault (T-2-01)
    _validate_vault_path(page_path, vault)

    # Idempotency: check frontmatter capture_id
    if page_path.exists():
        existing = frontmatter.load(page_path)
        if existing.metadata.get("capture_id") == capture_id:
            return page_path  # Already synced — no-op

    # Build page content
    content = f"# {original_text[:80]}\n\n{enriched_text}\n"
    if wikilinks:
        content += "\n## Related\n\n"
        for wl in wikilinks:
            content += f"- [[{wl}]]\n"

    # Build metadata
    metadata: dict[str, Any] = {
        "type": "inbox",
        "title": original_text[:80],
        "source": "inbox",
        "capture_id": capture_id,
        "bucket": bucket,
        "created": page_date.isoformat(),
        "updated": page_date.isoformat(),
        "tags": [*tags, "inbox", "quick-capture", bucket.lower()],
        "status": "current",
        "related": [f"[[{wl}]]" for wl in wikilinks],
    }

    post = frontmatter.Post(content)
    post.metadata = metadata
    _atomic_write(page_path, frontmatter.dumps(post))
    return page_path


def create_daily_rollup(
    target_date: date,
    entries: list[dict[str, Any]],
    vault_path: Path | None = None,
) -> Path:
    """Create or update a daily rollup page for the given date.

    Args:
        entries: List of dicts with capture_id, title, bucket keys.
    """
    vault = vault_path or VAULT_PATH
    filename = f"{target_date.isoformat()}.md"
    page_path = vault / "inbox" / "rollups" / "daily" / filename

    _validate_vault_path(page_path, vault)

    children = [
        {
            "capture_id": e["capture_id"],
            "title": e["title"][:80],
            "bucket": e["bucket"],
            "page": f"[[{target_date.isoformat()}-quick-capture-{e['capture_id'][:8]}]]",
        }
        for e in entries
    ]

    date_str = target_date.isoformat()
    content = f"# Daily Rollup — {date_str}\n\n"
    content += f"## Captures ({len(entries)})\n\n"
    for child in children:
        content += f"### {child['page']}\n"
        content += f"> {child['title']} — **{child['bucket']}**\n\n"

    week_num = target_date.isocalendar()[1]
    content += f"\n---\nSee also: [[{target_date.year}-W{week_num:02d}]]\n"

    metadata: dict[str, Any] = {
        "type": "rollup",
        "rollup_type": "daily",
        "title": f"Daily Rollup — {date_str}",
        "date": date_str,
        "created": date_str,
        "updated": date_str,
        "tags": ["rollup", "daily", "inbox"],
        "status": "current",
        "children": children,
        "related": [f"[[{target_date.year}-W{week_num:02d}]]"],
    }

    post = frontmatter.Post(content)
    post.metadata = metadata
    _atomic_write(page_path, frontmatter.dumps(post))
    return page_path


def create_weekly_rollup(
    year: int,
    week_num: int,
    daily_entries: list[dict[str, Any]],
    vault_path: Path | None = None,
) -> Path:
    """Create a weekly rollup page aggregating daily rollups.

    Args:
        daily_entries: List of dicts with date, title, children keys.
    """
    vault = vault_path or VAULT_PATH
    filename = f"{year}-W{week_num:02d}.md"
    page_path = vault / "inbox" / "rollups" / "weekly" / filename

    _validate_vault_path(page_path, vault)

    children = [
        {
            "date": entry["date"],
            "title": entry.get("title", f"Daily Rollup — {entry['date']}"),
            "page": f"[[{entry['date']}]]",
        }
        for entry in daily_entries
    ]

    content = f"# Weekly Rollup — {year}-W{week_num:02d}\n\n"
    content += f"## Daily Rollups ({len(daily_entries)})\n\n"
    for child in children:
        content += f"### {child['page']}\n"
        content += f"> {child['title']}\n\n"

    metadata: dict[str, Any] = {
        "type": "rollup",
        "rollup_type": "weekly",
        "title": f"Weekly Rollup — {year}-W{week_num:02d}",
        "created": f"{year}-W{week_num:02d}",
        "updated": f"{year}-W{week_num:02d}",
        "tags": ["rollup", "weekly", "inbox"],
        "status": "current",
        "children": children,
    }

    post = frontmatter.Post(content)
    post.metadata = metadata
    _atomic_write(page_path, frontmatter.dumps(post))
    return page_path


def sync_capture_to_wiki(
    capture_id: str,
    conn: object | None = None,
    vault_path: Path | None = None,
) -> Path | None:
    """Sync a single capture to wiki. Returns path or None on failure.

    After wiki sync, Reference-classified captures are dispatched to Karakeep.
    Karakeep failures are logged as warnings and do not affect the return value.
    """
    try:
        enrichment = get_enrichment(capture_id, conn=conn)
        if enrichment is None:
            logger.warning("No enrichment found for capture %s", capture_id)
            return None

        tags = enrichment["tags"]
        if isinstance(tags, str):
            tags = json.loads(tags)
        wikilinks_list = enrichment["wikilinks"]
        if isinstance(wikilinks_list, str):
            wikilinks_list = json.loads(wikilinks_list)

        path = create_inbox_page(
            capture_id=capture_id,
            original_text=enrichment["original_text"],
            enriched_text=enrichment["enriched_text"],
            bucket=enrichment["bucket"],
            tags=tags,
            wikilinks=wikilinks_list,
            created_at=enrichment["created_at"],
            vault_path=vault_path,
        )
        log_sync(capture_id, "wiki", conn=conn)
    except Exception:
        logger.exception("Failed to sync capture %s to wiki", capture_id)
        return None

    if enrichment["bucket"] == "Reference":
        sync_reference_to_karakeep(
            capture_id=capture_id,
            text=enrichment["original_text"],
            enriched_text=enrichment["enriched_text"],
            tags=tags,
            conn=conn,
        )

    return path


def sync_all_to_wiki(
    conn: object | None = None,
    vault_path: Path | None = None,
) -> int:
    """Full sync pipeline: sync all unsynced enriched captures to wiki.

    Creates individual inbox pages, daily rollups, and weekly rollups.
    Returns count of synced captures.
    """
    unsynced = get_unsynced_captures(target="wiki", conn=conn)

    if not unsynced:
        return 0

    synced_paths: list[dict[str, Any]] = []
    for row in unsynced:
        # Parse tags/wikilinks from JSON
        tags = row["tags"]
        if isinstance(tags, str):
            tags = json.loads(tags)
        wikilinks_list = row["wikilinks"]
        if isinstance(wikilinks_list, str):
            wikilinks_list = json.loads(wikilinks_list)

        path = sync_capture_to_wiki(
            capture_id=row["id"],
            conn=conn,
            vault_path=vault_path,
        )
        if path:
            synced_paths.append(
                {
                    "capture_id": row["id"],
                    "title": row["original_text"][:80],
                    "bucket": row["bucket"],
                    "date": row["created_at"][:10],
                }
            )

    # Group by date for daily rollups
    date_groups: dict[str, list[dict[str, Any]]] = {}
    for entry in synced_paths:
        date_groups.setdefault(entry["date"], []).append(entry)

    # Create daily rollups
    for target_date_str, date_entries in date_groups.items():
        target_date = date.fromisoformat(target_date_str)
        create_daily_rollup(
            target_date=target_date,
            entries=date_entries,
            vault_path=vault_path,
        )

    _build_weekly_rollups(date_groups, vault_path)

    return len(synced_paths)


def _build_weekly_rollups(
    date_groups: dict[str, list[dict[str, Any]]],
    vault_path: Path | None,
) -> None:
    """Create weekly rollup pages from date-grouped captures."""
    week_groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for target_date_str, date_entries in date_groups.items():
        d = date.fromisoformat(target_date_str)
        iso = d.isocalendar()
        week_groups.setdefault((iso[0], iso[1]), []).append(
            {
                "date": target_date_str,
                "title": f"Daily Rollup — {target_date_str}",
                "children": date_entries,
            }
        )

    for (year, week_num), daily_entries in week_groups.items():
        create_weekly_rollup(
            year=year,
            week_num=week_num,
            daily_entries=daily_entries,
            vault_path=vault_path,
        )
