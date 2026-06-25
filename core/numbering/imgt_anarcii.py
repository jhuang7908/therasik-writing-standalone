"""
IMGT - ANARCII

ANARCII，IMGT
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import re

try:
    from anarcii import Anarcii
    HAS_ANARCII = True
except ImportError:
    HAS_ANARCII = False
    Anarcii = None


# ，
# CPU（cpu=True），mode='accuracy'
_anarcii_obj: Optional[Anarcii] = None

def _get_anarcii_obj() -> Anarcii:
    """ANARCII（）"""
    global _anarcii_obj
    
    if not HAS_ANARCII:
        raise ImportError("anarcii package is not installed. Install with: pip install anarcii")
    
    if _anarcii_obj is None:
        _anarcii_obj = Anarcii(
            seq_type="antibody",
            mode="accuracy",
            batch_size=32,
            cpu=True,     # CPU（CPUtorch）
            ncpu=-1,      # CPU
            verbose=False,
        )
    
    return _anarcii_obj


class IMGTNumberingError(RuntimeError):
    """ANARCII，"""
    pass


def imgt_number_anarcii(seq: str) -> List[Dict[str, Any]]:
    """
    ANARCII/VHHIMGT。
    
    Args:
        seq: 
    
    Returns:
        list，:
        {
            "pos": int,        # IMGT，37
            "ins_code": str,   # ，'A'，' '
            "aa": str,         # 
            "chain_type": str, # 'H' / 'L' / 'K' 
            "scheme": str      # 'imgt'
        }
    
    Raises:
        IMGTNumberingError: 
        ImportError: anarcii
    """
    if not seq or not isinstance(seq, str):
        raise IMGTNumberingError("Sequence must be a non-empty string")
    
    if not seq.strip():
        raise IMGTNumberingError("Sequence cannot be empty or whitespace only")
    
    # （、）
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    
    if not seq_clean:
        raise IMGTNumberingError("Sequence is empty after cleaning")
    
    # ANARCIIdict，keyquery，'Sequence'
    try:
        anarcii_obj = _get_anarcii_obj()
        result = anarcii_obj.number(seq_clean)
    except ImportError as e:
        raise IMGTNumberingError(f"ANARCII not available: {e}") from e
    except Exception as e:
        raise IMGTNumberingError(f"ANARCII.number failed: {e}") from e
    
    if not isinstance(result, dict) or len(result) == 0:
        raise IMGTNumberingError(f"Unexpected ANARCII result: {result!r}")
    
    # key（'Sequence'）
    key = next(iter(result.keys()))
    seq_info = result.get(key, {})
    
    if not isinstance(seq_info, dict):
        raise IMGTNumberingError(f"Unexpected seq_info type: {type(seq_info)}")
    
    numbering = seq_info.get("numbering", [])
    chain_type = seq_info.get("chain_type", None)
    scheme = seq_info.get("scheme", None)
    
    if not numbering:
        raise IMGTNumberingError(f"No numbering found in ANARCII result for key={key!r}")
    
    rows: List[Dict[str, Any]] = []
    
    # numbering: [((pos, ins_code), aa), ...]
    for item in numbering:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        
        pos_info, aa = item[0], item[1]
        
        # gap
        if aa == "-" or pos_info is None:
            continue
        
        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            # ，
            continue
        
        pos = pos_info[0]
        ins_code = pos_info[1] if len(pos_info) > 1 else " "
        
        # Robust parsing: pos can sometimes be non-int-like for insertions in
        # certain tool outputs (e.g. "111A"). We normalize by taking leading digits.
        pos_num: Optional[int] = None
        try:
            pos_num = int(pos)
        except (ValueError, TypeError):
            m = re.match(r"^(\d+)", str(pos))
            if m:
                pos_num = int(m.group(1))
        if pos_num is None:
            continue
        
        if ins_code is None:
            ins_code = " "
        
        rows.append({
            "pos": pos_num,
            "ins_code": str(ins_code),
            "aa": str(aa),
            "chain_type": chain_type,
            "scheme": scheme,
        })
    
    if not rows:
        raise IMGTNumberingError("Parsed numbering rows is empty")
    
    return rows


def imgt_number_anarcii_indexed(seq: str) -> Dict[str, Any]:
    """
    Like imgt_number_anarcii(), but preserves mapping back to the original
    sequence indices using ANARCII's query_start/query_end.

    Returns:
        {
          "rows": [
             {"seq_idx": int, "pos": int, "ins_code": str, "aa": str, "chain_type": str, "scheme": str},
             ...
          ],
          "query_start": int,
          "query_end": int,
          "chain_type": str,
          "scheme": str,
        }

    Notes:
      - ANARCII may choose to number only a subsequence of the query (e.g. omit tail residues).
      - Gaps in ANARCII numbering (aa == '-') do not consume query indices.
    """
    if not seq or not isinstance(seq, str):
        raise IMGTNumberingError("Sequence must be a non-empty string")

    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    if not seq_clean:
        raise IMGTNumberingError("Sequence is empty after cleaning")

    try:
        anarcii_obj = _get_anarcii_obj()
        result = anarcii_obj.number(seq_clean)
    except ImportError as e:
        raise IMGTNumberingError(f"ANARCII not available: {e}") from e
    except Exception as e:
        raise IMGTNumberingError(f"ANARCII.number failed: {e}") from e

    if not isinstance(result, dict) or len(result) == 0:
        raise IMGTNumberingError(f"Unexpected ANARCII result: {result!r}")

    key = next(iter(result.keys()))
    seq_info = result.get(key, {})
    if not isinstance(seq_info, dict):
        raise IMGTNumberingError(f"Unexpected seq_info type: {type(seq_info)}")

    numbering = seq_info.get("numbering", [])
    chain_type = seq_info.get("chain_type", None)
    scheme = seq_info.get("scheme", None)
    q_start = seq_info.get("query_start", 0)
    q_end = seq_info.get("query_end", len(seq_clean) - 1)

    if numbering is None or not isinstance(numbering, list) or len(numbering) == 0:
        raise IMGTNumberingError(f"No numbering found in ANARCII result for key={key!r}")

    rows: List[Dict[str, Any]] = []
    seq_idx = int(q_start) if q_start is not None else 0

    for item in numbering:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        pos_info, aa = item[0], item[1]
        if pos_info is None:
            continue
        # gap in alignment (no residue consumed)
        if aa == "-":
            continue

        if not isinstance(pos_info, tuple) or len(pos_info) < 1:
            continue

        pos = pos_info[0]
        ins_code = pos_info[1] if len(pos_info) > 1 else " "

        pos_num: Optional[int] = None
        try:
            pos_num = int(pos)
        except (ValueError, TypeError):
            m = re.match(r"^(\d+)", str(pos))
            if m:
                pos_num = int(m.group(1))
        if pos_num is None:
            continue

        if ins_code is None:
            ins_code = " "

        # stop if ANARCII indicates end of numbered region
        if q_end is not None and seq_idx > int(q_end):
            break
        if seq_idx < 0 or seq_idx >= len(seq_clean):
            break

        # Optional sanity: ensure residue matches
        if seq_clean[seq_idx] != str(aa):
            # If mismatch occurs, still record, but do not crash
            pass

        rows.append(
            {
                "seq_idx": int(seq_idx),
                "pos": int(pos_num),
                "ins_code": str(ins_code),
                "aa": str(aa),
                "chain_type": chain_type,
                "scheme": scheme,
            }
        )
        seq_idx += 1

    if not rows:
        raise IMGTNumberingError("Parsed indexed numbering rows is empty")

    return {
        "rows": rows,
        "query_start": int(q_start) if q_start is not None else 0,
        "query_end": int(q_end) if q_end is not None else (len(seq_clean) - 1),
        "chain_type": chain_type,
        "scheme": scheme,
    }


def build_pos_to_aa_map(rows: List[Dict[str, Any]]) -> Dict[int, str]:
    """
    ：{pos: aa}，IMGT。
    
    Args:
        rows: imgt_number_anarcii
    
    Returns:
        ，{pos: aa}，{37: 'F', 44: 'E', 45: 'R', 47: 'G'}
    """
    pos2aa: Dict[int, str] = {}
    
    for r in rows:
        pos = r.get("pos")
        aa = r.get("aa")
        
        if isinstance(pos, int) and isinstance(aa, str) and aa != "-":
            pos2aa[pos] = aa
    
    return pos2aa


















