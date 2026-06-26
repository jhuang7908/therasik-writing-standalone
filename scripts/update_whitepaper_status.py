import re
from pathlib import Path

def main():
    path = Path("ACTES_WHITE_PAPER.md")
    content = path.read_text(encoding="utf-8")
    
    # Define patterns to match the lines and replace the status
    # We look for the entry name and the ** status at the end
    # Escape * as \*
    
    updates = [
        (r"(\|\s*\*\*SS1_MSLN_hu\*\*\s*\|.*?\|\s*)\*\*(\s*\|)", r"\1✅\2"),
        (r"(\|\s*\*\*GD2_14G2a_hu\*\*\s*\|.*?\|\s*)\*\*(\s*\|)", r"\1✅\2"),
        (r"(\|\s*\*\*Trastuzumab_scFv\*\*\s*\|.*?\|\s*)\*\*(\s*\|)", r"\1✅\2"),
        (r"(\|\s*\*\*Daratumumab_VH_VL\*\*\s*\|.*?\|\s*)\*\*(\s*\|)", r"\1✅\2")
    ]
    
    new_content = content
    for pattern, replacement in updates:
        # Check if pattern exists
        match = re.search(pattern, new_content)
        if match:
            new_content = re.sub(pattern, replacement, new_content)
            print(f"Updated: {pattern} -> Found: {match.group(0)}")
        else:
            print(f"Not found: {pattern}")
            
    path.write_text(new_content, encoding="utf-8")

if __name__ == "__main__":
    main()
