#!/usr/bin/env python3
"""
PDBHSA VHH
"""
import requests
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

# HSAPDB ID
HSA_RELATED_PDB_IDS = [
    "8Z8V",  # ALB8(VHH) - ！
    "8Y9S",  # nanobody MY6321 bound to HSA
    "8Y9U",  # nanobody MY6323 bound to HSA
    "8Y9T",  # nanobody MY6322 bound to HSA
    "8C7J",  # serum albumin binding knob domain
    "8C7V",  # serum albumin binding knob domain
    "5FUZ",  # half-life extension Fab
    "5FUO",  # half-life extension Fab
    "1YSX",  # domain 3 from HSA complexed
]

class HSAVHHExtractor:
    """PDBHSA VHH"""
    
    def __init__(self, output_dir: str = "projects/anti_HSA_VHH/input"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://data.rcsb.org/rest/v1/core"
        
    def extract_from_pdb_fasta(self, pdb_id: str) -> Optional[Dict]:
        """PDB FASTA"""
        print(f"\n {pdb_id}...")
        
        try:
            # entry
            entry_url = f"{self.base_url}/entry/{pdb_id.upper()}"
            entry_response = requests.get(entry_url, timeout=15)
            
            if entry_response.status_code != 200:
                print(f"  ❌ entry")
                return None
            
            entry_data = entry_response.json()
            title = entry_data.get("struct", {}).get("title", "")
            
            # PDBFASTA
            fasta_url = f"https://www.rcsb.org/fasta/entry/{pdb_id.upper()}"
            fasta_response = requests.get(fasta_url, timeout=15)
            
            if fasta_response.status_code == 200:
                fasta_content = fasta_response.text
                return self._parse_fasta_content(fasta_content, pdb_id, title)
            
            return None
        except Exception as e:
            print(f"  ❌ : {e}")
            return None
    
    def _parse_fasta_content(self, fasta_content: str, pdb_id: str, title: str) -> Optional[Dict]:
        """FASTA，VHH"""
        lines = fasta_content.strip().split('\n')
        current_header = ""
        current_seq = ""
        candidates = []
        
        for line in lines:
            if line.startswith('>'):
                # 
                if current_header and current_seq:
                    seq_info = self._analyze_sequence(current_seq, current_header, pdb_id, title)
                    if seq_info:
                        candidates.append(seq_info)
                
                current_header = line[1:].strip()
                current_seq = ""
            else:
                current_seq += line.strip()
        
        # 
        if current_header and current_seq:
            seq_info = self._analyze_sequence(current_seq, current_header, pdb_id, title)
            if seq_info:
                candidates.append(seq_info)
        
        if candidates:
            # VHH（，HSA）
            candidates.sort(key=lambda x: x["length"])
            for candidate in candidates:
                # HSA（，585 aa）
                if candidate["length"] < 200:
                    print(f"  ✓ VHH: {candidate['length']} aa - {candidate.get('description', '')[:50]}")
                    return candidate
        
        print(f"  ⚠️  VHH")
        return None
    
    def _analyze_sequence(self, sequence: str, header: str, pdb_id: str, title: str) -> Optional[Dict]:
        """VHH"""
        sequence = sequence.upper().replace('X', '').replace('*', '')
        
        # VHH
        if 90 <= len(sequence) <= 160:
            # VHH
            vhh_starts = ('QVQL', 'EVQL', 'DVQL', 'QVQ', 'EVQ', 'DVQ', 'QVL')
            if sequence.startswith(vhh_starts):
                # HSA（HSA）
                if 'albumin' not in header.lower() and len(sequence) < 200:
                    return {
                        "pdb_id": pdb_id.upper(),
                        "sequence": sequence,
                        "length": len(sequence),
                        "title": title,
                        "description": header,
                        "url": f"https://www.rcsb.org/structure/{pdb_id.upper()}"
                    }
        
        return None
    
    def extract_from_pdb(self, pdb_id: str) -> Optional[Dict]:
        """PDB IDVHH（FASTA）"""
        return self.extract_from_pdb_fasta(pdb_id)
    
    def extract_all(self, pdb_ids: List[str]) -> List[Dict]:
        """PDB ID"""
        print("=" * 60)
        print("PDBHSA VHH")
        print("=" * 60)
        
        all_sequences = []
        
        for pdb_id in pdb_ids:
            seq_data = self.extract_from_pdb(pdb_id)
            if seq_data:
                all_sequences.append(seq_data)
        
        return all_sequences
    
    def save_sequences(self, sequences: List[Dict]):
        """"""
        if not sequences:
            print("\n⚠️  ")
            return
        
        # FASTA
        fasta_file = self.output_dir / "anti_hsa_vhh_from_pdb.fasta"
        with open(fasta_file, 'w', encoding='utf-8') as f:
            for i, seq_data in enumerate(sequences, 1):
                pdb_id = seq_data["pdb_id"]
                entity_id = seq_data.get("entity_id", "1")
                title = seq_data.get("title", "")[:50]
                
                header = f">Anti_HSA_VHH_{pdb_id}_E{entity_id}|source:PDB|{title}"
                f.write(f"{header}\n")
                f.write(f"{seq_data['sequence']}\n")
        
        print(f"\n✅  {len(sequences)} : {fasta_file}")
        
        # JSON
        json_file = self.output_dir / "anti_hsa_vhh_from_pdb.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "description": "Anti-HSA VHH sequences extracted from PDB",
                    "total_sequences": len(sequences),
                    "warning": "⚠️ "
                },
                "sequences": sequences
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ : {json_file}")
        
        return fasta_file, json_file


def main():
    extractor = HSAVHHExtractor()
    
    # 
    sequences = extractor.extract_all(HSA_RELATED_PDB_IDS)
    
    if sequences:
        # 
        extractor.save_sequences(sequences)
        
        print("\n" + "=" * 60)
        print("！")
        print("=" * 60)
        print(f" {len(sequences)} HSA VHH")
        print("\n:")
        print("1. ⚠️  （ALB8）")
        print("2. ⚠️  FTO")
        print("3. ✅ ")
        print("\n:")
        print("1. ")
        print("2. ")
        print("3. :")
        print("   python app/run_vhh_cli.py --fasta projects/anti_HSA_VHH/input/anti_hsa_vhh_from_pdb.fasta --source alpaca")
    else:
        print("\n⚠️  ，PDB")


if __name__ == '__main__':
    main()
