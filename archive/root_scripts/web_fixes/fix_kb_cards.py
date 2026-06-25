import re

with open("docs/therasik_index.html", "r", encoding="utf-8") as f:
    content = f.read

# Add ADA Database to the Knowledge Base section
# Currently there are 4 cards: ADC, CAR, Guide, Vaccine.
# We need to add ADA Database to make it 5, and adjust the grid layout if necessary.

ada_card = '''        <div class="service-card" style="padding: 24px; border-radius: 12px; background: var(--card-surface);">
          <h3 style="font-size: 16px; margin-bottom: 8px;">ADA </h3>
          <p style="font-size: 13px; margin-bottom: 12px;">138 ，。</p>
          <a href="Therasik_ADA_Database.html" style="font-size: 13px;"> →</a>
        </div>
'''

kb_section = content[content.find('<section id="knowledge-base"'):content.find('</section>', content.find('<section id="knowledge-base"'))]

if 'ADA ' not in kb_section:
    # Insert ADA card before ADC card
    adc_card_start = content.find('<div class="service-card" style="padding: 24px; border-radius: 12px; background: var(--card-surface);">\n          <h3 style="font-size: 16px; margin-bottom: 8px;">ADC </h3>')
    
    if adc_card_start != -1:
        content = content[:adc_card_start] + ada_card + content[adc_card_start:]
        
        # Update grid to 5 columns or wrap
        content = content.replace('style="grid-template-columns: repeat(4, 1fr);"', 'style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px;"')
        
        with open("docs/therasik_index.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Added ADA Database card to index")
    else:
        print("Could not find ADC card to insert before")
else:
    print("ADA Database card already exists")
