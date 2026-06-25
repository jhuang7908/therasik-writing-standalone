class VRegionClassifier:

    def classify(self, vseq: str):
        score = 0
        detail = {}

        # Feature 1: FR2 hallmarks (VHH typically has more E/Q/R/G in FR2)
        fr2 = vseq[38:55] if len(vseq) > 55 else ""
        hallmark = sum(fr2.count(x) for x in ["E", "Q", "R", "G"])
        # VHH typically has 8+ hallmarks, VH has fewer
        if hallmark >= 8:
            score += 1.0
        elif hallmark >= 6:
            score += 0.5
        detail["fr2_hallmark_count"] = hallmark

        # Feature 2: FR4 motif (VHH typically ends with WG)
        fr4 = vseq[-12:] if len(vseq) >= 12 else vseq
        fr4_motif = fr4.startswith("WG") or "WGQ" in fr4
        if fr4_motif:
            score += 1.0
        detail["fr4_motif"] = fr4_motif

        # Feature 3: CDR3  (VHH typically has longer CDR3)
        if "C" in vseq:
            c1 = vseq.find("C")
            c2 = vseq.rfind("C")
            cdr3_len = c2 - c1 - 1
        else:
            cdr3_len = 10
        detail["cdr3_length"] = cdr3_len
        # VHH typically has CDR3 > 16, VH typically < 16
        if cdr3_len > 16:
            score += 1.0
        elif cdr3_len < 10:
            score -= 0.5  # Penalize very short CDR3 (more likely VH)

        is_vhh = score >= 2.5
        # Normalize confidence: score ranges from 0 to ~4, map to 0-1
        confidence = min(1.0, score / 4.0) if is_vhh else min(1.0, (2.5 - score) / 2.5)
        return {
            "is_vhh": is_vhh,
            "score": score,
            "confidence": confidence,
            "features": detail
        }


# Alias for backward compatibility
VClassifier = VRegionClassifier

