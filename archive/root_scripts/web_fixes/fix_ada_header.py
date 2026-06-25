import re

with open("docs/Therasik_ADA_Database.html", "r", encoding="utf-8") as f:
    content = f.read()

# The badge is missing from the header in ADA Database. We need to insert it back.
badge_html = '<div class="header-badge" style="white-space:nowrap;">n = 138 antibodies</div>'

if badge_html not in content:
    content = content.replace('</header>', f'  {badge_html}\n</header>')
    with open("docs/Therasik_ADA_Database.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added badge to ADA Database")
else:
    print("Badge already exists")
