import re
from pathlib import Path

def main():
    path = Path("ACTES_WHITE_PAPER.md")
    content = path.read_text(encoding="utf-8")
    
    names = ["SS1_MSLN_hu", "GD2_14G2a_hu", "Trastuzumab_scFv", "Daratumumab_VH_VL"]
    
    for name in names:
        print(f"--- Searching for {name} ---")
        for line in content.splitlines():
            if name in line:
                print(f"Found line: {line}")
                # Try to match the regex against this line
                pattern = r"(\|\s*\*\*" + re.escape(name) + r"\*\*\s*\|.*?\|\s*)\*\*(\s*\|)"
                if re.search(pattern, line):
                    print("Regex MATCHES!")
                else:
                    print(f"Regex DOES NOT MATCH pattern: {pattern}")
                    # Debug regex
                    print(f"Line content: '{line}'")

if __name__ == "__main__":
    main()
