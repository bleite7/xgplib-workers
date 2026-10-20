# Adversary review — ARCHITECTURE-SPINE.md (xgplib-workers)

- **Lens:** attack the spine by construction. For each hole, invent **two units one level below the architecture** (concrete files a developer would actually create under Stories 1.2–4.2), verify that **each one obeys every AD and every FR it serves** on its own terms, and then show the state where they still do not compose.
- **Target:** `_bmad-output/planning-artifacts/architecture/architecture-xgplib-workers-2026-08-26/ARCHITECTURE-SPINE.md`, status `final`, updated 2026-10-20, AD-1…AD-7 at `:21-65`.
- **Review date:** 2026-10-20.
- **Ground truth read:** `_bmad-output/planning-artifacts/epics.md` (Stories 1.1–4.2, FR-1.1…FR-3.3), `_bmad-output/specs/spec-xgplib-workers/SPEC.md` (CAP-1…CAP-4), `pyproject.toml`, `tests/test_layers.py`, `.github/workflows/ci.yml`, `_bmad-output/implementation-artifacts/deferred-work.md`, `src/` (three empty layer packages).
- **Companions:** `review-rubric-walker.md` and `review-tech-currency.md` audit *coverage* and *currency*. This review assumes the spine is only ever consulted as a rulebook by two developers who never talk, and asks the narrow question the other two lenses do not: **does obeying it produce a working system?**

## Verdict

**NOT READY — the first two units built under this spine will not compose, and the spine's own enforcement will report them as clean.**

AD-1 and AD-7 are a genuinely good constitution **for layering**. The problem is that they are a constitution for *where code lives*, and the system's failure modes live in *what code means*. Nothing in AD-1…AD-7 fixes any of these:

- the identity of the one entity every epic shares (`game`),
- the shape or the writer-set of the one JSONB column every epic writes,
- who may transition availability, in what order, under what completeness condition,
- the transaction boundary of an hourly run,
- whether an upstream outage and an upstream "no match" are distinguishable,
- where a port lives and what type it may return.

Every one of those is currently decided *implicitly*, per story, by whichever developer gets there first — and both choices are AD-compliant. I constructed 20 pairs; **5 are critical**, in the precise sense that the result is not a lint failure or a merge conflict but **silent data corruption, or two ADs whose letter cannot both be satisfied**.

The spine needs one decision pass adding roughly a dozen ADs. They are cheap to state now (each is a paragraph) and expensive to retrofit (each is a migration plus a rewrite of the unit that guessed wrong). Section **Consolidated AD index** at the end is paste-ready.

Tiering used throughout:

| Tier | Meaning for this lens |
| --- | --- |
| **Critical** | Two fully compliant units produce silent data corruption, or a requirement that no implementation can satisfy while obeying the ADs as written. |
| **High** | Two fully compliant units produce a runtime failure, a wrong-but-plausible result, or a duplicated mechanism, discovered only in integration or production. |
| **Medium** | Two fully compliant units diverge in behaviour and force rework, an unstable review surface, or an unqueryable requirement. |
| **Low** | Two fully compliant units diverge only in naming/shape; cheap now, churn later. |

---

# CRITICAL

## C1 — The shared entity has no identity, so Story 1.3 and Story 4.1 pick different upsert keys and both pass

**Pair**

| Unit | Story |
| --- | --- |
| `src/domain/entities/game.py` + `src/domain/ports/game_repository.py` | 1.3 (Game entity, abc.ABC port) |
| `src/infrastructure/persistence/repositories/sql_game_repository.py` (+ `.../models/game_model.py`) | 4.1 (upserts, "no duplicate rows") |

**Why each is compliant.** Developer A reads Story 1.3 ("the Game domain entity … repository port") and writes the idiomatic aggregate: `Game(id: UUID, product_id: str, title: str, is_active: bool)`, with `id` defaulting to `uuid4()` (`uuid` is stdlib, so AD-7 is untouched). The repository port declares `save(game: Game) -> None`, `get(game_id: UUID) -> Game`, `list_active() -> list[Game]`. Every AD holds: AD-3 (`abc.ABC`), AD-4 (`save` is the named persist call), AD-6/AD-7 (no third-party import in `domain`), AD-1 (folder, contract, controls).

Developer B reads Story 4.1 ("upserts for newly found or updated games … no duplicate rows for existing titles") and implements the natural SQLAlchemy upsert against the primary key the domain hands it:

```python
stmt = insert(GameModel).values(...)
stmt = stmt.on_conflict_do_update(index_elements=[GameModel.id], set_=...)
```

Both are correct readings. Nothing in AD-1…AD-7 states which attribute is *the* identity, or that the conflict target must be the natural key rather than the surrogate. FR-3.2 says "upserts"; Story 4.1's AC says "existing titles"; neither the AC nor any AD says what "existing" is keyed on.

**Incompatibility.** The enrichment path (Story 3.2) needs a game it did not create, so it calls `repo.get_by_product_id(...)` (a method dev B adds to the port to make its own story testable — still an `abc.ABC` port, so AD-3 is intact). `Game` has no identity equality (`uuid4()` per construction), so any load-and-save round trip through a re-hydrated entity carries a **fresh `id`** — `ON CONFLICT (id)` never fires, and the same Microsoft product is inserted again every hour. Story 4.1's own acceptance test passes, because it saves entities it created within the test. FR-3.2 is violated in production by a pair of units that are each green. The compensating move — adding `UNIQUE(product_id)` — turns the hourly run into an `IntegrityError` raised out of the adapter, i.e. a database exception crossing into `application` with no AD-5 translation path (see H1).

**Fix — AD-8: Canonical Entity Identity**

- **Binds:** identity of every persisted domain entity; the upsert conflict target; FR-3.2, Story 1.3, Story 4.1.
- **Prevents:** one entity with two identities; duplicate rows behind a green Story 4.1 test; an integrity error raised from the persistence adapter instead of being structurally impossible.
- **Rule:** every persisted entity declares exactly **one canonical identity**, and it is the upstream natural key — for `Game`, the Microsoft product id string (`str`), never a surrogate. The canonical key is set by the entity's constructor and is immutable (`frozen` value object or read-only property). Surrogate `UUID` primary keys are forbidden. The repository port exposes **no** lookup or conflict target over anything but the canonical key (`get_by_product_id`, `save` upserting on `product_id`), and the ORM model declares `UNIQUE(product_id)` so a duplicate insert fails at schema level, not in application logic. A test asserts that `save` called twice on two independently constructed entities with the same product id leaves exactly one row.

## C2 — "The catalog" is one row per title or one row per platform, and the two units disagree about which

**Pair**

| Unit | Story |
| --- | --- |
| `src/application/use_cases/detect_catalog_changes.py` | 2.3 (detect added/removed) |
| `src/domain/entities/game.py` (`is_active: bool`) + `src/application/use_cases/soft_delete_missing.py` | 1.3 / 4.2 (soft-delete) |

