import json
from pathlib import Path

def main():
    db_path = Path("data/actes_sequences/sequence_db.json")
    new_path = Path("data/actes_sequences/new_binders.json")
    
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
        
    with open(new_path, "r", encoding="utf-8") as f:
        new_entries = json.load(f)
        
    existing_ids = {e["entry_id"] for e in db["entries"]}
    
    for entry in new_entries:
        if entry["entry_id"] in existing_ids:
            print(f"Skipping existing entry: {entry['entry_id']}")
            # Update existing entry logic could go here
        else:
            print(f"Adding new entry: {entry['entry_id']}")
            db["entries"].append(entry)
            
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        
    print("Updated sequence_db.json")

if __name__ == "__main__":
    main()
