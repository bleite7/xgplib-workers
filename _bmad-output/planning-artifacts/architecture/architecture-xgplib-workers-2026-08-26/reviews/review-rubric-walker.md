# Rubric walker review — ARCHITECTURE-SPINE.md (xgplib-workers)

- Reviewer lens: good-spine checklist (rubric walker), `.agents/skills/bmad-architecture/references/reviewer-gate.md:11`
- Target: `_bmad-output/planning-artifacts/architecture/architecture-xgplib-workers-2026-08-26/ARCHITECTURE-SPINE.md` @ `ac8aae4`, status `final`, updated 2026-10-20
- Ground truth read: `pyproject.toml`, `tests/test_layers.py`, `.github/workflows/ci.yml`, `_bmad-output/specs/spec-xgplib-workers/SPEC.md`, `_bmad-output/planning-artifacts/epics.md`, `_bmad-output/planning-artifacts/prds/prd-xgplib-workers-2026-08-25/prd.md`, research note, `deferred-work.md`, `uv.lock`, git history (`f27724c`, `37bb259`, `20fcb23`, `cdf5ba9`, `ac8aae4`).

## Verdict

**NOT READY — needs another decision pass (do not hand to the epic level as-is).**

The spine is an accurate, well-enforced *constitution for hexagonal layering* (AD-1 and AD-7 are genuinely good and ratify the shipped code), but it is not a spine for *this system*: seven of seven ADs are generic Clean/Hexagonal rules, and none decides any of the seams Epics 2–4 must build against (HTTP/integration policy, resilience, persistence identity/transactions, scheduling, config/secrets, operations, deployment). The `## Deferred` section says "None", so the silence is not recoverable from the document: a story builder cannot tell a real decision from an omission. The mechanical lint passes with **zero findings only because the spine has no `## Stack` section and no placeholders** — the gate's cheap pass is vacuous here, not clean (`lint_spine.py:153-170` pins versions only inside a `## Stack` table).

## Checklist scorecard

| Criterion | Verdict | Note |
| --- | --- | --- |
| Fixes the real divergence points for the level below, misses none | **FAIL** | Covers layering/DI/ports/errors only; Epics 2–4 diverge on integration, resilience, persistence, scheduling (C1, H1–H5) |
| Every AD's Rule is enforceable and prevents its stated divergence | **PARTIAL** | AD-1, AD-7 (intent), AD-6 enforceable-ish; AD-2 not enforceable (H2); AD-7 not enforceable as written (H6); AD-3/AD-4 have no check (L1, L2) |
| Nothing under Deferred could let two units diverge | **FAIL** | Deferred is empty while AD-7's enforcement is deferred to Stories 1.2/1.3 and two real items sit in `deferred-work.md` (H8) |
| Named tech is verified-current | **FAIL** | No version anywhere, no Python baseline, no DI/HTTP/driver/migration/scheduler named (H7) |
| Ratifies rather than contradicts the brownfield codebase | **PASS (with one false claim)** | AD-1's three enforcement layers, layer order, roots, negative controls all verified true; the historical note in AD-1 is wrong (M3) |
| If a spec drove it, it covers that spec's capabilities | **FAIL** | CAP-2/CAP-3/CAP-4 have no governing AD; no Capability → Architecture Map (C1, M1) |
| Inherited parent spine not weakened | **N/A** | No parent spine; `SPEC.md:5` and `epics.md:5` list this spine as the source |
| Every altitude-owned dimension decided, deferred, or open | **FAIL** | ~8 dimensions silent, including the whole operational/environmental envelope (C2) |

## Findings

### CRITICAL