**Why each is compliant.** Story 2.1's AC returns ids **per endpoint** — Console, PC, EA Play — and Story 2.3 says "compares the freshly fetched catalog against the previously known catalog", returning "the set of added titles and the set of removed titles". Dev A therefore computes the diff **per platform slice**, because that is the only structure the adapter gives it: `removed[platform] = known[platform] - fetched[platform]`. AD-4 is satisfied literally: retrieve via port, compute, return.

Dev B reads FR-3.3 ("soft-delete titles removed from the catalog by flagging them inactive") and models availability as a boolean on the game row: `Game.deactivate()` sets `is_active = False`. AD-4 satisfied exactly as written ("invoke domain logic on the entity … explicitly call port methods").

Nothing in AD-1…AD-7 mentions platforms, markets, regions or plans — although FR-1.1 requires region, platform (PC/console/cloud) and plan (Core/Standard/Ultimate), and Story 2.1's AC takes "valid market/language parameters".

**Incompatibility.** A title that leaves Console but stays on PC is in `removed["Console"]` and not in `removed["PC"]`. Dev B's unit consumes a flat set of removed ids, so the first platform slice that reports a removal deactivates the title — and the catalogue then claims a game is unavailable while it is still available, violating CAP-1's "complete list of currently available titles" and FR-3.3's "database accurately reflects the current Microsoft catalog state". The reciprocal bug is equally compliant: a dev who unions the slices and deactivates only on intersection is correct for removals and wrong for additions (a title added to PC only is already `is_active=True`, so "added" is never observable). Both behaviours are chosen by the composition order of use cases, not by the architecture. The entity cannot express the truth at all: a single boolean has no room for `{console: yes, pc: no, ea_play: no, market: de-DE}`.

**Fix — AD-9: Availability is aggregate-owned state, not a column**

- **Binds:** the representation of availability; which unit may transition it; FR-1.1, FR-3.3, Story 2.3, Story 4.2.
- **Prevents:** a per-platform diff applied to a per-title flag; titles disappearing from the catalogue while still available; the same fact stored twice (a row-level flag and a platform table) and drifting.
- **Rule:** availability is a **set of value objects** (`Availability(market: str, platform: Platform, plan: Plan)`) owned by the `Game` aggregate, persisted in its own table keyed by `(product_id, market, platform, plan)`. No scalar `is_active` / `available` boolean may exist on the game row or in the entity. Every state transition is an aggregate method invoked once per run with the **union of all fetched slices**: `game.apply_availability(observed: frozenset[Availability], run: RunId)`. "Soft-deleted" means "availability set is empty", never "a flag was flipped". Use cases may not compute added/removed as sets of product ids; they compute a per-`Availability` delta and hand the whole delta to the aggregate. A test asserts that removing a title from one platform leaves it available on the others.

## C3 — The JSONB column has two writers with two shapes; the second silently erases raw Microsoft data

**Pair**

| Unit | Story |
| --- | --- |
| `src/infrastructure/persistence/repositories/sql_game_repository.py` (ingestion write) | 4.1 / 2.2 / 3.3 ("persisted with raw Microsoft data") |
| `src/application/use_cases/enrich_game.py` (enrichment write) | 3.2 (IGDB metadata) |

**Why each is compliant.** Dev A implements FR-3.1 exactly as written — "Use JSON/JSONB columns in PostgreSQL for flexible metadata schema" — as one opaque `metadata: Mapped[dict]` (`JSONB`). Writing the Microsoft hydration payload is required by Story 3.3 ("the title is persisted with raw Microsoft data"), so ingestion stores `{"raw_microsoft": {...}}` there. Dev B, per Story 3.2, gives the entity a mutator and the use case calls it with the IGDB record: `game.replace_metadata(record.to_dict())`, then `repo.save(game)`. AD-4 is satisfied verbatim — retrieve, invoke domain logic, save. AD-6 and AD-7 *require* the metadata shape to stay outside the domain (Pydantic DTOs live in `infrastructure`), so the domain cannot validate or even name the shape.

**Incompatibility.** Enrichment runs after ingestion in the same hourly run and **replaces** the column. For matched titles the raw Microsoft payload is gone; for unmatched titles it survives. Story 3.3's AC — "persisted with raw Microsoft data and **no metadata**" — is tested against an unmatched title, so it passes. The loss lands exactly on the population nobody tests, and it destroys the only record from which a later re-match could be attempted after IGDB metadata changes or after the manual-review script fixes a title (SPEC Assumptions: "manual resolution … via direct SQL scripts"). The two writers also disagree on key names (`cover` vs `cover_url`, `age_rating` vs `pegi`), so *no* consumer can read the column without knowing which writer ran last. AD-7 guarantees nothing mechanical catches this: `application` must not import the schema, and the JSONB type is invisible to import-linter.

**Fix — AD-10: Metadata payload ownership and merge semantics**

- **Binds:** the JSONB payload; who may write it; FR-2.3, FR-2.4, FR-3.1, Stories 3.2, 3.3, 4.1.
- **Prevents:** one column with two uncoordinated writers; raw upstream data erased by enrichment; key-name drift between writers; unreadable flexible schema.
- **Rule:** the JSONB payload is a **namespaced, merge-on-write** document, not a bag: exactly two top-level namespaces — `raw` (Microsoft, write-once per observation) and `enrichment` (IGDB, replaceable) — each with a declared shape expressed as a domain value object, serialized by a single mapper in `infrastructure`. Persistence **merges by namespace key** (`new = old | {namespace: value}`) and may never replace the whole column. Field-level ownership is explicit: Microsoft owns availability only (FR-2.3); IGDB owns every metadata field. A write that would remove a namespace it does not own is a domain error (`InvariantViolation`), tested. One round-trip test per namespace asserts every domain field survives persistence unchanged.

## C4 — Two mutation paths to "inactive", no ordering rule, and a partial fetch becomes a mass soft-delete

**Pair**

| Unit | Story |
| --- | --- |
| `src/application/use_cases/apply_catalog_state.py` (`save` sets `is_active=True`) | 4.1 |
| `src/application/use_cases/soft_delete_missing.py` → `repo.mark_inactive(product_ids)` (bulk `update()`) | 4.2 |

**Why each is compliant.** Dev A makes upsert restore availability, because Story 4.1 says existing titles are "updated in place" and a re-appearing title must be visible again; without that, a re-added title is invisible forever. Dev B needs to deactivate thousands of rows and writes a purpose-built port method implemented as one SQLAlchemy `update(...).values(is_active=False)`; AD-4 authorizes this because it says "explicitly call port methods **(e.g., `save`)**" — the `e.g.` makes any port method lawful. Both are `abc.ABC` ports (AD-3), both are orchestrated by use cases (AD-4), neither imports anything it should not (AD-1, AD-7).

**Incompatibility.** Three distinct failures, all reachable by compliant code:

