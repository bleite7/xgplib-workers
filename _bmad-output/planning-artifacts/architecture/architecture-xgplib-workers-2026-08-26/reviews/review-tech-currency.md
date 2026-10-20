# Tech-currency & reality-check review — ARCHITECTURE-SPINE.md (xgplib-workers)

- **Reviewer lens:** every committed decision must be web-researched or reality-checked, not asserted from training data — current versions, technology still exists and fits, greenfield starter defaults.
- **Target:** `_bmad-output/planning-artifacts/architecture/architecture-xgplib-workers-2026-08-26/ARCHITECTURE-SPINE.md` @ `ac8aae4`, status `final`, updated 2026-10-20.
- **Review date:** 2026-10-20. Anything unversioned is treated as suspect by definition.
- **Method:** web (PyPI JSON API, upstream release notes/changelogs, project docs, NVD) for every technology the spine commits to or leaves unnamed; repository reality-check (`pyproject.toml`, `uv.lock`, `.python-version`, `.github/workflows/ci.yml`, installed `.venv`); provenance check of the architecture memlog.

## Verdict

**NOT READY — the stack dimension is asserted, not researched, and two of its implied defaults are already superseded.**

The spine commits to exactly four technologies (AD-6) and to one unnamed "DI Container framework" (AD-2), and every one of those statements is unversioned and unsourced. The provenance is explicit: the memlog records the whole stack as a user direction — *"User requested binding common industry-standard libraries … (e.g. SQLAlchemy, Pydantic)"* (`.memlog.md:16`) — followed immediately by a decision, with **no research step and no version lookup anywhere in the run** (`.memlog.md:17`). Under a 2026-10-20 date that is not a stylistic omission: SQLAlchemy changed its default install shape *three weeks ago* (2.1.0, 2026-09-24), and the HTTP client that Epics 2–3 will reach for by reflex (`httpx`) has had **no stable release since 2024-12-06** and has been forked as `httpx2` (2.13.1, 2026-09-23). A builder following this spine will not be wrong about layering — AD-1 and AD-7 are excellent — but will be quietly wrong about everything it installs.

Two decisions are blocking before Epic 1 Story 1.2 and Epic 2 Story 2.1:

1. **AD-2 names no container.** The 2026 ecosystem is a real four-way choice, and the most obvious pick (`dependency-injector`) is the one whose idiomatic API collides with AD-7.
2. **AD-6/AD-7 name no versions and no driver,** and "the PostgreSQL driver" is now a resolved-for-you default that the spine never ratifies (SQLAlchemy 2.1 resolves `postgresql://` to **psycopg 3**).

Everything below is fixable in one edit pass; the exact table to paste is in **Appendix A**.

## Findings

