import re

def enrich_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add new CSS classes
    new_css = """
    .pipeline-flow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
    .pipe-step { background: var(--bg-white); border: 1px solid var(--border); border-radius: 10px; padding: 16px 12px; text-align: center; border-top: 3px solid var(--primary); }
    .pipe-step .step-num { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background: var(--primary); color: #fff; font-size: 12px; font-weight: 700; margin-bottom: 8px; }
    .pipe-step h4 { font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
    .pipe-step p { font-size: 12px; color: var(--text-muted); line-height: 1.4; margin: 0; }
    
    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
    .metric-card { background: var(--bg-white); border: 1px solid var(--border); border-radius: 10px; padding: 16px 12px; text-align: center; border-top: 3px solid var(--primary); }
    .metric-value { font-family: 'Cormorant Garamond', serif; font-size: 28px; font-weight: 700; color: var(--primary); line-height: 1; margin-bottom: 4px; }
    .metric-label { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 2px; }
    .metric-sub { font-size: 11px; color: #9ca3af; margin: 0; }
    """
    
    if ".pipeline-flow" not in content:
        content = content.replace('</style>', new_css + '\n  </style>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

files = [
    'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/case_pdl1_epitope_analysis.html',
    'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/case_ab278_fentanyl_affinity_maturation.html',
    'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/case_cdr_denovo_redesign.html'
]

for f in files:
    enrich_html(f)
    print(f"Enriched CSS for {f}")
