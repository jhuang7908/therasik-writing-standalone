"""
Strip the remaining accumulated junk CSS from all InSynBio pages.
The junk starts right after the original @media(max-width:600px) block
and ends at </style>.

Target: remove everything from the first injected mobile CSS block
(starting with the `.mobile-menu-btn, .std-mobile-btn { display: block !important; }` pattern)
through to </style>, then re-add </style>.
"""
import re
from pathlib import Path

SRC = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

# The junk starts with this EXACT sequence (injected by _fix_insynbio_mobile_nav.py)
JUNK_START_MARKER = (
    "\n    @media (max-width: 768px) {\n"
    "      \n"
    "      .mobile-menu-btn, .std-mobile-btn { display: block !important; }"
)

# Alternative marker for pages that have a slightly different first junk block
JUNK_ALT_MARKERS = [
    "\n    /* Global responsive table fix */\n    table { display: block;",
    "\n    \n    @media (max-width: 768px) {\n      \n      .std-slogan",
    "\n  \n    /* Global responsive table fix */",
]

def strip_junk(content: str) -> str:
    # Find the junk start
    pos = content.find(JUNK_START_MARKER)
    if pos == -1:
        # Try alternative markers
        for alt in JUNK_ALT_MARKERS:
            pos = content.find(alt)
            if pos != -1:
                break
    
    if pos == -1:
        return content  # Nothing to strip
    
    # Find </style> after the junk
    style_end = content.find('  </style>', pos)
    if style_end == -1:
        style_end = content.find('</style>', pos)
        if style_end == -1:
            return content
        return content[:pos] + '\n' + content[style_end:]
    
    # Remove junk, keep </style>
    return content[:pos] + '\n  </style>' + content[style_end + len('  </style>'):]

files_fixed = 0
for html_file in sorted(SRC.glob('*.html')):
    content = html_file.read_text(encoding='utf-8')
    new_content = strip_junk(content)
    if new_content != content:
        html_file.write_text(new_content, encoding='utf-8')
        files_fixed += 1
        print(f"  Stripped: {html_file.name}")

print(f"\nDone. Stripped {files_fixed} files.")
