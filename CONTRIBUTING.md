# Contributing to Quick Capture

First off, thank you for considering contributing to Quick Capture. It's people like you that make this tool better.

## How Can I Contribute?

### Reporting Bugs

- Open an [issue](https://github.com/gabrielassisxyz/quick-capture/issues/new?labels=bug&template=bug_report.md) with a clear title and description
- Include steps to reproduce, expected vs actual behavior, and your environment (OS, Python version, terminal)
- Check existing issues to avoid duplicates

### Suggesting Features

- Open an [issue](https://github.com/gabrielassisxyz/quick-capture/issues/new?labels=enhancement&template=feature_request.md) describing the problem you're trying to solve
- Explain why it fits the project's scope (frictionless capture, under 5 seconds from hotkey to saved entry)

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Make your changes with tests
4. Ensure all checks pass:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run ty check src/
   uv run pytest
   ```
5. Commit with a descriptive message following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation
   - `refactor:` code refactor
   - `test:` adding tests
6. Open a pull request against `main`

## Development Setup

```bash
git clone https://github.com/gabrielassisxyz/quick-capture.git
cd quick-capture
uv sync --all-groups
```

### Run the app

```bash
uv run python -m quick_capture
```

### Run tests

```bash
uv run pytest
uv run pytest -k "test_capture"   # run a single test
uv run pytest --cov                # with coverage
```

### Lint and format

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check src/
```

## Project Structure

```
quick-capture/
├── src/quick_capture/    # Application source code
│   ├── capture.py        # TUI capture window (Rich)
│   ├── db.py             # SQLite module (nexus.db tables)
│   ├── enrich.py         # LLM enrichment via opencode run
│   └── sync.py           # Wiki sync (pages + rollups)
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
└── pyproject.toml        # Project configuration
```

## Coding Conventions

- Follow the existing code style — [ruff](https://docs.astral.sh/ruff/) handles formatting and linting
- Write tests for any new behavior (TDD discipline)
- One logical change per commit, one logical change per PR
- Every bug fix gets a regression test
- Mock external I/O (filesystem, subprocess calls, SQLite) with named fakes, not inline stubs
- Comments explain WHY, not WHAT

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.