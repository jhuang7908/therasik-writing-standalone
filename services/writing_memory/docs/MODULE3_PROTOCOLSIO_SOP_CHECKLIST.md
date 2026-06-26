# Module 3 — protocols.io SOP rollout (ordered)

**Architecture:** SOP system-of-record = protocols.io workspace; writing consumes via Facts (Module 2).

## Step 1 — Create SOPs on protocols.io (manual, free tier)

1. Open workspace: https://www.protocols.io/workspace/insynbio  
2. **+ New** or **Import a Protocol** (PDF/Word → Protocolify on protocols.io servers).  
3. Publish as **Public** when ready for DOI/citation (Open research).  
4. Private drafts: max 2 on free tier — use public workspace SOPs for shared methods.

## Step 2 — Server token (Module 2/3 API bridge)

On VPS `/srv/services/writing_memory/.env`:

```bash
PROTOCOLSIO_ACCESS_TOKEN=<client access token from developers → Insynbio client>
PROTOCOLSIO_WORKSPACE_URI=insynbio
```

```bash
systemctl restart writing-memory
curl -s https://write.insynbio.com/lab/config
```

Expect: `"protocolsio":{"configured":true,"workspace_uri":"insynbio",...}`

## Step 3 — write.insynbio.com (consume into Facts)

| UI | Path | Purpose |
|----|------|---------|
| **Module 3 — Lab SOP** | Plan → Methods Template Library | List / Sync workspace SOPs → Facts |
| **public protocol search** | Same panel | Global methods search (Module 2 cite) |
| Facts buttons | protocols.io | Quick import |

API:

| Endpoint | Module |
|----------|--------|
| `POST /protocolsio/search` | M2 public search |
| `POST /protocolsio/workspace/list` | M3 workspace catalog |
| `POST /protocolsio/workspace/import_to_facts` | M3 → M2 Facts |

## Step 4 — eLabFTW (parallel, not replacement)

When `lab.insynbio.com` is live: reagents/experiments → **From eLabFTW** in Facts.  
Do not duplicate SOP authoring in eLabFTW; link to protocols.io URL in experiment notes.

## Step 5 — Optional next

- Full single-protocol markdown import (`GET v4/protocols/{id}`)  
- Hub asset file `data/hub/{project_id}.json` with `protocolsio_uri` pointers  
- OAuth only if multi-user private libraries required
