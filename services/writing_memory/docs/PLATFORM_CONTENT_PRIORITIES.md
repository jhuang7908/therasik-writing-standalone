# Platform & content priorities (billing deferred)

**Status:** Active · **Billing/credits:** planning only — not in dev scope until EN site is stable.

## Now (P0–P1)

| # | Item | Owner action | Done when |
|---|------|--------------|-----------|
| 1 | protocols.io API | VPS `.env`: `PROTOCOLSIO_ACCESS_TOKEN`, `PROTOCOLSIO_WORKSPACE_URI=insynbio` | `GET /lab/config` → `protocolsio.configured: true` |
| 2 | First SOP content | insynbio workspace: Import or New → review → **Publish (public)** if listed in write | **List SOPs** shows ≥1 row |
| 3 | write M2 | Plan → Methods: public search + **Module 3 Lab SOP** → Sync to Facts | Facts block appended |
| 4 | Portal copy | `insynbio-web-source/platform.html` → `deploy_insynbio.ps1` | www + write `/platform` match |
| 5 | eLabFTW | `install-elabftw-on-vps.ps1`, DNS `lab.insynbio.com`, `ELABFTW_*` | **From eLabFTW** imports items |

## Next (P2) — order: Module 3 → 4 → 5

| # | Item |
|---|------|
| 6 | **Module 3:** Lab HTML reports (i18n), hub reagent sync, RO-Crate optional |
| 7 | **Module 4:** OpenAlex watchlists + email digest |
| 8 | **Module 5:** Patent / sequence IP completion |
| 9 | Hub file `data/hub/{project_id}.json` asset pointers |

## Later (P3) — Module 6 Research Administration **last**

| # | Item |
|---|------|
| 10 | Dedicated admin shell: budget, members, literature inbox |
| 11 | Grant R01/SBIR Facts blocks (extend existing MVP) |

## Later (planning only)

- Credits wallet, Stripe USD (EN site), CNY site, SOP Studio GPT pipeline
- See conversation notes; no implementation gate for P0–P1

## Module split (reference)

- **M2 write:** writing, publication, cite methods → Facts
- **M3 lab:** SOP on protocols.io; reagents/experiments on eLabFTW
- **M4 literature:** OpenAlex + Zotero
- **M6 research admin:** grant, budget, team (last)

Checklist: `MODULE3_PROTOCOLSIO_SOP_CHECKLIST.md`, `ELABFTW_SETUP.md`