**C1 — The spine decides no seam of the system it governs; Epics 2–4 are ungoverned.**
All seven ADs are about *how Python code is arranged* (boundaries, DI, ports, mutation flow, exceptions, stack, framework isolation) — `ARCHITECTURE-SPINE.md:21-65`. The four capabilities it must serve are ingestion, enrichment, failure handling, and persistence (`SPEC.md:15-22`), decomposed into Epics 2–4 (`epics.md:71-88`). No AD names a component, port, or rule for: the two-step Microsoft extraction (`epics.md:139-163`), IGDB enrichment (`epics.md:194-231`), change detection against "the previously known catalog" (`epics.md:165-176`), upserts/soft-deletes (`epics.md:237-261`), or hourly execution (`epics.md:178-188`). Concretely: Story 2.1 and Story 3.1 can each choose a different HTTP client and retry style and both remain fully AD-compliant, then fail to compose at the port boundary.
*Fix:* add ADs covering (a) external-integration policy (one HTTP client, one batching/rate-limit rule, port granularity per external system), (b) resilience (H4), (c) persistence identity/upsert/soft-delete/transaction (H5), (d) execution/scheduling model, each with `Binds:` naming CAP-/FR-/NFR- IDs; and add the template's `## Capability → Architecture Map` table (`spine-template.md:69`) mapping CAP-1…CAP-4 → module → governing AD so the omission is mechanically visible next time.

**C2 — The operational/environmental envelope is entirely silent, and Deferred does not record it.**
There is no deployment/environments view, no infra/provider decision, and no operations decision — the exact failure mode `reviewer-gate.md:11` calls out. Missing: where the hourly worker runs (host process, container, platform scheduler), what environments exist (dev/test/prod), how PostgreSQL is provisioned and what tests run against, how secrets reach the process (the live symptom is that `.gitignore` has no `.env` pattern — `_bmad-output/implementation-artifacts/deferred-work.md:5-8`), and where the unmatched-title log for manual review (NFR/FR-2.4, `SPEC.md:19-20`, `epics.md:220-231`) actually goes. `ARCHITECTURE-SPINE.md:97-98` ("None explicitly deferred") means the reader is told these are *not* open — they are.
*Fix:* add a `## Stack`-adjacent or Structural-Seed **Deployment & environments** diagram (the template explicitly asks for it, `spine-template.md:60-66`), an AD for configuration & secrets (source = environment variables, validated by Pydantic at process start, fail-fast, `.env` never committed), an AD for operations (structured logging with the fields the manual-review query needs; a failed run must be observable), and — if the deployment target genuinely isn't known yet — move it into `## Deferred` with the reason it can wait, not into silence.

### HIGH

**H1 — I/O concurrency model undecided (sync vs async), which determines every port signature.**
AD-4's flow reads synchronously ("retrieve entities via ports, invoke domain logic, call port methods", `ARCHITECTURE-SPINE.md:43`), but nothing fixes sync vs async. This is not a style choice: it decides whether ports are `def` or `async def`, whether `infrastructure` uses `sqlalchemy.Engine`/`Session` or `AsyncSession` + `asyncpg`/`psycopg 3`, and whether the HTTP client is `httpx.Client` or `AsyncClient`. `pyproject.toml:13` still has `dependencies = []`, so no constraint exists yet. If Story 2.1 builds sync adapters and Story 3.1 async ones, the application layer cannot call both.
*Fix:* one AD: pick the model (an hourly, network-bound worker reads naturally as async — async everywhere, ports declared `async def`, `AsyncSession` + async driver in infrastructure, one `httpx.AsyncClient` reused across adapters), and add the async driver/client to the versioned stack table (H7).

**H2 — Port ownership is contradictory: AD-3 says domain-owned, the diagram and README say application-owned.**
AD-3 defines ports as "the interfaces defining what the domain needs from infrastructure" (`ARCHITECTURE-SPINE.md:38`), while the layer diagram puts `Ports / abc.ABC` inside the Application subgraph (`:76-78`) and the shipped README says `application/` holds "Use cases and ports (abc.ABC interfaces)" (`README.md`, Layout). `epics.md:124` says only "an abc.ABC repository port". Both placements pass the shipped `layers` contract (`pyproject.toml:43-46`), so the boundary machinery cannot detect the divergence.
*Fix:* decide explicitly (the mermaid + README already imply `application/ports`), rewrite AD-3's first clause to "the interfaces the application layer requires from infrastructure", add `application/ports` to AD-1's folder convention (`:25`), and add a boundary test that pins where port modules live.