1. **Ordering is undecided.** Nothing in the spine orders `apply_catalog_state` and `soft_delete_missing` inside a run. Both orders are correct against their own ACs, and both are wrong in one direction: marker-after-upsert is fine; upsert-after-marker re-activates everything the marker just removed, because the upsert's input list *is* the current catalogue.
2. **Bulk write bypasses the aggregate.** `mark_inactive` mutates state without invoking domain logic, so AD-4's "invoke domain logic on the entity" is honoured by the use case and evaded by the adapter. Any future invariant (do not deactivate without captured metadata; do not deactivate a title whose enrichment is pending) is unreachable from the bulk path.
3. **A degraded fetch deactivates the catalogue.** NFR-1 requires the batch to "pause/skip gracefully on outage". Story 2.2 hydrates in batches of 200; if batch 12 of 30 fails and the circuit opens, the run continues with a **smaller** catalogue. `detect_catalog_changes` (C2) sees thousands of absent titles, and `soft_delete_missing` faithfully deactivates them. No exception is raised, so AD-5 is satisfied and CI is green: **a brief Microsoft outage writes a false mass removal to the production catalogue**, which is the single most likely incident in this system.

**Fix — AD-11: Single mutation path and run-completeness gate**

- **Binds:** every state transition on `Game`; the right of a run to apply removals; NFR-1, FR-3.3, Stories 4.1, 4.2.
- **Prevents:** two ways to change one fact; ordering decided by wiring; an outage silently deleting the catalogue.
- **Rule:** each state transition has **exactly one owner** — a method on the aggregate — and repository ports expose **no** method that changes persisted state other than persisting an already-mutated aggregate (`save`); bulk `update`/`delete` statements are forbidden in repository implementations, asserted by a test that greps the adapters for `update(`/`delete(` outside `save`. Removals may be applied **only** from a snapshot certified complete: `CompleteCatalog` is a distinct domain type the ingestion use case can only produce when every platform slice and every hydration batch succeeded (partial results are `PartialCatalog`, which supports additions and enrichment but **not** removals). `Game.apply_availability` rejects a `PartialCatalog` with `IncompleteSnapshot`. The run applies additions, enrichment, then removals — in that order, in one use case — so ordering is a property of the architecture, not of the container.

## C5 — No transaction boundary: save-per-entity is the most literal reading of AD-4, and it corrupts the next run's baseline

**Pair**

| Unit | Story |
| --- | --- |
| `src/application/use_cases/apply_catalog_state.py` (`for entry in entries: repo.save(entry)`) | 4.1 |
| `src/infrastructure/persistence/repositories/sql_game_repository.py` (`with self._session.begin():` inside `save`) | 1.3 / 4.1 |

**Why each is compliant.** AD-4 describes the flow in the **singular**: "retrieve entities via ports, invoke domain logic on the entity, and explicitly call port methods (e.g., `save`) to persist the new state". A loop over the entry list is the most faithful implementation of that sentence. Dev B's `save` needs a session to write, so it opens one — and `repository` is an infrastructure concern, so owning `begin()` there is the ordinary SQLAlchemy pattern. No AD mentions transactions, sessions, unit-of-work, or which layer commits; AD-6 only says "SQLAlchemy for ORM and persistence in the Infrastructure layer".

**Incompatibility.** A run is ~30 hydration batches and thousands of titles. Per-entity commit means a crash, a circuit-break or a SIGTERM at item 2,500 leaves the catalogue **half-migrated** and leaves `igdb_id`/metadata half-written, while the run's own bookkeeping (if any) says nothing. The next hourly run diffs against that half-applied state and produces spurious removals — which then flow into C4's bulk-deactivate path. The same hole makes Story 4.1's "no duplicate rows" test order-dependent: the alternative implementation (`repo.save_all(entries)` in one transaction) is equally compliant and has entirely different failure semantics, and neither dev can tell from the spine which one the system needs.

**Fix — AD-12: Unit of work and transaction ownership**

- **Binds:** transaction boundaries; who commits; FR-3.2, FR-3.3, NFR-1, Stories 2.3, 4.1, 4.2.
- **Prevents:** a half-applied run poisoning the next run's diff; two different atomicity models behind one port; adapters committing in the middle of a use case.
- **Rule:** **one sync run is one unit of work.** The application layer obtains a `UnitOfWork` port (an `abc.ABC`) whose `commit()`/`rollback()` bracket the whole run; repository methods **never** commit, begin or end a transaction and take the session from the unit of work. The run's writes — availability, enrichment, removals, and the run record — commit atomically as the last statement of the run, and a failed or aborted run leaves the previous state byte-identical. A test asserts that an exception raised mid-run leaves row counts and payloads unchanged.

---

# HIGH

## H1 — AD-5 has no failure taxonomy, and AD-1 forbids the inner layers from naming anyone else's

**Pair**

| Unit | Story |
| --- | --- |
| `src/infrastructure/adapters/igdb/igdb_adapter.py` (catches `httpx` errors, raises `IgdbUnavailable(DomainError)`) | 3.1 |
| `src/application/use_cases/enrich_game.py` (`except DomainError: persist raw`) | 3.2 / 3.3 |

**Why each is compliant.** AD-5: "Domain and Application layers raise explicit, custom Domain Exceptions … The outermost layer is exclusively responsible for catching these exceptions." Dev A obeys it exactly: `httpx` stays in `infrastructure` (AD-7), the adapter translates its transport failure into a **domain** exception, the port is `abc.ABC` (AD-3), the exception lives in `src/domain/exceptions.py` (Story 1.3).

Dev B must satisfy FR-2.4 ("on exact-name match failure, skip enrichment, persist raw Microsoft data, log") and NFR-1 ("on outage, pause/skip gracefully without crashing the batch"). It catches `DomainError` — the only type it can name, since importing the adapter is forbidden by AD-1 — and persists the raw payload.

**Incompatibility.** The timeout and the no-match are both `DomainError` subclasses with no convention distinguishing them, so dev B's correct-for-no-match handler is also a correct-looking handler for an outage. Two equally compliant resolutions, both wrong:

- swallow the outage as "no match" → every title in the affected window is persisted as permanently unmatched, and since enrichment only runs for titles *arriving* in the catalogue, nothing ever revisits them: NFR-1's "pause/skip" became a permanent quality regression, silently;
- re-raise → the batch dies mid-loop (C5 makes that a partial write) and NFR-1 is violated outright.

It gets worse at the seam: dev A implements the circuit breaker (NFR-1, SPEC Constraints) inside the adapter and raises on *open*. Dev B, having converted the first three timeouts into "no match", consumes no retry budget and logs no outage, so the breaker opens against a caller that believes everything succeeded. Nothing in the spine requires the taxonomy to be closed (a second adapter can invent `MicrosoftQuotaExceeded` freely), nor that `RetryableError` and `PermanentError` be distinguishable by the application.

**Fix — AD-13: Closed failure taxonomy, with retryability as a domain fact**

