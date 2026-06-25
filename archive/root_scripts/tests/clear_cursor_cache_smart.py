#!/usr/bin/env python3
"""
 Cursor  - ，
"""

import os
import shutil
from pathlib import Path
import sys

def get_cache_directories_to_delete:
    """"""
    appdata_roaming = Path(os.environ.get("APPDATA", ""))
    appdata_local = Path(os.environ.get("LOCALAPPDATA", ""))
    
    # ， User （ settings.json）
    cache_dirs_to_delete = [
        # AppData\Roaming\Cursor 
        appdata_roaming / "Cursor" / "Cache",
        appdata_roaming / "Cursor" / "Code Cache",
        appdata_roaming / "Cursor" / "GPUCache",
        appdata_roaming / "Cursor" / "CachedData",
        appdata_roaming / "Cursor" / "CachedExtensionVSIXs",
        appdata_roaming / "Cursor" / "CachedProfilesData",
        appdata_roaming / "Cursor" / "CachedConfigurations",
        appdata_roaming / "Cursor" / "blob_storage",
        appdata_roaming / "Cursor" / "clp",
        appdata_roaming / "Cursor" / "Crashpad",
        appdata_roaming / "Cursor" / "DawnGraphiteCache",
        appdata_roaming / "Cursor" / "DawnWebGPUCache",
        appdata_roaming / "Cursor" / "Local Storage",
        appdata_roaming / "Cursor" / "logs",
        appdata_roaming / "Cursor" / "Network",
        appdata_roaming / "Cursor" / "Partitions",
        appdata_roaming / "Cursor" / "sentry",
        appdata_roaming / "Cursor" / "Service Worker",
        appdata_roaming / "Cursor" / "Session Storage",
        appdata_roaming / "Cursor" / "Shared Dictionary",
        appdata_roaming / "Cursor" / "shared_proto_db",
        appdata_roaming / "Cursor" / "VideoDecodeStats",
        appdata_roaming / "Cursor" / "WebStorage",
        appdata_roaming / "Cursor" / "Backups",  # 
        
        # AppData\Local\Cursor 
        appdata_local / "Cursor" / "Cache",
        appdata_local / "Cursor" / "Code Cache",
        appdata_local / "Cursor" / "GPUCache",
        appdata_local / "Cursor" / "ShaderCache",
        appdata_local / "Cursor" / "logs",
    ]
    
    return cache_dirs_to_delete

def get_directories_to_preserve:
    """"""
    appdata_roaming = Path(os.environ.get("APPDATA", ""))
    
    preserve_dirs = [
        appdata_roaming / "Cursor" / "User",  #  settings.json
        appdata_roaming / "Cursor" / "Workspaces",  # 
    ]
    
    return preserve_dirs

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

def clear_cursor_cache_smart(dry_run=True):
    """ Cursor """
    print("=" * 70)
    print("Cursor ")
    print("（，）")
    print("=" * 70)
    
    if dry_run:
        print("\n⚠️  （DRY RUN），")
        print("   ，: python clear_cursor_cache_smart.py --execute")
    else:
        print("\n⚠️  ： Cursor ！")
        print("   ✅ ：、")
        print("   ❌ ：、、")
        response = input("\n？(yes/no): ")
        if response.lower != "yes":
            print("。")
            return
    
    print("\n【】")
    print("-" * 70)
    
    cache_dirs = get_cache_directories_to_delete
    preserve_dirs = get_directories_to_preserve
    
    found_dirs = []
    total_size = 0
    
    for cache_dir in cache_dirs:
        if cache_dir.exists and cache_dir.is_dir:
            size_mb = get_cache_size(cache_dir)
            if size_mb > 0:  # 
                found_dirs.append((cache_dir, size_mb))
                total_size += size_mb
    
    # 
    print("\n【】")
    print("-" * 70)
    for preserve_dir in preserve_dirs:
        if preserve_dir.exists:
            size_mb = get_cache_size(preserve_dir)
            print(f"  ✅ : {preserve_dir} ({size_mb:.2f} MB)")
        else:
            print(f"  ⚠️  : {preserve_dir}")
    
    if not found_dirs:
        print("\n  ❌ ")
        print("\n：")
        print("  1. ")
        print("  2. ")
        return
    
    print("\n【】")
    print("-" * 70)
    for cache_dir, size_mb in found_dirs:
        print(f"  ❌ : {cache_dir} ({size_mb:.2f} MB)")
    
    print(f"\n {len(found_dirs)} ，: {total_size:.2f} MB")
    
    if dry_run:
        print("\n💡 ，: python clear_cursor_cache_smart.py --execute")
    else:
        print("\n【】")
        print("-" * 70)
        
        deleted_count = 0
        failed_count = 0
        freed_space = 0
        
        for cache_dir, size_mb in found_dirs:
            try:
                print(f"  : {cache_dir}...")
                shutil.rmtree(cache_dir)
                print(f"  ✅ : {cache_dir} ({size_mb:.2f} MB)")
                deleted_count += 1
                freed_space += size_mb
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
        print(f"  💾 : {freed_space:.2f} MB")
        if failed_count > 0:
            print(f"  ❌ : {failed_count} ")
        print("\n💡 ：")
        print("  1.  Cursor")
        print("  2. ")
        print("  3. ，")

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    clear_cursor_cache_smart(dry_run=dry_run)