| # | Tier | Finding | One-line evidence |
| --- | --- | --- | --- |
| C1 | Critical | Nothing in the spine is versioned or sourced; two implied defaults have moved since the spine was plausible | `ARCHITECTURE-SPINE.md:50-57`, `.memlog.md:16-17`; SQLAlchemy 2.1.0 2026-09-24; `httpx` 0.28.1 → `httpx2` 2.13.1 |
| C2 | Critical | AD-2 mandates an unnamed DI container; the ecosystem is a live 4-way choice and the "obvious" package name on PyPI is a 1.87 kB stub | AD-2 `:30-33`; dependency-injector 4.49.1 (abi3) / dishka 1.10.1 / punq 0.9.0 / injector 0.24.0; `python-dependency-injector` 4.41.0 = 1,870-byte wheel |
| H1 | High | `sqlalchemy` pinned plainly will break an async worker: greenlet is no longer installed by default in 2.1 | SQLAlchemy 2.1.0 release notes: "The greenlet dependency … no longer installs by default. Use `pip install sqlalchemy[asyncio]`" |
| H2 | High | No PostgreSQL driver named, and the driver the spine defers to is now chosen by SQLAlchemy itself | SQLAlchemy 2.1.0: "if using URLs of the form `postgresql://` … the driver selected will be psycopg (psycopg3)" |
| H3 | High | No migration tool named, though Epic 1 promises "migrations"; Alembic has new version constraints | Alembic 1.20.0 (2026-09-11): SQLAlchemy 1.4 support dropped, 2.0 is now the minimum |
| H4 | High | The HTTP client for Epics 2–3 is unnamed, and the default answer is a 2-year-stale package | `httpx` last stable 0.28.1 (2024-12-06); `httpx2` 2.13.1 (2026-09-23), fork of httpx 0.28.1 maintained by Pydantic |
| H5 | High | Resilience and scheduling (NFR-1, Story 2.4) are unstacked; the obvious scheduler pick has a 4.0 alpha trap and an open CVE | APScheduler 3.11.3 (2026-06-28) vs 4.0.0a6 ("do NOT use in production"); CVE-2026-31072 |
| M1 | Medium | Python baseline unratified while the repo pins 3.12, which is now security-only | `.python-version` 3.12, CI `python-version: "3.12"`; 3.12.15 (2026-10-01); 3.15.0 shipped 2026-10-09 |
| M2 | Medium | The only Ruff "pin" in the repo is a 2024-era floor; the spine states none | `pyproject.toml:19` `ruff>=0.6`; lock 0.16.9; current 0.17.1 (2026-10-15) |
| M3 | Medium | "Pydantic for configuration" is not a library; `pydantic_settings` is a separate top-level module that AD-7's forbidden list would miss | pydantic-settings 2.16.1 (2026-10-20); AD-7 `:62-64` enumerates exact top-level packages |
| M4 | Medium | No provenance convention, so the next dependency lands the same way AD-6 did | `.memlog.md:16-17`; `pyproject.toml:13` `dependencies = []` |
| M5 | Medium | The DI choice is an AD-7 question, not a taste question: marker-based containers force third-party imports into `application` | dependency-injector `@inject`/`Provide[...]`; dishka "You don't need to add custom markers to dependency code" |
| L1 | Low | Package manager and build backend unnamed, so the `--locked` guarantee is unowned | `uv 0.13.3` (2026-10-20), `hatchling 1.32.4` (2026-09-20); `ci.yml` runs `uv sync --locked` |
| L2 | Low | Staying on `httpx` also means staying on advisories fixed only in `httpx2` | httpx2 changelog 2.11.0/2.12.0 security-relevant fixes; no `httpx` release since 2024-12-06 |
| L3 | Low | Pydantic v3 is in planning; a loose `pydantic>=2` promise will not survive the next major | pydantic `docs/version-policy.md`; v3-labelled issues open as of 2026-10-02 |
| L4 | Low | `python-dependency-injector` is not the real package; it is an unrelated stub occupying the repo name | PyPI JSON: 4.41.0, 2026-09-11, 1 maintainer, no description/classifiers/`requires_dist`, 1 py3-none-any wheel |

---

### CRITICAL

#### C1 — AD-6 is an assertion, not a research result; two implied defaults are already superseded

AD-6 (`ARCHITECTURE-SPINE.md:50-57`) lists SQLAlchemy, Pydantic, Ruff, import-linter with **no version, no Python baseline, and no source**. Nothing else in the document pins a version either, and `## Deferred` (`:97-98`) says there is nothing deferred — so a reader is told the stack is settled while it is in fact unspecified. The mechanical lint passes vacuously for the same reason (no `## Stack` section).

The provenance is not ambiguous. The memlog shows the entire stack arriving as a direction and leaving as a decision in two consecutive lines:

```
.memlog.md:16  (direction) User requested binding common industry-standard libraries ... (e.g. SQLAlchemy, Pydantic).
.memlog.md:17  (decision) Binds: Foundational Stack. ... SQLAlchemy for ORM ..., Pydantic ..., Ruff ...
```

