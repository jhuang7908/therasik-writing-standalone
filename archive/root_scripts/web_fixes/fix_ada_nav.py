import re

with open("docs/Therasik_ADA_Database.html", "r", encoding="utf-8") as f:
    content = f.read()

# Make sure ADA Database has the exact same CSS for the header as the index page.
# The user's screenshot shows the ADA Database header is completely unstyled or broken,
# which means either the CSS is missing or the HTML structure is wrong.
# Let's check the CSS in Therasik_ADA_Database.html

if '.top-header {' in content:
    print("CSS for .top-header exists in ADA Database.")
else:
    print("CSS for .top-header is missing in ADA Database.")
    
# Check if the CSS is correct
if 'display:flex; align-items:center; justify-content:space-between;' in content:
    print("CSS for .top-header seems correct.")
else:
    print("CSS for .top-header might be wrong.")

# Check the nav CSS
if '.top-header-nav {' in content:
    print("CSS for .top-header-nav exists.")
else:
    print("CSS for .top-header-nav is MISSING!")

