import os
import sys

ANARCI_PY = r"d:\Users\NextVivo\miniconda3\envs\affmat\Lib\site-packages\anarci\anarci.py"

def main():
    if not os.path.exists(ANARCI_PY):
        print(f"Error: {ANARCI_PY} not found.")
        return

    with open(ANARCI_PY, 'r') as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    for line in lines:
        if "# --- pyhmmer path" in line:
            skip = True
            continue
        elif "# --- end pyhmmer attempt" in line:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    with open(ANARCI_PY, 'w') as f:
        f.writelines(new_lines)
    print("Successfully reverted anarci.py")

if __name__ == "__main__":
    main()
