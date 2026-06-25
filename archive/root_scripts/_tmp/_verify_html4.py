import pathlib, re
html = pathlib.Path('docs/adc_database.html').read_text(encoding='utf-8')

# Search for linker-specific fields
print("=== LINKER CARD CHECK ===")
# Find Cathepsin B cleavage label in context
idx = html.find('Cathepsin B (lysosomal cysteine protease')
if idx >= 0:
    chunk = html[max(0,idx-200):idx+500]
    text = re.sub(r'<[^>]+>', ' ', chunk)
    text = re.sub(r'  +', ' ', text)
    print("Cleavage enzyme field found:")
    print(text[:600])

print("\n=== HER2 ANTIGEN CARD SECTION ===")
# Find HER2 antigen card by looking for the antigen tab section
# Search for HER2 in data-expr attribute
idx2 = html.find('data-expr="Solid Tumor"')
if idx2 >= 0:
    chunk2 = html[idx2:idx2+4000]
    text2 = re.sub(r'<[^>]+>', ' ', chunk2)
    text2 = re.sub(r'  +', ' ', text2)
    print(text2[:1500])
