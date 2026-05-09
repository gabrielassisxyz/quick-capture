# Quick Capture — AGENTS.md

> Think of this file as the briefing you'd give a new teammate on day one. It covers what the project does, how to set it up, how to run tests, and what rules to follow.

**What it is:** Frictionless inbox capture for Hyprland. Hotkey → floating terminal → save. Then enrich via LLM with wiki context, store in SQLite, sync to Obsidian wiki. Source of truth is the `.md` file in the vault.

**Core Value:** Capture a thought in under 5 seconds, from hotkey to saved entry. Enrichment and review come after — the capture itself must be zero friction.

## Stack

- **Python 3.12+** with **uv** (package manager, runner, venv)
- **ruff** — lint + format
- **ty** — type checker
- **pytest** — testing
- **Rich** — TUI for the floating capture window
- **SQLite** — local storage in `~/repositories/nexus/nexus.db`
- **opencode run** — LLM enrichment subprocess
- **Hyprland + Ghostty** — hotkey triggers floating terminal

## Dev Environment Setup

From a fresh clone to running:

```bash
cd ~/repositories/quick-capture
uv sync                          # install deps, create venv
cp .env.example .env             # if .env.example exists
uv run python -m quick_capture   # verify it starts
```

## Essential Commands

```bash
uv run pytest                    # run all tests
uv run pytest tests/test_db.py   # run a single test file
uv run pytest -k "test_capture"  # run tests matching a name
uv run ruff check .               # lint
uv run ruff format --check .      # format check
uv run ty check                   # type check
uv run python -m quick_capture    # run the app
```

Run `uv run ruff check .` and `uv run pytest` before every commit.

## Project Structure

```
quick-capture/
├── src/quick_capture/    # Application source code
│   ├── capture.py        # TUI capture window (Rich)
│   ├── db.py             # SQLite module (nexus.db tables)
│   ├── enrich.py         # LLM enrichment via opencode run
│   └── sync.py           # Wiki sync (pages + rollups)
├── tests/                # Unit and integration tests
├── .planning/            # GSD planning artifacts
└── AGENTS.md
```

## Architectural Principles

- **YAGNI:** Don't generate preventive abstractions. No interfaces for single implementations, no mappers between identical layers — unless explicitly requested.
- **Encapsulation > Inversion:** Prefer hiding implementation details inside well-defined modules. Use Dependency Inversion only when there's a real need to swap providers or enable complex mocks.
- **Flat architecture:** Keep the file structure as flat as possible. Minimize files per feature.
- **Blast radius:** Before modifying shared modules, describe what might break and which parts of the system will be affected.
- **Document the why:** For each relevant architectural decision, suggest an entry in `docs/architecture.md` explaining the motivation.

## Code Style

- **Python:** Follow the **modern-python** skill for all Python conventions (project setup, uv, ruff, ty, patterns). Activate it before writing Python code.
- **Language:** Everything in English — folder names, file names, variable names, function names, comments, commit messages, documentation.
- **Formatting:** ruff handles it. Don't discuss style beyond that.
- **Comments:** Keep your own comments. Don't strip them on refactor — they carry intent and provenance. Write WHY, not WHAT. Reference issue numbers / commit SHAs when a line exists because of a bug or upstream constraint.

## Tests

- Tests run with a single command: `uv run pytest`.
- **TDD discipline:** Every new behavior begins with a failing test, then the minimal code to pass, then refactor.
- Every bug fix gets a regression test: reproduce the failure first, then apply the fix.
- Every new function gets a test.
- Mock external I/O (filesystem, subprocess calls, SQLite) with named fakes, not inline stubs.
- Tests must be F.I.R.S.T: fast, independent, repeatable, self-validating, timely.

## Logging

- Structured JSON when logging for debugging/observability.
- Plain text only for user-facing CLI output.
- Network and subprocess calls must have explicit timeout.

## Git — Golden Rule

### Branch per task
- ALWAYS create a new branch before starting any task: `feat/<short-name>`, `fix/<short-name>`.
- NEVER work directly on `main`.
- If the user requests something new while you're on another branch, finish or commit the WIP and create a new branch.

