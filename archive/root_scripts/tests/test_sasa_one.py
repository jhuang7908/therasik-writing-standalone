import freesasa
import sys
print('freesasa available')
s = freesasa.Structure('data/structures/natural/Adalimumab.pdb')
r = freesasa.calc(s)
print('Test SASA total:', round(r.totalArea(), 1), 'A2')
print('nAtoms:', s.nAtoms())
chains = set()
for i in range(s.nAtoms()):
    chains.add(s.chainLabel(i))
print('Chains:', chains)
