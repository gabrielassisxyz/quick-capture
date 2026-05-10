---
phase: 2
slug: wiki-sync-karakeep
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-05-09"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_sync.py tests/test_karakeep.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_sync.py tests/test_karakeep.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | STOR-03 | T-2-01 | Vault path validated within allowed dir | unit | `uv run pytest tests/test_sync.py::test_create_inbox_page -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | STOR-03 | T-2-03 | python-frontmatter handles YAML escaping | unit | `uv run pytest tests/test_sync.py::test_inbox_page_frontmatter -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | STOR-03 | — | Idempotent re-sync doesn't duplicate pages | unit | `uv run pytest tests/test_sync.py::test_inbox_page_idempotent -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | STOR-04 | — | Daily rollup aggregates all captures for a day | unit | `uv run pytest tests/test_sync.py::test_daily_rollup -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | STOR-04 | — | Daily rollup links to individual capture pages | unit | `uv run pytest tests/test_sync.py::test_daily_rollup_links -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | STOR-05 | — | Weekly rollup aggregates daily rollups | unit | `uv run pytest tests/test_sync.py::test_weekly_rollup -x` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 1 | STOR-05 | — | Weekly rollup links to daily rollup pages | unit | `uv run pytest tests/test_sync.py::test_weekly_rollup_links -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | REVW-03 | T-2-02 | API key never logged | unit | `uv run pytest tests/test_karakeep.py::test_dispatch_reference -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | REVW-03 | T-2-04 | Karakeep failure doesn't crash sync | unit | `uv run pytest tests/test_karakeep.py::test_karakeep_failure_graceful -x` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 2 | REVW-03 | — | URL detection for link vs text bookmark type | unit | `uv run pytest tests/test_karakeep.py::test_url_detection -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_sync.py` — stubs for STOR-03, STOR-04, STOR-05
- [ ] `tests/test_karakeep.py` — stubs for REVW-03
- [ ] Dependency install: `uv add python-frontmatter httpx` — both packages needed
- [ ] Existing test coverage omits sync.py (not yet created)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Wiki page appears in Obsidian | STOR-03 | Requires Obsidian to index the vault directory | Open Obsidian, navigate to inbox/, verify new page appears |
| Karakeep bookmark created | REVW-03 | Requires live Karakeep instance | Open Karakeep UI, verify bookmark appears with correct note |
| Daily rollup links resolve | STOR-04 | Requires Obsidian wikilink resolution | Click wikilinks in daily rollup, verify each resolves to capture page |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending