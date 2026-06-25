import re
import os

html_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'

def check_integrity:
    if not os.path.exists(html_path):
        print(f"File not found: {html_path}")
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read

    print("\n--- Therasik ADC Database Integrity Report ---")

    # 1. Structural Check: Tab Panels
    panels = ['panel-programs', 'panel-antigens', 'panel-payloads', 'panel-linkers', 'panel-conjugation', 'panel-experiments']
    all_panels_ok = True
    for p in panels:
        if f'id="{p}"' not in html:
            print(f"[FAIL] Panel '{p}' is missing from HTML.")
            all_panels_ok = False
            continue
        
        # Extract panel content to check div balance
        p_start = html.find(f'id="{p}"')
        # Find the start of the next panel or the end of the main container
        next_p = html.find('class="tab-panel"', p_start + 10)
        if next_p == -1:
            next_p = html.find('</main>', p_start)
        if next_p == -1:
            next_p = html.find('<script>', p_start)
            
        panel_content = html[p_start:next_p]
        open_divs = panel_content.count('<div')
        close_divs = panel_content.count('</div')
        
        if open_divs > close_divs:
            print(f"[FAIL] Panel '{p}' has unclosed divs (Open: {open_divs}, Close: {close_divs}). This will cause nesting issues.")
            all_panels_ok = False
        else:
            print(f"[PASS] Panel '{p}' structure is balanced.")

    # 2. Corruption Check: 'exp'
    corruptions = ['exp', 'exped', 'Exp']
    found_corruption = False
    for c in corruptions:
        count = html.count(c)
        if count > 0:
            print(f"[FAIL] Found {count} instances of corrupted string '{c}'.")
            found_corruption = True
    if not found_corruption:
        print("[PASS] No 'exp' corruption detected.")

    # 3. Data Quality Check: Question Marks in Antigens
    antigen_start = html.find('id="panel-antigens"')
    payload_start = html.find('id="panel-payloads"')
    if antigen_start != -1 and payload_start != -1:
        antigen_html = html[antigen_start:payload_start]
        q_marks = re.findall(r': \?|: \?|: \?', antigen_html)
        if q_marks:
            print(f"[WARN] Found {len(q_marks)} remaining '?' in antigen brief summaries.")
        else:
            print("[PASS] All antigen brief summaries have been populated with data/inferences.")

    # 4. Feature Check: Legend
    if '' in html:
        print("[PASS] Evidence Attribution Legend is present.")
    else:
        print("[FAIL] Evidence Attribution Legend is missing.")

    # 5. Feature Check: Design Logic
    if ' (Design Logic)' in html:
        print("[PASS] Design Logic sections are present.")
    else:
        print("[FAIL] Design Logic sections are missing.")

    print("-----------------------------------------------\n")

if __name__ == "__main__":
    check_integrity
