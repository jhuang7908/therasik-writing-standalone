#!/usr/bin/env python
# -*- coding: utf-8 -*-

""""""

import os
import sys

def get_dir_size(path):
    """"""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    if os.path.exists(filepath):
                        total += os.path.getsize(filepath)
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total

def format_size(size_bytes):
    """"""
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_mb / 1024
    if size_gb >= 1:
        return f"{size_mb:.2f} MB ({size_gb:.3f} GB)"
    else:
        return f"{size_mb:.2f} MB"

def main():
    packages = {}
    
    # torch
    try:
        import torch
        packages['torch'] = torch
    except ImportError:
        packages['torch'] = None
    
    # numpy
    try:
        import numpy
        packages['numpy'] = numpy
    except ImportError:
        packages['numpy'] = None
    
    # gemmi
    try:
        import gemmi
        packages['gemmi'] = gemmi
    except ImportError:
        packages['gemmi'] = None
    
    # anarcii
    try:
        import anarcii
        packages['anarcii'] = anarcii
    except ImportError:
        packages['anarcii'] = None
    
    print("=" * 70)
    print("")
    print("=" * 70)
    print()
    
    total_size = 0
    installed_count = 0
    
    for name, pkg in sorted(packages.items()):
        if pkg is None:
            print(f"{name:10} {'':>20}")
        else:
            try:
                pkg_path = os.path.dirname(pkg.__file__)
                size = get_dir_size(pkg_path)
                size_str = format_size(size)
                version = getattr(pkg, '__version__', '')
                total_size += size
                installed_count += 1
                print(f"{name:10} {size_str:>25} (: {version})")
            except Exception as e:
                print(f"{name:10} {'':>20} (: {e})")
    
    print()
    print("=" * 70)
    print(f": {installed_count}/{len(packages)} ")
    print(f": {format_size(total_size)}")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


















