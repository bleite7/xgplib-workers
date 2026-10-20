---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-xgplib-workers-2026-08-25/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-xgplib-workers-2026-08-26/ARCHITECTURE-SPINE.md
  - _bmad-output/specs/spec-xgplib-workers/SPEC.md
  - _bmad-output/planning-artifacts/research/technical-xbox-game-pass-endpoints-2026-08-26/research.md
---

# xgplib-workers - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for xgplib-workers, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1: Microsoft Catalog Ingestion
- FR-1.1: Fetch available Game Pass titles based on region, platform (PC, console, cloud), and subscription plan (Core, Standard, Ultimate).
- FR-1.2: Execute ingestion on a scheduled basis (cron) every hour.
- FR-1.3: Identify titles removed from the catalog since the last sync.

FR-2: Data Enrichment (IGDB Matching)
- FR-2.1: Query the IGDB API using the exact title string provided by Microsoft.
- FR-2.2: Retrieve core metadata (title, cover photo, screenshots, short description, full description, genres, age rating).
- FR-2.3: Treat IGDB as the absolute source of truth for metadata; use Microsoft data only for availability flags.
- FR-2.4: On exact-name match failure, skip enrichment, persist raw Microsoft data, and log the failure as an exception for manual review.

FR-3: Data Storage & State Management
- FR-3.1: Use JSON/JSONB columns in PostgreSQL for flexible metadata schema.
- FR-3.2: Perform upserts for newly found or updated games.
- FR-3.3: Soft-delete titles removed from the catalog by flagging them inactive (preserving history).

### NonFunctional Requirements

- NFR-1 (Resilience): Implement retries and circuit breakers for all external API calls (Microsoft and IGDB); on outage, pause/skip gracefully without crashing the batch.
- NFR-2 (Architecture): Adhere to Hexagonal Architecture and Clean Code, keeping external APIs and DB decoupled from core sync logic.
- NFR-3 (Testing): Use TDD; high coverage required for matching logic and state management.

### Additional Requirements

- Hexagonal boundaries enforced by folder convention (src/domain, src/application, src/infrastructure) plus an import-linter `layers` contract in `pyproject.toml`, proven by negative-control tests in `tests/test_layers.py`. Ruff covers style and formatting only.
- Inner layers stay framework-free: `domain` and `application` import no third-party runtime libraries; guarded by an import-linter `forbidden` contract whose `forbidden_modules` is an enumerated list (with `include_external_packages = true` as a top-level session option) that grows as dependencies land and is closed against `[project].dependencies` (Story 1.2, Story 1.3).
- Dependency Injection orchestrated via `dependency-injector`, declared once in the infrastructure composition root; inner layers take plain constructor parameters.
- The system is synchronous end to end (AD-8): ports and use cases are `def`, persistence uses `Session` on psycopg 3, HTTP adapters are synchronous.
- Ports defined with Python native `abc.ABC`.
- Use cases orchestrate state mutation imperatively (retrieve entity → invoke domain logic → call port `save`).
- Custom Domain Exceptions raised in domain/application; adapters/entrypoints translate them to infra responses.
- Foundational stack: SQLAlchemy (ORM), Pydantic (DTOs/config), Ruff (lint/format), import-linter (layer contracts).
- Two-step Microsoft extraction: fetch IDs from `catalog.gamepass.com/sigls/v2` (Console/PC/EA Play), then hydrate via `displaycatalog.mp.microsoft.com/v7.0/products` in batches of 200.
- **Open item:** FR-1.1 mentions "cloud" platform and subscription plans (Core/Standard/Ultimate), but the discovered endpoints only cover Console, PC, and EA Play. Cloud/plan filtering has no documented endpoint IDs yet — left open (not a V1 blocking decision).

### UX Design Requirements

None (headless worker; no UI in scope).

### FR Coverage Map

- FR-1.1: Epic 2 - Catalog ingestion by region/platform/plan
- FR-1.2: Epic 2 - Hourly cron scheduling
- FR-1.3: Epic 2 - Detect removed titles
- FR-2.1: Epic 3 - IGDB exact-name query
- FR-2.2: Epic 3 - Core metadata retrieval
- FR-2.3: Epic 3 - IGDB as source of truth
- FR-2.4: Epic 3 - Match-failure fallback (raw + log)
- FR-3.1: Epic 1 - JSON/JSONB data model
- FR-3.2: Epic 4 - Upserts
- FR-3.3: Epic 4 - Soft deletes (inactive flag)

