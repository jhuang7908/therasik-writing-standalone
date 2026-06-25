path = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\Therasik_OurTech.html"
with open(path, "r", encoding="utf-8") as f: text = f.read()
old = "background: linear-gradient(to bottom, rgba(0,0,0,0.18) 0%, rgba(0,0,0,0.0) 40%, rgba(0,0,0,0.0) 60%, rgba(0,0,0,0.35) 100%)"
new = "background: linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.2) 40%, rgba(0,0,0,0.2) 60%, rgba(0,0,0,0.6) 100%)"
if old in text:
    text = text.replace(old, new)
    with open(path, "w", encoding="utf-8") as f: f.write(text)
    print("Hero overlay updated")
