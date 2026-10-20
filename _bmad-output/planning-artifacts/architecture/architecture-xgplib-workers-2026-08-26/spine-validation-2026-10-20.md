# Architecture Spine Validation — xgplib-workers

- **Target:** `_bmad-output/planning-artifacts/architecture/architecture-xgplib-workers-2026-08-26/ARCHITECTURE-SPINE.md` @ `ac8aae4`, `status: final`, `updated: 2026-10-20`
- **Intent:** validate (spine unchanged by this run)
- **Date:** 2026-10-20
- **Gate:** `lint_spine.py` → 0 findings (**vacuous**: no `## Stack` section for the version-pin pass to check) · rubric walker · tech-currency lens · adversary lens

## Gate verdict

**NOT READY.** The spine is an accurate, well-enforced constitution for *hexagonal layering* — AD-1 and AD-7 are verified true against the shipped code — but it decides none of the system seams Epics 2–4 must build against, and `## Deferred` says "None", so every silence reads as a settled decision.

Three lenses, three NOT READY verdicts, no conflicting finding. Consolidated below by root cause; each finding names the two units that can obey every AD and still not compose.

## Checklist scorecard (rubric walker)

| Criterion | Verdict |
|---|---|
| Fixes the real divergence points for the level below, misses none | FAIL |
| Every AD's Rule is enforceable and prevents its stated divergence | PARTIAL |
| Nothing under Deferred could let two units diverge | FAIL |
| Named tech is verified-current | FAIL |
| Ratifies rather than contradicts the brownfield codebase | PASS (one false historical claim) |
| If a spec drove it, it covers that spec's capabilities | FAIL (CAP-2/3/4 ungoverned) |
| Inherited parent spine not weakened | N/A (none) |
| Every altitude-owned dimension decided, deferred, or open | FAIL (~8 silent, incl. the whole operational envelope) |

# Critical

## C-1 — The shared entity has no identity, no conflict target, no transaction boundary

*Root cause shared by:* rubric H5, adversary C1, adversary C5.

Stories 1.3 and 4.1 can each be written compliantly and still disagree about what a game *is*. Story 1.3's idiomatic `Game(id: UUID, product_id: str)` plus Story 4.1's `ON CONFLICT (id)` upsert means a re-hydrated entity carries a fresh uuid, so the hourly run re-inserts the same Microsoft product forever — while Story 4.1's own test passes, because it saves entities it created itself. Adding `UNIQUE(product_id)` instead pushes an `IntegrityError` out of the adapter with no AD-5 translation path.

AD-4 also describes mutation in the singular, so `for e in entries: repo.save(e)` is the most literal reading: a crash at item 2,500 leaves a half-migrated catalogue that C-2's deactivation path then turns into mass removals.

**Fix:** one AD fixing (a) the canonical identity — the upstream Microsoft product id, surrogate UUIDs forbidden, `UNIQUE(product_id)` at schema level; (b) the upsert contract `ON CONFLICT (product_id) DO UPDATE`; (c) the unit-of-work boundary per sync run; (d) the migration tool, pinned.

## C-2 — Availability cannot be expressed, and two mutation paths can delete the catalogue

*Root cause shared by:* adversary C2, adversary C4, rubric M6.

FR-1.1 requires market × platform (PC/console/cloud) × plan. Story 2.1 returns ids *per endpoint* (Console, PC, EA Play); Story 4.2 flips one boolean. A title leaving Console but staying on PC is deactivated. The reciprocal choice (union the slices) is equally AD-compliant and makes "added" unobservable. The entity has no room for `{console: yes, pc: no, market: de-DE}`.

Worse: Story 4.1's upsert sets active, Story 4.2 bulk-deactivates ids absent from the fetch. A failed hydration batch under NFR-1 ("skip gracefully") yields a smaller catalogue → mass false soft-delete, no exception raised, AD-5 satisfied.

**Fix:** availability as a set of `Availability(market, platform, plan)` value objects owned by the aggregate and persisted in its own table; no scalar `is_active`; "soft-deleted" means the availability set is empty; transitions applied once per run from the union of all slices; the deactivation path gated on fetch completeness; a run lock.

## C-3 — The JSONB column has two uncoordinated writers

