"""Fix openFDA effective_time in Ipilimumab ADA245 row + add DailyMed setid link."""
import csv
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "ada245" / "database" / "ada_master_245_curated.csv"

with urllib.request.urlopen(
    "https://api.fda.gov/drug/label.json?search=openfda.generic_name:%22ipilimumab%22&limit=1",
    timeout=60,
) as resp:
    d = json.loads(resp.read().decode())
r = d["results"][0]
et = r.get("effective_time")
if isinstance(et, list) and et:
    eff = et[0]
else:
    eff = str(et)
of = r.get("openfda", {})
spl = of.get("spl_id", [""])[0]
dailymed = f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={spl}"
api_url = "https://api.fda.gov/drug/label.json?search=openfda.generic_name:%22ipilimumab%22&limit=1"

rows = []
with CSV_PATH.open(encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        if row["antibody_name"] == "Ipilimumab":
            row["citation_urls"] = f"{dailymed} ; {api_url}"
            row["ada_source_url_primary"] = dailymed
            row["ada_evidence_chain_excerpt"] = (
                row["ada_evidence_chain_excerpt"].split(" openFDA spl_id=")[0]
                + f" SPL setid {spl} (DailyMed). openFDA label effective_time {eff}."
            )
        rows.append(row)

with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print("fixed Ipilimumab citations; effective_time=", eff)
