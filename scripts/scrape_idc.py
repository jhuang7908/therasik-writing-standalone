import urllib.request
import re
import json

url = 'https://www.biorxiv.org/content/10.64898/2025.12.08.692993v1.supplementary-material'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    # Find links ending with .xlsx or .csv
    links = re.findall(r'href="([^"]+\.(?:xlsx|csv|zip))"', html)
    print("Found links:", links)
    
    # Also find any biorxiv media links
    media_links = re.findall(r'href="([^"]+biorxiv[^"]+media[^"]+)"', html)
    print("Found media links:", media_links)
    
except Exception as e:
    print("Error:", e)
