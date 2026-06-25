import re

try:
    from anarci import run_anarci
    ANARCI_AVAILABLE = True
except ImportError:
    ANARCI_AVAILABLE = False


class VRegionFinder:

    FR1_PATTERNS = [
        r"QVQL", r"EVQL", r"QAVV", r"DIQL", r"DLQL", r"SVQL"
    ]

    def find_v_region(self, seq: str):
        """V：ANARCI HMM → fallback"""
        
        anarci_result = self._try_anarci(seq)

        if anarci_result["found"]:
            numbering = anarci_result["numbering"]
            start = numbering[0][0][0] - 1
            end = numbering[-1][0][0]
            return {
                "found": True,
                "sequence": seq[start:end],
                "start": start,
                "end": end,
                "confidence": 0.95,
                "method": anarci_result["method"]
            }

        # fallback
        fallback = self._fallback_window(seq)
        fallback["fallback_reason"] = anarci_result["method"]
        return fallback

    def _try_anarci(self, seq):
        if not ANARCI_AVAILABLE:
            return {"found": False, "method": "anarci_unavailable"}

        try:
            res = run_anarci([("seq", seq)], scheme='imgt')
            numbering = res[0][0]
            if numbering:
                return {
                    "found": True,
                    "numbering": numbering,
                    "method": "anarci"
                }
            return {"found": False, "method": "anarci_no_numbering"}

        except Exception:
            return {"found": False, "method": "anarci_failed"}

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
                    "sequence": seq[start:end],
                    "confidence": 0.7,  # Medium-high confidence for FR1 motif
                    "method": "fr1_motif"
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
                    "sequence": seq[start:end],
                    "confidence": 0.6,  # Medium confidence for anchor method
                    "method": "anchor"
                }
        return {"found": False}

    def _fallback_window(self, seq):
        best_score = -1
        best_window = None

        win_size = min(120, max(30, len(seq)))
        search_range = max(1, len(seq) - win_size + 1)

        for i in range(search_range):
            window = seq[i:i+win_size]
            score = window.count("C") + window.count("W")
            if score > best_score:
                best_score = score
                best_window = (i, i+win_size)

        start, end = best_window

        return {
            "found": True,
            "sequence": seq[start:end],
            "start": start,
            "end": end,
            "confidence": 0.40,
            "method": "fallback_window"
        }