No web lookup and no repository check appear in the run. That matters because between the "training-data" version of this stack and today's:

| Technology | What the spine implies | What is true on 2026-10-20 | Consequence for this project |
| --- | --- | --- | --- |
| SQLAlchemy | "ORM", unversioned (`:54`) | **2.1.5** (2026-10-16); 2.1.0 was the first production release (2026-09-24) and is now what `pip install sqlalchemy` yields. 2.0.55 is maintenance-only | Default driver changed to psycopg3; greenlet no longer default; min Python 3.11 (H1, H2) |
| Pydantic | "DTOs and configuration validation" (`:55`) | **2.14.1** (2026-10-11); 2.14.0 dropped Python 3.9, added 3.15. v3 unreleased | v2 is correct, but "Pydantic" ≠ config library (M3); v3 planning affects pinning (L3) |
| Ruff | "fast, unified linting and formatting" (`:56`) | **0.17.1** (2026-10-15); repo resolves **0.16.9**; repo floor is `>=0.6` | Two minors of drift plus an 11-minor floor (M2) |
| import-linter | "enforcing the inward-only dependency rule" (`:57`) | **2.15** (2026-09-04) — repo `uv.lock` already at 2.15 | Correct; the only stack entry that is both current and pinned |

**Fix (exact):** add the `## Stack` table from **Appendix A** immediately after AD-6, with one row per language/runtime/library and three columns the current doc lacks: **pin**, **role/layer**, and **verified (date)**. Reduce AD-6's body to one sentence pointing at it: *"The stack and its pins live in `## Stack`; every entry there was verified against PyPI/upstream release notes on the date shown. AD-6 no longer restates versions."* Then re-run the spine lint so the `version_pin` pass is no longer vacuous.

#### C2 — AD-2's unnamed DI container is a live four-way decision, and the name a builder will search for is a stub on PyPI

AD-2 (`:30-33`) mandates "a **DI Container framework** (rather than manual wiring)" and names nothing — no framework, no version, no composition-root location. As of today the candidates are all alive, so this is not an "obvious default" that can be waved through:

| Candidate | Current release | Date | Fit for this worker |
| --- | --- | --- | --- |
| `dependency-injector` | 4.49.1 | 2026-06-18 | Cython; ships `cp310-abi3` wheels so it **does** install on 3.12 (verified via PyPI file list). Idiomatic API is `@inject` + `Provide[...]` **in the consumer** — collides with AD-7 (M5) |
| `dishka` | 1.10.1 | 2026-04-25 | Pure Python, zero dependencies, scopes + finalization; explicitly *"You don't need to add custom markers to dependency code"* — the cleanest AD-7 fit |
| `punq` | 0.9.0 | 2026-09-08 | Small, no decorators, no global state; low release cadence (0.8.0 → 0.9.0 spanned years) |
| `injector` | 0.24.0 | 2026-01-09 | Guice-style, `@inject` on consumer `__init__` — same AD-7 problem as dependency-injector |

There is also a supply-chain trap worth writing down, because AD-2's phrasing invites it: the real project's **GitHub repository is named `python-dependency-injector`**, but the real **PyPI package is `dependency-injector`**. The name `python-dependency-injector` also exists on PyPI as an unrelated stub: version 4.41.0, published 2026-09-11, one maintainer, **no description, no classifiers, no `requires_dist`, no project URLs, a single 1,870-byte `py3-none-any` wheel**. `uv add python-dependency-injector` succeeds and gives you nothing.

**Fix (exact):** replace AD-2's Rule with a named decision and a location:

