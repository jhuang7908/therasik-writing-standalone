import pathlib, re
html = pathlib.Path('docs/adc_database.html').read_text(encoding='utf-8')

# Find DXd payload card (data-cls="Topoisomerase I Inhibitors")
idx = html.find('"Topoisomerase I Inhibitors"')
chunk = html[idx:idx+3000]
text = re.sub(r'<[^>]+>', ' ', chunk)
text = re.sub(r'  +', ' ', text)
print("=== DXd PAYLOAD CARD ===")
print(text[:2000])