*Root cause:* FR-3.1 + Story 3.2 + Story 3.3, governed by nothing.

Ingestion stores `{"raw_microsoft": …}` (required by Story 3.3); enrichment replaces the whole column with IGDB keys. For matched titles the raw payload is destroyed; it survives only on unmatched titles — precisely the population Story 3.3 tests. AD-7 *prevents* the domain from naming the shape (Pydantic DTOs must live in infrastructure), so nothing can validate it. Key-name drift between the two writers means no consumer can read the column without knowing which writer ran last.

**Fix:** namespaced merge-on-write document — `raw` (Microsoft, write-once) and `enrichment` (IGDB, replaceable) — each namespace with a declared shape, one mapper in infrastructure, persistence merges by namespace key and may never replace the whole column; a write that drops a namespace it does not own is a domain error, tested.

## C-4 — The spine governs no system seam; `Deferred` claims otherwise

*Root cause shared by:* rubric C1, rubric C2, rubric H8.

All seven ADs are about *how Python code is arranged*. No AD names a component, port, or rule for: the two-step Microsoft extraction, IGDB enrichment, change detection, upserts/soft-deletes, hourly execution. Stories 2.1 and 3.1 can pick different HTTP clients and retry styles and both stay canonical.

The operational/environmental envelope is entirely silent — deployment target, environments, how PostgreSQL is provisioned, what tests run against, how secrets arrive, where the unmatched-title log goes — and `## Deferred` says "None explicitly deferred", so a reader is told these are settled. The live symptom already exists: `.gitignore` has no `.env` pattern and the item sits in `deferred-work.md` instead of the spine.

**Fix:** ADs for external integration (one client, batching/rate limits, one port per external system), resilience, persistence, execution/scheduling, configuration & secrets, operations (log fields servable to the manual-review query), and testing strategy — each `Binds:` citing CAP-/FR-/NFR- IDs — plus a `## Capability → Architecture Map` and a populated `## Deferred`.

## C-5 — The stack is asserted, not researched, and two implied defaults moved

*Root cause shared by:* tech-currency C1, C2, H1–H5, M2–M3.

No version, no Python baseline, no source anywhere; the memlog shows the stack arriving as a user direction and leaving as a decision with no lookup (`memlog.md:16-17`). Spot-checked independently during this validation:

- **SQLAlchemy 2.1.5** (2026-10-16) is now the default install; 2.1.0 was the first production release (2026-09-24). `greenlet` is no longer installed by default (breaks async unless `sqlalchemy[asyncio]`), and `postgresql://` now resolves to **psycopg 3**.
- **`httpx`** has had no stable release since 2024-12-06; the maintained continuation is **`httpx2`** (Pydantic fork, 2.13.1, 2026-09-23).
- **AD-2's DI container is unnamed** in a live four-way choice — `dependency-injector` 4.49.1, `dishka` 1.10.1, `punq` 0.9.0, `injector` 0.24.0 — and the PyPI name `python-dependency-injector` is an unrelated 1,870-byte stub.

**Fix:** add a `## Stack` table (pin / role+layer / verified date) and reduce AD-6 to a pointer at it; name the DI container with its distribution name and composition-root path.

# High

- **H-1 Sync vs async is undecided**, which fixes every port signature, the driver (`Session` vs `AsyncSession` + async driver) and the client (`Client` vs `AsyncClient`). An hourly network-bound worker reads naturally as async. *[rubric H1]*
- **H-2 Port ownership is contradictory.** AD-3 says ports are domain-defined; the diagram and README put them in `application`. Both placements pass the shipped contract, so the machinery cannot detect the divergence. *[rubric H2; adversary]*
- **H-3 AD-2 and AD-7 cannot both be satisfied as written.** Mainstream containers need markers on the classes that live in `application`, which AD-7 forbids. Name the container, put the composition root in infrastructure, require plain constructor injection in use cases. *[rubric H3, tech M5]*
- **H-4 Resilience has no AD** although NFR-1 is a hard constraint in four artifacts: where retries/circuit breakers live, which library, where thresholds come from, what "skip gracefully" means for the use case. *[rubric H4]*
- **H-5 AD-7 is not mechanically enforceable as written.** import-linter has no "any external" wildcard; `forbidden_modules` must be exact top-level package names, and `include_external_packages` is a **top-level session option**, not a contract key — the spine's phrasing invites a config import-linter rejects. *[rubric H6, verified against the installed import-linter]*
- **H-6 AD-5 has no retryable-vs-permanent taxonomy**, so an IGDB outage is indistinguishable from a no-match, and no rule requires adapters to translate third-party exceptions inward. *[adversary, rubric H4]*
- **H-7 Entrypoints may call repositories directly** — infrastructure is one layer, and AD-4 binds only use cases. *[adversary]*
- **H-8 No migration tool is named** while Epic 1 promises migrations; Alembic's current floor is SQLAlchemy 2.0. *[rubric H5, tech H3]*

