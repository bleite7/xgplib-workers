# Technical Research: Xbox Game Pass Endpoints

**Context:** The official Microsoft documentation does not explicitly detail public endpoints for extracting the Xbox Game Pass catalog for bulk synchronization purposes. The community, however, has discovered and widely used a set of undocumented endpoints.

## Discovered Endpoints

Based on the [Game-Pass-API repository by NikkelM](https://github.com/NikkelM/Game-Pass-API) (Accessed Aug 26, 2026), the extraction process involves two steps:

### 1. Fetching Catalog IDs
The `catalog.gamepass.com` endpoint is used to get a list of game IDs for a specific platform.

*   **Console:** `https://catalog.gamepass.com/sigls/v2?id=f6f1f99f-9b49-4ccd-b3bf-4d9767a77f5e&language={language}&market={market}`
*   **PC:** `https://catalog.gamepass.com/sigls/v2?id=fdd9e2a7-0fee-49f6-ad69-4354098401ff&language={language}&market={market}`
*   **EA Play:** `https://catalog.gamepass.com/sigls/v2?id=b8900d09-a491-44cc-916e-32b5acae621b&language={language}&market={market}`

These endpoints return a JSON array of objects, where each object contains an `id` field.

### 2. Fetching Game Metadata
Once the IDs are obtained, they must be batched and sent to the `displaycatalog.mp.microsoft.com` API to get the actual game names and properties.

*   **Batch Metadata Endpoint:** `https://displaycatalog.mp.microsoft.com/v7.0/products?bigIds={batch_of_ids_comma_separated}&market={market}&languages={language}`

*Note on Batching:* The community recommends batching IDs (e.g., chunks of 200) to avoid hitting URL length limits (~8KB) enforced by CDNs and proxies.

## Impact on SPEC
This resolves the open question in the SPEC regarding which API endpoints to use. `xgplib-workers` will implement a two-step extraction process: fetch IDs from `catalog.gamepass.com` and then hydrate them in batches using `displaycatalog.mp.microsoft.com`.