**H3 — AD-2 mandates a DI *framework* but names none, cannot be verified, and is in direct tension with AD-7.**
AD-2 (`:30-33`) requires "a DI Container framework" with no framework, no version, no location for the container/composition root, and no rule forbidding `application` from importing it. AD-7 (`:62`) simultaneously forbids *any* third-party import in `application`. In Python, mainstream containers (`dependency-injector`'s `@inject`, `injector`'s `@inject`, `punq`) require annotating the very classes/functions that live in `application` — so as written the two ADs cannot both be satisfied, and a builder has no way to know which one wins. There is also no mechanical check that a container is used at all.
*Fix:* name the framework and version; state that all wiring (providers, singletons, lifecycles) lives in a single composition root under `infrastructure`; require plain constructor injection in use cases so `application` imports no container at all; and add the container package to AD-7's forbidden list for `application`, with a negative control.

**H4 — Resilience (retries + circuit breakers, NFR-1) has no AD, and AD-5 covers only the outbound half of failure policy.**
Retries and circuit breakers are a hard constraint in three artifact layers: `SPEC.md:33`, `prd.md:47`, `epics.md:38`, and each adapter story's acceptance criteria (`epics.md:150`, `:163`, `:205`). No AD fixes where the policy lives (adapter-internal vs a decorator around every port), which library, where thresholds come from config, or what "gracefully pause or skip without crashing the batch" means for the use case. AD-5 (`:48`) tells the outer layer how to translate *domain* exceptions *outwards*, but says nothing about the inbound duty — turning `httpx`/`sqlalchemy`/`psycopg` exceptions into a domain `ExternalServiceError` so the use case can skip one title and continue. Without that, NFR-1's behaviour is unreachable inside the ports-and-adapters shape.
*Fix:* add an AD: a shared resilience decorator applied in `infrastructure` around every external adapter, thresholds from configuration, and an inbound translation rule ("no third-party exception crosses a port; adapters raise `ExternalServiceError` subclasses"); extend AD-5 with the inbound mapping and the `Binds: NFR-1` tag.

**H5 — Persistence semantics are undecided: no identity key, no conflict target, no transaction boundary, no migration tool.**
Four stories depend on decisions the spine never makes: change detection needs a stable key to compare runs (`epics.md:171-176`), upsert needs a conflict target to satisfy "no duplicate rows" (`epics.md:243-248`), soft-delete needs a stated representation and timestamp (`epics.md:256-261`), and Epic 1 promises "migrations" without naming a tool (`epics.md:74`, `:130-131`). Microsoft exposes several identifiers (`bigIds` in research `:21-23`), and IGDB is the metadata source of truth (`epics.md:28`), so "which id is the primary key" is exactly the kind of thing two builders answer differently and then cannot reconcile. The transaction boundary (per title vs per batch vs one transaction per run) is likewise unowned, which is how a failed run leaves half-soft-deleted state.
*Fix:* one AD stating the natural key (e.g. Microsoft `bigId`/ProductId), the upsert contract (`ON CONFLICT (<key>) DO UPDATE`), the soft-delete columns (`is_active`, `deactivated_at`, UTC), the unit-of-work boundary per sync run, and Alembic (pinned) as the migration tool; add the Game table to the Structural Seed as a names-and-relationships ERD.

**H6 — AD-7's rule is not mechanically enforceable as written.**
"forbid `pydantic` (and any other runtime dependency) in `domain` and `application`" (`:62-64`) has no import-linter expression: a `forbidden` contract lists explicit module names, external forbidden modules must be exact top-level packages (no subpackages), and there is no "all externals" wildcard (`.venv/Lib/site-packages/importlinter/contracts/forbidden.py:227-251`). So `httpx`, `tenacity`, `asyncpg`, or an async driver can land in `application` and *nothing breaks* until someone remembers to enumerate it — precisely the divergence AD-7 exists to stop, and the rollout lines (`:63-64`) only enumerate `pydantic`, `sqlalchemy`, and "the PostgreSQL driver". Second defect: `include_external_packages` is a top-level `[tool.importlinter]` session option, not a contract key (`forbidden.py:238-241`, `:254`); the spine's phrasing ("an import-linter `forbidden` contract per layer, with `include_external_packages = true` set") invites a config that import-linter rejects.
*Fix:* state the enumerated `forbidden_modules` list per layer, state that `include_external_packages = true` belongs at the top of `[tool.importlinter]`, and make the rule self-maintaining: an executable proof that every entry in `[project].dependencies` appears in at least one forbidden contract (fails when a dependency is added without extending the list), plus the existing BROKEN negative control per contract (`:65`).

