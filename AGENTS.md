<!-- GSD:project-start source:PROJECT.md -->
## Project

**Quick Capture**

A frictionless inbox capture tool for Hyprland that lets you press a hotkey, type a thought in a floating terminal, and save it — then enriches that thought via LLM using your Obsidian wiki as context. Enriched entries are stored in SQLite (queryable by Nexus) and synced to the wiki as individual pages plus daily/weekly rollups. Review happens through Nexus (web UI now, TUI later).

**Core Value:** Capture a thought in under 5 seconds, from hotkey to saved entry. The enrichment and review come after — the capture itself must be zero friction.

### Constraints

- **Environment:** Arch Linux with Hyprland (Omarchy), Ghostty terminal
- **Wiki immutability:** Agent writes only to `wiki/` subdirectory in the Obsidian vault; daily/weekly rollups must go there
- **Nexus DB:** Must use existing `~/repositories/nexus/nexus.db` schema — extend, don't replace
- **Processing model:** `opencode run` for enrichment (not a custom API server)
- **Capture friction:** Hotkey to saved entry must be under 5 seconds for the capture itself
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
