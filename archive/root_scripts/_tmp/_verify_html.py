import pathlib, re
html = pathlib.Path('docs/adc_database.html').read_text(encoding='utf-8')

# Find first Tubulin card (MMAE)
idx = html.find('Tubulin Inhibitors')
snippet = html[idx:idx+1400]
text = re.sub(r'<[^>]+>', ' ', snippet)
text = re.sub(r'  +', ' ', text)
print('=== MMAE card (first 800 chars) ===')
print(text[:800])

# Clathrin-mediated internalization in HER2 card
idx2 = html.find('Clathrin-mediated endocytosis')
if idx2 >= 0:
    snip2 = html[idx2:idx2+500]
    text2 = re.sub(r'<[^>]+>', ' ', snip2)
    text2 = re.sub(r'  +', ' ', text2)
    print('\n=== HER2 internalization data ===')
    print(text2[:400])

# Linker: mc-val-cit-PABC 
idx3 = html.find('7 days (very stable')
if idx3 >= 0:
    snip3 = html[idx3:idx3+500]
    text3 = re.sub(r'<[^>]+>', ' ', snip3)
    text3 = re.sub(r'  +', ' ', text3)
    print('\n=== mc-vc-PABC linker plasma stability ===')
    print(text3[:350])

# Check DXd ILD toxicity
idx4 = html.find('Interstitial lung disease')
print('\nDXd ILD DLT present in HTML:', idx4 >= 0)

# Check shedding BCMA
idx5 = html.find('shed by ADAM10')
print('BCMA ADAM10 shedding data present:', idx5 >= 0)
