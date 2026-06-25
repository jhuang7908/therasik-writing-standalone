import pathlib

pdb_path = pathlib.Path("projects/fgf 23/vam_boltz_scan/FGF23/FGF23_relaxed.pdb")
chain_map = {"A": "H", "B": "L", "C": "A"}

lines = pdb_path.read_text().splitlines(keepends=True)
fixed = []
for line in lines:
    if line.startswith(("ATOM", "HETATM", "TER", "ANISOU")) and len(line) > 21:
        c = line[21]
        line = line[:21] + chain_map.get(c, c) + line[22:]
    fixed.append(line)

pdb_path.write_text("".join(fixed))
print("Chain rename done. Chains now:")

chains = set()
for line in fixed:
    if line.startswith("ATOM") and len(line) > 21:
        chains.add(line[21])
print(sorted(chains))
print("First 2 ATOM lines:")
for line in fixed[:4]:
    if line.startswith("ATOM"):
        print(line.rstrip())
