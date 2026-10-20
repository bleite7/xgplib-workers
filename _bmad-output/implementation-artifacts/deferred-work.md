# Deferred Work

## Open

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-establish-project-skeleton-hexagonal-boundaries.md`
  summary: `.gitignore` carries no `.env`/secret patterns, and the worker will hold Microsoft/IGDB credentials.
  evidence: Surfaced by the Story 1.1 review (2026-10-20) and deferred because no config or credential file exists until Story 1.2. Real risk once Pydantic configuration lands: a committed `.env` would leak credentials that the ignore file does not cover. Add `.env`, `.env.*` with a `!.env.example` exception alongside the configuration work.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-establish-project-skeleton-hexagonal-boundaries.md`
  summary: `[project]` metadata is incomplete — no authors, keywords, classifiers, urls, or `[project.scripts]` entrypoint.
  evidence: Deferred from the Story 1.1 review (2026-10-20): no runnable entrypoint is in scope (hourly scheduling lands in Story 2.4), and release metadata is packaging polish rather than skeleton/boundaries. Revisit when the worker gains its entrypoint.

## Resolved

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-establish-project-skeleton-hexagonal-boundaries.md`
  summary: Architecture spine AD-1 credited Ruff for import linting while boundary enforcement is implemented with import-linter.
  resolution: (2026-10-20) AD-1 rewritten to name the three enforcement layers — folder convention, the import-linter `layers` contract in `pyproject.toml`, and the executable negative controls in `tests/test_layers.py`. Ruff is scoped to style and formatting, and the tests are explicitly marked as deliberate (they caught the inverted `layers` order fixed in `37bb259`). AD-6 now lists import-linter in the foundational stack.
  evidence: `_bmad-output/planning-artifacts/architecture/architecture-xgplib-workers-2026-08-26/ARCHITECTURE-SPINE.md` (AD-1, AD-6)

## Resolved from: code review of spec-1-1-establish-project-skeleton-hexagonal-boundaries (2026-09-28)

- Architecture spine AD-1 and Epic 1 context credited Ruff for import linting and rejected "heavyweight architecture tests", while the implementation uses an import-linter `layers` contract plus a subprocess architecture test suite (278 lines at time of resolution).
  resolution: (2026-10-20) Spine AD-1 refreshed as above; `epic-1-context.md` rewritten to describe the import-linter contract plus executable boundary tests and to state that the tests are intentional. The "no heavyweight architecture tests" clause is gone.

- The `[tool.importlinter]` `layers` contract governs only `domain`, `application`, and `infrastructure`, so nothing stopped those layers from importing third-party libraries once Stories 1.2/1.3 introduce SQLAlchemy and Pydantic — leaving the "external APIs and the database stay decoupled from core logic" goal without a mechanical guard.
  resolution: (2026-10-20) New invariant **AD-7 (Framework Isolation of Domain and Application)** makes the inner layers framework-free and mandates an import-linter `forbidden` contract with `include_external_packages = true` (without that flag the contract ignores external packages and passes vacuously), each contract paired with a negative control in `tests/test_layers.py`. Rollout is scheduled in the story acceptance criteria: Story 1.2 forbids `pydantic` in `domain`/`application`, Story 1.3 extends the set to `sqlalchemy` and the PostgreSQL driver.
  evidence: `ARCHITECTURE-SPINE.md` (AD-7) · `_bmad-output/planning-artifacts/epics.md` (Stories 1.2 and 1.3)
