import json
path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\denovo_HER2_VGRW_SR_R2\phase1_generation\t1_ablang_scores.jsonl'
scores = []
with open(path) as f:
    for line in f:
        if line.strip():
            scores.append(json.loads(line.strip()))

vals = [r['ablang_mean_logp'] for r in scores]
vals.sort(reverse=True)
wt_score = scores[0].get('wt_score', 'N/A')
threshold = wt_score * 0.50 if isinstance(wt_score, (int, float)) else 'N/A'
print(f"WT score: {wt_score}")
print(f"Threshold (50%): {threshold}")
print(f"Top 5: {vals[:5]}")
print(f"Bottom 5: {vals[-5:]}")
print(f"Median: {vals[len(vals)//2]}")
print(f"All negative? {all(v < 0 for v in vals)}")
reasons = {}
for r in scores:
    reason = r['reason'][:30]
    reasons[reason] = reasons.get(reason, 0) + 1
print(f"Reasons: {reasons}")
print(f"Sample record: {scores[1]}")