- **Binds:** the exception vocabulary crossing every port; how the application branches on failure; AD-5; NFR-1, FR-2.4.
- **Prevents:** an outage indistinguishable from a no-match; adapter-local exception families the application can never catch; "skip gracefully" degrading into permanent data loss.
- **Rule:** the inner layers own a **closed** taxonomy in `src/domain/exceptions.py`: `DomainError` → `RetryableUpstreamError(upstream, retry_after)` and `PermanentUpstreamError(upstream, reason)`, with `EntityNotFound` and `InvariantViolation` under `DomainError` directly. Adapters **must** raise exactly these and must not define their own exception classes (a test asserts no `Exception` subclass is declared outside `domain/exceptions.py`). The application must branch on the two categories: `RetryableUpstreamError` aborts the run and marks it incomplete (so AD-11 forbids removals and AD-12 rolls back); `PermanentUpstreamError` is handled per item and recorded for review (AD-22). AD-5 is amended to say the outermost layer *translates for presentation only* — it is no longer the first place allowed to know something went wrong.

## H2 — Ports have no home and no signature rule, so the domain and the diagram push the same port in opposite directions

**Pair**

| Unit | Story |
| --- | --- |
| `src/domain/ports/game_repository.py` | 1.3 |
| `src/application/ports/igdb_port.py` returning `src/application/dtos/igdb_record.py` | 3.1 |

**Why each is compliant.** AD-3 says a port is "the interface defining what the **domain** needs from infrastructure" → dev A puts it in `domain`. The structural diagram (`ARCHITECTURE-SPINE.md:76-79`) draws a `Ports / abc.ABC` box **inside Application** → dev B puts it in `application`. Both cite the spine, both are `abc.ABC`, both are inward-only imports. AD-6 says "Pydantic for DTOs"; AD-7 says Pydantic lives in `infrastructure`; so dev B's port returns a frozen dataclass DTO rather than a Pydantic model — defensible, and the only shape AD-7 leaves legal.

**Incompatibility.** The collision is **forced, not chosen**: `src/domain/entities/game.py` cannot import `application` (AD-1), so `game.apply_metadata(record: IgdbRecord)` is unrepresentable — the domain method dev B needs cannot be annotated, and dev B's only escapes are (a) duplicate the DTO in `domain` (two shapes for one payload, which is C3 again), or (b) move the port to `domain` (which is dev A's answer — so AD-3 and the diagram cannot both be obeyed by one codebase). Second, Story 2.3's own text — "the previously known catalog is read via the repository port … a **minimal read-capable adapter** is sufficient for this story" — invites a second port for the same concept, and a dev who reads the diagram places it in `application`: `src/application/ports/catalog_snapshot_port.py::find_known_products() -> list[str]`. Now two ports, two adapters, two queries over the same table with different filters (`is_active` vs `last_seen_at`) — which is exactly the divergent-baseline condition that triggers C4's false removals. Third, a Pydantic DTO crossing a port forces `application` to import `pydantic` for the annotation; `from __future__ import annotations` plus `TYPE_CHECKING` does not help, because import-linter builds the module graph from the AST and counts those imports, so AD-7's forbidden contract breaks the build on the pattern AD-6 encourages.

**Fix — AD-14: Port placement, granularity and signature discipline**

