import sys; sys.path.insert(0, '.')
from core.vaccine_design.knowledge.autoimmune_targets import AUTOIMMUNE_TARGETS
from core.vaccine_design.knowledge.vaccine_vectors import VACCINE_VECTORS

print("=== Autoimmune Targets ===")
print(f"Count: {len(AUTOIMMUNE_TARGETS)}")
v0 = AUTOIMMUNE_TARGETS[0] if AUTOIMMUNE_TARGETS else None
if v0:
    print("Fields:", [f for f in dir(v0) if not f.startswith("_")])
    for a in AUTOIMMUNE_TARGETS[:5]:
        name = getattr(a, 'name', getattr(a, 'antigen', str(a)[:60]))
        print(f"  {name}")

print()
print("=== Vaccine Vectors ===")
print(f"Count: {len(VACCINE_VECTORS)}")
if VACCINE_VECTORS:
    v0 = VACCINE_VECTORS[0]
    print("Fields:", [f for f in dir(v0) if not f.startswith("_")])
    for v in VACCINE_VECTORS:
        name = getattr(v, 'name', str(v)[:60])
        ptype = getattr(v, 'vector_type', getattr(v, 'category', getattr(v, 'type', '?')))
        print(f"  {name}: {ptype}")
