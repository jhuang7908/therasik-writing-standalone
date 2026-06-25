import re

c = open(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html', encoding='utf-8').read()

# The data is in the HTML body as cards - find the first program section
idx = c.find('panel-programs')
if idx > 0:
    snippet = c[idx:idx+3000]
    print("panel-programs start:")
    print(snippet[:2000])
else:
    print("panel-programs not found")
    # Find Kadcyla or T-DM1 context
    idx2 = c.find('Kadcyla')
    if idx2 > 0:
        print(f"Found Kadcyla at {idx2}")
        print(repr(c[idx2-100:idx2+200]))