> **AD-2: Dependency Injection Strategy**
> **Rule:** Dependency injection is orchestrated by **dishka 1.10.x** (`dishka>=1.10,<1.11`, verified 2026-10-20). All providers, scopes, and lifetimes live in a single composition root at `src/infrastructure/composition.py`; nothing outside `infrastructure` imports `dishka`. Use cases and adapters use plain constructor injection with type-annotated parameters and therefore import no container (AD-7-compatible). `dishka` is added to AD-7's forbidden list for `domain` and `application` with a negative control. The PyPI distribution is **`dishka`**; `dependency-injector` is the only other approved alternative and its distribution name is `dependency-injector`, **never** `python-dependency-injector` (unrelated stub).

If the team prefers `dependency-injector`, the Rule must say so *and* state that `@inject`/`Provide[...]` markers are not permitted in `application`, leaving only constructor wiring through `providers.Factory` — otherwise AD-2 and AD-7 cannot both be satisfied (M5).

---

### HIGH

#### H1 — Plain `sqlalchemy` is wrong for an async worker under 2.1

SQLAlchemy 2.1.0 release notes (2026-09-24): *"The greenlet dependency, used for all asyncio features, no longer installs by default. Use `pip install sqlalchemy[asyncio]` to include this dependency."* AD-4 reads synchronously (`:43`) but nothing in the spine fixes sync vs async, so Story 1.3 can legitimately land `sqlalchemy` (no extra) while Story 2.1 lands an async HTTP client — and the failure appears only at first `AsyncSession` use, not at install time.

