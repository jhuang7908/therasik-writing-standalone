import urllib.request
import urllib.parse
import json
import time

peptides = [
    "SGQARMFPNAPYLPSC","PGSTAPPAHGVTSA","DKKQRFHNIRGR",
    "PESFDGDPASNTAPLQP","VLLKEFTVSGNI","WNRQLYPEWTEAQRL",
    "GVALQTMKQ","VVRCPHERCTEGAT","GWVKPIIIGHHAYGD",
    "EYLNKIQNSLSTEWSP","MEVGWYRSPFSRVVH","IPPSLRTLEDNER",
    "PQPELPYPQPE","QQYPSGEGSFQPSQE","RIHMVYSKRSGKPRG"
]

found = []
not_found = []

for p in peptides:
    url = "https://query-api.iedb.org/epitope_search?linear_sequence=eq." + p + "&limit=1&select=structure_id"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
        if d and d[0].get("structure_id"):
            sid = d[0]["structure_id"]
            print(p + " -> IEDB #" + str(sid) + " FOUND")
            found.append((p, sid))
        else:
            print(p + " -> Not in IEDB (any type)")
            not_found.append(p)
    except Exception as e:
        print(p + " -> Error: " + str(e))
        not_found.append(p)
    time.sleep(0.15)

print("\nSummary:")
print("Found: " + str(len(found)))
print("Not found: " + str(len(not_found)))
if not_found:
    print("Not found list:")
    for p in not_found:
        print("  " + p)
