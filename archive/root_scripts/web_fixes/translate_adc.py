import re

with open("scripts/_build_therasik_adc_db.py", "r", encoding="utf-8") as f:
    content = f.read

# Translate the title and subtitle
content = content.replace('ADC Knowledge Base', 'ADC ')
content = content.replace('Comprehensive reference database covering', '，')
content = content.replace('clinical programs', '')
content = content.replace('target antigens', '')
content = content.replace('payloads', '')
content = content.replace('mechanism classes', '')
content = content.replace('linkers', '')
content = content.replace('conjugation technologies', '')
content = content.replace('with chemical structures, patent status, and failure analysis.', '— 、。')

# Translate the hint box
content = content.replace('Each entry is an <strong>expandable card</strong>', '<strong></strong>')
content = content.replace('(same pattern as the', '（')
content = content.replace('antibody engineering reference', '')
content = content.replace('and', '')
content = content.replace('vaccine knowledge base', '')
content = content.replace('): <strong>click the card</strong> to show full details; a teal accent bar appears above the detail block.', '）：<strong></strong>；。')
content = content.replace('The control reads', '')
content = content.replace('Expand', '')
content = content.replace('Collapse', '')

# Translate the tabs
content = content.replace('Clinical Programs', '')
content = content.replace('Target Antigens', '')
content = content.replace('Payloads', '')
content = content.replace('Linkers', '')
content = content.replace('Conjugation Tech', '')
content = content.replace('Validation Assays', '')

with open("scripts/_build_therasik_adc_db.py", "w", encoding="utf-8") as f:
    f.write(content)
