class LinkerTagDetector:

    LINKERS = ["GGGGS", "GGGS", "GSGSG", "SSSS"]
    TAGS = ["HHHHHH", "FLAG", "STREP"]

    def detect(self, seq, v_region, fc_info):
        out = []

        if fc_info["present"]:
            # Fc
            fc_start = v_region["end"]
        else:
            fc_start = len(seq)

        # search linkers
        for lk in self.LINKERS:
            p = seq.find(lk)
            if p != -1:
                out.append({"type": "linker", "start": p, "sequence": lk})

        for t in self.TAGS:
            p = seq.find(t)
            if p != -1:
                out.append({"type": "tag", "start": p, "sequence": t})

        return out





