## Epic List

### Epic 1: Project Foundation & Data Model
Establish the runnable hexagonal worker base — folder boundaries (src/domain, src/application, src/infrastructure), DI container, configuration, and the PostgreSQL data model (SQLAlchemy with JSON/JSONB metadata) plus migrations — giving the project a stable, testable foundation.
**FRs covered:** FR-3.1 (NFR-2, NFR-3 setup; all Architecture ADs)

### Epic 2: Microsoft Catalog Ingestion
The worker fetches the current Game Pass catalog from Microsoft hourly, resolves game IDs via two-step extraction (sigls/v2 → displaycatalog in batches of 200), and detects titles added or removed since the last sync.
**FRs covered:** FR-1.1, FR-1.2, FR-1.3 (NFR-1 Microsoft)

### Epic 3: IGDB Metadata Enrichment
Titles are enriched with IGDB metadata via exact-name match; unmatched titles are stored raw and logged for manual review.
**FRs covered:** FR-2.1, FR-2.2, FR-2.3, FR-2.4 (NFR-1 IGDB)

### Epic 4: Catalog State Management
The database accurately reflects current catalog state via upserts for new/updated games and soft-deletes (inactive flag) for removed titles, preserving history.
**FRs covered:** FR-3.2, FR-3.3 (NFR-3 matching/state coverage)

## Epic 1: Project Foundation & Data Model

Establish the runnable hexagonal worker base — folder boundaries (src/domain, src/application, src/infrastructure), DI container, configuration, and the PostgreSQL data model (SQLAlchemy with JSON/JSONB metadata) plus migrations — giving the project a stable, testable foundation.

### Story 1.1: Establish Project Skeleton & Hexagonal Boundaries

As a developer,
I want a configured Python project with hexagonal folder boundaries and linting enforcement,
So that architecture invariants are enforced from day one.

**Acceptance Criteria:**

**Given** a fresh checkout
**When** I install dependencies and run the linter
**Then** src/domain, src/application, src/infrastructure exist and Ruff passes with no errors
**And** import rules prevent domain/application modules from importing infrastructure

### Story 1.2: Configuration & Dependency Injection Container

As a developer,
I want validated configuration (PostgreSQL URL, IGDB/Microsoft credentials, cron interval) and a DI container,
So that use cases receive dependencies as abstractions without hardcoded infrastructure.

**Acceptance Criteria:**

**Given** a config file with required values
**When** the worker starts
**Then** config is validated via Pydantic and invalid config fails fast
**And** the `dependency-injector` container, declared in the infrastructure composition root, resolves ports to their adapter implementations
**And** no module under `src/domain` or `src/application` imports `dependency_injector`
**And** an import-linter `forbidden` contract for `src/domain` and `src/application` forbids an enumerated list of top-level import names, with `include_external_packages = true` set at the top of `[tool.importlinter]`
**And** the forbidden list is closed against `[project].dependencies`: a test fails when a declared runtime dependency has no entry in the list
**And** a negative-control test proves that contract breaks when `domain` imports `pydantic`

### Story 1.3: Game Domain Model, Persistence Port & Database Schema

As a developer,
I want the Game domain entity, an abc.ABC repository port, custom domain exceptions, and a PostgreSQL schema with JSON/JSONB metadata,
So that persistence contracts and flexible metadata schema are in place.

**Acceptance Criteria:**

**Given** the Game entity and repository port defined via abc.ABC
**When** a migration runs
**Then** a games table is created with `product_id` as its primary key and a JSON/JSONB metadata column
**And** domain exceptions (e.g., DomainError, EntityNotFound) are defined and raised by domain/application layers
**And** the `forbidden` contract is extended to cover `sqlalchemy` and the PostgreSQL driver, with a negative-control test for each

## Epic 2: Microsoft Catalog Ingestion

The worker fetches the current Game Pass catalog from Microsoft hourly, resolves game IDs via two-step extraction (sigls/v2 → displaycatalog in batches of 200), and detects titles added or removed since the last sync.

### Story 2.1: Fetch Game Pass Catalog IDs from Microsoft

