# protocols.io — search, fork, and InSynBio integration

## Public search (Module 2)

- API: `GET https://www.protocols.io/api/v3/protocols?filter=public&key=...`
- Docs: https://apidocs.protocols.io/ (Protocols → Get List)
- **Indexing is English-first.** Queries like `cd34小鼠` often return **0** hits; the writing service expands to variants such as `CD34`, `CD34 mouse`, `cd34 mouse`.

### InSynBio endpoints

| Route | Behavior |
|-------|----------|
| `POST /protocolsio/search` | Multi-variant search + relevance ranking + `curated` top 3 |
| `POST /protocolsio/curate_import` | Auto-import curated rows into Facts (no manual selection) |

## Duplicate / fork — no single API

protocols.io does **not** expose `POST /protocols/{id}/fork` or `duplicate` in API v3/v4 docs.

| Concept | In API |
|---------|--------|
| Fork lineage | Response fields `fork_id`, `fork_info`, `number_of_forks` on protocol objects |
| UI “Fork” on website | Browser workflow only (not documented as REST duplicate) |
| Programmatic copy | **Manual pipeline:** `GET /api/v3/protocols/{id}` or v4 steps → `POST /api/v3/workspaces/{workspace_id}/protocols` + recreate steps/materials |

References:

- Create in workspace: `POST https://www.protocols.io/api/v3/workspaces/{workspace_uri}/protocols` (see apidocs **Create a protocol**)
- List workspace protocols: `GET .../workspaces/{workspace_uri}/protocols`
- Steps: `GET https://www.protocols.io/api/v4/protocols/{id}/steps`

**Product decision (current):** No auto-fork API yet. Customer flow:

1. Search public protocols → tick rows.
2. **Selected → Facts** — writing material (`POST /protocolsio/import_selected`).
3. **Selected → Lab queue** — per-project JSON under `data/lab_sop_queue/` (`POST /protocolsio/workspace/queue`); fork manually on protocols.io → publish in `insynbio` → **List published SOPs** / **Sync all SOPs → Facts**.

Optional **Auto-curate → Facts** still available; checkboxes remain the customer’s override.

## Module 3 lab SOP

- Workspace URI: `PROTOCOLSIO_WORKSPACE_URI` (default `insynbio`)
- Only **public** workspace protocols appear in `GET /workspaces/{uri}/protocols`
- Private drafts must be published on protocols.io before list/sync
