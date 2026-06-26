#!/usr/bin/env python3
"""
PDB - HSAVHH
"""
import requests
import json
from typing import List, Dict, Optional
import time

class EnhancedPDBSearcher:
    """PDB"""
    
    def __init__(self):
        self.base_url = "https://search.rcsb.org/rcsbsearch/v2/query"
        self.structure_url = "https://data.rcsb.org/rest/v1/core"
        
    def search_nanobody_albumin(self, max_results: int = 50) -> List[str]:
        """nanobodyalbumin"""
        print("=" * 60)
        print("PDBHSA VHH")
        print("=" * 60)
        
        all_results = []
        
        # 1: albumin + nanobody
        print("\n1:  'albumin nanobody'...")
        results1 = self._search_albumin_nanobody(max_results)
        all_results.extend(results1)
        
        # 2: HSA + VHH
        print("\n2:  'HSA VHH'...")
        results2 = self._search_hsa_vhh(max_results)
        all_results.extend(results2)
        
        # 3: serum albumin + single domain
        print("\n3:  'serum albumin single domain'...")
        results3 = self._search_serum_albumin_sdab(max_results)
        all_results.extend(results3)
        
        # 4: PDB ID（）
        print("\n4: PDB ID...")
        known_pdb_ids = ["1BJQ", "1U8K", "3KDM", "4KJJ", "5D6D", "6APQ", "7K8M"]
        results4 = self._check_known_pdb_ids(known_pdb_ids)
        all_results.extend(results4)
        
        # 
        unique_results = list(set(all_results))
        
        print(f"\n✅  {len(unique_results)} ")
        return unique_results[:max_results]
    
    def _search_albumin_nanobody(self, max_results: int) -> List[str]:
        """albuminnanobody"""
        query = {
            "query": {
                "type": "group",
                "logical_operator": "and",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_words",
                            "value": "albumin"
                        }
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_words",
                            "value": "nanobody"
                        }
                    }
                ]
            },
            "return_type": "entry",
            "request_options": {
                "results_verbosity": "compact",
                "paginate": {"start": 0, "rows": max_results}
            }
        }
        return self._execute_query(query)
    
    def _search_hsa_vhh(self, max_results: int) -> List[str]:
        """HSAVHH"""
        query = {
            "query": {
                "type": "group",
                "logical_operator": "and",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_words",
                            "value": "HSA"
                        }
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_words",
                            "value": "VHH"
                        }
                    }
                ]
            },
            "return_type": "entry",
            "request_options": {
                "results_verbosity": "compact",
                "paginate": {"start": 0, "rows": max_results}
            }
        }
        return self._execute_query(query)
    
    def _search_serum_albumin_sdab(self, max_results: int) -> List[str]:
        """serum albuminsingle domain antibody"""
        query = {
            "query": {
                "type": "group",
                "logical_operator": "and",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_phrase",
                            "value": "serum albumin"
                        }
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_words",
                            "value": "single domain"
                        }
                    }
                ]
            },
            "return_type": "entry",
            "request_options": {
                "results_verbosity": "compact",
                "paginate": {"start": 0, "rows": max_results}
            }
        }
        return self._execute_query(query)
    
    def _check_known_pdb_ids(self, pdb_ids: List[str]) -> List[str]:
        """PDB ID"""
        valid_ids = []
        for pdb_id in pdb_ids:
            try:
                info = self.get_structure_info(pdb_id)
                if info:
                    # albumin
                    title = info.get("title", "").lower()
                    keywords = info.get("keywords", "").lower()
                    if any(kw in title or kw in keywords for kw in ["albumin", "hsa", "serum"]):
                        valid_ids.append(pdb_id)
                        print(f"  ✓ : {pdb_id}")
            except:
                pass
        return valid_ids
    
    def _execute_query(self, query: dict) -> List[str]:
        """PDB"""
        try:
            response = requests.post(self.base_url, json=query, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get("result_set", [])
        except Exception as e:
            print(f"  : {e}")
        return []
    
    def _text_search(self, term1: str, term2: str, max_results: int) -> List[str]:
        """"""
        # ：nanobody
        query = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_entry_container_identifiers.entry_id",
                    "operator": "contains_words",
                    "value": "nanobody"
                }
            },
            "return_type": "entry",
            "request_options": {
                "results_verbosity": "compact",
                "paginate": {
                    "start": 0,
                    "rows": max_results
                }
            }
        }
        
        try:
            response = requests.post(self.base_url, json=query, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get("result_set", [])
        except Exception as e:
            print(f"  : {e}")
        
        return []
    
    def _structure_type_search(self, max_results: int) -> List[str]:
        """"""
        # 
        query = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "struct.title",
                    "operator": "contains_phrase",
                    "value": "single domain antibody"
                }
            },
            "return_type": "entry",
            "request_options": {
                "results_verbosity": "compact",
                "paginate": {
                    "start": 0,
                    "rows": max_results
                }
            }
        }
        
        try:
            response = requests.post(self.base_url, json=query, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get("result_set", [])
        except Exception as e:
            print(f"  : {e}")
        
        return []
    
    def get_structure_info(self, pdb_id: str) -> Optional[Dict]:
        """"""
        try:
            # entry
            entry_url = f"{self.structure_url}/entry/{pdb_id.upper()}"
            entry_response = requests.get(entry_url, timeout=10)
            
            if entry_response.status_code == 200:
                entry_data = entry_response.json()
                
                # polymer
                polymer_url = f"{self.structure_url}/polymerentity/{pdb_id.upper()}/1"
                polymer_response = requests.get(polymer_url, timeout=10)
                
                polymer_data = {}
                sequence = ""
                if polymer_response.status_code == 200:
                    polymer_data = polymer_response.json()
                    # ，
                    sequence_raw = polymer_data.get("entity_poly", {}).get("pdbx_seq_one_letter_code_can", "")
                    if sequence_raw:
                        import re
                        sequence = re.sub(r'[^A-Z]', '', sequence_raw.upper())
                
                # （）
                keywords = entry_data.get("struct_keywords", {}).get("pdbx_keywords", "")
                
                return {
                    "pdb_id": pdb_id.upper(),
                    "title": entry_data.get("struct", {}).get("title", ""),
                    "deposition_date": entry_data.get("rcsb_accession_info", {}).get("deposit_date", ""),
                    "sequence": sequence,
                    "keywords": keywords,
                    "url": f"https://www.rcsb.org/structure/{pdb_id.upper()}"
                }
        except Exception as e:
            pass  # ，
        
        return None
    
    def filter_albumin_related(self, pdb_ids: List[str]) -> List[Dict]:
        """albumin"""
        print("\nalbumin...")
        albumin_related = []
        
        keywords = ["albumin", "HSA", "serum albumin", "ALB", "human serum"]
        
        for pdb_id in pdb_ids[:30]:  # 
            try:
                info = self.get_structure_info(pdb_id)
                if info:
                    # 
                    title_lower = info.get("title", "").lower()
                    
                    # albumin（）
                    sequence = info.get("sequence", "").upper()
                    
                    # 
                    keywords_field = info.get("keywords", "").lower()
                    if (any(keyword.lower() in title_lower for keyword in keywords) or
                        any(keyword.lower() in keywords_field for keyword in keywords)):
                        albumin_related.append(info)
                        print(f"  ✓ {pdb_id}: {info.get('title', 'N/A')[:70]}")
            except Exception as e:
                continue
            time.sleep(0.3)  # 
        
        return albumin_related
    
    def generate_search_report(self, results: List[Dict], output_file: str = "projects/anti_HSA_VHH/pdb_search_report.md"):
        """"""
        from pathlib import Path
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# PDBHSA VHH\n\n")
            f.write(f"****: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"****: {len(results)}\n\n")
            f.write("---\n\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"## {i}. {result.get('pdb_id', 'Unknown')}\n\n")
                f.write(f"- ****: {result.get('title', 'N/A')}\n")
                f.write(f"- ****: {result.get('deposition_date', 'N/A')}\n")
                f.write(f"- **PDB**: {result.get('url', 'N/A')}\n")
                if result.get('sequence'):
                    seq = result['sequence'].replace('\n', '')
                    f.write(f"- ****: {len(seq)} aa\n")
                f.write("\n")
            
            f.write("\n---\n\n")
            f.write("## \n\n")
            f.write("1. PDB\n")
            f.write("2. \n")
            f.write("3. \n")
            f.write("4. extract_anti_hsa_sequences.py\n")
        
        print(f"\n✅ : {output_path}")


def main():
    """"""
    searcher = EnhancedPDBSearcher()
    
    # 
    pdb_ids = searcher.search_nanobody_albumin(max_results=50)
    
    if pdb_ids:
        print(f"\n {len(pdb_ids)} ")
        print("\n10PDB ID:")
        for i, pdb_id in enumerate(pdb_ids[:10], 1):
            print(f"  {i}. {pdb_id}")
        
        # albumin
        albumin_related = searcher.filter_albumin_related(pdb_ids)
        
        if albumin_related:
            # 
            searcher.generate_search_report(albumin_related)
            
            print("\n" + "=" * 60)
            print(":")
            print("=" * 60)
            print("1. : projects/anti_HSA_VHH/pdb_search_report.md")
            print("2. extract_anti_hsa_sequences.py")
            print("3. ")
        else:
            print("\n⚠️  albumin")
            print("\n...")
            
            # 20
            all_structures = []
            for pdb_id in pdb_ids[:20]:
                info = searcher.get_structure_info(pdb_id)
                if info:
                    all_structures.append(info)
                time.sleep(0.3)
            
            if all_structures:
                searcher.generate_search_report(all_structures, 
                    "projects/anti_HSA_VHH/pdb_all_candidates_report.md")
                print(f"✅  {len(all_structures)} ")
            
            print("\n:")
            print("1. : projects/anti_HSA_VHH/pdb_all_candidates_report.md")
            print("2. PDB")
            print("3. : 'albumin'  'HSA'  https://www.rcsb.org/")
            print("4. ")
    else:
        print("\n⚠️  ")
        print("\n:")
        print("1.  https://www.rcsb.org/")
        print("2. : 'nanobody albumin'  'VHH HSA'")
        print("3. ")


if __name__ == '__main__':
    main()
