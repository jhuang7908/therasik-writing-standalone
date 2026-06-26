#!/usr/bin/env python3
"""
color_scheme_manager.py

Flexible color scheme management for interface visualization.
Supports multiple predefined schemes + custom configuration.

FEATURES:
  • 8 predefined color schemes (rainbow, scientific, publication, etc.)
  • JSON-based custom scheme definition
  • PyMOL/Chimera spectrum command generation
  • B-factor range optimization
  • Scheme preview + documentation

USAGE:
    # Use predefined scheme
    python colorize_interface_pdb.py \
        --pdb complex.pdb \
        --scheme rainbow \
        --ab_chains A --ag_chain B \
        --output colored.pdb
    
    # Use custom scheme
    python colorize_interface_pdb.py \
        --pdb complex.pdb \
        --scheme-config my_colors.json \
        --ab_chains A --ag_chain B \
        --output colored.pdb
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class SchemeType(Enum):
    """Predefined color schemes."""
    RAINBOW = "rainbow"              # ：→→→→→
    SCIENTIFIC = "scientific"        # ：→→→→
    PUBLICATION = "publication"      # ：→→→
    DARK = "dark"                    # ：→→→
    THERMAL = "thermal"              # ：→→→
    PASTEL = "pastel"                # ：→→→
    GRAYSCALE = "grayscale"          # 
    CONTRASTING = "contrasting"      # ：→→


@dataclass
class ColorSpec:
    """Single color specification."""
    name: str
    hex_code: str                    # e.g., "#FF0000"
    pymol_name: str                  # e.g., "red"
    chimera_name: str                # e.g., "red"
    description: str = ""


@dataclass
class InterfaceRole:
    """Interface role definition."""
    name: str                        # "CDR", "Framework", "Antigen", "Non-interface"
    bfactor_range: Tuple[int, int]   # (min, max)
    color: ColorSpec
    pymol_alias: str = ""            # Alternative PyMOL name
    priority: int = 0                # Display priority (higher = more important)


class ColorScheme:
    """Complete color scheme definition."""
    
    def __init__(self, 
                 scheme_type: SchemeType = SchemeType.RAINBOW,
                 name: str = "",
                 description: str = ""):
        self.scheme_type = scheme_type
        self.name = name or scheme_type.value
        self.description = description
        self.roles: Dict[str, InterfaceRole] = {}
        self._load_scheme()
    
    def _load_scheme(self):
        """Load predefined scheme."""
        if self.scheme_type == SchemeType.RAINBOW:
            self._setup_rainbow()
        elif self.scheme_type == SchemeType.SCIENTIFIC:
            self._setup_scientific()
        elif self.scheme_type == SchemeType.PUBLICATION:
            self._setup_publication()
        elif self.scheme_type == SchemeType.DARK:
            self._setup_dark()
        elif self.scheme_type == SchemeType.THERMAL:
            self._setup_thermal()
        elif self.scheme_type == SchemeType.PASTEL:
            self._setup_pastel()
        elif self.scheme_type == SchemeType.GRAYSCALE:
            self._setup_grayscale()
        elif self.scheme_type == SchemeType.CONTRASTING:
            self._setup_contrasting()
    
    def _setup_rainbow(self):
        """Classic rainbow: red→yellow→green→cyan→blue→purple"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("Red", "#FF0000", "red", "red", "CDR hot spots"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("Cyan", "#00FFFF", "cyan", "cyan", "Framework contacts"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("Yellow", "#FFFF00", "yellow", "yellow", "Antigen contacts"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("White", "#FFFFFF", "white", "white", "Surface/buried"),
            priority=1
        )
    
    def _setup_scientific(self):
        """Scientific: white→blue→green→yellow→red"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("Red", "#E60000", "red", "red", "High energy"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("Blue", "#0000FF", "blue", "blue", "Low energy"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("Green", "#00AA00", "green", "green", "Medium energy"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("White", "#FFFFFF", "white", "white", "Bulk solvent"),
            priority=1
        )
    
    def _setup_publication(self):
        """Publication quality: gray→blue→green→red"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("Magenta", "#CC0066", "magenta", "magenta", "CDR regions"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("Blue", "#0033CC", "blue", "blue", "Framework regions"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("Orange", "#FF8800", "orange", "orange", "Antigen regions"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("LightGray", "#CCCCCC", "gray", "gray", "Non-interface"),
            priority=1
        )
    
    def _setup_dark(self):
        """Dark theme: black→blue→magenta→white"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("Magenta", "#FF00FF", "magenta", "magenta", "CDR hot spots"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("Cyan", "#00FFFF", "cyan", "cyan", "Framework"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("Yellow", "#FFFF00", "yellow", "yellow", "Antigen"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("Black", "#000000", "black", "black", "Buried"),
            priority=1
        )
    
    def _setup_thermal(self):
        """Thermal: blue (cold) → red (hot)"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("Red", "#FF0000", "red", "red", "Hot (CDR)"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("Green", "#00CC00", "green", "green", "Warm (FR)"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("Orange", "#FF6600", "orange", "orange", "Warm (Ag)"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("Blue", "#0000FF", "blue", "blue", "Cold"),
            priority=1
        )
    
    def _setup_pastel(self):
        """Pastel colors: soft, publication-friendly"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("PastelRed", "#FF9999", "red", "red", "CDR (soft)"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("PastelBlue", "#9999FF", "blue", "blue", "FR (soft)"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("PastelOrange", "#FFCC99", "orange", "orange", "Ag (soft)"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("PastelGray", "#DDDDDD", "gray", "gray", "Surface"),
            priority=1
        )
    
    def _setup_grayscale(self):
        """Grayscale: suitable for B&W printing"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("Black", "#000000", "black", "black", "CDR (darkest)"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("DarkGray", "#555555", "darkgray", "darkgray", "FR (dark)"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("Gray", "#888888", "gray", "gray", "Ag (mid)"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("LightGray", "#DDDDDD", "lightgray", "lightgray", "Surface"),
            priority=1
        )
    
    def _setup_contrasting(self):
        """High contrast: cyan, yellow, magenta"""
        self.roles["cdr"] = InterfaceRole(
            name="CDR Interface",
            bfactor_range=(90, 99),
            color=ColorSpec("Magenta", "#FF00FF", "magenta", "magenta", "CDR (bright)"),
            priority=3
        )
        self.roles["framework"] = InterfaceRole(
            name="Framework Interface",
            bfactor_range=(50, 59),
            color=ColorSpec("Cyan", "#00FFFF", "cyan", "cyan", "FR (bright)"),
            priority=2
        )
        self.roles["antigen"] = InterfaceRole(
            name="Antigen Interface",
            bfactor_range=(70, 79),
            color=ColorSpec("Yellow", "#FFFF00", "yellow", "yellow", "Ag (bright)"),
            priority=2
        )
        self.roles["other"] = InterfaceRole(
            name="Non-interface",
            bfactor_range=(0, 20),
            color=ColorSpec("White", "#FFFFFF", "white", "white", "Background"),
            priority=1
        )
    
    def to_pymol_spectrum(self) -> str:
        """Generate PyMOL spectrum command."""
        # Sort by B-factor for spectrum
        sorted_roles = sorted(
            self.roles.values(),
            key=lambda r: r.bfactor_range[0]
        )
        colors = ' '.join([r.color.pymol_name for r in sorted_roles])
        bmin = sorted_roles[0].bfactor_range[0]
        bmax = sorted_roles[-1].bfactor_range[1]
        return f"spectrum b, {colors}, {bmin}, {bmax}"
    
    def to_chimera_coloring(self) -> str:
        """Generate ChimeraX coloring command."""
        sorted_roles = sorted(
            self.roles.values(),
            key=lambda r: r.bfactor_range[0]
        )
        colors = ','.join([r.color.chimera_name for r in sorted_roles])
        bmin = sorted_roles[0].bfactor_range[0]
        bmax = sorted_roles[-1].bfactor_range[1]
        return f"color bfactor palette {colors} range {bmin},{bmax}"
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "scheme_name": self.name,
            "scheme_type": self.scheme_type.value,
            "description": self.description,
            "roles": {
                name: {
                    "bfactor_min": role.bfactor_range[0],
                    "bfactor_max": role.bfactor_range[1],
                    "color_name": role.color.name,
                    "hex_code": role.color.hex_code,
                    "pymol_name": role.color.pymol_name,
                    "chimera_name": role.color.chimera_name,
                    "description": role.color.description,
                    "priority": role.priority,
                }
                for name, role in self.roles.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ColorScheme":
        """Load from dictionary."""
        scheme = cls()
        scheme.name = data.get("scheme_name", "custom")
        scheme.description = data.get("description", "")
        scheme.roles = {}
        
        for role_name, role_data in data.get("roles", {}).items():
            color = ColorSpec(
                name=role_data["color_name"],
                hex_code=role_data["hex_code"],
                pymol_name=role_data["pymol_name"],
                chimera_name=role_data["chimera_name"],
                description=role_data.get("description", "")
            )
            scheme.roles[role_name] = InterfaceRole(
                name=role_name.upper(),
                bfactor_range=(role_data["bfactor_min"], role_data["bfactor_max"]),
                color=color,
                priority=role_data.get("priority", 0)
            )
        
        return scheme
    
    def print_summary(self):
        """Print scheme summary."""
        print(f"\n{'='*60}")
        print(f"Scheme: {self.name}")
        print(f"Type: {self.scheme_type.value}")
        print(f"Description: {self.description}")
        print(f"{'='*60}")
        
        for role_name, role in sorted(
            self.roles.items(),
            key=lambda x: x[1].bfactor_range[0],
            reverse=True
        ):
            b_min, b_max = role.bfactor_range
            print(f"\n{role.color.name:15} (B-factor {b_min:2d}–{b_max:2d})")
            print(f"  • PyMOL:    {role.color.pymol_name}")
            print(f"  • Chimera:  {role.color.chimera_name}")
            print(f"  • Hex:      {role.color.hex_code}")
            print(f"  • Role:     {role.color.description}")
        
        print(f"\n{'─'*60}")
        print(f"PyMOL Command:\n  {self.to_pymol_spectrum()}")
        print(f"\nChimeraX Command:\n  {self.to_chimera_coloring()}")
        print(f"{'='*60}\n")


class SchemeManager:
    """Manage multiple schemes + custom configurations."""
    
    BUILTIN_SCHEMES = {
        "rainbow": SchemeType.RAINBOW,
        "scientific": SchemeType.SCIENTIFIC,
        "publication": SchemeType.PUBLICATION,
        "dark": SchemeType.DARK,
        "thermal": SchemeType.THERMAL,
        "pastel": SchemeType.PASTEL,
        "grayscale": SchemeType.GRAYSCALE,
        "contrasting": SchemeType.CONTRASTING,
    }
    
    @staticmethod
    def get_scheme(scheme_name: str = "rainbow") -> ColorScheme:
        """Get a predefined scheme."""
        if scheme_name not in SchemeManager.BUILTIN_SCHEMES:
            logger.warning(f"Unknown scheme '{scheme_name}', using 'rainbow'")
            scheme_name = "rainbow"
        
        return ColorScheme(SchemeManager.BUILTIN_SCHEMES[scheme_name])
    
    @staticmethod
    def load_custom_scheme(config_path: str) -> ColorScheme:
        """Load custom scheme from JSON."""
        with open(config_path) as f:
            data = json.load(f)
        return ColorScheme.from_dict(data)
    
    @staticmethod
    def list_schemes() -> Dict[str, str]:
        """List all available schemes."""
        return {
            "rainbow": "Classic rainbow (red→cyan→yellow)",
            "scientific": "Scientific (white→blue→green→yellow→red)",
            "publication": "Publication quality (gray→blue→green→red)",
            "dark": "Dark theme (black→cyan→magenta→white)",
            "thermal": "Thermal gradient (blue→green→orange→red)",
            "pastel": "Soft pastel colors",
            "grayscale": "Grayscale (B&W printing friendly)",
            "contrasting": "High contrast (cyan/yellow/magenta)",
        }
    
    @staticmethod
    def create_custom_scheme_template(output_path: str = "custom_scheme.json"):
        """Create a template for custom scheme configuration."""
        template = {
            "scheme_name": "my_custom_scheme",
            "scheme_type": "custom",
            "description": "My custom color scheme for interface visualization",
            "roles": {
                "cdr": {
                    "bfactor_min": 90,
                    "bfactor_max": 99,
                    "color_name": "Red",
                    "hex_code": "#FF0000",
                    "pymol_name": "red",
                    "chimera_name": "red",
                    "description": "CDR interface hot spots",
                    "priority": 3
                },
                "framework": {
                    "bfactor_min": 50,
                    "bfactor_max": 59,
                    "color_name": "Blue",
                    "hex_code": "#0000FF",
                    "pymol_name": "blue",
                    "chimera_name": "blue",
                    "description": "Framework interface",
                    "priority": 2
                },
                "antigen": {
                    "bfactor_min": 70,
                    "bfactor_max": 79,
                    "color_name": "Green",
                    "hex_code": "#00AA00",
                    "pymol_name": "green",
                    "chimera_name": "green",
                    "description": "Antigen interface",
                    "priority": 2
                },
                "other": {
                    "bfactor_min": 0,
                    "bfactor_max": 20,
                    "color_name": "White",
                    "hex_code": "#FFFFFF",
                    "pymol_name": "white",
                    "chimera_name": "white",
                    "description": "Non-interface regions",
                    "priority": 1
                }
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2)
        
        logger.info(f"Template created: {output_path}")
    
    @staticmethod
    def export_all_schemes(output_dir: str = "color_schemes"):
        """Export all predefined schemes as JSON files."""
        Path(output_dir).mkdir(exist_ok=True)
        
        for scheme_name, scheme_type in SchemeManager.BUILTIN_SCHEMES.items():
            scheme = ColorScheme(scheme_type)
            output_path = Path(output_dir) / f"{scheme_name}.json"
            
            with open(output_path, 'w') as f:
                json.dump(scheme.to_dict(), f, indent=2)
            
            logger.info(f"Exported: {output_path}")


def main():
    """Demo: list all schemes and generate template."""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            print("\n" + "="*60)
            print("Available Color Schemes")
            print("="*60)
            for name, desc in SchemeManager.list_schemes().items():
                print(f"  • {name:15} → {desc}")
            print("="*60 + "\n")
        
        elif sys.argv[1] == "show":
            scheme_name = sys.argv[2] if len(sys.argv) > 2 else "rainbow"
            scheme = SchemeManager.get_scheme(scheme_name)
            scheme.print_summary()
        
        elif sys.argv[1] == "template":
            output = sys.argv[2] if len(sys.argv) > 2 else "custom_scheme.json"
            SchemeManager.create_custom_scheme_template(output)
        
        elif sys.argv[1] == "export":
            output_dir = sys.argv[2] if len(sys.argv) > 2 else "color_schemes"
            SchemeManager.export_all_schemes(output_dir)
        
        else:
            print("Usage:")
            print("  python color_scheme_manager.py list")
            print("  python color_scheme_manager.py show [scheme_name]")
            print("  python color_scheme_manager.py template [output.json]")
            print("  python color_scheme_manager.py export [output_dir]")
    
    else:
        # Demo: show all schemes
        for name in SchemeManager.BUILTIN_SCHEMES.keys():
            scheme = SchemeManager.get_scheme(name)
            scheme.print_summary()


if __name__ == "__main__":
    main()