As a developer,
I want an adapter that fetches catalog IDs from catalog.gamepass.com/sigls/v2 for Console, PC, and EA Play,
So that the worker obtains the raw list of available game IDs per platform.

**Acceptance Criteria:**

**Given** the markets and language configured for the run
**When** the adapter requests catalog IDs
**Then** it returns game IDs for the Console, PC, and EA Play endpoints for each configured market
**And** external call failures trigger retries with backoff and open the circuit breaker after a configured threshold

### Story 2.2: Hydrate Title Metadata from Microsoft

As a developer,
I want an adapter that resolves game IDs to full title metadata via displaycatalog.mp.microsoft.com/v7.0/products in batches of 200,
So that the worker gets names and properties for each catalog entry.

**Acceptance Criteria:**

**Given** a list of game IDs
**When** the adapter hydrates metadata
**Then** IDs are batched in chunks of 200 and each batch returns title names and properties
**And** retry/circuit breaker behavior matches the catalog adapter

### Story 2.3: Detect Added & Removed Titles

As a developer,
I want a use case that compares the freshly fetched catalog against the previously known catalog,
So that added and removed titles are identified each sync.

**Acceptance Criteria:**

**Given** a freshly fetched catalog and the previously known catalog
**When** the change-detection use case runs
**Then** it returns the set of added titles and the set of removed titles
**And** the previously known catalog is read via the repository port (defined in Epic 1); a minimal read-capable adapter is sufficient for this story

### Story 2.4: Scheduled Hourly Execution

As a developer,
I want the ingestion pipeline triggered on an hourly schedule,
So that the catalog stays up to date without manual runs.

**Acceptance Criteria:**

**Given** the worker is running
**When** an hour elapses
**Then** the ingestion pipeline executes automatically

## Epic 3: IGDB Metadata Enrichment

Titles are enriched with IGDB metadata via exact-name match; unmatched titles are stored raw and logged for manual review.

### Story 3.1: Query IGDB by Exact Name

As a developer,
I want an adapter that queries the IGDB API using the exact title name from Microsoft,
So that enrichment can retrieve the matching IGDB entry.

**Acceptance Criteria:**

**Given** a Microsoft title name
**When** the adapter queries IGDB
**Then** it returns the exact-name match (or no match)
**And** failures trigger retries and open the circuit breaker after a configured threshold

### Story 3.2: Enrich Titles with IGDB Metadata

As a developer,
I want a use case that enriches matched titles with IGDB metadata (cover, screenshots, short/full description, genres, age rating),
So that catalog entries carry rich metadata with IGDB as the source of truth.

**Acceptance Criteria:**

**Given** a matched IGDB entry
**When** the enrichment use case runs
**Then** the title is enriched with cover photo, screenshots, short/full description, genres, and age rating
**And** metadata comes exclusively from IGDB; Microsoft data is used only for availability flags

### Story 3.3: Handle IGDB Match Failures

As a developer,
I want unmatched titles stored with raw Microsoft data and logged for manual review,
So that no title is lost even when enrichment fails.

**Acceptance Criteria:**

**Given** a title with no IGDB exact match
**When** enrichment runs
**Then** the title is persisted with raw Microsoft data and no metadata
**And** the failure is logged as an exception for manual review

## Epic 4: Catalog State Management

The database accurately reflects current catalog state via upserts for new/updated games and soft-deletes (inactive flag) for removed titles, preserving history.

### Story 4.1: Persist Catalog via Upserts

As a developer,
I want the repository to upsert catalog entries (insert new, update existing),
So that the database reflects the latest catalog state.

**Acceptance Criteria:**

**Given** a list of catalog entries
**When** persistence runs
**Then** new titles are inserted and existing titles are updated in place, keyed by `product_id` (`ON CONFLICT (product_id) DO UPDATE`)
**And** no duplicate rows are created for existing titles: persisting the same batch twice leaves the row count and the ids unchanged
**And** a game that gains IGDB metadata after a failed match is updated in place, not duplicated

### Story 4.2: Soft-Delete Removed Titles

As a developer,
I want titles removed from the Microsoft catalog flagged as inactive instead of deleted,
So that historical data is preserved.

**Acceptance Criteria:**

**Given** a title no longer in the Microsoft catalog
**When** state management runs
**Then** the title is flagged inactive (not physically deleted)
**And** its metadata/history remains queryable

