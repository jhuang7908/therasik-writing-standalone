"""
Extract full content structure from all pages for site rebuild.
"""
import os, re, glob, json
from html.parser import HTMLParser

class ContentExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self.current = []
        self.skip = False
        self.in_nav = False
        self.nav_items = []
        self.in_link = False
        self.current_href = ''
        self.current_link_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.skip = True
        if tag == 'a':
            self.in_link = True
            self.current_href = attrs.get('href', '')
            self.current_link_text = []
        if tag == 'img':
            src = attrs.get('src', '')
            if src and src.startswith('http'):
                self.texts.append(f'[IMG:{src}]')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = False
        if tag == 'a':
            text = ''.join(self.current_link_text).strip()
            if text and self.current_href and not self.current_href.startswith('#'):
                self.nav_items.append({'text': text, 'href': self.current_href})
            self.in_link = False
            self.current_link_text = []

    def handle_data(self, data):
        if self.skip:
            return
        cleaned = data.strip()
        if self.in_link and cleaned:
            self.current_link_text.append(cleaned)
        if cleaned and len(cleaned) > 1:
            self.texts.append(cleaned)


base = '.'
html_files = sorted(glob.glob(f'{base}/**/*.html', recursive=True))

site_content = {}
all_nav = {}

for hf in html_files:
    p = ContentExtractor()
    try:
        content = open(hf, 'r', encoding='utf-8', errors='ignore').read()
        # Get title
        title_m = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
        title = title_m.group(1).strip() if title_m else ''
        p.feed(content)
        texts = [t for t in p.texts if not t.startswith('[IMG:') and len(t) > 1]
        imgs  = [t[5:-1] for t in p.texts if t.startswith('[IMG:')]
        nav   = [n for n in p.nav_items if n['text'] and len(n['text']) > 0]
        rel_path = hf.replace(base + os.sep, '').replace(base + '/', '')
        site_content[rel_path] = {
            'title': title,
            'text_blocks': texts[:80],   # first 80 blocks
            'images': imgs,
            'nav': nav[:20]
        }
    except Exception as e:
        print(f'Error {hf}: {e}')

# Save
with open('site_content.json', 'w', encoding='utf-8') as f:
    json.dump(site_content, f, ensure_ascii=False, indent=2)

print(f'Extracted {len(site_content)} pages')
for page, data in site_content.items():
    print(f'\n=== {page} ===')
    print(f'  Title: {data["title"]}')
    print(f'  Text blocks: {len(data["text_blocks"])}')
    print(f'  Images: {len(data["images"])}')
    sample = [t for t in data["text_blocks"] if len(t) > 3][:5]
    for s in sample:
        print(f'    > {s[:80]}')
