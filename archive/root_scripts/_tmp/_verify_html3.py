import pathlib, re
html = pathlib.Path('docs/adc_database.html').read_text(encoding='utf-8')

# Find mc-val-cit-PABC linker card
idx = html.find('mc-val-cit-PABC')
chunk = html[idx:idx+3000]
text = re.sub(r'<[^>]+>', ' ', chunk)
text = re.sub(r'  +', ' ', text)
print("=== mc-val-cit-PABC LINKER CARD ===")
print(text[:1800])

print("\n")
# Find HER2 antigen card
idx2 = html.find('>HER2<')
chunk2 = html[idx2:idx2+3500]
text2 = re.sub(r'<[^>]+>', ' ', chunk2)
text2 = re.sub(r'  +', ' ', text2)
print("=== HER2 ANTIGEN CARD ===")
print(text2[:1800])
