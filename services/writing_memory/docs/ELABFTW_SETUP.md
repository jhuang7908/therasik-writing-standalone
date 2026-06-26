# Module 3 — eLabFTW + protocols.io

## protocols.io (public protocol search)

1. Register at [protocols.io/developers](https://www.protocols.io/developers) and create a **client access token**.
2. On VPS `.env`:

```bash
PROTOCOLSIO_ACCESS_TOKEN=<client token>
```

3. Restart `writing-memory`.
4. In **write.insynbio.com** → Plan → **Methods Template Library** → protocols.io search, or Facts → **protocols.io**.

| Endpoint | Purpose |
|----------|---------|
| `POST /protocolsio/search` | Keyword search on public protocols |
| `POST /protocolsio/import_to_facts` | Search + optional step fetch → Facts block |
| `POST /protocolsio/workspace/list` | Public SOPs in workspace (default `insynbio`) |
| `POST /protocolsio/workspace/import_to_facts` | Workspace SOP list → Facts block |

Env: `PROTOCOLSIO_WORKSPACE_URI=insynbio` (optional, default `insynbio`).

Rollout order: `docs/MODULE3_PROTOCOLSIO_SOP_CHECKLIST.md`

`GET /lab/config` also returns `protocolsio.configured` and `workspace_uri`.

---

# eLabFTW setup

## Quick path on VPS `157.180.91.72`

```powershell
# From Antibody_Engineer_Suite repo root
powershell -File services/writing_memory/deploy/install-elabftw-on-vps.ps1
```

1. Point **DNS** `lab.insynbio.com` → VPS IP.
2. TLS: `sudo certbot --nginx -d lab.insynbio.com` (on VPS).
3. Open `https://lab.insynbio.com`, finish eLabFTW install, create team.
4. **Settings → API** → generate key.
5. On VPS, edit `/srv/services/writing_memory/.env`:

```bash
ELABFTW_BASE_URL=https://lab.insynbio.com
ELABFTW_PUBLIC_URL=https://lab.insynbio.com
ELABFTW_API_TOKEN=<paste key>
```

6. `sudo systemctl restart writing-memory`
7. In **write.insynbio.com** → Facts Summary → **From eLabFTW**

## Multi-tenant Lab routing

Default mode is still one server-side `ELABFTW_API_TOKEN` for the internal demo Lab. For customer use, do not share the internal token. Create one eLabFTW Team per customer, create a service account/API key for that Team, and route write requests by `project_id` or `customer_id`.

1. Copy the example mapping to a server-only path:

```bash
cp /srv/services/writing_memory/deploy/elabftw_tenants.example.json /srv/services/writing_memory/lab_tenants.json
chmod 600 /srv/services/writing_memory/lab_tenants.json
```

2. Add the mapping path and customer token env vars to `/srv/services/writing_memory/.env`:

```bash
ELABFTW_TENANTS_FILE=/srv/services/writing_memory/lab_tenants.json
ELABFTW_TOKEN_CUSTOMER_A=<customer-a-team-service-api-key>
```

3. Edit `lab_tenants.json` so each customer entry contains:

- `tenant_id` — display/audit identifier, e.g. `customer-a`
- `customer_id` — customer account identifier
- `project_ids` — project IDs that should route to this Lab tenant
- `base_url` / `public_url` — usually `https://lab.insynbio.com` for shared-instance Team mode
- `api_token_env` — env var holding that customer's service API key

4. Restart `writing-memory`.

The UI sends the current `project_id` to `/lab/config` and `/lab/import_reagents`; the server chooses the matching tenant and never exposes API tokens to the browser.

## Writing API

| Endpoint | Purpose |
|----------|---------|
| `GET /lab/config?project_id=...` | Whether the matching Lab tenant is configured |
| `POST /lab/status` | Ping eLabFTW API for optional `project_id` / `customer_id` |
| `POST /lab/import_reagents` | Pull `items` rows into Facts block for the matching Lab tenant |

## AGPL-3.0

eLabFTW is AGPL. Review obligations if offering multi-tenant hosted lab to third parties.
