import os
import re

FILES = [
    "docs/Therasik_Antibody_Page.html",
    "docs/Therasik_CART_Page.html",
    "docs/Therasik_Bispecific_Page.html"
]

def remove_services_table(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to remove the section "Current and planned offerings" and the table following it.
    # The section starts with <h2 id="services">...</h2> and ends before the next <h2>.
    # Or more specifically, it contains the table with class "table-wrap".
    
    # Let's find the specific H2 and remove everything until the next H2 or the end of the table div.
    # The H2 is: <h2 id="services">...Current and planned offerings...</h2>
    # Followed by a <p>...InSynBio provides...</p>
    # Followed by <div class="table-wrap">...<table>...</table></div>
    
    # We can use regex to match this block.
    # Pattern: <h2 id="services">.*?</div>\s*
    # But be careful not to match too much. The next tag is usually another <h2>.
    
    # Let's look for the specific H2 ID.
    if 'id="services"' in content:
        # Match from <h2 id="services"> to the closing </div> of the table-wrap.
        # The table-wrap is the last thing in this section usually.
        # Let's try to match:
        # <h2 id="services">...</h2>
        # ... content ...
        # <div class="table-wrap">...</div>
        
        # We can try to find the start index of <h2 id="services">
        # and the end index of the corresponding table-wrap div.
        
        # Alternatively, since we know the structure is consistent in these files (they were generated from templates),
        # we can use a regex that matches the H2 and the following table.
        
        pattern = r'<h2 id="services">.*?<div class="table-wrap">.*?</table>\s*</div>'
        
        # Check if the pattern matches
        match = re.search(pattern, content, flags=re.DOTALL)
        if match:
            # Replace with empty string
            new_content = content.replace(match.group(0), "")
            
            # Also remove any trailing whitespace/newlines left behind
            new_content = re.sub(r'\n\s*\n', '\n', new_content)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Removed services table from {filepath}")
        else:
            print(f"Pattern not found in {filepath}")
    else:
        print(f"Section 'services' not found in {filepath}")

if __name__ == "__main__":
    for f in FILES:
        if os.path.exists(f):
            remove_services_table(f)
        else:
            print(f"File not found: {f}")
