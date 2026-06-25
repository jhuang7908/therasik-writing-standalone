import os
from bs4 import BeautifulSoup

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

case_cards = soup.find_all(class_='case-card')
for i, card in enumerate(case_cards):
    print(f"--- Case {i+1} HTML ---")
    print(card.prettify()[:500]) # Print first 500 chars to understand structure
