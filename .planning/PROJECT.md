# Quick Capture

## What This Is

A frictionless inbox capture tool for Hyprland that lets you press a hotkey, type a thought in a floating terminal, and save it — then enriches that thought via LLM using your Obsidian wiki as context. Enriched entries are stored in SQLite (queryable by Nexus) and synced to the wiki as individual pages plus daily/weekly rollups. Review happens through Nexus (web UI now, TUI later).

## Core Value

Capture a thought in under 5 seconds, from hotkey to saved entry. The enrichment and review come after — the capture itself must be zero friction.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Hotkey triggers floating terminal in Hyprland for text capture
- [ ] Multiline text entry with save-and-close on submit
- [ ] Entry saved to SQLite database with original text, timestamp, and status
- [ ] LLM enrichment via `opencode run` using wiki-query skill for context
- [ ] Enrichment preserves original capture alongside developed content
- [ ] Enrichment classifies entry into buckets: Task, Idea, Reference, Question
- [ ] References are sent to Karakeep with intent retrieval notes
- [ ] SQLite storage integrates with existing nexus.db at ~/repositories/nexus/
- [ ] Wiki sync: one page per capture (source: inbox) + daily/weekly rollup pages
- [ ] Multiple processing triggers: immediate, batch (after N captures), on-demand from UI
- [ ] Nexus web UI can display and filter enriched entries by bucket
- [ ] Optional dispatch: discuss with LLM further before sending to a project

### Out of Scope

- Mobile capture — desktop-only (Hyprland hotkey)
- Voice input — text only
- Real-time sync across devices — local-first
- Automatic task execution (GSD-style dispatch) — this tool enriches, it doesn't execute

## Context

- **Prior art:** `~/repositories/llm-cli/quickask.py` — proven pattern for floating terminal + Hyprland + LLM API calls. Uses Ghostty with window rules, Rich for TUI, httpx for API.
- **Wiki:** Obsidian vault at `~/Documents/obsidian/Akademia/` with wiki-query skill for context retrieval
- **Nexus:** Project dashboard at `~/repositories/nexus/` with SQLite DB (`nexus.db`) schema: projects, tasks, sessions, project_tags, project_backlog_items, project_logs
- **Karakeep:** Bookmark manager with intent retrieval support
- **OpenCode CLI:** `opencode run` supports non-interactive prompts, enabling programmatic LLM enrichment
- **Analog inspiration:** The Analog Capture concept (folha A6) — physical constraint forces prioritization, this tool mirrors that digitally

## Constraints

- **Environment:** Arch Linux with Hyprland (Omarchy), Ghostty terminal
- **Wiki immutability:** Agent writes only to `wiki/` subdirectory in the Obsidian vault; daily/weekly rollups must go there
- **Nexus DB:** Must use existing `~/repositories/nexus/nexus.db` schema — extend, don't replace
- **Processing model:** `opencode run` for enrichment (not a custom API server)
- **Capture friction:** Hotkey to saved entry must be under 5 seconds for the capture itself

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite as primary store, wiki as sync target | Nexus already uses SQLite; fast queries, easy integration with web/TUI; wiki provides knowledge graph and searchability | — Pending |
| `opencode run` for enrichment | Leverages existing wiki-query skill natively, no custom API needed, context-aware enrichment | — Pending |
| One page per capture + rollups | Matches existing wiki pattern, enables cross-linking, daily/weekly rollups for reviewability | — Pending |
| Karakeep integration for references | References are URLs/links — Karakeep already handles bookmarking with intent retrieval notes | — Pending |
| Flexible processing triggers | Different thoughts need different timing — some are urgent, some benefit from batching | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-09 after initialization*