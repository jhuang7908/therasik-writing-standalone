import os
import re

files = {
    "zh": r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html",
    "en": r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"
}

for lang, fpath in files.items:
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        html = f.read

    # --- 1. Fix Cover Subtitle line breaks and spacing ---
    # English
    html = html.replace("<br>to deliver actionable drug design", " to deliver actionable drug design")
    # if it's too wide, it'll auto-wrap correctly based on the 800px constraint.
    
    # --- 2. Add Presenter / Date / Location Info on Cover ---
    presenter_en = """
    <div style="margin-top: 48px; font-size: 18px; color: rgba(255,255,255,0.5); line-height: 1.8;">
      <div><strong style="color:var(--text);">Presenter:</strong> [Name / Title]</div>
      <div><strong style="color:var(--text);">Date:</strong> [YYYY-MM-DD]</div>
      <div><strong style="color:var(--text);">Location:</strong> [Event / Online]</div>
    </div>
    """
    presenter_zh = """
    <div style="margin-top: 48px; font-size: 18px; color: rgba(255,255,255,0.5); line-height: 1.8;">
      <div><strong style="color:var(--text);">：</strong>[]</div>
      <div><strong style="color:var(--text);">：</strong>[]</div>
      <div><strong style="color:var(--text);">/：</strong>[]</div>
    </div>
    """
    
    # Insert it right before the close of the cover slide-inner
    # Find '<div class="slide-num">01 / 15</div>' and insert before its parent closing div
    if "Presenter:" not in html and "：" not in html:
        insert_block = presenter_zh if lang == "zh" else presenter_en
        # The cover slide ends with:
        #   </div>
        #   <div class="slide-num">01 / 15</div>
        # </section>
        # We can find `01 / 15</div>` and pre-pend the insert block before the `</div>` that precedes it.
        # It's safer to use regex targeting slide 1 specifically.
        html = re.sub(
            r'(</p>\s*)</div>(\s*<div class="slide-num">01)',
            r'\1' + insert_block + r'\n  </div>\2',
            html
        )


    # --- 3. Fix Tech Arsenal Nested Card ---
    # The nested card looks like:
    # <div class="card" style="text-align:center;padding:16px; border:2px dashed #0d9488;">
    # It was injected inside the RFdiffusion card due to misaligned </div> counts.
    # We will find the proprietary card string, remove it, and place it immediately AFTER the closing </div> of the RFdiffusion card.
    
    prop_start_idx = html.find('<div class="card" style="text-align:center;padding:16px; border:2px dashed #0d9488;">')
    if prop_start_idx != -1:
        # Find the end of this proprietary card
        # It has 3 inner divs, then a closing div.
        prop_end_idx = html.find('</div>', prop_start_idx) # closes the title
        prop_end_idx = html.find('</div>', prop_end_idx + 1) # closes tool 1
        prop_end_idx = html.find('</div>', prop_end_idx + 1) # closes tool 2
        
        # if vaccine is there, there is another div
        if "Vaccine Design Suite" in html[prop_start_idx:prop_start_idx+800] or "" in html[prop_start_idx:prop_start_idx+800]:
             prop_end_idx = html.find('</div>', prop_end_idx + 1) # closes tool 3
        
        prop_end_idx = html.find('</div>', prop_end_idx + 1) # closes the card itself
        # Add 6 to include the </div>
        full_prop_card = html[prop_start_idx:prop_end_idx + 6]
        
        # Remove from current location
        html = html.replace(full_prop_card, "")
        
        # Now find the <div class="card-grid g5"> block for the second row
        # and insert the full_prop_card at the very end of it, right before its closing </div>
        row2_start = html.find('<div class="card-grid g5">')
        if row2_start != -1:
            row2_end = html.find('</div>\n    </div>', row2_start)
            if row2_end != -1:
                # Insert safely
                html = html[:row2_end] + "\n      " + full_prop_card + "\n    " + html[row2_end:]


    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)

print("Fixes applied successfully!")