### Atomic and frequent commits
- One commit per feature or fix. If the user asks for 3 things in the same prompt, that's 3 separate commits.
- If a file changed and the build/preview still works, commit.
- Message: `type: what changed` (e.g., `feat: capture window with Rich TUI`, `fix: db connection retry`).
- Don't accumulate changes. Once a logical unit of work is done, commit before starting the next.

### Push
- Run `git push` after every commit. Unpushed work is work that can be lost.
- If push fails, notify the user immediately.

### Before editing
- Run `git status` and `git diff` before any edit. If there are uncommitted changes, commit or warn BEFORE overwriting.
- NEVER overwrite a file without first verifying its current state. If the content differs from what you expect, STOP and ask.

## Agent Behavior

- **NEVER enter a thinking loop.** If you've tried the same approach twice without success, investigate it. If you still can't fix it, STOP and ask.
- **Thinking Stall Detection:** If you have made ≥2 tool calls in this conversation without a single `edit`, `write`, or `bash` execution that modifies the system, you are deliberating instead of acting. STOP immediately. Do not make a third thinking tool call. Either execute or ask the user.
- When in doubt, ask. The user resolves in seconds what you'd spend minutes guessing.
- If an operation runs >30s without progress, notify.
- If a tool fails more than once in a row, STOP and ask for direction.

## PR Instructions

- Title format: `feat: short description` / `fix: short description`
- Run `uv run ruff check .` and `uv run pytest` before opening a PR.
- Commits must pass all tests before merging.
- One logical change per PR. If you're touching capture + DB + wiki sync, that's three PRs.

## Anti-regression

- Before implementing any module, READ the full current file. Don't assume you know what's there.
- Never rewrite an entire file when a surgical edit will do.
- If you're unsure of the current state, ask the user for a screenshot or run the app and describe what you see.

## After Every Edit

- Re-read the file before editing it again.
- Run `uv run ruff check` and `uv run ty check` before declaring success.
- For large files, read in chunks — assume silent truncation of long results.

## Before Declaring Done, Verify

- Did you run `uv run pytest`? Do all tests pass?
- If you added/changed behavior, did you write/update the corresponding tests (TDD)?
- Did you update `docs/` if you changed features or file structure?
- Can this go to production?
- Is it readable?
- Is it secure?
- Is it maintainable?
- Does it integrate with the rest of the system?
- Does it solve the right problem?

## Boundaries

- ✅ **Always do:** Write tests before code (TDD), run `uv run ruff check` before committing, follow the modern-python skill conventions, create a branch before any work
- ⚠️ **Ask first:** Modifying nexus.db schema (extend, don't replace), adding new dependencies, changing the capture flow (must stay under 5 seconds)
- 🚫 **Never do:** Modify existing Nexus tables — only add new ones, commit secrets or API keys, work directly on `main`, persist UI state in the frontend (sessionStorage/localStorage)

## Don't

- Don't treat SQLite as source of truth — the vault `.md` files are source of truth, the database is just a cache.
- Don't build a custom API server for enrichment — use `opencode run`.
- Don't add a web framework — this is a CLI/TUI tool, not a web app.
- Don't go mobile-first — Arch Linux desktop with Hyprland, two 4K monitors.

## Wiki / Memory

- Wiki: `/home/gabriel/Documents/obsidian/Akademia/wiki/`
- Read wiki/hot.md for recent context
- Save architectural decisions: `/save`

## Security

- This project runs via `ai-jail` (bubblewrap sandbox).
- `rw`: project directory
- `ro`: `~/repositories`, `~/Documents/obsidian/Akademia`
- `.env`, `.env.local` files are masked in the jail.
- The project reads personal data from the vault — be careful with hardcoded paths.

## Known Hurdles

- **Hyprland window rules:** Need exact matching for the floating capture window — class/title must be consistent.
- **opencode run subprocess:** Invocation model is still being figured out. The enrichment pipeline depends on this interface.
- **nexus.db coupling:** Adding tables to a database owned by another project. Schema changes need coordination.
- **Work loss from missing commits:** This has happened on other projects. The branch + atomic commit + push rule exists because of this.