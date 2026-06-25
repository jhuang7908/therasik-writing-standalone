import csv
import os

data_text = """
1. （transgenic_animal，210）
Abrilumab, Acrixolimab, Adakitug, Adezkibart, Aducanumab, Afimkibart, Alirocumab, Amlenetug, Amubarvimab, Anifrolumab, Ansipastobart, Anzurstobart, Ascrinvacumab, Atenastobart, Atidortoxumab, Atigotatug, Atinumab, Balonkibart, Balstilimab, Bapotulimab, Batoclimab, Bebtelovimab, Befovacimab, Belrestotug, Berlimatoxumab, Bersanlimab, Bimagrumab, Birinkibart, Bleselumab, Brazikumab, Briakinumab, Brodalumab, Calotatug, Calpurbatug, Camoteskimab, Canakinumab, Carlumab, Casdozokitug, Cepeprubart, Cetrelimab, Cifurtilimab, Cixutumumab, Claseprubart, Clesrovimab, Crebankitug, Crotedumab, Cudarolimab, Dargistotug, Dectrekumab, Demupitamab, Denosumab, Denrakibart, Dibotatug, Drozitumab, Dupilumab, Durvalumab, Eblasakimab, Ebronucimab, Eldelumab, Elgemtumab, Elipovimab, Eltivutabart, Emiltatug, Enlonstobart, Enokizumab, Enoticumab, Erenumab, Ersodetug, Evalstotug, Evinacumab, Evolocumab, Evunzekibart, Exbivirumab, Fezakinumab, Fianlimab, Figitumumab, Firivumab, Firsekibart, Foralumab, Foravirumab, Fulranumab, Gantenerumab, Garetosmab, Gimsilumab, Golimumab, Gotistobart, Greziprubart, Ianalumab, Icrucumab, Idactamab, Imeroprubart, Inclacumab, Indematug, Indenebart, Intetumumab, Ipilimumab, Iratumumab, Iscalimab, Itepekimab, Ivuxolimab, Lanadelumab, Latozinemab, Lemzoparlimab, Lesofavumab, Libevitug, Linavonkibart, Lirilumab, Lodapolimab, Lotivibart, Lunlekitug, Maftivimab, Manelimab, Masavibart, Mavrilimumab, Melrilimab, Micvotabart, Nadecnemab, Namilumab, Narlumosbart, Narsoplimab, Nipocalimab, Nirsevimab, Nisevokitug, Nivisnebart, Nivolumab, Ofatumumab, Ogalvibart, Olaratumab, Olinvacimab, Omoprubart, Opucolimab, Ordesekimab, Orticumab, Osocimab, Oxelumab, Pacibekitug, Pacmilimab, Panitumumab, Panobacumab, Pemivibart, Perenostobart, Pimivalimab, Plutavimab, Precemtabart, Prezalumab, Pritumumab, Pulocimab, Puxitatug, Rapaprutug, Remternetug, Renvistobart, Retavibart, Rilotumumab, Rinucumab, Romlusevimab, Samatatug, Sarilumab, Selicrelumab, Seribantumab, Setrusumab, Sifalimumab, Siltartoxatug, Simaravibart, Sipavibart, Sirukumab, Socazolimab, Sovipostobart, Suptavumab, Suvratoxumab, Tabalumab, Tafolecimab, Tarextumab, Telikibart, Teprotumumab, Teropavimab, Tesidolumab, Tesnatilimab, Tezepelumab, Timolumab, Tisotumab, Tixestobart, Torudokimab, Tosatoxumab, Tovetumab, Tozorakimab, Tralokinumab, Traxivitug, Trinbelimab, Trovostobart, Tuvonralimab, Ulocuplumab, Umesolerbart, Urabrelimab, Ustekinumab, Utomilumab, Varisacumab, Varlilumab, Varokibart, Verekitug, Vesencumab, Vipalanebart, Vixarelimab, Vixticibart, Volagidemab, Xeligekimab, Zalifrelimab, Zanolimumab, Zeluvalimab, Zimberelimab, Zovostotug
2. （phage_display，108）
Abelacimab, Adalimumab, Adecatumumab, Afasevikumab, Alextatug, Alomfilimab, Alsevalimab, Amlitelimab, Anumigilimab, Astegolimab, Atisnolerbart, Avdoralimab, Avelumab, Barecetamab, Belimumab, Beludavimab, Bempikibart, Botensilimab, Bremzalerbart, Canrivitug, Cenvacibart, Cliramitug, Cosibelimab, Crexavibart, Crovalimab, Dalnicastobart, Daxdilimab, Dusigitumab, Duvakitug, Ecleralimab, Efalizumab, Enuzovimab, Erzotabart, Exerenibart, Fasinumab, Felmetatug, Fiztasovimab, Flanvotumab, Fletikumab, Freneslerbart, Fresolimumab, Ganitumab, Garadacimab, Gedivumab, Ginisortamab, Golocdacimab, Gorivitug, Guselkumab, Ibramvibart, Iluzanebart, Izastobart, Lerdelimumab, Letaplimab, Lexatumumab, Lomtegovimab, Lucatumumab, Maridebart, Metelimumab, Mevonlerbart, Mibavademab, Narnatumab, Necitumumab, Negalstobart, Nepuvibart, Nesvacumab, Nurulimab, Nuvustotug, Oberotatug, Odesivimab, Oleclumab, Omodenbamab, Ontamalimab, Onvatilimab, Opicinumab, Ormutivimab, Otilimab, Pamrevlumab, Patritumab, Ponsegromab, Pozelimab, Quisovalimab, Rademikibart, Ramucirumab, Relatlimab, Rinatabart, Robatumumab, Rocatinlimab, Roledumab, Secukinumab, Sintilimab, Sonavibart, Stamulumab, Sudubrilimab, Sugemalimab, Surzebiclimab, Tamgiblimab, Timcevibart, Tiragolumab, Tobevibart, Trabikibart, Tremelimumab, Trevogrumab, Urelumab, Verzistobart, Vilamakitug, Vofatamab, Zalutumumab, Zinlirvimab
3. B （human_b_cell_derived，39）
Actoxumab, Adintrevimab, Alcestobart, Aldastotug, Amrecibart, Ansuvimab, Apitegromab, Atoltivimab, Bamlanivimab, Bentracimab, Bermekimab, Bezlotoxumab, Burosumab, Cemiplimab, Cilgavimab, Cinpanemab, Conatumumab, Daratumumab, Diridavumab, Ebrasodebart, Emapalumab, Etesevimab, Imalumab, Lanerkitug, Lesabelimab, Libivirumab, Marstacimab, Navivumab, Nelistotug, Potravitug, Rafivirumab, Regdanvimab, Rezorstobart, Sotrovimab, Tixagevimab, Vantictumab, Vebanvibart, Vopikitug, Vulinacimab
4. （unlabeled，27）— 
Anetumab, Aprutumab, Bezetabart, Camidanlumab, Danburstotug, Efungumab, Enapotamab, Enfortumab, Gancotamab, Glembatumumab, Indusatumab, Lenzilumab, Lupartumab, Moflerafusp, Ompekimig2, Opelkibart, Palverafusp, Pelgifatamab, Radretumab, Ramantamig2, Ruzaltatug, Sirtratumab, Solabafusp, Tabirafusp, Tilrekimig2, Torvutatug, Vislarafusp
"""

