import os
from bs4 import BeautifulSoup

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# Find the case studies section
# Usually under a section with id="cases" or similar, or look for elements with class "case-card"
case_cards = soup.find_all(class_='case-card')
print(f"Found {len(case_cards)} case cards.")

for i, card in enumerate(case_cards):
    title_elem = card.find(class_='case-title')
    type_elem = card.find(class_='case-type')
    result_elem = card.find(class_='case-result')
    detail_elem = card.find(class_='case-detail')
    
    title = title_elem.text.strip() if title_elem else 'N/A'
    ctype = type_elem.text.strip() if type_elem else 'N/A'
    result = result_elem.text.strip() if result_elem else 'N/A'
    detail = detail_elem.text.strip() if detail_elem else 'N/A'
    
    print(f"--- Case {i+1} ---")
    print(f"Type: {ctype}")
    print(f"Title: {title}")
    print(f"Result: {result}")
    print(f"Detail: {detail}")
