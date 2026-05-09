# Quick Capture

[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)

> Frictionless inbox capture for Hyprland — hotkey to floating terminal to saved entry, then enrich via LLM with wiki context.

Quick Capture lets you press a hotkey, type a thought in a floating terminal, and save it in under 5 seconds. Captures are then enriched via LLM using your Obsidian wiki as context, stored in SQLite, and synced back to the wiki as individual pages with daily/weekly rollups.

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Architecture](#architecture)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Background

Capturing thoughts should be zero friction. By the time you open a note app and find the right place to write, the thought is gone. Quick Capture solves this by leveraging Hyprland's window rules to spawn a floating terminal, Rich for the TUI, and `opencode run` for LLM-powered enrichment.

The tool integrates with an existing Obsidian wiki and Nexus dashboard, treating the wiki `.md` files as the source of truth and SQLite as a queryable cache.

**Core value:** Capture a thought in under 5 seconds, from hotkey to saved entry. Enrichment and review come after — the capture itself must be zero friction.

## Install

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Ghostty](https://ghostty.org/) terminal (or modify Hyprland config for your terminal)
- Hyprland window manager
- Obsidian vault (for wiki sync)

### Setup

```bash
git clone https://github.com/gabrielassisxyz/quick-capture.git
cd quick-capture
uv sync --all-groups
```

## Usage

### Launch the capture window

```bash
# Via Hyprland keybinding (recommended):
# Add to hyprland.conf: bind = $mainMod, C, exec, ai-jail opencode

# Or run directly:
uv run python -m quick_capture
```

### Enrich captures

```bash
# Process a single capture immediately:
uv run python -m quick_capture --enrich <capture_id>

# Batch process all unprocessed captures:
uv run python -m quick_capture --enrich-all
```

### View status

```bash
uv run python -m quick_capture --status
```

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌───────────┐     ┌─────────────┐
│  Hyprland   │────▶│  Rich    │────▶│  SQLite   │────▶│  Obsidian   │
│  Hotkey     │     │  TUI     │     │  (nexus)  │     │  Wiki       │
└─────────────┘     └──────────┘     └─────┬─────┘     └──────┬──────┘
                                           │                   │
                                           ▼                   │
                                    ┌──────────────┐           │
                                    │ opencode run │◀──────────┘
                                    │ (enrichment) │  (wiki-query
                                    └──────────────┘   context)
```

**Capture flow:** Hotkey → floating terminal → type thought → save → close (under 5 seconds).

**Enrichment flow:** Unprocessed entry → `opencode run` with wiki-query context → classified (Task/Idea/Reference/Question) → stored enriched → synced to wiki.

### Project Structure

```
src/quick_capture/
├── __init__.py     # Package init, exposes main()
├── __main__.py     # CLI entry point
├── capture.py      # TUI capture window (Rich)
├── db.py           # SQLite module (nexus.db tables)
├── enrich.py       # LLM enrichment via opencode run
└── sync.py         # Wiki sync (pages + rollups)
```

## Development

### Run the test suite

```bash
uv run pytest                    # all tests
uv run pytest tests/test_db.py   # single file
uv run pytest -k "test_capture"  # by name
uv run pytest --cov              # with coverage
```

### Lint, format, and type check

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check src/
```

### Quick check (run before every commit)

```bash
uv run ruff check . && uv run pytest
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Bug reports and feature requests welcome at [issues](https://github.com/gabrielassisxyz/quick-capture/issues).

## License

[MIT](LICENSE) © Gabriel Assis