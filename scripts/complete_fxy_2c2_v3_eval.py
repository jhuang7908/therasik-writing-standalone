
import json
import sys
import pathlib

# Add workspace root to path
ROOT_DIR = pathlib.Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from core.evaluation.evaluator import AbEvaluator, AntibodyType

def main():
    project_dir = ROOT_DIR / "projects" / "fxy_2c2_Redesign"
    results_path = project_dir / "fxy_2c2_results.json"
    
    if not results_path.exists():
        print(f"Error: {results_path} not found.")
        sys.exit(1)
        
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    # Get v3 details
    v3_vh = results["sequences"].get("v3_VH")
    v3_vl = results["sequences"].get("v3_VL")
    # PDB is vernier_round2_pdb
    v3_pdb = results["structure"].get("v3_pdb")
    mouse_pdb = results["structure"].get("mouse_pdb")
    
    if not (v3_vh and v3_vl and v3_pdb and mouse_pdb):
        print("Error: Missing v3 info in results.json")
        sys.exit(1)
        
    # Resolve paths relative to ROOT_DIR if they are relative
    # The paths in JSON are relative to ROOT_DIR usually?
    # "projects/fxy_2c2_Redesign/..."
    # Let's check if they exist.
    
    def resolve_path(p):
        if pathlib.Path(p).exists():
            return pathlib.Path(p)
        if (ROOT_DIR / p).exists():
            return ROOT_DIR / p
        return None

    abs_v3_pdb = resolve_path(v3_pdb)
    abs_mouse_pdb = resolve_path(mouse_pdb)
    
    if not abs_v3_pdb or not abs_mouse_pdb:
        print(f"Error: PDB files not found. v3={v3_pdb}, mouse={mouse_pdb}")
        sys.exit(1)
        
    print(f"Evaluating v3...\nVH: {v3_vh[:10]}...\nVL: {v3_vl[:10]}...\nPDB: {abs_v3_pdb}")
    
    # Run Evaluator
    ev = AbEvaluator(
        project_name="fxy_2c2_v3_eval",
        ab_type=AntibodyType.HUMANIZED,
        pdb_path=str(abs_v3_pdb),
        ref_pdb_path=str(abs_mouse_pdb),
        vh_chain="H",
        vl_chain="L",
        vh_seq=v3_vh,
        vl_seq=v3_vl,
        strict_qa=False # We want to capture results even if some fail, verify will audit them
    )
    
    # Run structure modules AND immunogenicity
    # We don't need developability here as it's already in results["developability"]
    # But verify reads structure metrics from evaluation_v3
    # And verify checks for immunogenicity presence in evaluation results
    eval_result = ev.run(modules=["structure_13param", "delta_vs_mouse", "immunogenicity"])
    
    # Convert to dict
    # AbEvaluator returns EvaluationResult object? No, it returns a dict-like object or we need to convert it?
    # ev.run() returns EvaluationResult.
    # We need to serialize it.
    
    # Helper to serialize (similar to abenginecore.py)
    payload = {
        "project_name": eval_result.project_name,
        "ab_type": eval_result.ab_type.value,
        "overall_status": eval_result.overall_status,
        "modules_run": eval_result.modules_run,
        "overall_flags": eval_result.overall_flags,
        "generated_at": eval_result.generated_at,
        "results": eval_result.results,
    }
    
    # Inject into _internal
    if "_internal" not in results:
        results["_internal"] = {}
        
    results["_internal"]["evaluation_v3"] = payload
    
    # Also update the main "results" block to reflect v3 (SSOT)
    results["results"] = payload["results"]
    results["overall_status"] = payload["overall_status"]
    
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("Updated results.json with evaluation_v3.")

if __name__ == "__main__":
    main()
