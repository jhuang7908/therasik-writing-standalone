#!/usr/bin/env python3
"""
 Cursor 
， Cursor 
"""

import os
import shutil
from pathlib import Path
import sys

def get_cache_directories:
    """ Cursor """
    home = Path.home
    appdata_roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    appdata_local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    temp_dir = Path(os.environ.get("TEMP", home / "AppData" / "Local" / "Temp"))
    
    cache_dirs = [
        # 
        appdata_roaming / "Cursor",
        appdata_local / "Cursor",
        
        # 
        appdata_local / "Cursor" / "Cache",
        appdata_local / "Cursor" / "Code Cache",
        appdata_local / "Cursor" / "GPUCache",
        appdata_local / "Cursor" / "ShaderCache",
        appdata_local / "Cursor" / "logs",
        
        # 
        temp_dir / "Cursor",
    ]
    
    return cache_dirs

def get_cache_size(path):
    """（MB）"""
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
        return total_size / (1024 * 1024)  #  MB
    except Exception:
        return 0

def clear_cursor_cache(dry_run=True):
    """ Cursor """
    print("=" * 70)
    print("Cursor ")
    print("=" * 70)
    
    if dry_run:
        print("\n⚠️  （DRY RUN），")
        print("   ，: python clear_cursor_cache.py --execute")
    else:
        print("\n⚠️  ： Cursor ！")
        print("    Cursor ！")
        response = input("\n？(yes/no): ")
        if response.lower != "yes":
            print("。")
            return
    
    print("\n【】")
    print("-" * 70)
    
    cache_dirs = get_cache_directories
    found_dirs = []
    total_size = 0
    
    for cache_dir in cache_dirs:
        if cache_dir.exists and cache_dir.is_dir:
            size_mb = get_cache_size(cache_dir)
            found_dirs.append((cache_dir, size_mb))
            total_size += size_mb
            print(f"  ✅ : {cache_dir}")
            print(f"     : {size_mb:.2f} MB")
    
    if not found_dirs:
        print("  ❌  Cursor ")
        print("\n：")
        print("  1. Cursor ")
        print("  2. ")
        print("  3. Cursor ")
        return
    
    print(f"\n {len(found_dirs)} ，: {total_size:.2f} MB")
    
    if dry_run:
        print("\n【：】")
        print("-" * 70)
        for cache_dir, size_mb in found_dirs:
            print(f"  - {cache_dir} ({size_mb:.2f} MB)")
        print("\n💡 ，: python clear_cursor_cache.py --execute")
    else:
        print("\n【】")
        print("-" * 70)
        
        deleted_count = 0
        failed_count = 0
        
        for cache_dir, size_mb in found_dirs:
            try:
                print(f"  : {cache_dir}...")
                shutil.rmtree(cache_dir)
                print(f"  ✅ : {cache_dir} ({size_mb:.2f} MB)")
                deleted_count += 1
            except PermissionError:
                print(f"  ❌ : {cache_dir}")
                print("     :  Cursor ，")
                failed_count += 1
            except Exception as e:
                print(f"  ❌ : {cache_dir}")
                print(f"     : {e}")
                failed_count += 1
        
        print("\n" + "=" * 70)
        print("！")
        print("=" * 70)
        print(f"  ✅ : {deleted_count} ")
        if failed_count > 0:
            print(f"  ❌ : {failed_count} ")
        print("\n💡 ：")
        print("  1.  Cursor")
        print("  2. ")
        print("  3. ， Cursor")

def check_cursor_running:
    """ Cursor """
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'cursor' in proc.info['name'].lower:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    except ImportError:
        #  psutil，
        try:
            import subprocess
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq Cursor.exe'],
                capture_output=True,
                text=True
            )
            return 'Cursor.exe' in result.stdout
        except Exception:
            return None  # 

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    
    #  Cursor 
    if not dry_run:
        print("\n【 Cursor 】")
        print("-" * 70)
        is_running = check_cursor_running
        if is_running:
            print("  ⚠️  ： Cursor ！")
            print("      Cursor，。")
            print("     ：")
            print("     1.  Cursor  Ctrl+Shift+Q")
            print("     2.  Cursor ")
            response = input("\n？(yes/no): ")
            if response.lower != "yes":
                print("。")
                sys.exit(0)
        elif is_running is None:
            print("  ⚠️   Cursor ， Cursor ")
        else:
            print("  ✅ Cursor ，")
    
    clear_cursor_cache(dry_run=dry_run)
