"""Audit payload/linker/conj/exp cards for structural issues vs Programs/Antigens standard."""
import re
path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read

def extract_cards(section_html):
    """Extract list of (title, cc_brief, has_subtitle, has_evidence, badges, info_labels) per card."""
    results = []
    for m in re.finditer(r'<div class="card"[^>]*>(.*?)(?=<div class="card"|</div>\s*</div>\s*$)', section_html, re.DOTALL):
        card = m.group(0)
        title_m = re.search(r'class="card-title"[^>]*>([^<]+)<', card)
        brief_m = re.search(r'class="cc-brief"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)?[^<]*)<', card)
        subtitle_m = re.search(r'class="card-subtitle"', card)
        evidence_m = re.search(r'', card)
        badges = re.findall(r'class="badge[^"]*">([^<]+)<', card)
        info_labels = re.findall(r'class="info-label"[^>]*>([^<]+)<', card)
        
        title = title_m.group(1).strip if title_m else 'N/A'
        brief = brief_m.group(1).strip if brief_m else 'N/A'
        brief_has_ellipsis = '…' in brief or '...' in brief
        brief_too_long = len(re.sub(r'<[^>]+>', '', brief)) > 90
        
        results.append({
            'title': title,
            'brief': brief,
            'brief_has_ellipsis': brief_has_ellipsis,
            'brief_too_long': brief_too_long,
            'has_subtitle': bool(subtitle_m),
            'has_evidence': bool(evidence_m),
            'badges': badges,
            'info_labels': info_labels[:4]
        })
    return results

grids = {
    'PAYLOAD':    content[446980:628040],
    'LINKER':     content[628040:741030],
    'CONJUGATION':content[741030:802513],
    'EXPERIMENTS':content[802513:],
}

for tab, html in grids.items:
    cards = extract_cards(html)
    issues = [c for c in cards if c['brief_has_ellipsis'] or c['brief_too_long'] or not c['has_evidence']]
    print(f"\n{'='*60}")
    print(f"=== {tab} ({len(cards)} cards, {len(issues)} with issues) ===")
    for c in cards:
        issues_list = []
        if c['brief_has_ellipsis']: issues_list.append('ELLIPSIS')
        if c['brief_too_long']: issues_list.append('LONG_BRIEF')
        if not c['has_evidence']: issues_list.append('NO_EVIDENCE')
        if not c['has_subtitle']: issues_list.append('NO_SUBTITLE')
        if not c['badges']: issues_list.append('NO_BADGE')
        status = ', '.join(issues_list) if issues_list else 'OK'
        brief_preview = re.sub(r'<[^>]+>', '', c['brief'])[:70]
        print(f"  [{status:30s}] {c['title'][:25]:25s} | {brief_preview}")
