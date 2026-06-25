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
    if '</div>\n\n' + payloads_marker not in html and '</div>\n<!-- ═══ PAYLOADS ═══ -->' not in html:
        # We need to insert a closing </div> for the card-grid
        # Let's find the last </div> before payloads_marker
        last_div_pos = html.rfind('</div>', 0, pos)
        # The structure should be:
        #   </div> (closes card)
        # </div> (closes card-grid)
        # <!-- ═══ PAYLOADS ═══ -->
        
        # Let's count the divs in the last card to be sure
        last_card_start = html.rfind('<div class="card"', 0, pos)
        card_content = html[last_card_start:pos]
        open_divs = card_content.count('<div')
        close_divs = card_content.count('</div')
        
        print(f"Last card divs: open={open_divs}, close={close_divs}")
        
        # If open_divs == close_divs, then the card is closed, but the grid is NOT.
        if open_divs == close_divs:
            html = html[:pos] + '</div>\n\n' + html[pos:]
            print("Inserted missing </div> for gridAntigens")

# 2. Double check for any remaining 'exp'
html = html.replace('exp', 'expand')
html = html.replace('Exp', 'Expand')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("HTML structure and corruption fix completed.")
