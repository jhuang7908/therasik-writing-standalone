"""
C - 

Windows C
"""

import os
import shutil
import time
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import logging

# 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup_log.txt', encoding='utf-8'),
        logging.StreamHandler
    ]
)
logger = logging.getLogger(__name__)


class CDriveCleaner:
    """C"""
    
    def __init__(self, dry_run: bool = False):
        """
        
        
        Args:
            dry_run: True，，
        """
        self.dry_run = dry_run
        self.stats = {
            "files_deleted": 0,
            "folders_deleted": 0,
            "space_freed_mb": 0,
            "errors": []
        }
        self.c_drive = Path("C:/")
        
    def get_folder_size(self, folder_path: Path) -> int:
        """"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    try:
                        total_size += filepath.stat.st_size
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        return total_size
    
    def safe_delete(self, path: Path, is_folder: bool = False) -> bool:
        """
        
        
        Args:
            path: 
            is_folder: 
        
        Returns:
            
        """
        try:
            if not path.exists:
                return False
            
            if self.dry_run:
                size = self.get_folder_size(path) if is_folder else path.stat.st_size
                logger.info(f"[DRY RUN] : {path} ({size / 1024 / 1024:.2f} MB)")
                return True
            
            if is_folder:
                shutil.rmtree(path)
                self.stats["folders_deleted"] += 1
            else:
                size = path.stat.st_size
                path.unlink
                self.stats["files_deleted"] += 1
                self.stats["space_freed_mb"] += size / 1024 / 1024
            
            return True
        except PermissionError as e:
            error_msg = f"， {path}: {e}"
            logger.warning(error_msg)
            self.stats["errors"].append(error_msg)
            return False
        except Exception as e:
            error_msg = f" {path}: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            return False
    
    def clean_temp_files(self) -> int:
        """Windows"""
        logger.info("=" * 60)
        logger.info("Windows...")
        
        temp_paths = [
            Path(os.environ.get("TEMP", "C:/Windows/Temp")),
            Path(os.environ.get("TMP", "C:/Windows/Temp")),
            Path("C:/Windows/Temp"),
            Path(os.environ.get("LOCALAPPDATA", "C:/Users")) / "Temp",
        ]
        
        cleaned = 0
        for temp_path in temp_paths:
            if not temp_path.exists:
                continue
            
            logger.info(f": {temp_path}")
            try:
                for item in temp_path.iterdir:
                    try:
                        # ，
                        if item.is_file:
                            if self.safe_delete(item, is_folder=False):
                                cleaned += 1
                        elif item.is_dir:
                            # 
                            try:
                                list(item.iterdir)
                                # ，
                                if self.safe_delete(item, is_folder=True):
                                    cleaned += 1
                            except PermissionError:
                                pass
                    except Exception as e:
                        logger.warning(f" {item}: {e}")
            except PermissionError:
                logger.warning(f" {temp_path}，")
        
        logger.info(f"， {cleaned} ")
        return cleaned
    
    def clean_python_cache(self) -> int:
        """Python"""
        logger.info("=" * 60)
        logger.info("Python...")
        
        cleaned = 0
        cache_patterns = ["__pycache__", "*.pyc", "*.pyo", ".pytest_cache"]
        
        # Python
        search_paths = [
            Path.home / "Documents",
            Path.home / "Desktop",
            Path("C:/Users") / os.environ.get("USERNAME", "User"),
        ]
        
        for search_path in search_paths:
            if not search_path.exists:
                continue
            
            logger.info(f"Python: {search_path}")
            try:
                for pycache_dir in search_path.rglob("__pycache__"):
                    if self.safe_delete(pycache_dir, is_folder=True):
                        cleaned += 1
                
                for pyc_file in search_path.rglob("*.pyc"):
                    if self.safe_delete(pyc_file, is_folder=False):
                        cleaned += 1
                
                for pyo_file in search_path.rglob("*.pyo"):
                    if self.safe_delete(pyo_file, is_folder=False):
                        cleaned += 1
            except Exception as e:
                logger.warning(f" {search_path} : {e}")
        
        logger.info(f"Python， {cleaned} ")
        return cleaned
    
    def clean_browser_cache(self) -> int:
        """"""
        logger.info("=" * 60)
        logger.info("...")
        
        cleaned = 0
        browser_paths = {
            "Chrome": Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default/Cache",
            "Edge": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data/Default/Cache",
            "Firefox": Path(os.environ.get("LOCALAPPDATA", "")) / "Mozilla/Firefox/Profiles",
        }
        
        for browser_name, cache_path in browser_paths.items:
            if not cache_path.exists:
                continue
            
            logger.info(f" {browser_name} : {cache_path}")
            try:
                if cache_path.is_dir:
                    for item in cache_path.iterdir:
                        if item.is_file:
                            if self.safe_delete(item, is_folder=False):
                                cleaned += 1
            except Exception as e:
                logger.warning(f" {browser_name} : {e}")
        
        logger.info(f"， {cleaned} ")
        return cleaned
    
    def clean_old_logs(self, days_old: int = 30) -> int:
        """"""
        logger.info("=" * 60)
        logger.info(f" {days_old} ...")
        
        cleaned = 0
        cutoff_date = datetime.now - timedelta(days=days_old)
        
        log_paths = [
            Path("C:/Windows/Logs"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Temp",
            Path.home / "Documents",
        ]
        
        for log_path in log_paths:
            if not log_path.exists:
                continue
            
            try:
                for log_file in log_path.rglob("*.log"):
                    try:
                        file_time = datetime.fromtimestamp(log_file.stat.st_mtime)
                        if file_time < cutoff_date:
                            if self.safe_delete(log_file, is_folder=False):
                                cleaned += 1
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f" {log_path}: {e}")
        
        logger.info(f"， {cleaned} ")
        return cleaned
    
    def clean_downloads_old_files(self, days_old: int = 90) -> int:
        """"""
        logger.info("=" * 60)
        logger.info(f" {days_old} ...")
        
        cleaned = 0
        downloads_path = Path.home / "Downloads"
        
        if not downloads_path.exists:
            logger.warning("")
            return 0
        
        cutoff_date = datetime.now - timedelta(days=days_old)
        
        try:
            for item in downloads_path.iterdir:
                try:
                    if item.is_file:
                        file_time = datetime.fromtimestamp(item.stat.st_mtime)
                        if file_time < cutoff_date:
                            logger.info(f": {item.name} (: {file_time.strftime('%Y-%m-%d')})")
                            if self.safe_delete(item, is_folder=False):
                                cleaned += 1
                except Exception as e:
                    logger.warning(f" {item} : {e}")
        except Exception as e:
            logger.error(f": {e}")
        
        logger.info(f"， {cleaned} ")
        return cleaned
    
    def get_disk_space(self) -> Dict[str, float]:
        """C"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("C:/")
            return {
                "total_gb": total / 1024 / 1024 / 1024,
                "used_gb": used / 1024 / 1024 / 1024,
                "free_gb": free / 1024 / 1024 / 1024,
                "used_percent": (used / total) * 100
            }
        except Exception as e:
            logger.error(f": {e}")
            return {}
    
    def print_summary(self):
        """"""
        logger.info("=" * 60)
        logger.info("")
        logger.info("=" * 60)
        logger.info(f": {self.stats['files_deleted']}")
        logger.info(f": {self.stats['folders_deleted']}")
        logger.info(f": {self.stats['space_freed_mb']:.2f} MB ({self.stats['space_freed_mb'] / 1024:.2f} GB)")
        logger.info(f": {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            logger.warning(":")
            for error in self.stats['errors'][:10]:  # 10
                logger.warning(f"  - {error}")
        
        # 
        disk_info = self.get_disk_space
        if disk_info:
            logger.info("=" * 60)
            logger.info("C:")
            logger.info(f"  : {disk_info['total_gb']:.2f} GB")
            logger.info(f"  : {disk_info['used_gb']:.2f} GB ({disk_info['used_percent']:.1f}%)")
            logger.info(f"  : {disk_info['free_gb']:.2f} GB")
    
    def run_full_cleanup(self, options: Dict[str, bool] = None):
        """
        
        
        Args:
            options: 
                - temp_files: 
                - python_cache: Python
                - browser_cache: 
                - old_logs: 
                - old_downloads: 
        """
        if options is None:
            options = {
                "temp_files": True,
                "python_cache": True,
                "browser_cache": False,  # ，
                "old_logs": True,
                "old_downloads": False,  # ，
            }
        
        logger.info("=" * 60)
        logger.info("C")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.warning("⚠️   DRY RUN ，")
        
        # 
        disk_info = self.get_disk_space
        if disk_info:
            logger.info("C:")
            logger.info(f"  : {disk_info['total_gb']:.2f} GB")
            logger.info(f"  : {disk_info['used_gb']:.2f} GB ({disk_info['used_percent']:.1f}%)")
            logger.info(f"  : {disk_info['free_gb']:.2f} GB")
            logger.info("")
        
        start_time = time.time
        
        if options.get("temp_files", False):
            self.clean_temp_files
        
        if options.get("python_cache", False):
            self.clean_python_cache
        
        if options.get("browser_cache", False):
            self.clean_browser_cache
        
        if options.get("old_logs", False):
            self.clean_old_logs(days_old=30)
        
        if options.get("old_downloads", False):
            self.clean_downloads_old_files(days_old=90)
        
        elapsed_time = time.time - start_time
        
        logger.info("")
        self.print_summary
        logger.info("")
        logger.info(f"，: {elapsed_time:.2f} ")
        
        if not self.dry_run:
            # 
            disk_info_after = self.get_disk_space
            if disk_info_after and disk_info:
                logger.info("C:")
                logger.info(f"  : {disk_info_after['free_gb']:.2f} GB")
                logger.info(f"  : {disk_info_after['free_gb'] - disk_info['free_gb']:.2f} GB")


def main:
    """"""
    import argparse
    
    parser = argparse.ArgumentParser(description="C - ")
    parser.add_argument("--dry-run", action="store_true", help="，")
    parser.add_argument("--temp", action="store_true", default=True, help="")
    parser.add_argument("--python-cache", action="store_true", default=True, help="Python")
    parser.add_argument("--browser-cache", action="store_true", help="")
    parser.add_argument("--old-logs", action="store_true", default=True, help="")
    parser.add_argument("--old-downloads", action="store_true", help="")
    parser.add_argument("--all", action="store_true", help="")
    
    args = parser.parse_args
    
    # --all，
    if args.all:
        options = {
            "temp_files": True,
            "python_cache": True,
            "browser_cache": True,
            "old_logs": True,
            "old_downloads": True,
        }
    else:
        options = {
            "temp_files": args.temp,
            "python_cache": args.python_cache,
            "browser_cache": args.browser_cache,
            "old_logs": args.old_logs,
            "old_downloads": args.old_downloads,
        }
    
    # 
    if options.get("browser_cache") or options.get("old_downloads"):
        if not args.dry_run:
            print("\n⚠️  : :")
            if options.get("browser_cache"):
                print("  - ")
            if options.get("old_downloads"):
                print("  - ")
            
            confirm = input("\n？(yes/no): ")
            if confirm.lower not in ["yes", "y"]:
                print("")
                return
    
    cleaner = CDriveCleaner(dry_run=args.dry_run)
    cleaner.run_full_cleanup(options)


if __name__ == "__main__":
    main

















