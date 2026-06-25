import pathlib

pdb_path = pathlib.Path("projects/fgf 23/vam_boltz_scan/FGF23/FGF23_relaxed.pdb")
lines = pdb_path.read_text().splitlines(keepends=True)

heavy = [
    line for line in lines
    if not (line.startswith(("ATOM", "HETATM")) and
            len(line) > 13 and line[12:16].strip().startswith("H"))
]

pdb_path.write_text("".join(heavy))
print(f"Original lines: {len(lines)}, After H-strip: {len(heavy)}, Removed: {len(lines)-len(heavy)}")

# Verify chains still correct
chains = sorted(set(line[21] for line in heavy if line.startswith("ATOM") and len(line) > 21))
print(f"Chains: {chains}")
print("First ATOM:")
for line in heavy[:2]:
    if line.startswith("ATOM"):
        print(" ", line.rstrip())
