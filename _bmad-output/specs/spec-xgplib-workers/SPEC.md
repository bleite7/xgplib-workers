---
companions: []
sources:
  - ../../planning-artifacts/prds/prd-xgplib-workers-2026-08-25/prd.md
  - ../../planning-artifacts/architecture/architecture-xgplib-workers-2026-08-26/ARCHITECTURE-SPINE.md
---

# SPEC: xgplib-workers

## Why
Power a modern, intelligent, and user-friendly digital catalog for Xbox Game Pass by providing a robust, automated back-end data engine. This synchronization layer extracts raw availability data from Microsoft and enriches it with high-quality metadata from IGDB.

## Capabilities

- **CAP-1**: Fetch Xbox Game Pass catalog from Microsoft via scheduled cron (hourly) and identify added/removed titles.
  - *Success:* A complete list of currently available and recently removed titles is generated hourly.
- **CAP-2**: Query IGDB API for exact title matches to retrieve core metadata.
  - *Success:* Titles matching IGDB have their metadata enriched (cover, description, etc.).
- **CAP-3**: Handle IGDB match failures by storing raw data and logging for manual review.
  - *Success:* Unmatched titles are persisted without metadata and flagged for intervention.
- **CAP-4**: Persist catalog updates to database using upserts and soft-deletes (inactive flags).
  - *Success:* The database accurately reflects the current Microsoft catalog state and retains history of removed games.

## Constraints

- Use Hexagonal Architecture (Ports and Adapters).
- Use Python's native `abc.ABC` for Ports.
- Use Dependency Injection container framework.
- Use standard stack: SQLAlchemy, Pydantic, Ruff.
- PostgreSQL with JSON/JSONB fields for metadata.
- Use explicit custom Domain Exceptions for error handling.
- Use Test-Driven Development (TDD).
- Must implement circuit breakers and retries for external APIs.

## Non-goals

- Front-end application development.
- User-facing back-end APIs.
- Complex fuzzy-matching algorithms (V1 relies on exact match and manual intervention).

## Assumptions & Open Questions

**Assumptions:**
- Manual resolution of unmatched titles will be done via direct SQL scripts initially.

**Resolved Questions (from research):**
- *What are the exact Microsoft API endpoints?* We will use the community-discovered `catalog.gamepass.com/sigls/v2` endpoints (with specific IDs for Console, PC, and EA Play) to fetch raw game IDs, and then hydrate the metadata using `displaycatalog.mp.microsoft.com/v7.0/products` in batches of 200.
