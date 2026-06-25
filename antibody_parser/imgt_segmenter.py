class IMGT_Segmenter:

    def segment(self, vseq, is_vhh=False):
        L = len(vseq)
        def safe(a,b): return vseq[a:b] if a < L else ""

        seg = {
            "FR1":  safe(0, 26),
            "CDR1": safe(26, 38),
            "FR2":  safe(38, 55),
            "CDR2": safe(55, 65),
            "FR3":  safe(65, 104),
        }

        # CDR3: from 104 until FR4
        if is_vhh:
            # find WGQG
            idx = vseq.find("WG")
            if idx != -1:
                seg["CDR3"] = vseq[104:idx]
                seg["FR4"] = vseq[idx:]
            else:
                seg["CDR3"] = vseq[104:]
                seg["FR4"] = ""
        else:
            seg["CDR3"] = safe(104, 117)
            seg["FR4"] = safe(117, 128)

        return seg


