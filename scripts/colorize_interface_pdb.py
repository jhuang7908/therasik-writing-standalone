#!/usr/bin/env python3
"""
colorize_interface_pdb.py

Directly modify PDB B-factors to encode interface roles.
This creates a PDB file that displays correctly in any viewer supporting B-factor coloring.

RATIONALE:
  Problem: VHH framework + HER2 ECD have similar default colors → hard to see sidechain contacts
  Solution: Encode interface role in B-factor field using customizable color schemes

FEATURES:
  • 8 predefined color schemes (rainbow, scientific, publication, etc.)
  • Custom JSON-based color configuration
  • Interface role mapping (CDR, Framework, Antigen, Other)
  • PyMOL/Chimera spectrum command generation

USAGE:
    # Default rainbow scheme
    python colorize_interface_pdb.py \
        --pdb complex.pdb \
        --ab_chains A,B \
        --ag_chain C \
        --output interface_colored.pdb
    
    # Specific scheme
    python colorize_interface_pdb.py \
        --pdb complex.pdb \
        --scheme publication \
        --ab_chains A,B \
        --ag_chain C \
        --output interface_colored.pdb
    
    # Custom scheme
    python colorize_interface_pdb.py \
        --pdb complex.pdb \
        --scheme-config my_colors.json \
        --ab_chains A,B \
        --ag_chain C \
        --output interface_colored.pdb
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import numpy as np
from Bio.PDB import PDBParser, PDBIO, Select
from Bio.PDB.Polypeptide import three_to_one

# Import color scheme manager
import sys
sys.path.insert(0, str(Path(__file__).parent))
from color_scheme_manager import SchemeManager, ColorScheme

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class InterfaceColorizer:
    """Assign B-factors based on interface role for color-coded PDB export."""
    
    def __init__(self, pdb_path: str, contact_dist: float = 4.5, 
                 color_scheme: Optional[ColorScheme] = None):
        self.pdb_path = Path(pdb_path)
        self.contact_dist = contact_dist
        self.parser = PDBParser(QUIET=True)
        self.structure = self.parser.get_structure("complex", str(self.pdb_path))
        
        # Color scheme
        self.color_scheme = color_scheme or SchemeManager.get_scheme("rainbow")
        self._setup_bfactor_mapping()
        
        # CDR ranges (Kabat, approximate)
        self.cdr_ranges = {
            'H': [(26, 35), (50, 65), (95, 102)],  # H1, H2, H3
            'L': [(24, 34), (50, 56), (89, 97)],   # L1, L2, L3
        }
        
        # Interface tracking
        self.interface_residues_ab: Set[Tuple[str, int]] = set()
        self.interface_residues_ag: Set[Tuple[str, int]] = set()
    
    def _setup_bfactor_mapping(self):
        """Extract B-factor ranges from color scheme."""
        self.B_CDR = self.color_scheme.roles.get("cdr").bfactor_range[0] if "cdr" in self.color_scheme.roles else 95
        self.B_FR = self.color_scheme.roles.get("framework").bfactor_range[0] if "framework" in self.color_scheme.roles else 55
        self.B_AG = self.color_scheme.roles.get("antigen").bfactor_range[0] if "antigen" in self.color_scheme.roles else 75
        self.B_SURFACE = self.color_scheme.roles.get("other").bfactor_range[0] if "other" in self.color_scheme.roles else 5
    
    def is_cdr(self, chain_id: str, res_num: int) -> bool:
        """Check if residue is in CDR region."""
        chain_type = chain_id[-1].upper() if chain_id[-1].upper() in ['H', 'L'] else None
        if chain_type not in self.cdr_ranges:
            return False
        
        for start, end in self.cdr_ranges[chain_type]:
            if start <= res_num <= end:
                return True
        return False
    
    def compute_interfaces(self, ab_chains: List[str], ag_chain: str) -> None:
        """Identify interface residues."""
        model = self.structure[0]
        
        # Collect all atoms
        ab_atoms = {}
        ag_atoms = {}
        
        for chain_id in ab_chains:
            if chain_id not in model.child_dict:
                logger.warning(f"Chain {chain_id} not found in antibody")
                continue
            chain = model[chain_id]
            for residue in chain:
                res_num = residue.id[1]
                for atom in residue:
                    ab_atoms[(chain_id, res_num, atom.name)] = np.array(atom.coord)
        
        if ag_chain not in model.child_dict:
            logger.warning(f"Chain {ag_chain} (antigen) not found")
            return
        
        chain = model[ag_chain]
        for residue in chain:
            res_num = residue.id[1]
            for atom in residue:
                ag_atoms[(ag_chain, res_num, atom.name)] = np.array(atom.coord)
        
        # Find residue pairs within contact distance
        ab_res_set = set((c, r) for c, r, _ in ab_atoms.keys())
        ag_res_set = set((c, r) for c, r, _ in ag_atoms.keys())
        
        for ab_chain, ab_res in ab_res_set:
            for ag_chain_id, ag_res in ag_res_set:
                # Min distance between any atoms of these residues
                min_dist = float('inf')
                for ab_key, ab_coord in ab_atoms.items():
                    if ab_key[:2] != (ab_chain, ab_res):
                        continue
                    for ag_key, ag_coord in ag_atoms.items():
                        if ag_key[:2] != (ag_chain_id, ag_res):
                            continue
                        dist = np.linalg.norm(ab_coord - ag_coord)
                        min_dist = min(min_dist, dist)
                
                if min_dist <= self.contact_dist:
                    self.interface_residues_ab.add((ab_chain, ab_res))
                    self.interface_residues_ag.add((ag_chain_id, ag_res))
        
        logger.info(f"Antibody interface: {len(self.interface_residues_ab)} residues")
        logger.info(f"Antigen interface: {len(self.interface_residues_ag)} residues")
    
    def assign_bfactors(self, ab_chains: List[str], ag_chain: str) -> None:
        """Assign B-factors based on interface role and CDR status."""
        model = self.structure[0]
        
        for chain_id, chain in model.child_dict.items():
            for residue in chain:
                res_num = residue.id[1]
                
                # Determine B-factor
                if chain_id in ab_chains:
                    if (chain_id, res_num) in self.interface_residues_ab:
                        # Interface residue
                        if self.is_cdr(chain_id, res_num):
                            bfactor = self.B_CDR
                        else:
                            bfactor = self.B_FR
                    else:
                        # Non-interface antibody residue
                        bfactor = self.B_SURFACE
                
                elif chain_id == ag_chain:
                    if (chain_id, res_num) in self.interface_residues_ag:
                        bfactor = self.B_AG
                    else:
                        bfactor = self.B_SURFACE
                
                else:
                    bfactor = self.B_BURIED
                
                # Assign to all atoms in residue
                for atom in residue:
                    atom.bfactor = float(bfactor)
    
    def save_colored_pdb(self, output_path: str) -> None:
        """Export colored PDB."""
        io = PDBIO()
        io.set_structure(self.structure)
        io.save(output_path)
        logger.info(f"Colored PDB saved: {output_path}")
    
    def generate_pymol_coloring_script(self, output_prefix: str) -> None:
        """Generate PyMOL script to color by B-factor."""
        script_file = Path(output_prefix).parent / f"{Path(output_prefix).stem}_color_by_bfactor.pml"
        
        script_lines = [
            "# Color by B-factor encoding",
            f"load {output_prefix}",
            "",
            "# Spectrum: B-factor → color",
            "spectrum b, white cyan blue orange red",
            "show sticks",
            "show surface",
            "set transparency, 0.3",
            "",
            "# Legend",
            "# Red/Magenta (B≈95): CDR interface",
            "# Cyan/Blue (B≈55): Framework interface",
            "# Orange/Yellow (B≈75): Antigen interface",
            "# Gray/White: Non-interface",
        ]
        
        with open(script_file, 'w') as f:
            f.write('\n'.join(script_lines))
        
        logger.info(f"PyMOL coloring script: {script_file}")
    
    def generate_summary_report(self, output_prefix: str) -> None:
        """Generate summary of B-factor assignments."""
        report_file = Path(output_prefix).parent / f"{Path(output_prefix).stem}_coloring_report.txt"
        
        lines = [
            "INTERFACE COLORING REPORT",
            "=" * 60,
            "",
            "B-Factor Encoding:",
            f"  • CDR interface:       B = {self.B_CDR} → RED/MAGENTA",
            f"  • Framework interface: B = {self.B_FR} → CYAN/BLUE",
            f"  • Antigen interface:   B = {self.B_AG} → ORANGE/YELLOW",
            f"  • Non-interface:       B = {self.B_SURFACE} → WHITE/GRAY",
            "",
            f"Antibody interface residues: {len(self.interface_residues_ab)}",
            f"Antigen interface residues:  {len(self.interface_residues_ag)}",
            "",
            "USAGE IN PYMOL:",
            "  1. Open the PDB in PyMOL",
            "  2. Run: spectrum b, white cyan blue orange red",
            "  3. Adjust clipping: set clipping_plane_z, -200",
            "",
            "USAGE IN CHIMERA:",
            "  1. Open the PDB in ChimeraX",
            "  2. Run: color bfactor palette rainbow",
        ]
        
        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Summary report: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Colorize PDB interface by B-factor encoding with customizable color schemes"
    )
    parser.add_argument("--pdb", required=True, help="Input PDB")
    parser.add_argument("--ab_chains", default="A,B", help="Antibody chains")
    parser.add_argument("--ag_chain", default="C", help="Antigen chain")
    parser.add_argument("--contact_dist", type=float, default=4.5, help="Contact distance (Å)")
    parser.add_argument("--output", required=True, help="Output PDB file")
    parser.add_argument("--scheme", default="rainbow", 
                        help=f"Color scheme: {', '.join(SchemeManager.BUILTIN_SCHEMES.keys())}")
    parser.add_argument("--scheme-config", help="Path to custom color scheme JSON")
    
    args = parser.parse_args()
    
    # Load color scheme
    if args.scheme_config:
        try:
            color_scheme = SchemeManager.load_custom_scheme(args.scheme_config)
            logger.info(f"Loaded custom scheme from {args.scheme_config}")
        except Exception as e:
            logger.error(f"Failed to load custom scheme: {e}")
            sys.exit(1)
    else:
        color_scheme = SchemeManager.get_scheme(args.scheme)
        logger.info(f"Using scheme: {args.scheme}")
    
    ab_chains = args.ab_chains.split(',')
    
    colorizer = InterfaceColorizer(args.pdb, args.contact_dist, color_scheme)
    colorizer.compute_interfaces(ab_chains, args.ag_chain)
    colorizer.assign_bfactors(ab_chains, args.ag_chain)
    colorizer.save_colored_pdb(args.output)
    colorizer.generate_pymol_coloring_script(args.output)
    colorizer.generate_summary_report(args.output)
    
    logger.info("✅ Coloring complete. Use B-factor spectrum in PyMOL/Chimera for visualization.")


if __name__ == "__main__":
    main()
