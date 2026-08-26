---
title: xgplib-workers (Game Pass Catalog Sync)
status: final
created: 2026-08-25
updated: 2026-08-25
---

# xgplib-workers PRD

## 1. Objective and Scope

### 1.1 Product Vision
Power a modern, intelligent, and user-friendly digital catalog for Xbox Game Pass by providing a robust, automated back-end data engine. This project (`xgplib-workers`) acts as the synchronization layer, extracting raw availability data from Microsoft and enriching it with high-quality metadata from IGDB, ultimately replacing the poor experience of the official UI. It serves end users indirectly by feeding data to front-end and back-end applications.

### 1.2 Scope
This PRD covers only the **Worker/Synchronization component** (headless data pipeline). It does not include the front-end application or the user-facing back-end APIs that will consume this data.

**In Scope:**
- Scheduled ingestion of Xbox Game Pass catalog data via Microsoft APIs.
- Data enrichment and mapping via IGDB public API.
- Error handling, resilience (circuit breakers and retries), and logging for unmatched titles.
- Database storage and state management (active vs. inactive games).

**Out of Scope:**
- Complex fuzzy-matching algorithms (V1 relies on exact match and manual intervention).

## 2. Core Capabilities & Functional Requirements (FR)

### FR-1: Microsoft Catalog Ingestion
- **FR-1.1:** Fetch available titles based on region, platform (PC, console, cloud), and subscription plan (Core, Standard, Ultimate).
- **FR-1.2:** Execute on a scheduled basis (Cron). Execution frequency is set to **every hour** to capture dynamic catalog changes.
- **FR-1.3:** Identify titles that have been removed from the catalog since the last sync.

### FR-2: Data Enrichment (IGDB Matching)
- **FR-2.1:** Query the IGDB API using the exact title string provided by Microsoft.
- **FR-2.2:** Retrieve core metadata: title, cover photo, screenshots, short description, full description, genres, and age rating.
- **FR-2.3:** IGDB is designated as the absolute source of truth for all metadata. Microsoft data is only used for availability flags.
- **FR-2.4:** If an exact name match fails between Microsoft and IGDB, the worker must skip the enrichment for that title, store the raw Microsoft data, and log the failure as an exception for manual review.

### FR-3: Data Storage & State Management
- **FR-3.1:** Use JSON/JSONB fields in PostgreSQL to allow flexible schema evolution for metadata.
- **FR-3.2:** Perform "upserts" (update or insert) for newly found or updated games.
- **FR-3.3:** Implement "soft deletes": Titles removed from the Microsoft catalog must be flagged as "inactive" rather than physically deleted, preserving historical data.

## 3. Non-Functional Requirements & Resilience (NFR)

- **NFR-1 (Resilience):** Implement retry mechanisms and circuit breaker patterns for all external API calls (Microsoft and IGDB). If an API outage occurs, the worker must gracefully pause or skip without crashing the entire batch process.
- **NFR-2 (Architecture):** Must strictly adhere to hexagonal architecture and clean code principles, ensuring external APIs and database implementations are decoupled from the core synchronization logic.
- **NFR-3 (Testing):** Use test-driven development (TDD). High coverage is required for matching logic and state management.

## 4. Open Questions & Assumptions

- **[OPEN QUESTION]** Microsoft API endpoints for catalog extraction (region, platform, plan) need to be officially identified and documented during the initial technical spike. We know public/undocumented APIs exist, but exact integration points must be validated.
- **[ASSUMPTION]** For manual resolution of failed matches (FR-2.4), we assume a simple SQL script will be used directly on the database initially, rather than building a full admin UI.
