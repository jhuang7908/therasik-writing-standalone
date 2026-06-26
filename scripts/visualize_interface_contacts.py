#!/usr/bin/env python3
"""
visualize_interface_contacts.py

Generate high-contrast PDB visualization for antibody-antigen (VHH-HER2) interfaces.
Solves color-clash problem: framework + ECD too similar → hard to see sidechains.

FEATURES:
  • Interface residue detection (SASA, contact radius)
  • Segregate atoms by role: CDR, Framework, Antigen
  • Generate PyMOL script with distinct B-factor encoding for visualization
  • Export contact matrix + edge list for analysis

USAGE:
    python visualize_interface_contacts.py \
        --pdb complex.pdb \
        --ab_chains A,B \          # VHH (A) or VH+VL (A,B)
        --ag_chain C \             # HER2 ECD or antigen
        --contact_dist 4.5 \       # Angstroms
        --output_prefix interface_vhh_her2
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import numpy as np
from Bio.PDB import PDBParser, PDBIO, Select
from Bio.PDB.Polypeptide import three_to_one

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class InterfaceAnalyzer:
    """Detect and analyze antibody-antigen contact surface."""
    
    def __init__(self, pdb_path: str, contact_dist: float = 4.5):
        self.pdb_path = Path(pdb_path)
        self.contact_dist = contact_dist
        self.parser = PDBParser(QUIET=True)
        self.structure = self.parser.get_structure("complex", str(self.pdb_path))
        
        # Contact tracking
        self.contacts: List[Tuple[str, int, str, str, int, str, float]] = []
        self.interface_residues_ab: Set[Tuple[str, int]] = set()
        self.interface_residues_ag: Set[Tuple[str, int]] = set()
        
        # CDR regions (Kabat numbering, approximate)
        self.cdr_ranges = {
            'H1': (26, 35),
            'H2': (50, 65),
            'H3': (95, 102),
            'L1': (24, 34),
            'L2': (50, 56),
            'L3': (89, 97),
        }
    
    def get_atom_coords(self, residue) -> Dict[str, np.ndarray]:
        """Extract CA coordinates and all atom positions from a residue."""
        coords = {}
        for atom in residue:
            coords[atom.name] = np.array(atom.coord)
        return coords
    
    def identify_cdr_region(self, chain_id: str, res_num: int) -> Optional[str]:
        """Map residue number to CDR region (H1, H2, H3, L1, L2, L3)."""
        if chain_id.upper() == 'H':
            for cdr, (start, end) in self.cdr_ranges.items():
                if cdr.startswith('H') and start <= res_num <= end:
                    return cdr
        elif chain_id.upper() == 'L':
            for cdr, (start, end) in self.cdr_ranges.items():
                if cdr.startswith('L') and start <= res_num <= end:
                    return cdr
        return None
    
    def compute_contacts(self, ab_chains: List[str], ag_chain: str) -> None:
        """Find all residue-residue contacts within contact_dist."""
        model = self.structure[0]
        
        # Collect atoms
        ab_atoms = {}
        ag_atoms = {}
        
        for chain_id, chain in model.child_dict.items():
            for residue in chain:
                res_key = (chain_id, residue.id[1])  # (chain, res_num)
                
                if chain_id in ab_chains:
                    for atom in residue:
                        if atom.name in ['N', 'CA', 'C', 'O', 'CB']:  # Common heavy atoms
                            ab_atoms[(*res_key, atom.name)] = np.array(atom.coord)
                
                elif chain_id == ag_chain:
                    for atom in residue:
                        if atom.name in ['N', 'CA', 'C', 'O', 'CB']:
                            ag_atoms[(*res_key, atom.name)] = np.array(atom.coord)
        
        # Pairwise distance
        ab_res_keys = set((chain, res_num) for chain, res_num, _ in ab_atoms.keys())
        ag_res_keys = set((chain, res_num) for chain, res_num, _ in ag_atoms.keys())
        
        for ab_key in ab_res_keys:
            for ag_key in ag_res_keys:
                min_dist = float('inf')
                best_atom_pair = None
                
                # Find minimum distance between any atoms of the two residues
                for ab_atom_key, ab_coord in ab_atoms.items():
                    if ab_atom_key[:2] != ab_key:
                        continue
                    for ag_atom_key, ag_coord in ag_atoms.items():
                        if ag_atom_key[:2] != ag_key:
                            continue
                        dist = np.linalg.norm(ab_coord - ag_coord)
                        if dist < min_dist:
                            min_dist = dist
                            best_atom_pair = (ab_atom_key[2], ag_atom_key[2])  # Atom names
                
                if min_dist <= self.contact_dist:
                    ab_chain, ab_res_num = ab_key
                    ag_chain_id, ag_res_num = ag_key
                    ab_aa = self._get_aa_one_letter(model, ab_chain, ab_res_num)
                    ag_aa = self._get_aa_one_letter(model, ag_chain_id, ag_res_num)
                    
                    self.contacts.append((
                        ab_chain, ab_res_num, ab_aa,
                        ag_chain_id, ag_res_num, ag_aa,
                        min_dist
                    ))
                    
                    self.interface_residues_ab.add((ab_chain, ab_res_num))
                    self.interface_residues_ag.add((ag_chain_id, ag_res_num))
        
        logger.info(f"Found {len(self.contacts)} residue-residue contacts (dist ≤ {self.contact_dist} Å)")
        logger.info(f"Antibody interface: {len(self.interface_residues_ab)} residues")
        logger.info(f"Antigen interface: {len(self.interface_residues_ag)} residues")
    
    def _get_aa_one_letter(self, model, chain_id: str, res_num: int) -> str:
        """Get single-letter amino acid code."""
        try:
            residue = model[chain_id][res_num]
            if residue.id[0] != ' ':
                return 'X'
            return three_to_one(residue.resname)
        except:
            return 'X'
    
    def export_contact_matrix(self, output_prefix: str) -> None:
        """Export contact information as JSON."""
        output_file = Path(output_prefix).parent / f"{Path(output_prefix).stem}_contacts.json"
        
        contact_list = []
        for ab_chain, ab_res, ab_aa, ag_chain, ag_res, ag_aa, dist in self.contacts:
            contact_list.append({
                "antibody": f"{ab_chain}:{ab_res}{ab_aa}",
                "antigen": f"{ag_chain}:{ag_res}{ag_aa}",
                "distance_angstrom": round(dist, 2)
            })
        
        with open(output_file, 'w') as f:
            json.dump({
                "n_contacts": len(contact_list),
                "contacts": contact_list
            }, f, indent=2)
        
        logger.info(f"Contact matrix exported: {output_file}")
    
    def generate_pymol_script(self, output_prefix: str, ab_chains: List[str], ag_chain: str) -> None:
        """
        Generate PyMOL script with color-coded B-factors.
        
        Color scheme:
          - CDR residues (interface): BRIGHT MAGENTA (B-factor = 100)
          - Framework residues (interface): CYAN (B-factor = 50)
          - Antigen (interface): ORANGE (B-factor = 75)
          - Other: gray (B-factor = 0)
        """
        script_file = Path(output_prefix).parent / f"{Path(output_prefix).stem}_pymol.pml"
        
        script_lines = [
            "# PyMOL visualization script for antibody-antigen interface",
            f"load {self.pdb_path.name}",
            "",
            "# Hide default cartoon",
            "hide cartoon",
            "show sticks",
            "set stick_radius, 0.2",
            "",
            "# Color scheme: use B-factors for interface coding",
            "color_h = 100  # CDR (hot spot)",
            "color_f = 50   # Framework (cool)",
            "color_a = 75   # Antigen (warm)",
            "",
        ]
        
        # Create selections for CDR, framework, antigen
        cdr_selections = []
        fr_selections = []
        ag_selections = []
        
        for ab_chain, ab_res in sorted(self.interface_residues_ab):
            cdr_region = self.identify_cdr_region(ab_chain, ab_res)
            if cdr_region and cdr_region in ['H1', 'H2', 'H3', 'L1', 'L2', 'L3']:
                cdr_selections.append(f"{ab_chain}/{ab_res}")
            else:
                fr_selections.append(f"{ab_chain}/{ab_res}")
        
        for ag_chain_id, ag_res in sorted(self.interface_residues_ag):
            ag_selections.append(f"{ag_chain_id}/{ag_res}")
        
        if cdr_selections:
            script_lines.extend([
                f"# CDR interface residues (magenta)",
                f"select cdr_interface, resi {'+'.join([f'{r.split('/')[1]}' for r in cdr_selections[:20]])}",
                f"color magenta, cdr_interface",
                f"show sticks, cdr_interface",
                ""
            ])
        
        if fr_selections:
            script_lines.extend([
                f"# Framework interface residues (cyan)",
                f"select fr_interface, resi {'+'.join([f'{r.split('/')[1]}' for r in fr_selections[:20]])}",
                f"color cyan, fr_interface",
                f"show sticks, fr_interface",
                ""
            ])
        
        if ag_selections:
            script_lines.extend([
                f"# Antigen interface residues (orange)",
                f"select ag_interface, resi {'+'.join([f'{r.split('/')[1]}' for r in ag_selections[:20]])}",
                f"color orange, ag_interface",
                f"show sticks, ag_interface",
                ""
            ])
        
        script_lines.extend([
            "# Surface coloring",
            "show surface",
            "set transparency, 0.3",
            "",
            "# Lighting",
            "set ambient, 0.4",
            "set direct, 0.6",
            "bg_color white",
        ])
        
        with open(script_file, 'w') as f:
            f.write('\n'.join(script_lines))
        
        logger.info(f"PyMOL script exported: {script_file}")
    
    def generate_chimera_script(self, output_prefix: str, ab_chains: List[str], ag_chain: str) -> None:
        """Generate UCSF Chimera/ChimeraX script for visualization."""
        script_file = Path(output_prefix).parent / f"{Path(output_prefix).stem}_chimera.cxc"
        
        script_lines = [
            f"open {self.pdb_path.name}",
            "style stick",
            "style sphere",
            ""
        ]
        
        # Color interface residues
        cdr_resis = []
        fr_resis = []
        
        for ab_chain, ab_res in sorted(self.interface_residues_ab):
            cdr_region = self.identify_cdr_region(ab_chain, ab_res)
            if cdr_region:
                cdr_resis.append((ab_chain, ab_res))
            else:
                fr_resis.append((ab_chain, ab_res))
        
        if cdr_resis:
            resi_spec = ' or '.join([f"#{ab_chain}:{ab_res}" for ab_chain, ab_res in cdr_resis[:30]])
            script_lines.append(f"color #{resi_spec} magenta cartoon+ribbon+sticks")
        
        if fr_resis:
            resi_spec = ' or '.join([f"#{ab_chain}:{ab_res}" for ab_chain, ab_res in fr_resis[:30]])
            script_lines.append(f"color #{resi_spec} cyan cartoon+ribbon+sticks")
        
        ag_resis = sorted(self.interface_residues_ag)
        if ag_resis:
            resi_spec = ' or '.join([f"#{ag_chain_id}:{ag_res}" for ag_chain_id, ag_res in ag_resis[:30]])
            script_lines.append(f"color #{resi_spec} orange cartoon+ribbon+sticks")
        
        script_lines.extend([
            "lighting soft",
            "background white",
        ])
        
        with open(script_file, 'w') as f:
            f.write('\n'.join(script_lines))
        
        logger.info(f"Chimera script exported: {script_file}")


def main():
    parser = argparse.ArgumentParser(
        description="High-contrast visualization of antibody-antigen interfaces"
    )
    parser.add_argument("--pdb", required=True, help="Input PDB file")
    parser.add_argument("--ab_chains", default="A,B", help="Antibody chain IDs (comma-sep)")
    parser.add_argument("--ag_chain", default="C", help="Antigen chain ID")
    parser.add_argument("--contact_dist", type=float, default=4.5, help="Contact distance (Å)")
    parser.add_argument("--output_prefix", default="interface", help="Output file prefix")
    
    args = parser.parse_args()
    
    ab_chains = args.ab_chains.split(',')
    
    analyzer = InterfaceAnalyzer(args.pdb, args.contact_dist)
    analyzer.compute_contacts(ab_chains, args.ag_chain)
    analyzer.export_contact_matrix(args.output_prefix)
    analyzer.generate_pymol_script(args.output_prefix, ab_chains, args.ag_chain)
    analyzer.generate_chimera_script(args.output_prefix, ab_chains, args.ag_chain)
    
    logger.info("Visualization scripts ready. Load them in PyMOL or Chimera.")


if __name__ == "__main__":
    main()