**H7 — The Stack dimension is absent: nothing is versioned, so "verified-current" cannot hold and the lint passes vacuously.**
AD-6 (`:50-57`) names SQLAlchemy, Pydantic, Ruff, import-linter — no versions, no Python baseline, and it omits the stack members the plan already requires: PostgreSQL driver, migration tool (Epic 1), DI container (AD-2), HTTP client (Epics 2–3), scheduler (Story 2.4). There is no `## Stack` table (`spine-template.md:52`), so `lint_spine.py`'s `version_pin` pass reports zero findings (`lint_spine.py:153-170`) — a clean lint here means "not checked", not "pinned". The repo meanwhile sets a baseline the spine never ratifies: Python `>=3.12` / `.python-version` 3.12 (`pyproject.toml:10`), and resolved versions already well past the floors (`uv.lock`: ruff 0.16.9 vs `ruff>=0.6`, pytest 9.1.1 vs `pytest>=8.0` — `pyproject.toml:16-20`).
*Fix:* add the `## Stack` table with one row per language/framework/key dep/platform, each with a pinned version verified at authoring (Python 3.12, Ruff 0.16.x, pytest 9.x, import-linter 2.15, SQLAlchemy 2.x, Pydantic 2.x, the chosen driver/client/DI/scheduler), and keep AD-6 as the *rationale-free* pointer to that table.

**H8 — `Deferred` is empty while the spine itself defers enforcement, and two deferrals live only in implementation notes.**
`:97-98` says nothing is deferred, yet AD-7 defers two mandatory contracts to Story 1.2 and Story 1.3 (`:63-64`). Today that means AD-7 is stated as an invariant, is marked `final`, and is enforced by nothing: `pyproject.toml:40-46` holds only the `layers` contract, and AD-7's own evidence requirement (`:65`) cannot be satisfied because no forbidden contract exists. Separately, `deferred-work.md:5-12` carries two items that are architecture-shaped (`.env`/secret ignore patterns; packaging/entrypoint metadata) which do not appear on the spine at all.
*Fix:* populate `## Deferred` with each AD-7 rollout step + owning story + the reason it can wait, record the `.env`/config-secrets item against the new config AD (C2) and the entrypoint item against the scheduling AD, and annotate AD-7 with "enforcement not yet in place as of 2026-10-20" so no reader mistakes `final` for `enforced`.

### MEDIUM

**M1 — `Binds` are prose placeholders, not capability/unit IDs, and there is no Capability → Architecture Map.**
Every AD binds to a restatement of its own title — "Dependency Rule Enforcement" (`:22`), "Dependency Injection Orchestration" (`:31`), "Foundational Stack" (`:51`) — instead of CAP-/FR-/NFR- IDs from `SPEC.md:15-33` / `epics.md:20-40`. The consequence is untraceability: no one can ask "what governs CAP-3?" and get an AD. The template expects IDs (`spine-template.md:11`, `:69`).
*Fix:* rewrite each `Binds:` with real IDs and add the Capability → Architecture Map table.

**M2 — No Consistency Conventions table: the cross-cutting defaults independent builders drift on are unowned.**
Naming (entities, modules, port classes), id representation, date/time convention (UTC, `*_at`, `timestamptz`), error shape, log record fields, config variable names, auth — none are stated; only AD-5's exception *policy* and AD-3's port *mechanism* are. The template asks for exactly this table (`spine-template.md:42`). Two units naming the same concept `Game`/`GameEntry`/`Product` or storing naive vs aware timestamps is the most common real-world drift at this level.
*Fix:* add the table with those rows filled (UTC timestamps, `is_active`/`deactivated_at`, `<Thing>Port` naming, exception base in `domain/exceptions.py`, log fields `game_id`, `title`, `source`, `outcome`).

