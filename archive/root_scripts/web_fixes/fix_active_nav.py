import re
import glob
import os

files = glob.glob("docs/Therasik_*.html")

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read
    
    # Remove active class from 
    content = content.replace('<a href="index.html" class="active"></a>', '<a href="index.html"></a>')
    
    # Determine which item should be active
    filename = os.path.basename(file_path)
    
    if "ADA" in filename or "ADC_Database" in filename or "Component" in filename or "Antibody_Guide" in filename or "Vaccine_KB" in filename:
        # Highlight 
        content = content.replace('<a href="#knowledge-base"></a>', '<a href="index.html#knowledge-base" class="active"></a>')
    elif "Page" in filename or "Design" in filename:
        # Highlight 
        content = content.replace('<a href="index.html#services"></a>', '<a href="index.html#services" class="active"></a>')
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Fixed active state in {file_path}")
