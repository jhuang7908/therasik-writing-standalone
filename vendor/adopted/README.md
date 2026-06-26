# Adopted static mirrors (git-tracked)

Upstream static fragments from `nature-skills` and `science-skills` mirrored here for version control.  
Runtime copies also live under `.cursor/skills/insynbio-*/static/` (gitignored).

## nature-skills mirrors (`vendor/nature_skills.lock.json`)

| Local skill | Upstream module | Update |
|-------------|-----------------|--------|
| `insynbio-citation` | `nature-citation` | `python scripts/diff_nature_adopt.py --mirror citation` |
| `insynbio-paper-to-patent` | `nature-paper-to-patent` | `python scripts/diff_nature_adopt.py --mirror paper-to-patent` |
| `insynbio-paper-reader` | `nature-reader` | `python scripts/diff_nature_adopt.py --mirror reader` |
| `insynbio-paper2ppt` | `nature-paper2ppt` | `python scripts/diff_nature_adopt.py --mirror paper2ppt` |
| `insynbio-polishing` | `nature-polishing` | `python scripts/diff_nature_adopt.py --mirror polishing` |

## GDM science-skills mirrors (`vendor/science_skills.lock.json`)

| Local skill / module | Upstream skill | Mirror file |
|----------------------|----------------|-------------|
| `scripts/insynbio_openalex.py` + `insynbio-literature-search` v1.2 | `literature_search_openalex` | `science-skills/openalex/SKILL_mirror.md` |
| `core/figure/afdb_plddt.py` + `insynbio-figure` v1.2 recipe | `alphafold_database_fetch_and_analyze` | `science-skills/afdb/SKILL_mirror.md` |

Each mirror file begins with an HTML comment citing the upstream commit pin.
