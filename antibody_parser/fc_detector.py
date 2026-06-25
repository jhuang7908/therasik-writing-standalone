from Bio import pairwise2
import json
import os


class FcDetector:

    def __init__(self):
        # 
        fc_templates_file = os.path.join(os.path.dirname(__file__), "fc_templates.json")
        
        if os.path.exists(fc_templates_file):
            with open(fc_templates_file, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        else:
            #  data 
            data_dir = os.path.join(os.path.dirname(__file__), "data")
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

    def detect(self, seq):
        """
        Detect Fc region in sequence (auto-detects V region end).
        This is a convenience method that tries to find V region end automatically.
        """
        # Try to find V region end by looking for common V region patterns
        # This is a simplified approach - in practice, you might want to use VRegionFinder
        v_end = len(seq)
        
        # Look for common V region termination patterns
        # FR4 typically ends around position 110-130 in V region
        # Look for common patterns that indicate end of V region
        for i in range(len(seq) - 50, max(0, len(seq) - 300), -1):
            # Check if this looks like end of V region (WG motif, etc.)
            if i < len(seq) - 10:
                window = seq[i:i+20]
                if "WG" in window or "WGQ" in window:
                    v_end = i + 20
                    break
        
        # If no clear pattern, assume V region is first 120-130 AA
        if v_end == len(seq):
            v_end = min(130, len(seq) - 50)
        
        return self.detect_fc(seq, v_end)

