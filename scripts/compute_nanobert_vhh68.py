#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/compute_nanobert_vhh68.py
===================================
Computes nanoBERT log-likelihood scores for the 68 VHH sequences.
Uses NaturalAntibody/nanoBERT from Hugging Face.
"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM
from pathlib import Path
from tqdm import tqdm

SUITE_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "vhh_structural_union_index.json"
OUT_PATH = SUITE_ROOT / "data" / "vhh_structural_union" / "nanobert_scores_vhh68.json"

MODEL_NAME = "NaturalAntibody/nanoBERT"

def compute_pll(sequence, model, tokenizer, device):
    """Compute Pseudo-Log-Likelihood (PLL) for a sequence."""
    # nanoBERT uses space-separated amino acids
    spaced_seq = " ".join(list(sequence))
    inputs = tokenizer(spaced_seq, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits  # [1, seq_len, vocab_size]
        
    # Get log-probabilities
    log_probs = torch.log_softmax(logits, dim=-1)
    
    # Extract log-probs for the actual residues
    input_ids = inputs["input_ids"][0]
    # Skip [CLS] and [SEP]
    actual_log_probs = []
    for i in range(1, len(input_ids) - 1):
        res_id = input_ids[i]
        lp = log_probs[0, i, res_id].item()
        actual_log_probs.append(lp)
        
    pll = sum(actual_log_probs) / len(actual_log_probs) if actual_log_probs else 0.0
    return round(pll, 4)

def main():
    if not INDEX_PATH.exists():
        print(f"Error: {INDEX_PATH} not found.")
        return

    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    all_vhh = data.get("clinical_vhh", []) + data.get("database_b", [])
    
    print(f"Loading model {MODEL_NAME}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME).to(device)
    model.eval()
    
    print(f"Computing nanoBERT scores for {len(all_vhh)} sequences on {device}...")
    results = {}
    for item in tqdm(all_vhh):
        vhh_id = item["id"]
        seq = item["sequence"]
        score = compute_pll(seq, model, tokenizer, device)
        results[vhh_id] = score
        
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Done! Results saved to {OUT_PATH}")

if __name__ == "__main__":
    main()
