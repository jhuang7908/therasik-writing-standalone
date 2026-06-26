
import json
import sys
import pathlib

# Add workspace root to path
ROOT_DIR = pathlib.Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

def main():
    project_dir = ROOT_DIR / "projects" / "fxy_2c2_Redesign"
    results_path = project_dir / "fxy_2c2_results.json"
    
    if not results_path.exists():
        print(f"Error: {results_path} not found.")
        sys.exit(1)
        
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    # Define v2->v3 mutations explicitly
    # Based on my previous fix script
    
    v2_to_v3_mutations = [
        # Vernier Round 2
        {
            "chain": "VH",
            "kabat_pos": 2,
            "from": "V",
            "to": "I",
            "region": "FR1 (Vernier)",
            "rationale": "：Vernier Round 2 （CDR RMSD ）"
        },
        # CMC pI optimization
        {
            "chain": "VH",
            "kabat_pos": 12,
            "from": "K",
            "to": "Q",
            "region": "FR1",
            "rationale": "CMC： (pI 8.98 -> 8.31)"
        },
        {
            "chain": "VH",
            "kabat_pos": 13,
            "from": "K",
            "to": "Q",
            "region": "FR1",
            "rationale": "CMC： (pI 8.98 -> 8.31)"
        },
        {
            "chain": "VL",
            "kabat_pos": 18,
            "from": "R",
            "to": "Q",
            "region": "FR1",
            "rationale": "CMC： (pI 8.98 -> 8.31)"
        }
    ]
    
    if "mutations" not in results:
        results["mutations"] = {}
        
    results["mutations"]["v2_to_v3"] = v2_to_v3_mutations
    
    # Also ensure _internal_note has vernier_round2 info if not already correct
    # It seems verify_vhvl_v44_project.py reads from _internal_note.vernier_round2
    # My previous script might have overwritten or not fully populated it.
    # Let's check if it exists.
    
    # Actually, verify script looks for "evaluation_vX_vernier_round2" in _internal
    # OR it looks at _internal_note inside the evaluation object.
    
    # Let's just ensure the mutations are there, which is what the user asked about ("CMC？")
    
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("Updated mutations in results.json")

if __name__ == "__main__":
    main()
