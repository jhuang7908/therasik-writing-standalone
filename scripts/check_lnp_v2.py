"""Check LNP targeting registry entries for humanization status and sequence validity."""
import json, sys

with open("config/cart_components_registry.json") as f:
    data = json.load(f)

lnp = [e for e in data.get("elements", []) if e.get("subcategory") == "LNP/mRNA Targeting Ligand"]

valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
print(f"{'ID':<47} {'HU_STATUS':<12} {'CALC':>5} {'STORED':>6}  {'ISSUES'}")
print("-" * 95)
for e in lnp:
    seq = e.get("sequence", "")
    calc_len = len(seq)
    stored_len = e.get("length", "?")
    hstatus = e.get("humanization_status", "UNKNOWN")
    bad = [c for c in seq if c not in valid_aa]
    issues = []
    if bad:
        issues.append(f"BAD_CHARS:{set(bad)}")
    if stored_len != "?" and stored_len != calc_len:
        issues.append(f"LEN_MISMATCH")
    if not seq:
        issues.append("NO_SEQUENCE")
    print(f"{e['id'][:46]:<47} {hstatus:<12} {calc_len:>5} {str(stored_len):>6}  {', '.join(issues) or 'OK'}")

print(f"\nTotal LNP entries: {len(lnp)}")
hu = [e for e in lnp if e.get("humanization_status") == "HUMANIZED"]
mu = [e for e in lnp if e.get("humanization_status") == "MURINE"]
unk = [e for e in lnp if e.get("humanization_status") not in ("HUMANIZED", "MURINE")]
print(f"  HUMANIZED: {len(hu)}")
print(f"  MURINE:    {len(mu)}")
print(f"  UNKNOWN:   {len(unk)} -> {[e['id'] for e in unk]}")
