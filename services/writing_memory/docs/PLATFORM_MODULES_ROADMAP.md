# InSynBio Platform — Six Modules Roadmap



**Status:** Active development · **Owner policy:** Reuse open-source systems of record; do not rebuild ELN/LIMS or reference managers.



**Rollout order (owner, 2026-06):** **③ Lab** → **④ Literature** → **⑤ Patent & IP** → **⑥ Research Administration** (last)

**Module 6:** Research Administration — grant, budget, team progress, literature digests, members (see `MODULE6_RESEARCH_ADMINISTRATION.md`).

**Note:** eLabFTW + protocols.io are part of Module 3 completion, not Module 6.



## Server layout (one VPS + GitHub Pages)



| Host | Where it runs | Files / service |

|------|----------------|-----------------|

| **www.insynbio.com** | **GitHub Pages** (`jhuang7908/insynbio-website`, branch `master`) | `insynbio-web-source/` → `deploy_insynbio.ps1` |

| **console.insynbio.com** | VPS `157.180.91.72` | nginx → `127.0.0.1:8000` |

| **write.insynbio.com** | Same VPS | nginx → `127.0.0.1:8100` (`/srv/services/writing_memory`) |

| **lab.insynbio.com** | Same VPS (Module 3) | eLabFTW Docker — `deploy/install-elabftw-on-vps.ps1` |



## Portal



| Entry | URL | Status |

|-------|-----|--------|

| Hub | `https://insynbio.com/platform.html` | Live (6 modules, auto status sync) |

| Hub mirror | `https://write.insynbio.com/platform` | Live |

| Module 3 Lab | `https://lab.insynbio.com` | Deploy script ready |

| Module 4 Literature | OpenAlex via API | Backend MVP |



## Shared Project Data Hub



Schema: `schemas/project_asset_hub_v1.json` — `project_id` links assets across modules.



## Open-source stack



| Module | Tool | Integration |

|--------|------|-------------|

| 3 Lab · SOP | [protocols.io](https://www.protocols.io/) | `protocolsio_client.py`, workspace list/import → Facts; SoR = insynbio workspace |

| 3 Lab · ELN | [eLabFTW](https://github.com/elabftw/elabftw) | `elabftw_client.py`, `/lab/*`, Facts **From eLabFTW** |

| 4 Literature | [OpenAlex](https://openalex.org/) | `openalex_client.py`, `POST /library/openalex/search` |

| 2 Writing | Zotero + protocols.io search | `/library/*`, `/protocolsio/*` (public search + workspace sync into Facts) |

| 4 Research Administration | RePORTER / SBIR / team RBAC | **Last** — after M3, M5, M6 |



Setup: `docs/ELABFTW_SETUP.md`, `deploy/elabftw.env.example`



## Implementation phases



### Phase 0 — Done



- [x] Portal + Grant templates + Document class + SOP article type + hub schema

- [x] Article JSON: `documentClass`, `grantFunder`, `articleType`, `hubProjectId`



### Phase 1 — protocols.io SOP + eLabFTW

**protocols.io (Module 3 SOP)**

- [x] `protocolsio_client.py` — public search + workspace list/import

- [x] API + write UI (public search + **Module 3 — Lab SOP**)

- [x] VPS: `PROTOCOLSIO_ACCESS_TOKEN` + `PROTOCOLSIO_WORKSPACE_URI=insynbio`

- [ ] Team: 1–2 public SOPs in workspace — see `MODULE3_PROTOCOLSIO_SOP_CHECKLIST.md`

**eLabFTW (Module 3 ELN)**

- [x] `elabftw_client.py` + `/lab/import_reagents`

- [x] `install-elabftw-on-vps.ps1`, nginx example, `ELABFTW_SETUP.md`

- [ ] VPS: install, DNS `lab.insynbio.com`, `ELABFTW_*` in `.env`

- [ ] Hub asset sync (`data/hub/{project_id}.json`) — optional



### Phase 2 — Module 3 Lab completion (current focus)



- [ ] Finish Lab IDE: SOP dropdown, HTML reports (i18n, print CSS), reagent hub sync, RO-Crate optional

- [ ] Team: 1–2 public SOPs on protocols.io — `MODULE3_PROTOCOLSIO_SOP_CHECKLIST.md`

- [ ] eLabFTW production: DNS `lab.insynbio.com`, multi-tenant `ELABFTW_*`

- [ ] Hub asset sync (`data/hub/{project_id}.json`)



### Phase 3 — Module 4 Literature (after Module 3 Lab)



- [x] `openalex_client.py` + `POST /library/openalex/search`

- [x] UI: References rail — search + import to Facts (`?entry=literature`)

- [ ] Cron: saved queries → weekly digest per `team_id` / `project_id`

- [ ] Email digest to member email (feeds Module 6 later)



### Phase 4 — Module 5 Patent & sequence IP (after Literature)



- [x] Portal card + hub schema (`patent`, `patent_sequence`)

- [x] `patent_client.py` + `/ip/*` routes + portal link fallback

- [x] UI: References → Patents (`?entry=patents`)

- [x] `USPTO_ODP_API_KEY` + ODP DSL search — see `deploy/USPTO_ODP_API_KEY.md`

- [ ] Sequence homology (WIPO / NCBI Patents BLAST)



### Phase 5 — Module 6 Research Administration (**last**)



- [x] Grant application MVP: document class + NIH R01 / SBIR templates (`schemas/grant_templates/`)

- [x] Portal deep link `?entry=grant&doc=grant` (legacy; UI label = Research Administration)

- [x] Lab HTML progress reports visible to PI (interim in write Plan panel)

- [ ] Rename portal + dedicated admin shell

- [ ] Budget Facts + Questions completeness

- [ ] TeamID / email RBAC + member management

- [ ] Tri-reviewer personas

- [ ] RePORTER / SBIR scan

- [ ] Literature digest inbox integration



## NCBI FTP

Bulk PubMed/GenBank only — not for grants. Use OpenAlex + E-utilities + RePORTER/SBIR APIs. Patent sequences: Module 5 track B.

