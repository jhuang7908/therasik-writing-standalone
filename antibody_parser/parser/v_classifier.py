class VRegionClassifier:

    def classify(self, vseq: str):
        score = 0
        detail = {}

        # Feature 1: FR2 hallmarks
        fr2 = vseq[38:55] if len(vseq) > 55 else ""
        hallmark = sum(fr2.count(x) for x in ["E", "Q", "R", "G"])
        score += hallmark * 0.5
        detail["fr2_hallmark_count"] = hallmark

        # Feature 2: FR4 motif
        fr4 = vseq[-12:]
        fr4_motif = fr4.startswith("WG")
        if fr4_motif:
            score += 1.0
        detail["fr4_motif"] = fr4_motif

        # Feature 3: CDR3 
        if "C" in vseq:
            c1 = vseq.find("C")
            c2 = vseq.rfind("C")
            cdr3_len = c2 - c1 - 1
        else:
            cdr3_len = 10
        detail["cdr3_length"] = cdr3_len
        if cdr3_len > 16:
            score += 1.0

        is_vhh = score >= 2.5
        return {
            "is_vhh": is_vhh,
            "score": score,
            "features": detail
        }





















