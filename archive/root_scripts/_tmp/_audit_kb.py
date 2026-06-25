import sys
sys.path.insert(0, '.')

from core.vaccine_design.knowledge.taa_database import TAA_DATABASE
from core.vaccine_design.knowledge.adjuvants import ADJUVANT_DATABASE
from core.vaccine_design.knowledge.vaccine_vectors import VACCINE_VECTORS
from core.vaccine_design.knowledge.infectious_antigens import INFECTIOUS_ANTIGENS
import core.vaccine_design.knowledge.tcr_epitope_db as tcr_mod

# Find TCR list names
tcr_names = [n for n in dir(tcr_mod) if not n.startswith('_') and isinstance(getattr(tcr_mod, n), list)]
print("TCR module list exports:", tcr_names)
for n in tcr_names:
    lst = getattr(tcr_mod, n)
    print(f"  {n}: {len(lst)} entries")
    if lst:
        first = lst[0]
        print(f"    Sample: {first}")

taa_ep = sum(len(t.known_epitopes_mhc1) + len(t.known_epitopes_mhc2) for t in TAA_DATABASE)
inf_ep = sum(len(i.known_epitopes_mhc1) + len(i.known_epitopes_mhc2) for i in INFECTIOUS_ANTIGENS)

print()
print("=" * 60)
print("REAL DATA COUNTS:")
print(f"  TAA_DATABASE:        {len(TAA_DATABASE)} antigens, {taa_ep} MHC epitope entries")
print(f"  ADJUVANT_DATABASE:   {len(ADJUVANT_DATABASE)} adjuvants")
print(f"  VACCINE_VECTORS:     {len(VACCINE_VECTORS)} vectors/platforms")
print(f"  INFECTIOUS_ANTIGENS: {len(INFECTIOUS_ANTIGENS)} pathogens, {inf_ep} MHC epitope entries")
print()

print("TAA spot-check (first 10):")
for t in TAA_DATABASE[:10]:
    ep1 = [e["peptide"] for e in t.known_epitopes_mhc1[:2]]
    pmids = [e.get("pmid","?") for e in t.known_epitopes_mhc1[:2]]
    print(f"  Rank{t.nci_rank:2d} {t.name:12s} | epitopes={ep1} | PMIDs={pmids}")

print()
print("Adjuvant spot-check:")
for a in ADJUVANT_DATABASE[:6]:
    n_approved = len(a.approved_vaccines)
    print(f"  {a.name[:38]:38s} | {a.immune_profile:20s} | approved_in={n_approved} vaccines | {a.regulatory_status[:25]}")

print()
print("Vaccine vectors spot-check:")
for v in VACCINE_VECTORS[:5]:
    print(f"  {v.name[:35]:35s} | {v.platform_type}")

print()
print("Infectious antigen spot-check:")
for i in INFECTIOUS_ANTIGENS[:6]:
    ep = [e["peptide"] for e in i.known_epitopes_mhc1[:2]]
    pmids = [e.get("pmid", "?") for e in i.known_epitopes_mhc1[:2]]
    print(f"  {i.pathogen:20s} | {i.antigen_name[:22]:22s} | ep={ep} pmids={pmids}")
