import json
import csv
import os
import re

def validate_domains():
    MOD_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_SEARCH_PATHS = [
        os.path.join(MOD_DIR, "..", "..", "..", "..", "data", "design_rules", "functional_domains.json"),
        os.path.join(MOD_DIR, "..", "resources", "functional_domains.json")
    ]
    
    domain_db = {}
    for path in DB_SEARCH_PATHS:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                domain_db = json.load(f)
            print(f"Loaded database from: {path}")
            break
            
    if not domain_db:
        print("Error: Could not locate functional_domains.json")
        return

    report_rows = []
    
    def add_entry(category, sub_category, name, data):
        if not isinstance(data, dict):
            # This is a string reference to another domain
            report_rows.append({
                "Category": category,
                "Sub-Category": sub_category,
                "Element_Name": name,
                "Length": "N/A",
                "QA_Source": "Reference",
                "QA_Status": "Linked",
                "Validation_Issues": "Reference Link"
            })
            return
            
        seq = data.get("seq", "")
        if not seq and "components" not in data: 
            return # Skip purely informational nodes like 'targets' unless they have a sequence
            
        qa_block = data.get("qa", {})
        qa_source = qa_block.get("source", qa_block.get("uniprot", "Missing"))
        qa_status = qa_block.get("status", "Unverified")
        
        issues = []
        if not seq:
            issues.append("MISSING SEQUENCE")
        else:
            # Basic sequence validation (only valid AA letters)
            if not re.match(r"^[ACDEFGHIKLMNPQRSTVWY_]+$", seq.upper()):
                issues.append("INVALID AMINO ACIDS DETECTED")
                
            # Specific domain heuristic checks
            if category == "hinges":
                if "Short" in name and len(seq) > 60:
                    issues.append("Length exceeds expected for Short Hinge")
                if "Long" in name and len(seq) < 100:
                    issues.append("Length unusually short for Long Hinge")
            elif category == "leaders" and not seq.startswith("M"):
                issues.append("Signal peptide does not start with Methionine (M)")
            elif "CD3z" in data.get("source", name) or "activation" in sub_category.lower():
                # Check for ITAM motif roughly YxxL/I x(6-8) YxxL/I
                itam_count = len(re.findall(r"Y..[LI].{6,8}Y..[LI]", seq))
                if itam_count < 3 and "CD3z" in data.get("source", name):
                    issues.append(f"Expected 3 ITAMs, found {itam_count}")

        report_rows.append({
            "Category": category,
            "Sub-Category": sub_category,
            "Element_Name": name,
            "Length": len(seq) if seq else 0,
            "QA_Source": qa_source,
            "QA_Status": qa_status,
            "Validation_Issues": " | ".join(issues) if issues else "PASS"
        })

    # Parse different nested structures
    for cat, items in domain_db.items():
        if cat in ["targets"]: continue # Skip targets metadata
        
        for key, value in items.items():
            if cat in ["scaffolds"]: # Deeply nested (CAR-T, CAR-NK)
                for scaf_name, scaf_data in value.items():
                    components = scaf_data.get("components", {})
                    for comp_name, comp_data in components.items():
                        if isinstance(comp_data, dict):
                            add_entry(cat, f"{key} / {scaf_name}", comp_name, comp_data)
            elif cat in ["linkers"]: # Length categories (Short, Medium, Long)
                for linker_name, linker_data in value.items():
                    add_entry(cat, key, linker_name, linker_data)
            else:
                add_entry(cat, "N/A", key, value)
                
    # Sort and output
    report_rows.sort(key=lambda x: (x["Category"], x["Sub-Category"], x["Element_Name"]))
    
    out_dir = os.path.join(MOD_DIR, "..", "..", "..", "..", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "Virtual_Library_Validation_Report.csv")
    
    with open(out_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["Category", "Sub-Category", "Element_Name", "Length", "QA_Source", "QA_Status", "Validation_Issues"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in report_rows:
            writer.writerow(row)
            
    print(f"\n✅ Total elements scanned: {len(report_rows)}")
    issues_found = sum(1 for r in report_rows if r["Validation_Issues"] != "PASS")
    print(f"⚠️ Elements flaggged for manual review: {issues_found}")
    print(f"📊 Global Validation Report generated successfully at:\n   {out_file}")

if __name__ == "__main__":
    validate_domains()