user_abs = {}
current_cat = None
for line in data_text.split('\n'):
    if line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.'):
        current_cat = line.split('（')[1].split('，')[0]
    elif line.strip and current_cat:
        abs_list = [x.strip for x in line.split(',') if x.strip]
        for a in abs_list:
            user_abs[a.lower] = {'name': a, 'category': current_cat}

master_path1 = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\immunogenicity_panel_136_master.csv'
master_path2 = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_negative_library_by_phase.csv'

db_metadata = {}
ada_found = set

def load_db(path):
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('antibody_name', '').lower
            if not name: continue
            
            target = row.get('target', row.get('Target', ''))
            phase = row.get('clinical_phase', row.get('highest_status', row.get('status', '')))
            indication = row.get('indication', row.get('primary_indication', ''))
            
            db_metadata[name] = {
                'target': target,
                'phase': phase,
                'indication': indication
            }
            
            val = row.get('ada_first_pct', '')
            if val and str(val).strip != '' and str(val).strip.lower != 'nan':
                ada_found.add(name)

load_db(master_path1)
load_db(master_path2)

candidates = []

for ab_low, info in user_abs.items:
    if ab_low in db_metadata and ab_low not in ada_found:
        meta = db_metadata[ab_low]
        candidates.append({
            'name': info['name'],
            'category': info['category'],
            'target': meta['target'],
            'phase': meta['phase'],
            'indication': meta['indication']
        })

# Sort candidates: we can try to prioritize Ph III, Approved, etc.
def phase_score(p):
    p = p.lower
    if 'approved' in p or 'market' in p: return 4
    if '3' in p or 'iii' in p: return 3
    if '2' in p or 'ii' in p: return 2
    if '1' in p or 'i' in p: return 1
    return 0

candidates.sort(key=lambda x: (phase_score(x['phase']), x['name']), reverse=True)

out_md = "#  ADA  ( %d )\n\n" % len(candidates)
out_md += "|  |  |  |  |  |\n"
out_md += "| :--- | :--- | :--- | :--- | :--- |\n"

for c in candidates:
    out_md += f"| **{c['name']}** | {c['category']} | {c['target']} | {c['phase']} | {c['indication']} |\n"

out_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_candidates_to_fill.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(out_md)
print(f"Generated {out_path} with {len(candidates)} candidates.")
