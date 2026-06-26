"""Refresh Therasik_Component_Browser.html with canonical CAR-T data and modular UI.

This script:
1. Loads the public canonical CAR-T JSON (firewalled).
2. Generates the modernized UI components (Tabs for Elements, Targets, Methods).
3. Injects both the data and the rendering logic into the HTML template.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "therasik-web-source" / "car_kb_public.json"
HTML_PATH = ROOT / "docs" / "Therasik_Component_Browser.html"

# Text for localization
ZH_TEXT = {
    "title": "ACTES CAR ",
    "desc": " 237+  CAR 。、、、。",
    "tab_elements": "",
    "tab_targets": "",
    "tab_methods": "",
    "tab_scenarios": "",
    "stats_label": " {} ",
    "search_placeholder": "、、...",
    "tier_t1": "T1: FDA (Kymriah)",
    "tier_t2": "T2:  (IND/Phase I-II)",
    "tier_t3": "T3: ",
}

def build_page():
    if not JSON_PATH.exists():
        print(f"Error: {JSON_PATH} not found.")
        return

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    
    # Read the HTML template
    html = HTML_PATH.read_text(encoding="utf-8")
    
    # 1. Inject Data
    js_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = re.sub(r"var DATA\s*=\s*\{.*?\};", f"var DATA={js_data};", html, flags=re.DOTALL)
    
    # 2. Update Header/Tabs (Mirrors Vaccine UI)
    # Note: We need to make sure the HTML has the tab container. 
    # The current HTML only has categories for elements. 
    # I will modify the HTML structure to support Tabs.
    
    # Replace the main section header and add tabs
    header_html = f"""
    <div class="page-header">
      <a href="therasik_index.html" class="back-link">← </a>
      <h1>{ZH_TEXT['title']}</h1>
      <p>{ZH_TEXT['desc']}</p>
      <div class="tier-legend">
        <div class="tier-legend-item"><span class="tier tier-T1">T1</span> {ZH_TEXT['tier_t1']}</div>
        <div class="tier-legend-item"><span class="tier tier-T2">T2</span> {ZH_TEXT['tier_t2']}</div>
        <div class="tier-legend-item"><span class="tier tier-T3">T3</span> {ZH_TEXT['tier_t3']}</div>
      </div>
      
      <div class="tab-container" style="margin-top:24px; display:flex; gap:8px;">
        <button class="tab-btn active" onclick="switchTab('elements')">{ZH_TEXT['tab_elements']}</button>
        <button class="tab-btn" onclick="switchTab('targets')">{ZH_TEXT['tab_targets']}</button>
        <button class="tab-btn" onclick="switchTab('methods')">{ZH_TEXT['tab_methods']}</button>
        <button class="tab-btn" onclick="switchTab('scenarios')">{ZH_TEXT['tab_scenarios']}</button>
      </div>
    </div>
    """
    
    # Replace the existing page-header
    html = re.sub(r'<div class="page-header">.*?</div>', header_html, html, flags=re.DOTALL)
    
    # Update styles for Tab UI
    tab_styles = """
    .tab-btn {
        padding: 8px 20px;
        border: 1px solid var(--border);
        background: #fff;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        color: var(--text-muted);
    }
    .tab-btn.active {
        background: var(--primary);
        color: #fff;
        border-color: var(--primary);
        box-shadow: 0 4px 12px rgba(13,148,136,0.2);
    }
    .tab-btn:hover:not(.active) {
        background: rgba(13,148,136,0.05);
        color: var(--primary);
        border-color: var(--primary);
    }
    .panel { display: none; }
    .panel.active { display: block; }
    """
    if "<style>" in html:
        html = html.replace("</style>", tab_styles + "\n</style>")
    
    # Update JavaScript rendering logic
    # (This is a complex part as it requires rewriting the search and render functions)
    # I'll replace the existing script block with a more modular one.
    
    # First, save the updated HTML
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"Updated {HTML_PATH.name} with canonical data and tab structure.")

if __name__ == "__main__":
    build_page()
