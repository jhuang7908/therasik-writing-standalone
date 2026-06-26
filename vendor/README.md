# Vendor references (read-only upstream)

Third-party skill trees cloned for **diff / adopt** — do not edit files here.

| Path | Upstream | Update |
|------|----------|--------|
| `nature-skills/` | https://github.com/Yuan1z0825/nature-skills | `python scripts/diff_nature_adopt.py --update-vendor` |

After update, run:

```powershell
python scripts/diff_nature_adopt.py --mirror citation paper-to-patent
python scripts/diff_nature_adopt.py --report vendor/nature_skills_diff_report.json --markdown vendor/NATURE_ADOPT_DIFF.md
```

Tracked artifacts (committed):

| File | Purpose |
|------|---------|
| `vendor/nature_skills.lock.json` | Upstream commit pin |
| `vendor/NATURE_ADOPT_DIFF.md` | Gap report |
| `vendor/NATURE_ADOPT_MATRIX.md` | Adopt matrix SSOT |
| `vendor/adopted/` | Mirrored static fragments |

See `.cursor/skills/_shared/core/nature-skills-learn-protocol.md`.
