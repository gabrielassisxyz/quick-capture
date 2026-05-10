"""Wiki sync — create inbox pages, daily rollups, and weekly rollups."""

from __future__ import annotations

from pathlib import Path

VAULT_PATH = Path.home() / "Documents" / "obsidian" / "Akademia" / "wiki"


def sync_all_to_wiki(
    conn: object | None = None,  # noqa: ARG001 — placeholder, full impl in Task 2
    vault_path: Path | None = None,  # noqa: ARG001 — placeholder, full impl in Task 2
) -> int:
    """Sync all enriched captures to wiki pages and rollups.

    Placeholder — full implementation in Task 2.
    """
    return 0