- **Binds:** where ports live, how many exist per external system, and what types may appear in their signatures; AD-3; Stories 1.3, 2.1, 2.3, 3.1.
- **Prevents:** the same port in two layers; a second read port per use case; port signatures that drag third-party types into the inner layers; DI registration keys that do not match.
- **Rule:** **every** port lives in `src/domain/ports/` (AD-3's reading wins; the diagram is corrected to show ports in Domain, implemented in Infrastructure). Exactly **one** port per external system — `MicrosoftCatalogPort`, `IgdbPort`, `GameRepository`, `UnitOfWork`, `Clock`, `RunLock` — and adding a port requires amending this AD; "a minimal read port for this story" is forbidden. Port signatures may mention only stdlib types, domain types and domain exceptions: no Pydantic models, no dicts-as-DTOs, no ORM rows. Pydantic is reserved for configuration and for parsing upstream wire payloads **inside** the adapter, which then constructs domain value objects. Ports are registered and resolved by their abstract type, and a test asserts every port is implemented by exactly one adapter.

## H3 — Nobody owns any field, so the hourly upsert erases the hourly enrichment (or re-queries IGDB forever)

**Pair**

| Unit | Story |
| --- | --- |
| `src/infrastructure/persistence/repositories/sql_game_repository.py::upsert` (builds the row from the Microsoft-sourced entry only) | 4.1 |
| `src/application/use_cases/enrich_game.py` (`save` with `igdb_id` + metadata) | 3.2 |

**Why each is compliant.** Story 4.1 says the repository upserts "catalog entries"; the catalog entry is by definition the Microsoft-sourced object from Story 2.2. Dev A maps that object's fields onto the row and lets every other column take its model default. Dev B persists the enriched aggregate through the same port method (AD-4: "call port methods (e.g., `save`)"). Neither unit breaks an AD; neither story mentions the other's columns.

**Incompatibility.** Two orderings, both compliant, both destructive:

- **upsert → enrich:** the upsert sets `igdb_id = None` (model default) every hour, so enrichment's "already enriched, skip" check never holds; every title is re-queried against IGDB **every hour, forever**. IGDB's rate limit plus NFR-1's breaker means the circuit opens in hour 1 and never closes — the enrichment epic degrades to a permanent no-op that reports success.
- **enrich → upsert:** the enrichment is erased every hour, so `metadata` is always empty at read time and CAP-2's success criterion ("titles matching IGDB have their metadata enriched") is never observable.

FR-2.3 ("IGDB is the absolute source of truth for metadata") argues for enrichment last; FR-3.2 ("perform upserts for newly found or updated games") argues for upsert last. Both are in the spec, and the spine adjudicates neither. The same hole applies to `is_active` (C4) and to any future column.

**Fix — AD-10 (extension): field-level ownership, merge-only upserts**

- **Binds:** which source owns which field; what `save` may overwrite; FR-2.3, FR-3.2, Stories 3.2, 4.1.
- **Prevents:** an hourly write silently resetting another epic's columns; permanent re-query loops; source-of-truth drift between Microsoft and IGDB.
- **Rule:** every persisted field has exactly **one owning source**, stated in a table in this AD: Microsoft owns availability (`AD-9`), IGDB owns `/enrichment` and `igdb_id`, the system owns identity (`AD-8`), timestamps and the run stamp. `save` merges owned fields and **never** writes a field it does not own; an entity loaded, modified and saved by one use case must not reset another epic's fields, asserted by a test that saves a fully enriched game through the ingestion path and compares every column. Enrichment is **idempotent and skip-aware**: a game with `igdb_id` set is not re-queried unless a re-enrichment flag is set, and re-enrichment is an explicit use case, not a side effect of the hourly run.

## H4 — Time has two representations on either side of the persistence seam

**Pair**

| Unit | Story |
| --- | --- |
| `src/domain/entities/game.py` (`datetime.now()` / `datetime.utcnow()`, `last_seen_at: datetime`) | 1.3 |
| `src/infrastructure/persistence/models/game_model.py` (`DateTime(timezone=True)` / `server_default=func.now()`) | 1.3 / 4.1 |

**Why each is compliant.** AD-7 forbids third-party libraries inside `domain`, so dev A reaches for stdlib `datetime` — and `datetime.now()` is stdlib, obvious, and readable. Dev B follows the SQLAlchemy recommendation for PostgreSQL and declares `mapped_column(DateTime(timezone=True), server_default=func.now())`, which is the correct column type. Neither unit violates anything; AD-6 says "SQLAlchemy for ORM", and no AD mentions clocks, timezones or temporal types.

**Incompatibility.** Reading `TIMESTAMP WITH TIME ZONE` yields **aware** datetimes, so every entity that comes from the repository is aware while every timestamp the domain stamps itself (per AD-4, the entity mutates its own state) is naive. `src/application/use_cases/detect_catalog_changes.py` then evaluates `game.last_seen_at < run_started_at` → `TypeError: can't compare offset-naive and offset-aware datetimes` — but only on the production wiring, because unit tests construct both sides in-process and consistently. Switching dev B's column to `TIMESTAMP` (naive) fixes the comparison and breaks the raw JSONB payload: a Microsoft product payload carrying `LastModified` cannot be `json.dumps`-ed (`TypeError: Object of type datetime is not JSON serializable`), which surfaces as a write failure inside the adapter — i.e. it becomes an infrastructure exception with no AD-5 translation (H1). Additionally, nothing forbids calling `datetime.now()` *inside* a use case, so "now" differs per unit and the run's own diff is not reproducible or testable.

**Fix — AD-15: Time is injected, aware, UTC and stored as such**

- **Binds:** every temporal value and every clock read; AD-7; Stories 1.3, 2.3, 4.1, 4.2.
- **Prevents:** naive/aware comparisons failing only against a real database; non-reproducible runs; un-serializable payloads.
- **Rule:** all domain datetimes are **timezone-aware UTC** (`datetime.now(timezone.utc)`); naive datetimes are forbidden and a test rejects any `datetime` value with `tzinfo is None` at the entity boundary. No unit calls `datetime.now()` directly: a `Clock` port (`now() -> datetime`, `abc.ABC`) is injected, so runs are reproducible under a fake clock. Persistence uses `TIMESTAMP WITH TIME ZONE` exclusively, and the mapper converts on both directions. Wire payloads are stored as received (JSON-safe strings), never as Python datetime objects.

## H5 — The natural attribute name for the JSONB column is reserved, and the workaround silently writes the wrong object

**Pair**

| Unit | Story |
| --- | --- |
| `src/domain/entities/game.py` (`self.metadata: Mapping[str, object]`) | 1.3 |
| `src/infrastructure/persistence/models/game_model.py` (`payload = mapped_column("metadata", JSONB)`) | 1.3 |

**Why each is compliant.** FR-3.1 says "JSON/JSONB columns … for metadata"; Story 1.3 says "a PostgreSQL schema with JSON/JSONB metadata" — so `metadata` is the name both stories use, and dev A uses it on the entity. Dev B cannot: SQLAlchemy's Declarative API reserves the attribute name `metadata` (`InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API`) because it belongs to `DeclarativeBase.metadata`. Renaming the Python attribute to `payload` while keeping the DB column named `metadata` is the correct, documented workaround. Both units are innocuous; no AD says a word about ORM attribute naming or mapping.

**Incompatibility.** The translation now exists **only** in a mapper that no AD mentions and no test covers: `src/infrastructure/persistence/mappers/game_mapper.py` maps `game.metadata ↔ row.payload`. A later unit — say the enrichment save path, or a bulk field update added for Story 4.2 — writes `row.metadata = game.metadata` and gets no exception: on a mapped class instance, `metadata` resolves to the class-level `MetaData` object, so either the assignment creates a shadowing instance attribute that is never persisted (data vanishes, silently, at commit) or the read returns a `MetaData` and `dict(...)` blows up far from the cause. `Base.metadata` also shows up in Alembic autogenerate, so a schema-only reader believes the column is unmapped. AD-6 guarantees SQLAlchemy is present and AD-7 guarantees the domain cannot see the ORM, so nothing bridges the two names by force.

**Fix — AD-16: One mapper per aggregate, round-trip proven, forbidden attribute names**

- **Binds:** the domain↔ORM mapping surface; Stories 1.3, 3.2, 4.1.
- **Prevents:** silent divergence between a domain attribute and its column; ad-hoc attribute copies outside the mapper; names that collide with Declarative internals.
- **Rule:** each aggregate has **exactly one** mapper module under `src/infrastructure/persistence/mappers/`; no other module may assign ORM attributes directly. No mapped attribute may be named `metadata`, `registry` or `query`; the domain keeps `metadata`, the ORM attribute is `payload`, mapped with an explicit `mapped_column("metadata")`. A round-trip test asserts every domain field survives `save` → `get` unchanged, and a schema test asserts the DB column list matches the mapper's declarations.

## H6 — The composition root has no legal, verifiable home, and one plausible location is not even packaged

**Pair**

| Unit | Story |
| --- | --- |
| `src/container.py` (DI container at package root) | 1.2 |
| `src/infrastructure/entrypoints/hourly_sync_job.py` (needs the container) | 2.4 |

**Why each is compliant.** AD-1 says "the layers live at exactly `src/domain`, `src/application`, `src/infrastructure`" — it constrains where *layers* live, and says nothing that forbids a module next to them. AD-2 says "DI must be orchestrated via a DI Container framework" and names neither the framework nor the file. `src/container.py` is a common convention and it imports both `application` and `infrastructure`, which no declared contract watches because `root_packages = ["domain", "application", "infrastructure"]` does not include it.

**Incompatibility.** Three, all mechanical:

1. **Invisible to every gate.** `tests/test_layers.py:97-107` enumerates `src/*` with `path.is_dir()` — a **file** at `src/` root escapes the coverage assertion, and a module outside every root package is not analysed by import-linter at all. The composition root is the one module allowed to touch everything, and it is the one module nothing checks.
2. **Not in the artifact.** `pyproject.toml` builds the wheel from `packages = ["src/domain", "src/application", "src/infrastructure"]` and `deferred-work.md` already records that `[project.scripts]` is absent. So `pip install` produces a package with **no entrypoint and no composition root**: `uv run` from the checkout works, the deployed artifact cannot start. Story 2.4 can be "done" and undeployable.
3. **Two roots.** Dev B, blocked in CI from importing an unpackaged module (or simply working in `infrastructure` where the story lives), adds `src/infrastructure/container.py`. Now there are two wiring paths; `tests/conftest.py` uses one and the process uses the other, so the integration path is never the tested path.

**Fix — AD-17: One composition root, inside the packaged layers**

- **Binds:** where wiring lives; what may sit at `src/` root; the distribution shape; AD-1, AD-2; Story 1.2.
- **Prevents:** an ungoverned module that may import anything; an unpackaged entrypoint; two wiring paths (tested vs. deployed).
- **Rule:** exactly one composition root, `src/infrastructure/composition.py`, exposing `build_sync_run(...)` and nothing else; it is the **only** module permitted to construct adapters. `src/` contains exactly the three layer packages — `tests/test_layers.py` is extended to assert no files or extra packages at `src/` root, and `root_packages` parity is asserted over directories *and* modules. Entrypoints are `src/infrastructure/entrypoints/*`, receive the composition root's return value, and construct nothing. `[project.scripts]` declares at least one entrypoint, and a test asserts every `src/` package appears in `[tool.hatch.build.targets.wheel].packages`.

## H7 — Entrypoints may call repositories directly, because `infrastructure` is a single layer and AD-4 binds only use cases

**Pair**

| Unit | Story |
| --- | --- |
| `src/infrastructure/entrypoints/hourly_sync_job.py` (calls `SqlGameRepository` itself) | 2.4 |
| `src/application/use_cases/run_catalog_sync.py` (the orchestrated pipeline) | 2.3 / 4.1 |

**Why each is compliant.** Story 2.4's AC is two lines: "the worker is running" → "the ingestion pipeline executes automatically". A dev can satisfy it by having the job call the adapters it already has: `sigls = MicrosoftCatalogAdapter(...)`, `repo = SqlGameRepository(session)`, fetch, hydrate, `repo.upsert(entries)`. Every AD holds: AD-1 (imports `infrastructure`→`infrastructure` is intra-layer, and `infrastructure`→`domain` is the permitted direction; the `layers` contract treats `infrastructure` as one blob, so the answer is KEPT), AD-3 (the adapter implements the `abc.ABC` port), AD-5 (the entrypoint catches domain exceptions — it is the outermost layer, exactly as required), AD-6/AD-7 (SQLAlchemy stays in infra). AD-4 is not violated because AD-4 has **scope = "Use Cases (Application layer)"**, and this code contains no use case.

**Incompatibility.** The pipeline now exists twice: once as `run_catalog_sync` (which the story's tests exercise) and once inside the entrypoint (which the process actually executes). The two drift immediately — the entrypoint's version has no completeness gate (AD-11), no unit of work (AD-12), no `Clock` (AD-15) and no aggregate mutation (AD-9) — so every subsequent AD in this list is unenforceable by construction: a developer can implement the architecture perfectly in `application` and the deployed system bypasses it wholesale. This is the deepest structural hole after C1: **the spine states a dependency direction but no driving-side discipline**, so "the use case is the only mutator" is a convention, not an invariant.

**Fix — AD-18: Driving-side discipline (entrypoints → use cases only)**

- **Binds:** what an entrypoint may import and call; AD-1's intra-`infrastructure` freedom; AD-4's scope.
- **Prevents:** a second, ungoverned pipeline in the entrypoint; adapters being driven directly with no use case; AD-4 becoming vacuous.
- **Rule:** `src/infrastructure` is split into `src/infrastructure/entrypoints/` and `src/infrastructure/adapters/`, and a second import-linter contract forbids `infrastructure.entrypoints` → `infrastructure.adapters` (entrypoints may import only `infrastructure.composition` and `application`). An entrypoint's whole body is: build the run, call one use case, translate its exception (AD-5). Adapters may be constructed only by the composition root (AD-17). A test asserts the entrypoints package imports nothing from `infrastructure.adapters`.

## H8 — Two schedulers, no run lock, and the second run eats the first

**Pair**

| Unit | Story |
| --- | --- |
| `src/infrastructure/entrypoints/apscheduler_runner.py` (`BackgroundScheduler`, in-process cron) | 2.4 |
| `src/infrastructure/entrypoints/hourly_sync_job.py` (one-shot process invoked by external cron) | 2.4 |

**Why each is compliant.** Story 2.4 says "when an hour elapses … the ingestion pipeline executes automatically" and Story 1.2's config lists "cron interval". APScheduler is the obvious library; external cron (systemd timer, Kubernetes CronJob, GitHub Actions schedule) is the obvious infrastructure. Both satisfy the AC, both keep the third-party library in `infrastructure` (AD-7), both call a use case (AD-4). No AD mentions the execution model, the cadence shape (integer hours vs cron expression — the two units parse Story 1.2's "cron interval" differently), overlap, or leadership.

**Incompatibility.** With the in-process runner, a run that exceeds 60 minutes — likely, given 30 hydration batches plus one IGDB request per title plus NFR-1 backoff — overlaps its successor. Two runs then read the same baseline (C2), compute removals from two different snapshots, and write concurrently: duplicate inserts under C1's surrogate key, mutually contradictory availability writes under AD-9's union rule, and a second bulk-deactivate racing the first. With external cron the topology is safer but the unit relies on a packaged entrypoint that H6 shows does not exist yet, and nothing prevents two replicas from ticking simultaneously. The system has no concept of "a run", so it cannot record which run wrote a row, cannot detect an overlap, and cannot be asked "did the 03:00 run succeed?".

**Fix — AD-19: Run model, cadence and mutual exclusion**

- **Binds:** how often the sync runs, how overlap is prevented, what a run is; NFR-1, Story 2.4, Story 1.2's config.
- **Prevents:** concurrent runs corrupting the catalogue; in-process timers that hide failures; an unanswerable "did the hour succeed?".
- **Rule:** the sync is a **single-shot process**; no in-process scheduler, no threads. Cadence is external (platform cron), expressed in configuration as a **cron expression string**, not an interval integer. Each run acquires a named PostgreSQL advisory lock through a `RunLock` port and exits cleanly without writing if it cannot; it mints a `RunId`, stamps every row it writes (`last_modified_by_run`), and records start/end/outcome plus counts in a `sync_runs` table so the run is queryable. A test asserts a second concurrent `acquire()` fails fast and leaves the database untouched.

---

# MEDIUM

## M1 — AD-2's letter and AD-7's letter contradict each other, and only one of the two is enforced

**Pair:** `src/application/use_cases/detect_catalog_changes.py` decorated with `@inject` + `Provide[...]` (dependency-injector's idiomatic API, Story 1.2/2.3) vs. `src/infrastructure/composition.py` with explicit constructor wiring.

**Why each is compliant.** AD-2: "Dependency Injection must be orchestrated via a **DI Container framework** … ensuring the Application layer only asks for abstractions." `@inject` plus `Provide[Container.repo]` is how the most popular framework does exactly that, so the use case "asks for abstractions" and nothing is hardcoded. AD-7 forbids third-party imports in `application`, which the decorator requires.

**Incompatibility.** Unit A satisfies AD-2 and breaks AD-7; unit B satisfies both. The spine gives no precedence rule, so the first developer to read AD-2 writes code that the AD-7 contract rejects — and the natural "fix" is to relax the forbidden list, which silently disables the most valuable AD in the document. `review-tech-currency.md` covers the package choice (four-way, with a PyPI stub at the obvious name); the *architectural* gap is that the injection **style** is unpinned.

**Fix — AD-20: Injection style is constructor injection; containers do not reach the inner layers**

- **Binds:** how dependencies arrive in `domain`/`application`; AD-2, AD-7.
- **Prevents:** container libraries annotating inner-layer code; AD-7 being relaxed to accommodate AD-2.
- **Rule:** dependencies arrive **only as constructor parameters** typed against `abc.ABC` ports. No decorators, markers, `Provide[...]`, service-locator lookups or global registries in `domain` or `application`. The container lives only in `infrastructure/composition.py` (AD-17), and the container library itself is added to AD-7's forbidden set with a negative control. If a container can only express itself through inner-layer markers, that container is disqualified.

## M2 — Title normalization is owned by no one, and the manual-review query is written against the wrong string

**Pair:** `src/domain/value_objects/title.py` (NFC normalize, collapse whitespace, strip `™`/`®`) vs. `src/infrastructure/adapters/igdb/igdb_adapter.py` (sends `entry.name` verbatim).

**Why each is compliant.** FR-2.1: "Query the IGDB API using the **exact title string provided by Microsoft**" — dev B is implementing the requirement literally. Dev A is enforcing a domain invariant ("one canonical spelling per title") for the same requirement, also literally.

**Incompatibility.** Microsoft returns names with trailing padding, `™`, and non-NFC accents; the two units therefore query different strings, and the match rate depends on which one is live. Worse for the SPEC's stated resolution path — "manual resolution … via direct SQL scripts": the script joins on the **stored** title while the adapter queried the **normalized** one, so the rows flagged for review cannot be reproduced by hand; and an entity round-tripped through the repository gets normalized on read but was written raw, so the same product has two spellings depending on the access path. No AD mentions normalization, and neither FR nor story says who owns it.

**Fix — AD-21: One normalizer, in the domain, used at every boundary**

- **Binds:** the comparison/matching key for titles; FR-2.1…FR-2.4.
- **Prevents:** adapter-decided matching; un-reproducible manual-review queries; two spellings for one product.
- **Rule:** a `Title` value object (stdlib `unicodedata` only) is the **only** normalization; adapters, use cases and persistence accept and emit `Title`, never `str`. The raw upstream string is stored separately (`raw` namespace, AD-10) and never used for matching. The matching key is persisted alongside the title so the manual-review query reproduces the adapter's request exactly.

## M3 — "Logged as an exception for manual review" is owned by nobody, and AD-5 forbids the layer the story needs to do it

**Pair:** `src/application/use_cases/enrich_game.py` (logs via stdlib `logging`) vs. `src/infrastructure/entrypoints/hourly_sync_job.py` (configures logging and is, per AD-5, "exclusively responsible").

**Why each is compliant.** Story 3.3's AC: "the failure is logged as an exception for manual review" — dev A logs it where it is detected. AD-5: "the outermost layer is exclusively responsible for catching these exceptions and translating them into the appropriate infrastructure response (e.g., specific logs, queue NACKs, HTTP codes)" — dev B configures logging and owns the translation. Both are obeying a document that says two different things.

**Incompatibility.** If dev A logs (AD-5 violation), the record is unstructured and dies with log rotation, so FR-2.4's "flagged for intervention" is not a queryable state and SPEC's direct-SQL workflow has nothing to select. If dev B logs (AD-5-compliant), the use case cannot say *why* — it has no access to the unmatched title's identity once the exception unwinds, and the batch continues so the entrypoint sees nothing. Either way, "manual review" has no owner, no schema, and no durability; and AD-5's "exclusively" makes the correct implementation illegal.

**Fix — AD-22: Review queue is a port, not a log line**

- **Binds:** how enrichment failures are recorded; AD-5's scope; FR-2.4, Story 3.3.
- **Prevents:** review state living in rotated logs; the use case configuring logging; AD-5 outlawing the only legal recording path.
- **Rule:** unmatched titles are recorded through a `ReviewQueue` **port** (`record(UnmatchedTitle)`) into a persistent table with stable fields (`product_id`, `raw_title`, `attempted_query`, `run_id`, `reason`, `recorded_at`), queryable by SQL — not logged. Structured logging is configured only in `infrastructure`, and the application may emit records only through ports. AD-5 is amended: the outer layer translates *exceptions into transport responses*; the inner layers *report* through ports.

## M4 — Port conformance is unproven, so the fake in tests and the adapter in production disagree

**Pair:** `tests/unit/fakes/fake_game_repository.py` vs. `src/infrastructure/persistence/repositories/sql_game_repository.py`.

**Why each is compliant.** The fake subclasses the `abc.ABC` port (AD-3), so ABC instantiation guarantees method **presence**. `tests/` is not a root package, so AD-1's contract does not apply to it and the fake may import anything. AD-7's forbidden contracts cover `domain`/`application` only.

**Incompatibility.** Presence is not behaviour. The fake dedupes by object identity or by `id`; the SQL adapter dedupes by `product_id` (AD-8) — so C1's duplicate-insert bug is **invisible in every unit test** and appears first in production. The same holds for C5 (fake never commits, so half-applied runs cannot be tested), C3 (fake stores whatever dict, no merge semantics) and AD-9 (fake has no availability table). Combined with AD-4's description of mutation as "retrieve → invoke → save", the shape of the unit tests is fixed by the spine while the behaviour they must guard is not.

**Fix — AD-23: Port conformance suites**

- **Binds:** how a port's behaviour is specified; the status of test doubles; NFR-3.
- **Prevents:** a fake and an adapter that satisfy the same ABC and disagree; behavioural bugs only visible in production.
- **Rule:** every port ships an **abstract conformance test class** in `tests/ports/`, and every implementation — production adapter *and* in-memory fake — must subclass and pass it. The conformance suite is part of the port's definition: adding a port without a suite is an incomplete port. Conformance tests run against both the fake and a real PostgreSQL instance (testcontainers or a CI service), and the fake and adapter may not be used interchangeably anywhere the suite does not cover.

## M5 — "Preserving history" is satisfied by a boolean that records no history

**Pair:** `src/application/use_cases/soft_delete_missing.py` (`is_active = False`) vs. `src/infrastructure/persistence/repositories/sql_game_repository.py::list_removed_since` (reads `removed_at`).

**Why each is compliant.** FR-3.3 says "flag them inactive (preserving history)"; Story 4.2 says "its metadata/history remains queryable". Dev A reads that as "the row is not deleted". Dev B, needing "recently removed titles" (CAP-1's success criterion: "currently available and **recently removed** titles"), adds `removed_at: datetime | None` and writes it on deactivation — a superset, fully compliant.

**Incompatibility.** A boolean cannot answer "recently removed" — it cannot distinguish "removed three weeks ago" from "never added", and once a title returns and leaves again the previous interval is lost. So dev B's `removed_at` becomes the de-facto truth while AD-9's availability set (correct fix for C2) makes both redundant; three representations of one fact (bool, timestamp, availability rows) exist and drift. Story 4.2's AC passes against either. No AD defines what "history" means, so it is unverifiable.

**Fix — AD-9 (extension): history is the availability transition log**

- **Binds:** the meaning of "preserving history"; FR-3.3, Story 4.2, CAP-1.
- **Prevents:** a boolean standing in for history; three representations of availability.
- **Rule:** history is an append-only `availability_transition` table (`product_id`, `availability`, `run_id`, `observed_at`, `kind ∈ {added, removed}`), written by the aggregate in the same unit of work (AD-12). No `is_active`, and no free-standing `removed_at` — "recently removed" is a query over transitions within a window, and a test asserts that a title removed, restored and removed again yields three transitions and no lost interval.

---

# LOW

## L1 — Canonical layout is unpinned, so every unit is a coin flip on names

**Pair:** `src/application/use_cases/ingest.py` + `src/domain/ports/game_repository.py` vs. `src/application/services/ingest_catalog.py` + `src/domain/repositories/game_repository.py`. Both obey AD-1 (folders) and AD-3 (`abc.ABC`); `use_cases`/`services` and `ports`/`repositories`/`interfaces` are all common. Result: `git grep` for a component misses half of it, reviewers argue about placement, and the composition root imports from both conventions forever.

**Fix — AD-24 (Layout): one canonical tree, asserted by a test.**
**Binds:** module placement and naming below the three layers. **Prevents:** per-developer vocabulary; discoverability loss; import churn. **Rule:** the spine publishes the exact tree (`domain/{entities,value_objects,ports,exceptions}.py`, `application/use_cases/{verb_noun}.py`, `infrastructure/{adapters,persistence/{models,repositories,mappers},entrypoints,composition}.py`) and a test asserts that no other package names exist under `src/`.

## L2 — AD-4's "e.g., `save`" makes the persist surface arbitrary

**Pair:** `repo.save(game)` (dev A) vs. `repo.upsert(game)` / `repo.store(game)` / `repo.persist(entries)` (dev B). AD-4's parenthetical legitimizes all of them, so the port's method set, its arity (entity vs. list) and its return type (`None` vs. `Game` vs. id) are decided per unit. Result: the fake, the adapter and the use case must be rewritten each time a story changes the verb, and the conformance suite (AD-23) cannot be written against a moving name. (The rubric-walker review records the same gap as L2; the adversarial consequence is that the *seam AD-23 depends on* does not exist.)

**Fix:** fold into **AD-14** — the port surface is enumerated in the AD itself, and the phrase "e.g., `save`" is deleted so the method name is no longer advisory. **Rule:** `GameRepository` exposes exactly `get(product_id) -> Game`, `save(game: Game) -> None`, `list_active() -> list[Game]`; any addition is a change to this AD.

---

# Consolidated AD index

Paste-ready ordering. `AD-8`…`AD-24` are numbered to append after the existing seven; re-sequence to taste, but keep the cross-references (`AD-9` is referenced by `AD-10`, `AD-11`, `AD-12`, `AD-19`).

| AD | Name | Closes | One-line rule |
| --- | --- | --- | --- |
| AD-8 | Canonical entity identity | C1 | Identity is the upstream natural key (`product_id`), immutable; upsert conflicts on it; no surrogates. |
| AD-9 | Availability is aggregate-owned | C2, M5 | A `Game` owns a set of `Availability` VOs; no `is_active`; transitions logged, not flagged. |
| AD-10 | Payload ownership & merge | C3, H3 | Namespaced JSONB (`raw`, `enrichment`), merge-on-write, field-level source ownership. |
| AD-11 | Single mutation path + completeness gate | C4 | Only aggregate methods mutate; `PartialCatalog` may never cause a removal. |
| AD-12 | Unit of work | C5 | One run = one transaction; repositories never commit; failure leaves state untouched. |
| AD-13 | Closed failure taxonomy | H1 | `RetryableUpstreamError` vs `PermanentUpstreamError`, owned by domain, closed set. |
| AD-14 | Port placement & signatures | H2, L2 | All ports in `domain/ports`, one per external system, domain types only, enumerated surface. |
| AD-15 | Time | H4 | Aware UTC only, injected `Clock`, `TIMESTAMP WITH TIME ZONE`. |
| AD-16 | Mapping discipline | H5 | One mapper per aggregate, round-trip proven, `metadata` forbidden as an ORM attribute. |
| AD-17 | Composition root | H6 | One root in `infrastructure/composition.py`; `src/` holds only the three packages; entrypoint packaged. |
| AD-18 | Driving-side discipline | H7 | Entrypoints import the composition root and `application` — never adapters. |
| AD-19 | Run model | H8 | Single-shot process, external cadence, advisory lock, `RunId` stamped on every write. |
| AD-20 | Injection style | M1 | Constructor injection only; no container markers in the inner layers. |
| AD-21 | Title normalization | M2 | One `Title` VO, used at every boundary; raw string stored separately. |
| AD-22 | Review queue | M3 | Unmatched titles persist through a port, not a log line; logging is infra-only. |
| AD-23 | Port conformance suites | M4 | Every port ships an abstract conformance test; fake and adapter must both pass. |
| AD-24 | Canonical layout | L1 | The exact module tree is part of the AD and is test-asserted. |

Two amendments to existing ADs are also required and are not optional:

- **AD-5** is wrong as written (`:48`). "The outermost layer is exclusively responsible for catching these exceptions" (a) makes Story 3.3's logging requirement illegal, (b) gives adapters nowhere to put retryability, and (c) leaves the application unable to distinguish an outage from a no-match. Amend to: *the inner layers raise a closed taxonomy (`AD-13`) and report through ports; the outermost layer translates a `DomainError` into a transport/operational response and is the only place that configures logging or decides exit status.*
- **AD-4** (`:43`) is right in spirit and under-specified in fact: it fixes the *shape* of a mutation (retrieve → mutate → save) but not its *unit* (one entity vs. one run, `AD-12`), not its *owner* (the aggregate vs. a bulk repository method, `AD-11`), not its *scope* (use cases only, so entrypoints are free, `AD-18`), and not its *port surface* (the `e.g.` in "e.g., `save`", `AD-14`).

# What this spine already gets right (do not weaken it while fixing the above)

- **AD-1's three-layer enforcement is real and verified.** `pyproject.toml:40-46` matches `tests/test_layers.py:87-107`, the negative controls at `:213-238` genuinely fail the contract, and the positive control at `:240-255` genuinely passes. Every fix above assumes this harness exists; extend it, do not replace it.
- **AD-7's `include_external_packages = true`** is the difference between a contract and a decoration. Any new forbidden contract (e.g. the container library in AD-20, `httpx` in the adapters-only direction) inherits that flag and its own negative control.
- **AD-1's refusal to let Ruff do boundary work** (`:26`) is correct and should survive: none of the ADs above should be implemented as a Ruff rule, except where genuinely stylistic (AD-24).
- **AD-2's direction** (constructor-injected abstractions, no hardcoded adapters) is the right call; only its letter is dangerous (M1).

# Method note (so the next reviewer can reproduce or refute)

Each pair was constructed by (1) taking two stories whose acceptance criteria are individually satisfiable, (2) implementing each in the most idiomatic way for that story alone, (3) checking AD-1…AD-7 line by line against both, and (4) keeping only pairs where **both pass**. Pairs where one side already violated an AD were discarded as ordinary defects, not architectural holes. The five critical items survived because the incompatibility is invisible to every existing gate: no import crosses a forbidden boundary, no type error occurs in the unit test, and each story's own acceptance test is green. That property — compliant, tested, and still wrong together — is the definition of a spine hole.
