import re

with open("docs/therasik_index.html", "r", encoding="utf-8") as f:
    content = f.read

# Make sure all 5 cards have the exact same styling
kb_section = content[content.find('<section id="knowledge-base"'):content.find('</section>', content.find('<section id="knowledge-base"'))]

# The cards should all have:
# <div class="service-card" style="padding: 24px; border-radius: 12px; background: var(--card-surface);">
#   <h3 style="font-size: 16px; margin-bottom: 8px;">Title</h3>
#   <p style="font-size: 13px; margin-bottom: 12px;">Desc</p>
#   <a href="..." style="font-size: 13px;">Link →</a>
# </div>

# They look consistent based on the code I just inserted.
# The grid is now `grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px;`
# But wait, the user also mentioned "ADA，。" (ADA Database's top nav bar is different from others).
# I already ran fix_headers.py and fix_active_nav.py, which should have synced the ADA Database header with the rest.
# Let's double check Therasik_ADA_Database.html to see if it's actually fixed.

with open("docs/Therasik_ADA_Database.html", "r", encoding="utf-8") as f:
    ada_content = f.read

if '<nav class="top-header-nav">' in ada_content:
    print("ADA Database has the correct nav structure.")
else:
    print("ADA Database is missing the correct nav structure.")
