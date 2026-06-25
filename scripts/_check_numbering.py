import subprocess, sys
for pkg in ['anarci', 'abnumber']:
    r = subprocess.run([sys.executable, '-c', f'import {pkg}; print("{pkg} ok")'],
        capture_output=True, text=True)
    print(f'{pkg}:', r.stdout.strip() or r.stderr.strip()[:100])
