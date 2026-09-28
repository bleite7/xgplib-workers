# Epic 1 Context: Project Foundation & Data Model

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Establish the runnable hexagonal worker base that every later capability depends on: clear layer boundaries, validated configuration, dependency injection, and the PostgreSQL data model. This epic delivers a stable, testable foundation where architecture invariants are enforced mechanically and persistence contracts exist before ingestion, enrichment, or state management are built — so subsequent epics can add behavior without architectural drift or schema rework.

## Stories

- Story 1.1: Establish Project Skeleton & Hexagonal Boundaries
- Story 1.2: Configuration & Dependency Injection Container
- Story 1.3: Game Domain Model, Persistence Port & Database Schema

## Requirements & Constraints

- Enforce Hexagonal Architecture and Clean Code so external APIs and the database stay decoupled from core synchronization logic.
- Layer boundaries follow folder convention (`src/domain`, `src/application`, `src/infrastructure`); domain and application code must not import infrastructure. Enforce this via Ruff (styling and import linting) rather than heavyweight architecture tests.
- Configuration (PostgreSQL connection, IGDB and Microsoft credentials, cron interval) is validated at startup and fails fast on invalid or missing values.
- Dependencies are supplied as abstractions; no hardcoded concrete infrastructure inside use cases.
- Domain and application layers signal errors via explicit custom domain exceptions; translation into infrastructure concerns (logging, queue NACKs, HTTP codes) happens only at the outermost adaptation layer.
- The metadata schema must remain flexible enough to evolve without rigid migrations; PostgreSQL JSON/JSONB is the chosen mechanism.
- Persistence is exposed through a port, not a concrete driver, so adapters remain swappable and testable.
- TDD is required: write tests first, with high coverage expected for matching and state-management logic. Prefer automated linting and formatting over manual checks.

## Technical Decisions

- Hexagonal Architecture (Ports and Adapters) with the dependency rule pointing inward toward the domain; the domain knows nothing of the application layer, and the application layer knows nothing of infrastructure.
- Ports are defined with Python's native `abc.ABC`, giving fail-fast instantiation when an adapter omits a required method.
- Dependency injection is orchestrated through a DI container framework (not manual wiring), standardizing how components receive abstractions as the project scales.
- Use cases orchestrate state mutation imperatively: retrieve entities through ports, invoke domain logic on the entity, then explicitly call the port to persist the new state.
- Foundational stack: SQLAlchemy for ORM and persistence, Pydantic for DTOs and configuration validation, Ruff for unified linting and formatting.
- Data model: a Game domain entity, an `abc.ABC` repository port, and migrations that create a games table with a JSON/JSONB metadata column.
- Domain exceptions (a general domain error plus specific ones such as entity-not-found) live in the domain/application layers; adapters translate them outward.

## Cross-Story Dependencies

- Story 1.1 provides the project skeleton and boundary enforcement that Stories 1.2 and 1.3 build on.
- Story 1.2 supplies the validated configuration and DI wiring used by Story 1.3's persistence setup.
- Story 1.3's Game entity, repository port, and schema are the contracts later epics consume: catalog ingestion reads the previously known catalog, enrichment persists raw data on match failure, and state management upserts and soft-deletes games.
