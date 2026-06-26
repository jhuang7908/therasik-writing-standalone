"""
C - 

，
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def quick_cleanup:
    """ - """
    logger.info("=" * 60)
    logger.info("C")
    logger.info("=" * 60)
    
    space_freed_mb = 0
    files_deleted = 0
    
    # 1. Windows
    temp_paths = [
        Path(os.environ.get("TEMP", "C:/Windows/Temp")),
        Path(os.environ.get("TMP", "C:/Windows/Temp")),
    ]
    
    logger.info("\n1. Windows...")
    for temp_path in temp_paths:
        if temp_path.exists:
            try:
                for item in temp_path.iterdir:
                    try:
                        if item.is_file:
                            size = item.stat.st_size
                            item.unlink
                            space_freed_mb += size / 1024 / 1024
                            files_deleted += 1
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"   {temp_path}: {e}")
    
    # 2. Python
    logger.info("\n2. Python...")
    current_dir = Path.cwd
    for pycache in current_dir.rglob("__pycache__"):
        try:
            size = sum(f.stat.st_size for f in pycache.rglob("*") if f.is_file)
            shutil.rmtree(pycache)
            space_freed_mb += size / 1024 / 1024
            files_deleted += 1
        except Exception:
            pass
    
    # 3. （7）
    logger.info("\n3. （7）...")
    cutoff_date = datetime.now - timedelta(days=7)
    for log_file in current_dir.rglob("*.log"):
        try:
            if datetime.fromtimestamp(log_file.stat.st_mtime) < cutoff_date:
                size = log_file.stat.st_size
                log_file.unlink
                space_freed_mb += size / 1024 / 1024
                files_deleted += 1
        except Exception:
            pass
    
    # 
    logger.info("\n" + "=" * 60)
    logger.info("！")
    logger.info(f": {files_deleted}")
    logger.info(f": {space_freed_mb:.2f} MB ({space_freed_mb / 1024:.2f} GB)")
    logger.info("=" * 60)
    
    # 
    try:
        total, used, free = shutil.disk_usage("C:/")
        logger.info(f"\nC: {free / 1024 / 1024 / 1024:.2f} GB")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        quick_cleanup
    except KeyboardInterrupt:
        logger.info("\n\n")
    except Exception as e:
        logger.error(f"\n: {e}")

















