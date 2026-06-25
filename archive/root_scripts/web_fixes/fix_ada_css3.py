import re

with open("docs/therasik_index.html", "r", encoding="utf-8") as f:
    index_content = f.read()

with open("docs/Therasik_ADA_Database.html", "r", encoding="utf-8") as f:
    ada_content = f.read()

# Let's find where the header CSS actually is in index
css_start = index_content.find('.top-header {')
css_end = index_content.find('</style>')

if css_start != -1 and css_end != -1:
    header_css = index_content[css_start:css_end]
    
    # Replace the header CSS in ADA Database
    ada_css_start = ada_content.find('.top-header {')
    ada_css_end = ada_content.find('/* ── Hero ── */')
    
    if ada_css_start != -1 and ada_css_end != -1:
        ada_content = ada_content[:ada_css_start] + header_css + '\n    ' + ada_content[ada_css_end:]
        
        with open("docs/Therasik_ADA_Database.html", "w", encoding="utf-8") as f:
            f.write(ada_content)
        print("Replaced header CSS in ADA Database")
    else:
        print("Could not find header CSS block in ADA Database")
else:
    print("Could not find header CSS block in index")
