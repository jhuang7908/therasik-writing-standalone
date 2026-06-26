#!/usr/bin/env python3
"""
HSAVHH
：PDB、、
"""
import json
import re
import os
from pathlib import Path
from typing import List, Dict, Optional
import requests
from urllib.parse import quote

class AntiHSASequenceExtractor:
    """HSA VHH"""
    
    def __init__(self, output_dir: str = "projects/anti_HSA_VHH/input"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sequences = []
        
    def extract_from_pdb(self, pdb_id: str) -> Optional[Dict]:
        """PDB ID"""
        print(f"\nPDB: {pdb_id}")
        
        # PDB API endpoint
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id.upper()}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                entry_data = response.json()
                
                # 
                polymer_url = f"https://data.rcsb.org/rest/v1/core/polymerentity/{pdb_id.upper()}/1"
                polymer_response = requests.get(polymer_url, timeout=10)
                
                if polymer_response.status_code == 200:
                    polymer_data = polymer_response.json()
                    
                    # 
                    sequence = polymer_data.get("entity_poly", {}).get("pdbx_seq_one_letter_code_can", "")
                    if sequence:
                        # 
                        sequence = re.sub(r'[^A-Z]', '', sequence.upper())
                        
                        return {
                            "source": "PDB",
                            "pdb_id": pdb_id.upper(),
                            "sequence": sequence,
                            "name": f"Anti_HSA_VHH_{pdb_id.upper()}",
                            "description": f"Extracted from PDB {pdb_id.upper()}",
                            "url": f"https://www.rcsb.org/structure/{pdb_id.upper()}"
                        }
        except Exception as e:
            print(f"  : {e}")
        
        return None
    
    def extract_from_manual_input(self, sequence: str, name: str = "Anti_HSA_VHH", 
                                  description: str = "", source: str = "Manual") -> Dict:
        """"""
        # 
        sequence = re.sub(r'[^A-Z]', '', sequence.upper())
        
        return {
            "source": source,
            "sequence": sequence,
            "name": name,
            "description": description,
            "length": len(sequence)
        }
    
    def add_known_reference_sequences(self):
        """（，）"""
        print("\n（）...")
        
        # ：，
        known_sequences = [
            {
                "name": "ALB1_Reference",
                "description": "ALB1（）",
                "source": "Literature_Reference",
                "note": "⚠️ ，",
                "sequence": ""  # 
            }
        ]
        
        print("  ：PDB")
        return known_sequences
    
    def save_to_fasta(self, sequences: List[Dict], filename: str = "anti_hsa_vhh_sequences.fasta"):
        """FASTA"""
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for seq_data in sequences:
                if 'sequence' in seq_data and seq_data['sequence']:
                    name = seq_data.get('name', 'Unknown')
                    desc = seq_data.get('description', '')
                    source = seq_data.get('source', 'Unknown')
                    
                    header = f">{name}|source:{source}"
                    if desc:
                        header += f"|{desc}"
                    
                    f.write(f"{header}\n")
                    f.write(f"{seq_data['sequence']}\n")
        
        print(f"\n✅ : {output_file}")
        return output_file
    
    def save_to_json(self, sequences: List[Dict], filename: str = "anti_hsa_vhh_sequences.json"):
        """JSON"""
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "description": "Anti-HSA VHH sequences from various sources",
                    "extraction_date": str(Path.cwd()),
                    "total_sequences": len(sequences),
                    "warning": "⚠️ "
                },
                "sequences": sequences
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ : {output_file}")
        return output_file
    
    def interactive_extract(self):
        """"""
        print("=" * 60)
        print("HSA VHH")
        print("=" * 60)
        
        sequences = []
        
        while True:
            print("\n:")
            print("1. PDB ID")
            print("2. ")
            print("3. （FASTA）")
            print("4. ")
            
            choice = input("\n (1-4): ").strip()
            
            if choice == '1':
                pdb_id = input("PDB ID (: 1BJQ): ").strip()
                if pdb_id:
                    seq_data = self.extract_from_pdb(pdb_id)
                    if seq_data:
                        sequences.append(seq_data)
                        print(f"✅ : {seq_data['name']}")
                    else:
                        print("❌ ，PDB ID")
            
            elif choice == '2':
                print("\n（，）:")
                lines = []
                while True:
                    line = input()
                    if not line.strip():
                        break
                    lines.append(line.strip())
                
                sequence = ''.join(lines)
                if sequence:
                    name = input(" (: Anti_HSA_VHH_Manual): ").strip() or "Anti_HSA_VHH_Manual"
                    desc = input(" (): ").strip()
                    seq_data = self.extract_from_manual_input(sequence, name, desc)
                    sequences.append(seq_data)
                    print(f"✅ : {name}")
            
            elif choice == '3':
                filepath = input("FASTA: ").strip()
                if os.path.exists(filepath):
                    sequences.extend(self._parse_fasta(filepath))
                    print(f"✅  {len(sequences)} ")
                else:
                    print("❌ ")
            
            elif choice == '4':
                break
            
            else:
                print("❌ ")
        
        # 
        if sequences:
            self.save_to_fasta(sequences)
            self.save_to_json(sequences)
            print(f"\n✅  {len(sequences)} ")
        else:
            print("\n⚠️  ")
        
        return sequences
    
    def _parse_fasta(self, filepath: str) -> List[Dict]:
        """FASTA"""
        sequences = []
        current_name = ""
        current_seq = ""
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if current_name and current_seq:
                        sequences.append(self.extract_from_manual_input(
                            current_seq, current_name, "", "FASTA_File"
                        ))
                    current_name = line[1:].split()[0]
                    current_seq = ""
                else:
                    current_seq += line
        
        if current_name and current_seq:
            sequences.append(self.extract_from_manual_input(
                current_seq, current_name, "", "FASTA_File"
            ))
        
        return sequences


def main():
    """"""
    extractor = AntiHSASequenceExtractor()
    
    # 
    sequences = extractor.interactive_extract()
    
    print("\n" + "=" * 60)
    print(":")
    print("=" * 60)
    print("1. ")
    print("2. （FTO）")
    print("3. :")
    print("   python app/run_vhh_cli.py --fasta projects/anti_HSA_VHH/input/anti_hsa_vhh_sequences.fasta --source alpaca")


if __name__ == '__main__':
    main()
