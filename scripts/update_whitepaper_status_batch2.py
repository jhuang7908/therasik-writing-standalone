import re
from pathlib import Path

def main():
    path = Path("ACTES_WHITE_PAPER.md")
    content = path.read_text(encoding="utf-8")
    
    # Update ROR1_R12 to use R11 as substitute and mark as verified
    # Update Anti_B7H3_hu to use Enoblituzumab and mark as verified
    # Update MOG_CAAR to mark as verified
    
    updates = [
        (r"(\|\s*\*\*ROR1_R12\*\*\s*\|.*?\|\s*)\*\*(\s*\|)", r"\1✅ (R11)\2"),
        (r"(\|\s*\*\*Anti_B7H3_hu\*\*\s*\|.*?\|\s*)\*\*(\s*\|)", r"\1✅ (Enoblituzumab)\2"),
        (r"(\|\s*\*\*MOG_CAAR\*\*\s*\|.*?\|\s*)\*\*(\s*\|)", r"\1✅\2")
    ]
    
    new_content = content
    for pattern, replacement in updates:
        if re.search(pattern, new_content):
            new_content = re.sub(pattern, replacement, new_content)
            print(f"Updated: {pattern}")
        else:
            print(f"Not found: {pattern}")
            
    path.write_text(new_content, encoding="utf-8")

if __name__ == "__main__":
    main()
