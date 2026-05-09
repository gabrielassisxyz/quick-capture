# State: Quick Capture

**Last updated:** 2026-05-09
**Current phase:** — (not started)
**Project status:** initialized

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-09)

**Core value:** Capture a thought in under 5 seconds, from hotkey to saved entry.
**Current focus:** Phase 1 — Capture & Enrich MVP

## Phase Progress

| Phase | Name | Status | Plans | Progress |
|-------|------|--------|-------|----------|
| 1 | Capture & Enrich MVP | ○ Not started | 0/3 | 0% |
| 2 | Wiki Sync & Karakeep | ○ Not started | 0/0 | 0% |
| 3 | Flexible Processing | ○ Not started | 0/0 | 0% |
| 4 | Dispatch Discussion | ○ Not started | 0/0 | 0% |

## Active Blockers

None.

## Key Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-09 | SQLite as primary store, wiki as sync | Nexus already uses SQLite; wiki provides knowledge graph |
| 2026-05-09 | opencode run for enrichment | Leverages wiki-query skill, context-aware, no custom API |
| 2026-05-09 | One page per capture + rollups | Matches existing wiki pattern, enables cross-linking |
| 2026-05-09 | Karakeep for references | Karakeep already handles bookmarks with intent retrieval |
| 2026-05-09 | Vertical MVP structure | Each phase delivers working end-to-end capability |
| 2026-05-09 | Separate tables in nexus.db | Don't extend existing schema, add new tables for captures |