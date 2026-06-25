#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek 
 DeepSeek API 
"""

import os
import time
from typing import Dict, Any
from datetime import datetime
from openai import OpenAI


class AntibodyDeepSeekClient:
    """ DeepSeek """
    
    def __init__(self, api_key: str = None):
        """
        
        
        Args:
            api_key: API，None
        """
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError(" DEEPSEEK_API_KEY  API ")
        
        #  DeepSeek 
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        self.model = "deepseek-chat"
        self.max_retries = 3
        self.retry_delay = 1.0
    
    def analyze_vhh_sequence(self, sequence: str, analysis_focus: str = "comprehensive") -> Dict[str, Any]:
        """ VHH """
        system_prompt = """，VHH、。
。"""
        
        focus_prompts = {
            "structure": "：1) 2)VHH 3)",
            "function": "：1) 2) 3)CDR",
            "developability": "：1) 2) 3)",
            "comprehensive": "：1) 2) 3) 4)"
        }
        
        prompt = f"""VHH：

: {sequence}

{focus_prompts.get(analysis_focus, focus_prompts['comprehensive'])}"""
        
        try:
            response = self._safe_api_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            return {
                'success': True,
                'timestamp': datetime.now.isoformat,
                'sequence': sequence,
                'analysis_focus': analysis_focus,
                'analysis': response
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def suggest_affinity_mutations(self, wild_type_seq: str, target_epitope: str) -> Dict[str, Any]:
        """"""
        prompt = f"""，VHH：

: {wild_type_seq}
: {target_epitope}

：
1. 
2. 
3. 
4. """
        
        try:
            response = self._safe_api_call(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.4
            )
            
            return {
                'success': True,
                'wild_type': wild_type_seq,
                'target_epitope': target_epitope,
                'suggestions': response
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _safe_api_call(self, **kwargs) -> str:
        """ API ，"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    **kwargs
                )
                return response.choices[0].message.content.strip
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise e
    
    def validate_api_key(self) -> Dict[str, Any]:
        """ API """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "，''"}],
                max_tokens=10
            )
            return {
                'valid': True,
                'message': response.choices[0].message.content.strip
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }


# 
if __name__ == "__main__":
    import sys
    
    print("🧬 DeepSeek ")
    print("=" * 50)
    
    #  API 
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌  DEEPSEEK_API_KEY ")
        print("💡  PowerShell : $env:DEEPSEEK_API_KEY = 'API'")
        sys.exit(1)
    
    try:
        # 
        client = AntibodyDeepSeekClient(api_key)
        
        #  API
        print("🔍  API ...")
        validation = client.validate_api_key
        if validation['valid']:
            print(f"✅ API : {validation['message']}")
        else:
            print(f"❌ API : {validation['error']}")
            sys.exit(1)
        
        # 
        test_sequence = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSFGMSWVRQAPGKGLEWVSYISQGSDIYYADSVKGRFTISRDNAKTTLYLQMNSLRPEDTAVYYCAA"
        print(f"""
🧪 :
: {test_sequence[:50]}...""")
        
        result = client.analyze_vhh_sequence(test_sequence, "comprehensive")
        if result['success']:
            print("✅ !")
            print(f": {result['analysis'][:200]}...")
        else:
            print(f"❌ : {result['error']}")
        
        print("\n🎉 DeepSeek !")
        
    except Exception as e:
        print(f"❌ : {e}")
        sys.exit(1)
