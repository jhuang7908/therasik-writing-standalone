path = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/immunogenicity_study.html"
with open(path, encoding="utf-8") as f:
    content = f.read()

# min-width for 420px charts (2 of them)
content = content.replace(
    '<svg viewBox="0 0 420 188" width="100%" xmlns="http://www.w3.org/2000/svg">',
    '<svg viewBox="0 0 420 188" width="100%" style="min-width:360px;" xmlns="http://www.w3.org/2000/svg">'
)

# min-width for 560px chart
content = content.replace(
    '<svg viewBox="0 0 560 160" width="100%" xmlns="http://www.w3.org/2000/svg">',
    '<svg viewBox="0 0 560 160" width="100%" style="min-width:480px;" xmlns="http://www.w3.org/2000/svg">'
)

# Add overflow-x to the 560-wide chart container (model performance chart)
content = content.replace(
    '<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:18px;margin-top:12px;">',
    '<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:18px;margin-top:12px;overflow-x:auto;-webkit-overflow-scrolling:touch;">'
)

# Add mobile CSS for charts grid
mobile_css = """
    @media (max-width: 640px) {
      .charts-grid { grid-template-columns: 1fr !important; }
    }"""

content = content.replace("  </style>", mobile_css + "\n  </style>", 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("immunogenicity_study.html fixed")
