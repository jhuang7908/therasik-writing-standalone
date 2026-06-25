import haddock, os
d = os.path.dirname(haddock.__file__)
print("haddock:", d)
for root, dirs, files in os.walk(d):
    for f in files:
        if "cns" in f.lower():
            print(os.path.join(root, f))
