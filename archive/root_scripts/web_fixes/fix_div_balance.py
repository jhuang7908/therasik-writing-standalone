import re

html_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# The integrity check showed panel-antigens has unclosed divs.
# Open: 2017, Close: 1939. Difference = 78.
# This is exactly the number of antigens (78)!
# This means each card is missing one </div>.

print("Fixing unclosed divs in antigen cards...")

# The current card structure in the file seems to be:
# <div class="card" ...>
#   <div class="card-header">...</div>
#   <div class="card-body">
#     ...
#     <div class="cc-detail">
#       ...
#     </div>
#   </div>
# (MISSING </div> here to close the card)

# Let's find the antigen section
start_marker = '<!-- ═══ ANTIGENS ═══ -->'
end_marker = '<!-- ═══ PAYLOADS ═══ -->'
grid_start = html.find(start_marker)
grid_end = html.find(end_marker)

antigen_section = html[grid_start:grid_end]

# We need to find the end of each card and add a </div>
# Cards are separated by newlines in the current version
cards = re.split(r'(?=<div class="card")', antigen_section)
fixed_cards = []

for card in cards:
    if not card.strip():
        fixed_cards.append(card)
        continue
    
    # Count divs in this card
    open_count = card.count('<div')
    close_count = card.count('</div')
    
    if open_count > close_count:
        # Add the missing closing div(s)
        diff = open_count - close_count
        fixed_card = card.strip() + ('</div>' * diff) + '\n'
        fixed_cards.append(fixed_card)
    else:
        fixed_cards.append(card)

new_antigen_section = "".join(fixed_cards)
new_html = html[:grid_start] + new_antigen_section + html[grid_end:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Div balance fix completed.")
