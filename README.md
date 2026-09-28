# xgplib-workers

Hexagonal worker that synchronizes the Xbox Game Pass catalog.

The codebase follows Clean Code and Hexagonal Architecture (Ports and Adapters).
Dependencies point inward: `infrastructure` may import `application` and
`domain`; `application` may import `domain`; `domain` imports neither. The rule
is enforced mechanically by [import-linter](https://import-linter.readthedocs.io/),
not by convention alone.

## Requirements

- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 and dependencies)

## Setup

```bash
uv sync
```

`uv` installs Python 3.12 as pinned by `.python-version`, creates `.venv`, and
installs the dev tools.

## Commands

| Command | Purpose |
| --- | --- |
| `uv run ruff check .` | Lint (PEP-8) |
| `uv run ruff format --check .` | Verify formatting |
| `uv run ruff format .` | Apply formatting |
| `uv run lint-imports` | Enforce the hexagonal dependency rule |
| `uv run pytest` | Run the test suite |

The lint, format-check, boundary, and test commands run in CI on Python 3.12
(`.github/workflows/ci.yml`); applying formatting (`uv run ruff format .`) stays
local.

## Layout

```
src/
  domain/          # Pure entities, value objects, domain exceptions
  application/     # Use cases and ports (abc.ABC interfaces)
  infrastructure/  # Adapters, entrypoints, framework wiring
tests/             # Test suite
```
