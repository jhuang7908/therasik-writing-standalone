import os
import re

base_path = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-clone"
english_idx = os.path.join(base_path, "index.html")

def finalize():
    if not os.path.exists(english_idx):
        print("Error: index.html not found.")
        return

    # 1. Load the English index (the one with all sections and conflicts)
    with open(english_idx, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 2. Resolve Git conflicts (choose the updated version)
    # The SECOND part (after =======) is usually the correct content for us.
    # We will choose the content between ======= and >>>>>>>
    
    # Regex to find all conflict blocks and replace them with the second part.
    def resolve_conflict(match):
        return match.group(2)
    
    content = re.sub(r'<<<<<<< HEAD(.*?)\n=======\n(.*?)\n>>>>>>> [a-f0-9]+', resolve_conflict, content, flags=re.DOTALL)
    
    # 3. Global Rebranding
    content = content.replace("InSynBio", "Therasik")
    content = content.replace("insynbio.com", "therasik.com")
    content = content.replace("AI for Life Sciences", "AI ")
    content = content.replace('<html lang="en">', '<html lang="zh">')
    
    # 4. Critical Section Translations
    # Title
    content = content.replace("<title>Therasik | AI-Powered Design for Therapeutics</title>", "<title>Therasik | AI </title>")
    
    # Hero
    content = content.replace("AI-Powered Design for Therapeutics", "AI ")
    content = content.replace("Clinical data meets machine learning. From antibody assessment to CAR-T engineering — accelerating biotherapeutic innovation.", 
                              "AI 。，，。")
    content = content.replace("AI-Driven Design", "AI ")
    content = content.replace("Expert-Reviewed Reports", "")
    content = content.replace("Start Assessment", "")
    
    # Nav
    content = content.replace('>Home</a>', '></a>')
    content = content.replace(">About Us</a>", "></a>")
    content = content.replace(">Services</a>", "></a>")
    content = content.replace(">Case Studies</a>", "></a>")
    content = content.replace(">Workflow</a>", "></a>")
    content = content.replace(">Contact Us</a>", "></a>")
    
    # Services Tags
    content = content.replace("Antibody Development & Assessment", "")
    content = content.replace("Smart CAR-T Design", " CAR-T ")
    content = content.replace("Multispecific Engineering", "")
    
    # About
    content = content.replace("AI for Drug R&D", "AI ")
    
    # Case Studies Section
    content = content.replace("Selected Projects", "")
    
    # Case Card 1: Humanization
    content = content.replace("Humanization", "")
    content = content.replace("muMAb4D5 → Herceptin Precursor Humanization", "muMAb4D5 → ")
    content = content.replace("Read full case study", "")
    
    # CMC
    content = content.replace("CMC & Assessment", "")
    content = content.replace("Case Study: 4D5 Developability", "：4D5 ")
    
    # Links
    page_map = {
        "InSynBio_Antibody_Developability_Assessment_Page.html": "Therasik_Antibody_Page.html",
        "InSynBio_CART_Design_Page.html": "Therasik_CART_Page.html",
        "InSynBio_Bispecific_Antibody_Design_Page.html": "Therasik_Bispecific_Page.html"
    }
    for old, new in page_map.items():
        content = content.replace(old, new)
        
    # 5. Fix Footer
    content = content.replace("© 2026 Therasik", "© 2026 Therasik AI Solutions")
    
    # 6. Save
    with open(english_idx, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Final Chinese Landing Page Generated in therasik-web-clone/index.html")

if __name__ == "__main__":
    finalize()
