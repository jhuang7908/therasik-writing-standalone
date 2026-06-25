import re

with open("docs/Therasik_ADC_Database.html", "r", encoding="utf-8") as f:
    content = f.read

# Make sure the title is translated in the HTML file as well, just in case the build script didn't catch everything
content = content.replace('ADC Knowledge Base', 'ADC ')
content = content.replace('Comprehensive reference database covering', '，')
content = content.replace('clinical programs', '')
content = content.replace('target antigens', '')
content = content.replace('payloads', '')
content = content.replace('mechanism classes', '')
content = content.replace('linkers', '')
content = content.replace('conjugation technologies', '')
content = content.replace('with chemical structures, patent status, and failure analysis.', '— 、。')

with open("docs/Therasik_ADC_Database.html", "w", encoding="utf-8") as f:
    f.write(content)