**Fix (exact):** resolve concurrency before pins (the rubric review's H1 already asks for this), then pin `sqlalchemy[asyncio]>=2.1.5,<2.2` for the async model, or `sqlalchemy>=2.1.5,<2.2` for the sync model. Record the extra in the stack table's pin column so no story can drop it.

#### H2 — "the PostgreSQL driver" is no longer a free choice; SQLAlchemy 2.1 already made it

AD-7 rollout line 2 (`:64`) says *"extend the forbidden set with `sqlalchemy` and the PostgreSQL driver"* — a placeholder, not a module name. Beyond the enforcement problem (an import-linter `forbidden` contract needs an exact top-level package), the environment has moved: SQLAlchemy 2.1 release notes state that *"if using URLs of the form `postgresql://` or `oracle://` without a specific driver name, the driver selected will be psycopg (also known as psycopg3)"*.

Current drivers, verified:

- **psycopg 3.3.6** (2026-09-18), Python 3.10–3.15, PostgreSQL 10–18, sync **and** `AsyncConnection`; `pip install "psycopg[binary]"`. URL: `postgresql+psycopg://`.
- **asyncpg 0.32.0** (2026-10-06), Python 3.9+, ships cp315 wheels. URL: `postgresql+asyncpg://`.

**Fix (exact):** name the driver in the stack table and in AD-7's forbidden list. Recommended V1: `psycopg[binary]>=3.3.6,<3.4` — it is the SQLAlchemy 2.1 default, has both sync and async APIs, and means one driver covers whichever concurrency model wins. If asyncpg is chosen for throughput, then AD-7's forbidden module is `asyncpg` and the DSN must be `postgresql+asyncpg://` (a mismatch here is a runtime error, not a lint error).

#### H3 — Migrations are promised by Epic 1 but no tool is named, and Alembic's constraints changed

`epics.md:74` ("PostgreSQL data model … plus migrations") and Story 1.3 AC (`epics.md:130-131`) both depend on a migration tool. The spine never names one. Alembic **1.20.0** (2026-09-11) dropped SQLAlchemy 1.4 entirely — *"SQLAlchemy 2.0.0 is now the minimum required version"* — and 1.18.0+ carries explicit SQLAlchemy 2.1 compatibility work (`isolate_from_table=True` adjusted again in 1.18.1). Pinning Alembic below 1.18 against SQLAlchemy 2.1 is a known-bad combination.

**Fix (exact):** add `alembic>=1.20,<1.21` to the stack table with role "schema migrations (`src/infrastructure/migrations`)" and state in the persistence AD that *the only writer of DDL is the Alembic revision* — no `Base.metadata.create_all()` in the app or in tests.

#### H4 — The HTTP client for Epics 2–3 is unnamed, and the reflex answer is two years stale

Story 2.1, 2.2 and 3.1 each need an HTTP client; the spine says nothing, so two adapters may pick two clients and still be AD-compliant. The default name a builder will type is now the wrong one:

- `httpx` **0.28.1** — last stable release **2024-12-06**. Nothing since; only `1.0.dev*` pre-releases (latest `1.0.dev6`, 2026-08-31).
- `httpx2` **2.13.1** — **2026-09-23**. Changelog: *"First release of httpx2, a fork of httpx maintained by Pydantic. Forked from httpx 0.28.1."* Import becomes `httpx2`; no other public API changed; `alias_httpx()` (added 2.9.0) can make `import httpx` resolve to `httpx2` process-wide.

**Fix (exact):** stack table row `httpx2>=2.13.1,<3` with role "sole HTTP client, instantiated once in `infrastructure` and injected into Microsoft and IGDB adapters"; AD-7's forbidden list includes **both** `httpx2` and `httpx` (a story that installs the old name must trip the contract, not sail through). State explicitly: *"`httpx` (0.28.x) is not approved; it has had no stable release since 2024-12-06."*

#### H5 — Resilience and scheduling are unstacked, and the obvious scheduler pick has a trap

NFR-1 is a hard constraint in three artifacts (`SPEC.md:33`, `epics.md:38`, and every adapter AC), and Story 2.4 needs hourly cron. No library is named for either. Current state of the art:

- **Retries:** `tenacity` **9.2.1** (2026-10-07) — healthy, `>=3.10`, the right default.
- **Circuit breakers:** thin. `pybreaker` **1.4.1** (2025-09-21 — a year old, thread-safe *sync*, no native asyncio), `aiobreaker` 1.1.0 (stale), `asyncbreaker` **2.1.1** (2026-08-14, active but a single-maintainer rewrite of a fork).
- **Scheduler:** `APScheduler` **3.11.3** (2026-06-28) is the stable line. **4.0 is still pre-release** — the project's own warning: *"The v4.0 series is provided as a pre-release and may change in a backwards incompatible fashion without any migration pathway, so do NOT use this release in production!"* (latest `4.0.0a6`). Additionally **CVE-2026-31072** (published 2026-05-19): insecure deserialization in `JSONSerializer`/`CBORSerializer` *"all versions including 3.10.x and 4.0.0a5"* — it only bites if you use a persistent job store with those serializers.

**Fix (exact):** stack rows `tenacity>=9.2,<10` (retries, wrapped in the shared adapter decorator) and `apscheduler>=3.11.3,<4` (**not** 4.x). Add to the scheduling AD: *"Job stores must be in-memory only; `JSONSerializer`/`CBORSerializer` are forbidden (CVE-2026-31072). If the deployment target already provides cron, prefer external cron over an in-process scheduler and record that instead."* For the breaker, either accept `pybreaker` 1.4.1 with a sync-only wrapper (if the worker stays sync) or state *"no breaker library in V1; implement a 25-line breaker in `infrastructure/resilience.py` behind the same decorator so it does not depend on an unmaintained package"* — what must not happen is silence.

---

### MEDIUM

#### M1 — Python baseline is unratified, and the pinned baseline is security-only

The spine never states a Python version, while the repo pins one in four places: `requires-python = ">=3.12"` (`pyproject.toml:10`), `.python-version` = `3.12`, CI `python-version: "3.12"`, and the installed venv is **3.12.15**. Meanwhile 3.12 is in **security-only** maintenance (3.12.15 on 2026-10-01; bugfix support ended 2025-04), and **3.15.0 shipped 2026-10-09** (3.14.8 is the current 3.14). Every library in the proposed stack supports 3.12 fine — this is a currency choice, not a compatibility failure.

**Fix (exact):** add a row to the stack table — `Python | 3.12.15 (security-only; EOL Oct 2028) | runtime floor and CI target` — and one line of rationale in AD-6: *"3.12 is ratified as the target for V1 (match the shipped `.python-version`); a move to 3.13/3.14 is a separate, deliberate decision recorded in `## Deferred`."* Greenfield is the cheapest moment to choose 3.13/3.14; if the team does, change `.python-version`, `requires-python`, and `ci.yml` in the same commit.

#### M2 — The only Ruff pin in the repo is stale enough to permit 2024 behaviour

`pyproject.toml:19` declares `ruff>=0.6` (a floor from early 2024). `uv.lock` resolves **0.16.9** (2026-09-24); current is **0.17.1** (2026-10-15, and 0.17.0 began code-signing the Windows/macOS binaries). The spine states no version at all, so the effective answer to "which Ruff?" is "whatever the floor allows", i.e. 11 minor versions of drift if the lock is ever regenerated without care. The same shape applies to `pytest>=8.0` (`:18`) while the lock has **9.1.1** (2026-06-19) — a floor that permits pytest 8 against a pytest-9 test suite.

**Fix (exact):** stack rows `ruff | 0.17.1 | lint + format | verified 2026-10-20` and `pytest | 9.1.1 | tests`. Raise the floors in the same change (`ruff>=0.17`, `pytest>=9.1`) so the floor and the lock agree, and note that `import-linter 2.15` already matches its lock exactly — that one needs no action.

#### M3 — "Pydantic for configuration" is not a library, and AD-7's forbidden list will miss the real one

Story 1.2's AC is *"config is validated via Pydantic"* (`epics.md:116`). Pydantic core does validation but has no environment/file source; that is `pydantic-settings` — **2.16.1, published today (2026-10-20)**. Without naming it, Story 1.2 either hand-rolls `os.environ` parsing (violating the spirit of validated config) or adds an unnamed dependency. Worse for AD-7: `pydantic_settings` is a **separate top-level module** from `pydantic`, and import-linter `forbidden` contracts list exact top-level packages — so a developer who correctly adds the library, then uses it in `application`, passes the contract that AD-7 (`:63`) describes as "forbid `pydantic` (and any other runtime dependency)".

**Fix (exact):** stack row `pydantic-settings | 2.16.1 | env/file configuration source | verified 2026-10-20`; amend Story 1.2's rollout line to *"forbid `pydantic` **and** `pydantic_settings` in `domain` and `application`, each with its own negative control"*; and state that the settings model lives in `src/infrastructure/config.py`.

#### M4 — No provenance convention, so the next dependency will land the way AD-6 did

`pyproject.toml:13` is still `dependencies = []`, which means every runtime pin is still ahead of the team. AD-6 contains no date, no source, and no rule that a dependency must be verified when added — the memlog is the proof (`:16-17`). Nothing in the spine would have caught C1/H4.

**Fix (exact):** add one convention row: *"Every entry in `[project].dependencies` must also appear in the `## Stack` table with a pin and a `verified` date. A dependency added without a table row fails the epic's definition of done."* Optionally make it mechanical next to the AD-7 dependency-coverage test the rubric review already proposes.

#### M5 — The container choice is an AD-7 compatibility question, not a preference

AD-7 (`:62`) bans *any* third-party import in `application`. `dependency-injector` and `injector` both expect the **consumer** to carry markers (`@inject`, `Provide[...]`) when using their idiomatic wiring; `dishka`'s documented selling point is the opposite (*"Clean dependencies. You don't need to add custom markers to dependency code to make it visible for the library."*), and `punq` is likewise decorator-free. So AD-2's silence is not neutral: it permits a container that makes AD-7 unenforceable in year one.

**Fix (exact):** decide as in C2 and add one sentence to AD-2's evidence requirement that mirrors AD-7's: *"The chosen container must resolve use cases with constructor injection only; a test asserts that no module under `src/application` imports the container package."*

---

### LOW

- **L1 — Package manager and build backend unowned.** `uv 0.13.3` (2026-10-20) and `hatchling 1.32.4` (2026-09-20) are current, and CI already runs `uv sync --locked` (`ci.yml`), but the spine never states that dependency resolution is locked. *Fix:* one stack row each, plus the convention *"dependencies land via `uv add`; `uv.lock` is committed; CI uses `--locked`."*
- **L2 — Staying on `httpx` means staying on advisories that only `httpx2` fixes.** The `httpx2` changelog shows security-relevant work landing in 2.11.0 (HTTP/2 stream failure propagation) and 2.12.0 (*"Bound peak memory while streaming compressed responses and close response streams when decoding fails"*). No equivalent release exists for `httpx` since 2024-12-06. *Fix:* covered by H4; the wording above ("not approved") is the mitigation.
- **L3 — Pydantic v3 is in planning.** `docs/version-policy.md`: deprecated V2 functionality *"will not be removed until the next major V3 release"*, and v3-labelled issues are open (e.g. #13923, 2026-10-02). *Fix:* pin `pydantic>=2.14,<3` (minor-bounded) rather than `>=2`, so v3 is a deliberate migration.
- **L4 — `python-dependency-injector` is a stub, not the framework.** 4.41.0, 2026-09-11, 1 maintainer, no description/classifiers/`requires_dist`, single 1,870-byte wheel. *Fix:* covered by C2's explicit name note; optionally add it to a "rejected packages" line in the stack section.

---

## Verified correct (do not "fix" these)

- **import-linter 2.15** (2026-09-04) is current and is the exact version in `uv.lock`; `include_external_packages` is still the real top-level session option (re-verified in `.venv/Lib/site-packages/importlinter/contracts/forbidden.py`: the top-level config must set `include_external_packages=True` when external forbidden modules are used). AD-7's warning about the flag is accurate today.
- **pytest 9.1.1** (2026-06-19) is current and matches the lock; **Python 3.12.15** in the venv matches `.python-version` and CI exactly.
- **AD-1's** folder order, `root_packages`, and Ruff's inability to scope banned imports by source module are all still true in Ruff 0.17.1 (`flake8-tidy-imports` bans modules globally, not per-source-layer).
- **SQLAlchemy 2.1** still supports the target Python (3.11+), **Pydantic 2.14** supports 3.10–3.15, **psycopg 3.3** supports 3.10–3.15, **Alembic 1.20** supports SQLAlchemy 2.0/2.1 — so every proposed pin is compatible with Python 3.12 and with each other. The stack is not wrong; it is unspecified.
- **No starter is leaned on.** This is a hand-built greenfield repo (hatchling + `src/` three-package layout, no generated template), so there are no starter defaults (pinned Python, pre-wired DI, pre-chosen driver) to audit — the absence is real, not an oversight to chase.

## Scope checks performed (for the record)

| Technology | Lever | Source |
| --- | --- | --- |
| SQLAlchemy | PyPI JSON + `sqlalchemy.org/download.html` + 2.1.0 release blog | 2.1.5, 2026-10-16; 2.1.0, 2026-09-24; 2.0.55 maintenance, 2026-10-16 |
| Pydantic / pydantic-settings | GitHub releases + PyPI JSON + version-policy doc | 2.14.1, 2026-10-11; settings 2.16.1, 2026-10-20 |
| Ruff | GitHub releases + PyPI JSON | 0.17.1, 2026-10-15 |
| import-linter | GitHub tags + release notes + installed source | 2.15, 2026-09-04 |
| DI containers | PyPI JSON (`dependency-injector`, `dishka`, `punq`, `injector`, `python-dependency-injector`) | 4.49.1 / 1.10.1 / 0.9.0 / 0.24.0; stub 4.41.0 |
| HTTP client | PyPI RSS + `httpx2` changelog | `httpx` 0.28.1 (2024-12-06); `httpx2` 2.13.1 (2026-09-23) |
| PostgreSQL drivers | PyPI JSON + psycopg docs | psycopg 3.3.6 (2026-09-18); asyncpg 0.32.0 (2026-10-06) |
| Migrations | Alembic changelog + PyPI | 1.20.0 (2026-09-11) |
| Resilience | PyPI (tenacity, pybreaker, asyncbreaker, aiobreaker) | tenacity 9.2.1 (2026-10-07); pybreaker 1.4.1 (2025-09-21); asyncbreaker 2.1.1 (2026-08-14) |
| Scheduling | PyPI + project docs + NVD | APScheduler 3.11.3 (2026-06-28), 4.0.0a6 pre-release; CVE-2026-31072 |
| Runtime | python.org downloads + 3.12 changelog | 3.12.15 (2026-10-01); 3.15.0 (2026-10-09) |
| Tooling | PyPI JSON | uv 0.13.3 (2026-10-20); hatchling 1.32.4 (2026-09-20) |

---

## Appendix A — proposed `## Stack` table (paste under AD-6)

| Item | Pin | Role / layer | Verified |
| --- | --- | --- | --- |
| Python | 3.12.15 | Runtime floor + CI target (`.python-version`, `requires-python`); security-only, EOL Oct 2028 | 2026-10-20 |
| uv | 0.13.x | Dependency + lock management; CI uses `uv sync --locked` | 2026-10-20 |
| hatchling | 1.32.x | Build backend | 2026-10-20 |
| SQLAlchemy | `sqlalchemy[asyncio]>=2.1.5,<2.2` | ORM/persistence, `infrastructure` only; `[asyncio]` required (greenlet is no longer a default dep in 2.1) | 2026-10-20 |
| psycopg | `psycopg[binary]>=3.3.6,<3.4` | PostgreSQL driver (SQLAlchemy 2.1 default; sync + async); DSN `postgresql+psycopg://` | 2026-10-20 |
| Alembic | `alembic>=1.20,<1.21` | Schema migrations; requires SQLAlchemy ≥2.0 | 2026-10-20 |
| Pydantic | `pydantic>=2.14,<3` | DTOs, `infrastructure` only | 2026-10-20 |
| pydantic-settings | `pydantic-settings>=2.16,<3` | Config source (`src/infrastructure/config.py`); separate top-level module → add to AD-7 forbidden list | 2026-10-20 |
| dishka | `dishka>=1.10,<1.11` | DI container; composition root `src/infrastructure/composition.py`; marker-free (AD-7-safe) | 2026-10-20 |
| httpx2 | `httpx2>=2.13.1,<3` | Sole HTTP client for Microsoft + IGDB adapters; `httpx` 0.28.x **not approved** (no stable release since 2024-12-06) | 2026-10-20 |
| tenacity | `tenacity>=9.2,<10` | Retry policy inside the shared adapter decorator | 2026-10-20 |
| APScheduler | `apscheduler>=3.11.3,<4` | Hourly trigger (3.x only — 4.0 is pre-release); in-memory job store; no `JSONSerializer`/`CBORSerializer` (CVE-2026-31072) | 2026-10-20 |
| Ruff | 0.17.1 (`ruff>=0.17`) | Lint + format (style only, not boundaries) | 2026-10-20 |
| import-linter | 2.15 (`import-linter>=2.15`) | `layers` + `forbidden` boundary contracts | 2026-10-20 |
| pytest | 9.1.1 (`pytest>=9.1`) | Test runner | 2026-10-20 |

Two open cells are deliberate and must be closed by the concurrency decision, not by a story: if the worker is **sync**, drop the `[asyncio]` extra and pin the breaker library (`pybreaker 1.4.1`, sync); if **async**, keep `[asyncio]`, use `AsyncSession`, `httpx2.AsyncClient`, and state whether the breaker is `asyncbreaker 2.1.1` or a local implementation.
