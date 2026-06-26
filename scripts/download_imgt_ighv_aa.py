"""
 IMGT IGHV_aa FASTA 

 IMGT  IGHV  FASTA 
：data/germlines/IMGT_V-QUEST_reference_directory/Homo_sapiens/IG_aa/
"""

from pathlib import Path
import urllib.request
import zipfile
import shutil
import tempfile
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "germlines" / "IMGT_V-QUEST_reference_directory" / "Homo_sapiens" / "IG_aa"
TARGET_FILE = "IGHV_aa.fasta"

# IMGT V-QUEST （）
IMGT_DOWNLOAD_URL = "https://www.imgt.org/download/V-QUEST/IMGT_V-QUEST_reference_directory.zip"


def download_with_progress(url: str, output_path: Path):
    """"""
    def reporthook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        print(f"\r[] {percent}% ({count * block_size}/{total_size} bytes)", end="", flush=True)
    
    print(f"[INFO] ：{url}")
    print(f"[INFO] ：{output_path}")
    
    try:
        urllib.request.urlretrieve(url, output_path, reporthook=reporthook)
        print("\n[OK] ")
        return True
    except Exception as e:
        print(f"\n[ERROR] ：{e}")
        return False


def extract_ighv_aa_from_zip(zip_path: Path, output_dir: Path) -> Optional[Path]:
    """ ZIP  IGHV_aa.fasta"""
    print(f"[INFO]  ZIP ：{zip_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            #  IGHV_aa.fasta 
            target_path = None
            for name in zip_ref.namelist():
                if "Homo_sapiens" in name and "IG_aa" in name and "IGHV_aa" in name and name.endswith(".fasta"):
                    target_path = name
                    break
            
            if not target_path:
                print("[ERROR]  ZIP  IGHV_aa.fasta")
                print("[INFO] ZIP ：")
                for name in sorted(zip_ref.namelist())[:20]:
                    print(f"  - {name}")
                return None
            
            print(f"[INFO] ：{target_path}")
            
            # 
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 
            output_file = output_dir / TARGET_FILE
            with zip_ref.open(target_path) as source, open(output_file, 'wb') as target:
                shutil.copyfileobj(source, target)
            
            print(f"[OK] ：{output_file}")
            return output_file
            
    except Exception as e:
        print(f"[ERROR] ：{e}")
        return None


def download_imgt_ighv_aa(
    output_dir: Optional[Path] = None,
    zip_file_path: Optional[Path] = None,
    auto: bool = False
) -> Optional[Path]:
    """
     IMGT IGHV_aa FASTA 
    
    Args:
        output_dir: （：data/germlines/IMGT_V-QUEST_reference_directory/Homo_sapiens/IG_aa/）
        zip_file_path:  ZIP ，
    
    Returns:
         FASTA ， None
    """
    if output_dir is None:
        output_dir = DOWNLOAD_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ，
    existing_file = output_dir / TARGET_FILE
    if existing_file.exists():
        print(f"[INFO] ：{existing_file}")
        if not auto:
            response = input("？(y/n): ").strip().lower()
            if response != 'y':
                print("[INFO] ")
                return existing_file
        else:
            print("[INFO] ：")
            return existing_file
    
    # 1： ZIP ，
    if zip_file_path and zip_file_path.exists():
        return extract_ighv_aa_from_zip(zip_file_path, output_dir)
    
    # 2： ZIP 
    print("\n[1]  IMGT ...")
    print("[] IMGT ，：")
    print("  https://www.imgt.org/vquest/refseqh.html")
    print("  ：")
    print(f"  {IMGT_DOWNLOAD_URL}")
    print()
    
    if auto:
        use_download = 'y'
        print("[INFO] ：")
    else:
        use_download = input(" ZIP ？(y/n): ").strip().lower()
    
    if use_download == 'y':
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "IMGT_V-QUEST_reference_directory.zip"
            if download_with_progress(IMGT_DOWNLOAD_URL, zip_path):
                return extract_ighv_aa_from_zip(zip_path, output_dir)
            else:
                print("\n[2] ，")
    
    # 3：
    print("\n" + "="*60)
    print("：")
    print("="*60)
    print("1.  IMGT V-QUEST ：")
    print("   https://www.imgt.org/vquest/refseqh.html")
    print()
    print("2.  'IMGT_V-QUEST_reference_directory.zip'")
    print()
    print("3.  ZIP ：")
    print(f"   python scripts\\download_imgt_ighv_aa.py --zip-file <ZIP>")
    print()
    print("4.  ZIP ，：")
    print("   IMGT_V-QUEST_reference_directory/Homo_sapiens/IG_aa/IGHV_aa.fasta")
    print("   ：")
    print(f"   {output_dir / TARGET_FILE}")
    print("="*60)
    
    return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description=" IMGT IGHV_aa FASTA ")
    parser.add_argument(
        "--output-dir",
        type=str,
        help="（：data/germlines/IMGT_V-QUEST_reference_directory/Homo_sapiens/IG_aa/）",
    )
    parser.add_argument(
        "--zip-file",
        type=str,
        help=" ZIP （，）",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="：，",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    zip_file = Path(args.zip_file) if args.zip_file else None
    
    result = download_imgt_ighv_aa(output_dir=output_dir, zip_file_path=zip_file, auto=args.auto)
    
    if result:
        print(f"\n[SUCCESS] IGHV_aa.fasta ：{result}")
        print(f"\n：")
        print(f"  python scripts\\extract_human_vh3_frameworks.py --fasta-dir {result.parent}")
    else:
        print("\n[INFO] ")


if __name__ == "__main__":
    main()




