# Medium (tail)

- Binds are prose restatements, not CAP-/FR-/NFR- IDs; no Capability → Architecture Map.
- No Consistency Conventions table: naming, id representation, UTC/`*_at` convention, error shape, log fields, config variable names.
- **AD-1's historical note is factually wrong** (see *Regression* below).
- AD-5 names no module home for the exception hierarchy and no base-class contract.
- Testing strategy unowned (port fakes vs HTTP fixtures, ephemeral PostgreSQL, coverage gate).
- Market/language scope undecided, which decides whether the persistence key is `(id)` or `(id, market)`.
- Flat top-level import roots (`domain`, `application`, `infrastructure` in site-packages) neither ratified nor flagged.
- Frontmatter carries no `purpose`, `altitude`, `binds`, or `sources`, so the document never claims what it governs.
- Port granularity and the 200-id batch constant unowned.
- Python 3.12 is security-only while unratified; `ruff>=0.6` floor vs 0.17.1 current; `pydantic-settings` is a separate top-level package AD-7's list would miss; no dependency-provenance convention.

# Low (tail)

- AD-3's "fail-fast instantiation" claim has no test.
- AD-4 sets no port surface (methods, return types).
- AD-1 says the contract "fails the build"; the gate is CI + pytest, not a build hook.
- Reproducibility unstated (lockfile committed, `uv sync --locked`).
- The diagram has no composition root or scheduler node, so it will drift at Stories 1.2 and 2.4.
- Package manager and build backend unnamed.

# Regression introduced during this validation cycle

**AD-1's note is false.** AD-1 (`:28`) claims the boundary tests "caught an inverted `layers` order that the declarative contract alone reported as kept (`37bb259`)". Verified against git: the shipped order was already correct at `f27724c`, and `37bb259` never touched `pyproject.toml` — it fixed the *tests*, because an inverted order **would have shipped undetected**. The sentence was added by `cdf5ba9` (this cycle's doc commit) and should be corrected to: *"the review of Story 1.1 found the direction was never verified — an inverted `layers` order would have shipped reporting KEPT (`37bb259`) — so the tests are deliberate; do not remove them."*

# What the spine gets right (keep)

- **AD-1** as three named, mechanical enforcement layers, with the instruction not to remove the subprocess tests — every part verified true against `pyproject.toml` and `tests/test_layers.py`.
- **AD-7's direction** is the most valuable invariant in the document; the `include_external_packages` trap it names is real. It needs enforcement, not removal.
- Every brownfield fact checked is accurate: layer order, `root_packages`, parity test, three negative controls plus a positive control, per-layer `src/<layer>` resolution, and the CI-gate assertions.

# Recommended next step

An **Update** pass (spine changes, AD IDs stable, AD-8 onward). Suggested order, cheapest first:

1. Fix AD-1's false historical note and reword AD-7 to the enforceable form. *(minutes)*
2. Add `## Stack` with pins and verified dates; name the DI container; populate `## Deferred`. *(one pass)*
3. Decide the load-bearing calls: sync vs async, identity key, availability model, JSONB namespaces, transaction boundary, resilience policy, config & secrets. *(needs your input)*
4. Add the operational envelope: deployment, environments, PostgreSQL provisioning, observability, testing strategy.

The three reviewer files hold the full evidence and paste-ready AD text: `reviews/review-rubric-walker.md`, `reviews/review-tech-currency.md`, `reviews/review-adversary.md`.
