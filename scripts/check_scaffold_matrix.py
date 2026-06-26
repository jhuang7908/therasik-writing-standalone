#!/usr/bin/env python3
"""
 scaffold /
"""

import re
import json
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def search_code_for_matrix_references() -> List[Tuple[str, int, str]]:
    """ scaffold /"""
    print("=== [1/4]  scaffold / ===")
    
    pattern = re.compile(
        r'align(ment)?_matrix|scaffold.*matrix|matrix.*scaffold|npz|parquet|cache.*scaffold',
        re.IGNORECASE
    )
    
    matches = []
    for search_dir in ['core', 'scripts']:
        search_path = PROJECT_ROOT / search_dir
        if not search_path.exists():
            continue
        
        for py_file in search_path.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.search(line):
                            matches.append((str(py_file.relative_to(PROJECT_ROOT)), line_num, line.strip()))
            except Exception as e:
                pass
    
    for file_path, line_num, line_content in matches[:50]:
        print(f"{file_path}:{line_num}:{line_content}")
    
    return matches


def list_matrix_cache_directories() -> List[Path]:
    """/"""
    print("\n=== [2/4] / ===")
    
    keywords = ['matrix', 'cache', 'asset', 'data']
    dirs = []
    
    for path in PROJECT_ROOT.rglob('*'):
        if path.is_dir() and any(kw in path.name.lower() for kw in keywords):
            dirs.append(path)
    
    for d in sorted(set(dirs))[:50]:
        print(str(d.relative_to(PROJECT_ROOT)))
    
    return dirs


def find_matrix_files() -> List[Path]:
    """"""
    print("\n=== [3/4] （npz/pkl/parquet/json）===")
    
    extensions = ['.npz', '.pkl', '.parquet']
    files = []
    
    # 
    for ext in extensions:
        files.extend(PROJECT_ROOT.rglob(f'*{ext}'))
    
    # matrixJSON
    for json_file in PROJECT_ROOT.rglob('*.json'):
        if 'matrix' in json_file.name.lower():
            files.append(json_file)
    
    for f in sorted(files)[:50]:
        print(str(f.relative_to(PROJECT_ROOT)))
    
    return files


def check_result_json_files() -> None:
    """JSON"""
    print("\n=== [4/4]  Python ： candidates  ===")
    
    # 
    pattern = "result*_20251217_*.json"
    paths = sorted(PROJECT_ROOT.rglob(pattern))
    
    print(f"found result json: {len(paths)}")
    
    for p in paths[:10]:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                d = json.load(f)
            
            if isinstance(d, dict):
                status = d.get('status', 'N/A')
                error = d.get('error', 'N/A')
                candidates = d.get('candidates', [])
                best_match = d.get('best_match')
                
                if (candidates == [] or best_match is None) and error:
                    print(f"- {p.relative_to(PROJECT_ROOT)} | status={status} | error={error[:80]}")
        except Exception as e:
            print(f"skip {p.relative_to(PROJECT_ROOT)}: {e}")


def check_alignment_matrix_file() -> None:
    """"""
    print("\n=== []  ===")
    
    #  core/scaffolds.py 
    scaffolds_file = PROJECT_ROOT / "core" / "scaffolds.py"
    if scaffolds_file.exists():
        with open(scaffolds_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 
            path_patterns = [
                r'["\']([^"\']*alignment[^"\']*\.json)["\']',
                r'["\']([^"\']*matrix[^"\']*\.json)["\']',
                r'Path\(["\']([^"\']+)["\']\)',
            ]
            
            for pattern in path_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:10]:
                    if isinstance(match, tuple):
                        match = match[0]
                    test_path = PROJECT_ROOT / match
                    if test_path.exists():
                        print(f"✅ : {match}")
                    else:
                        print(f"❌ : {match}")


def main():
    print("=" * 80)
    print("Scaffold /")
    print("=" * 80)
    
    search_code_for_matrix_references()
    list_matrix_cache_directories()
    find_matrix_files()
    check_result_json_files()
    check_alignment_matrix_file()
    
    print("\n" + "=" * 80)
    print("✅ ")
    print("=" * 80)


if __name__ == "__main__":
    main()




