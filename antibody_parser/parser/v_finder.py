from anarci import run_anarci
import re


class VRegionFinder:

    FR1_PATTERNS = [
        r"QVQL", r"EVQL", r"QAVV", r"DIQL", r"DLQL", r"SVQL"
    ]

    def find_v_region(self, seq: str):
        """V：HMM → motif → anchor → fallback"""
        
        # Strategy 1: ANARCI HMM
        v = self._try_anarci(seq)
        if v["found"]:
            return v
        
        # Strategy 2: FR1 motif
        v = self._try_fr1_motif(seq)
        if v["found"]:
            return v
        
        # Strategy 3: Anchor residues (C23/W41/C104)
        v = self._try_anchor_method(seq)
        if v["found"]:
            return v

        # Strategy 4: Sliding fuzzy window
        return self._fallback_window(seq)

    def _try_anarci(self, seq):
        try:
            res = run_anarci([("q", seq)], scheme="imgt", output=False)
            numbering = res[0][0]

            if numbering is None:
                return {"found": False}

            start = numbering[0][0][0]
            end = numbering[-1][0][0]
            return {
                "found": True,
                "start": start - 1,
                "end": end,
                "sequence": seq[start-1:end]
            }
        except:
            return {"found": False}

    def _try_fr1_motif(self, seq):
        for pat in self.FR1_PATTERNS:
            m = re.search(pat, seq)
            if m:
                start = m.start
                end = min(start + 130, len(seq))
                return {
                    "found": True,
                    "start": start,
                    "end": end,
                    "sequence": seq[start:end]
                }
        return {"found": False}

    def _try_anchor_method(self, seq):
        cpos = [i for i, c in enumerate(seq) if c == "C"]
        for c23 in cpos:
            # look for W downstream
            wpos = [w for w in range(c23+10, c23+40) if w < len(seq) and seq[w] == "W"]
            if wpos:
                w41 = wpos[0]
                start = max(0, c23 - 22)
                end = min(len(seq), w41 + 80)
                return {
                    "found": True,
                    "start": start,
                    "end": end,
                    "sequence": seq[start:end]
                }
        return {"found": False}

    def _fallback_window(self, seq):
        best = (0, 0, 0)  # score, start, end
        for i in range(len(seq)-80):
            window = seq[i:i+120]
            score = window.count("C") + window.count("W")
            if score > best[0]:
                best = (score, i, i+120)
        return {
            "found": True,
            "start": best[1],
            "end": best[2],
            "sequence": seq[best[1]:best[2]],
            "warning": "fallback window method used"
        }





