**M3 — AD-1's historical justification for the subprocess tests is factually wrong.**
`:28` claims the tests "caught an inverted `layers` order that the declarative contract alone reported as kept (`37bb259`)". The shipped order was correct from the skeleton commit onward (`git show f27724c:pyproject.toml` → `layers = ["infrastructure", "application", "domain"]`) and `37bb259` did not touch `pyproject.toml` at all (it changed `tests/test_layers.py`, `ci.yml`, and docs). What the review found was that an inverted order *would have shipped undetected*, because the negative controls ran a duplicated literal with no parity check — see the story's own triage entry (`_bmad-output/implementation-artifacts/spec-1-1-establish-project-skeleton-hexagonal-boundaries.md`, finding "Real layering contract is never direction-verified").
*Fix:* reword to "the review of Story 1.1 found the direction was never verified — an inverted `layers` order would have shipped reporting `KEPT` (`37bb259`) — so the tests are deliberate; do not remove them."

**M4 — AD-5 does not fix the exception taxonomy's home or the outer layers' inbound obligation.**
`:48` names two exception classes but not where they live (module path), not the base class's contract, and not that adapters must translate library exceptions inward (see H4). "e.g., `DomainError`, `EntityNotFound`" in an invariant gives each unit licence to invent its own hierarchy.
*Fix:* state `src/domain/exceptions.py`, the base `DomainError`, the required subclasses per bounded concern, and that adapters raise/wrap rather than leak.

**M5 — Testing strategy is unowned, though NFR-3 is a stated requirement.**
NFR-3 requires TDD and high coverage of matching/state logic (`epics.md:40`, `SPEC.md:32`), and the brownfield already ships a heavyweight mechanical test suite (`tests/test_layers.py`, 329 lines, including subprocess CI-gate assertions at `:309-329`). Nothing states how external services are faked (port fakes vs HTTP fixtures), whether persistence tests use a real PostgreSQL (and how it is provisioned — ties to C2), or whether coverage is gated. Story 1.2's "invalid config fails fast" AC (`epics.md:114-119`) has no test strategy behind it.
*Fix:* one AD: external calls faked at the port boundary, adapters covered with recorded HTTP fixtures, repositories tested against an ephemeral PostgreSQL (name the mechanism), coverage gate for matching/state modules.

**M6 — Region/market/language scope is undecided, which changes both the identity key and change detection.**
Both Microsoft endpoints are `market`/`language` scoped (research `:12-14`, `:21`), FR-1.1 covers region/platform/plan (`epics.md:21`), and only the cloud/plan part is flagged open (`epics.md:52`). Whether a run covers one market or iterates several determines whether the catalog is per-market and therefore whether the persistence key (H5) is `(id)` or `(id, market)`.
*Fix:* decide the V1 market/language scope in the persistence AD, or move it to `## Deferred` with the reason and a named trigger.

**M7 — The shipped distribution shape (three flat top-level packages) is neither ratified nor flagged.**
`pyproject.toml:22-23` ships `src/domain`, `src/application`, `src/infrastructure` as three top-level import roots, and the story forbids nesting under a second level ("Never: Nest packages under a second `src/<pkg>/` level"), so `domain`, `application`, and `infrastructure` are installed into site-packages with generic names. That is a deployment/consumer constraint (collision risk, no namespacing) and a refactor nobody can do cheaply later — exactly what a spine should ratify or overturn. The spine implies the folder convention (`:25`) but never states the import-root decision or its consequence.
*Fix:* add a line to AD-1 ratifying flat top-level roots as an accepted V1 trade-off (or record the intended namespacing), so a future packaging change is a conscious decision rather than drift.

**M8 — Frontmatter does not say what this spine governs.**
Only `title/type/status/updated` are set (`:1-6`); `purpose`, `altitude`, `paradigm`, `scope`, `binds`, `sources`, `created` are missing (`spine-template.md:1-13`), even though a spec drove the run (`SPEC.md:5`, `epics.md:5`). Without `binds`, nothing states which capabilities the spine claims to cover — which is why C1 is invisible on the document's face.
*Fix:* fill the frontmatter (`altitude: feature`, `paradigm: hexagonal`, `scope: hourly catalog-sync worker`, `binds: [CAP-1..CAP-4, FR-1..FR-3, NFR-1..NFR-3]`, `sources: [SPEC.md]`).

