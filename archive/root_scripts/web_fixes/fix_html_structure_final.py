import re

html_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read

# 1. Fix the missing closing div for gridAntigens
# Find the PAYLOADS section marker
payloads_marker = '<!-- ═══ PAYLOADS ═══ -->'
if payloads_marker in html:
    pos = html.find(payloads_marker)
    # Check if there is a closing div before it
    # We need to look back from pos
    before_payloads = html[:pos]
    
    # Let's find the last </div> before payloads_marker
    last_div_pos = html.rfind('</div>', 0, pos)
    
    # Let's count the divs in the last card to be sure
    last_card_start = html.rfind('<div class="card"', 0, pos)
    card_content = html[last_card_start:pos]
    open_divs = card_content.count('<div')
    close_divs = card_content.count('</div')
    
    print(f"Last card divs: open={open_divs}, close={close_divs}")
    
    # If open_divs == close_divs, then the card is closed, but the grid is NOT.
    # We need TWO closing divs: one for card-grid, one for tab-panel
    # Actually, the structure is:
    # <div class="tab-panel" id="panel-antigens">
    #   ...
    #   <div class="card-grid" id="gridAntigens">
    #     <div class="card">...</div>
    #   </div>
    # </div>
    
    # Let's check how many divs are open after the last card
    # We need to close card-grid AND tab-panel
    html = html[:pos] + '    </div>\n  </div>\n\n' + html[pos:]
    print("Inserted missing </div></div> for gridAntigens and panel-antigens")

# 2. Fix the missing content for other tabs
# The user said "，"
# This is likely because they are all nested inside the unclosed panel-antigens.
# The fix above should solve this.

# 3. Double check for any remaining 'exp'
html = html.replace('exp', 'expand')
html = html.replace('Exp', 'Expand')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("HTML structure and corruption fix completed.")
