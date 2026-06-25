import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

class VAMIntelligenceHub:
    """
    InSynBio vAM ：
    ，，。
    """
    def __init__(self, root_dir=None):
        if root_dir is None:
            # Default to repo root (two levels up from core/evolution/)
            self.root = Path(__file__).resolve().parents[2]
        else:
            self.root = Path(root_dir)
            
        self.kb_path = self.root / "data" / "vAM_intelligence_kb.json"
        self.kb = self._load_kb()

    def _load_kb(self):
        if self.kb_path.exists():
            try:
                return json.loads(self.kb_path.read_text())
            except Exception:
                pass
        return {
            "version": "1.1",
            "last_updated": None,
            "projects_processed": [],
            "logic_performance": {
                "Cavity_Filling": {"count": 0, "avg_ddg": 0.0, "success_rate": 0.0},
                "Electrostatic_Patching": {"count": 0, "avg_ddg": 0.0, "success_rate": 0.0},
                "Conformational_Locking": {"count": 0, "avg_ddg": 0.0, "success_rate": 0.0},
                "Polar_Network": {"count": 0, "avg_ddg": 0.0, "success_rate": 0.0}
            },
            "tool_biases": {}, # Logic -> [MMGBSA_ddg / EvoEF2_ddg]
            "site_patterns": [] # Specific successful mutations and their contexts
        }

    def auto_scan_and_learn(self):
        """， Phase 4 """
        projects_dir = self.root / "projects"
        if not projects_dir.exists():
            print(f"[Intelligence Hub] Projects directory not found at {projects_dir}")
            return

        new_data = False
        for p_dir in projects_dir.iterdir():
            if not p_dir.is_dir(): continue
            # Look for both standard and project-specific results
            res_files = list(p_dir.glob("phase4_mmgbsa_results.csv"))
            
            for res_file in res_files:
                project_id = f"{p_dir.name}_{res_file.name}"
                if project_id not in self.kb["projects_processed"]:
                    print(f"[Intelligence Hub] Learning from: {project_id}")
                    self._process_project(p_dir.name, res_file)
                    self.kb["projects_processed"].append(project_id)
                    new_data = True

        if new_data:
            self.kb["last_updated"] = datetime.now().isoformat()
            self._save_kb()
            print("[Intelligence Hub] Knowledge base updated and evolved.")

    def _process_project(self, name, csv_path):
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"Error reading {csv_path}: {e}")
            return

        # Filter significant hits (ddg < -5.0 as a broader learning threshold)
        top_hits = df[df['mmgbsa_ddg'] < -5.0].copy()
        
        for _, row in top_hits.iterrows():
            logic = self._infer_physics_logic(row)
            ddg = float(row['mmgbsa_ddg'])
            
            # Update stats
            stats = self.kb["logic_performance"][logic]
            old_count = stats["count"]
            stats["avg_ddg"] = (stats["avg_ddg"] * old_count + ddg) / (old_count + 1)
            stats["count"] += 1
            
            # Track tool bias
            evo_ddg = float(row.get('evoef2_ddg', 0))
            if evo_ddg != 0:
                bias = ddg / evo_ddg
                if logic not in self.kb["tool_biases"]:
                    self.kb["tool_biases"][logic] = []
                self.kb["tool_biases"][logic].append(bias)
            
            # Record pattern
            self.kb["site_patterns"].append({
                "project": name,
                "mutation": row['mutation'],
                "logic": logic,
                "mmgbsa_ddg": ddg,
                "timestamp": datetime.now().isoformat()
            })

    def _infer_physics_logic(self, row):
        mut_aa = str(row['mutation'])[-1]
        if mut_aa in "WFYLI": return "Cavity_Filling"
        if mut_aa in "EDRK": return "Electrostatic_Patching"
        if mut_aa == "P": return "Conformational_Locking"
        return "Polar_Network"

    def _save_kb(self):
        self.kb_path.parent.mkdir(parents=True, exist_ok=True)
        self.kb_path.write_text(json.dumps(self.kb, indent=2))

if __name__ == "__main__":
    hub = VAMIntelligenceHub()
    hub.auto_scan_and_learn()