**M9 — Port granularity and the batching constant are unowned.**
Story 2.1/2.2 create two Microsoft adapters and Story 3.1 a third (`epics.md:139-163`, `:194-205`); nothing says whether that is one `CatalogSource` port or three, nor where the 200-id batch size (research `:23`) lives (domain constant vs configuration). Port granularity is a use-case-shaping decision — change detection has to depend on the right one.
*Fix:* an AD row or convention: one port per external system, adapters implement it, batch size is configuration with a documented default.

### LOW

- **L1 — AD-3's "fail-fast instantiation" claim has no proof.** `:38` asserts `abc.ABC` gives fail-fast instantiation, but no test exercises an adapter missing a method (contrast AD-7's explicit evidence requirement at `:65`). Fix: one test in `tests/test_layers.py` style asserting a partial implementation raises `TypeError`.
- **L2 — AD-4 sets no port contract shape.** `:43` says "explicitly call port methods (e.g., `save`)" without naming the port methods, their return values (`None` vs entity vs id), or whether reads return entities or collections. Fix: list the repository port's minimal surface in the convention table.
- **L3 — AD-1 says the contract "fails the build", but the gate is CI-only.** `:26` reads as build-time; today the check runs in CI (`.github/workflows/ci.yml:37-38`) and via pytest (`tests/test_layers.py:141-155`), with no pre-commit or build hook. Not wrong, but say "fails CI and the test suite" so nobody assumes a build plugin exists.
- **L4 — Reproducibility is unstated.** `uv.lock` is committed and CI runs `uv sync --locked` (`.github/workflows/ci.yml:29`), but nothing in the spine says dependency resolution is locked; a future unit could add an unpinned dependency. Fix: one convention row ("dependencies land via `uv add`, lockfile committed, CI uses `--locked`").
- **L5 — The diagram will drift on the next story.** `:69-95` has no composition root / DI-wiring node (Story 1.2) and no scheduler/entrypoint trigger (Story 2.4); both are structural, both will be added beneath the current diagram without it. Fix: add them now (dashed "wires" edge from a `CompositionRoot` node; a `Cron`/scheduler node calling the entrypoint).

## Dimension coverage (altitude-owned)

| Dimension | Status in the spine |
| --- | --- |
| Paradigm & dependency direction | Decided (AD-1, AD-7, §1) — good |
| Layer folder convention / import roots | Decided for folders; distribution shape silent (M7) |
| Port definition mechanism | Decided (AD-3) — ownership ambiguous (H2) |
| DI | Stated, unnamed, unenforceable, conflicts with AD-7 (H3) |
| Use-case state mutation | Decided in prose (AD-4); no port contract (L2) |
| Error handling | Half-decided: outbound only (H4) |
| Resilience (retries/circuit breaker) | **Silent** (H4) — hard SPEC constraint |
| I/O concurrency model | **Silent** (H1) |
| Data model / identity / transactions / migrations | **Silent** (H5) |
| External integration (client, auth, batching, rate limits) | **Silent** (C1, M9) |
| Scheduling / execution model | **Silent** (C1) |
| Configuration & secrets | **Silent** (C2) |
| Observability / logging / manual review | **Silent** (C2) |
| Deployment & environments | **Silent** (C2) |
| Infra/provider strategy (PostgreSQL hosting, test DB) | **Silent** (C2) |
| Testing strategy | **Silent** (M5) |
| Market/language/region scope | **Silent** (M6) |
| Stack versions / Python baseline | **Silent** (H7) |
| Inherited parent spine | N/A — none exists |

## What the spine gets right (keep)

- AD-1 is exemplary: three named enforcement layers, each mechanical, with the honest instruction not to remove the subprocess tests (`:24-28`) — all three verified true against `pyproject.toml:40-46` and `tests/test_layers.py:87-155, 213-255`.
- AD-7's *direction* is the single most valuable new invariant in the document, and the `include_external_packages` trap it calls out is real (`forbidden.py:238-241`) — it only needs to become enforceable (H6).
- Every brownfield fact I checked is accurate: layer order, `root_packages`, the parity test, the three negative controls plus positive control, per-layer `src/<layer>` resolution, and the CI gate assertions (`tests/test_layers.py:309-329` vs `.github/workflows/ci.yml:28-41`). Only the history note in AD-1 is wrong (M3).
- AD-6 correctly promotes `import-linter` into the foundational stack, matching `pyproject.toml:16-20`.
