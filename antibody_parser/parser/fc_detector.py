from Bio import pairwise2
import json
import os


class FcDetector:

    def __init__(self):
        path = os.path.join("data", "fc_templates.json")
        # 
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        fc_templates_file = os.path.join(data_dir, "fc_templates.json")
        
        if os.path.exists(fc_templates_file):
            with open(fc_templates_file, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        else:
            # 
            self.templates = {
                "human_igg1": ["ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSCDKTHTCPPCPAPELLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVKFNWYVDGVEVHNAKTKPREEQYNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKALPAPIEKTISKAKGQPREPQVYTLPPSRDELTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK"]
            }

    def detect_fc(self, seq, v_end):
        tail = seq[v_end:]

        if len(tail) < 50:
            return {"present": False}

        best = ("unknown", 0)

        for species, fc_seqs in self.templates.items:
            for fc in fc_seqs:
                aln = pairwise2.align.localms(tail, fc, 2, -1, -5, -1)
                if aln:
                    score = aln[0].score / len(fc)
                    if score > best[1]:
                        best = (species, score)

        return {
            "present": best[1] > 0.3,
            "species": best[0],
            "confidence": best[1]
        }





















