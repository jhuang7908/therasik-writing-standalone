import csv
import re
import os

# Data from user
data_text = """
1. （transgenic_animal，210）
Abrilumab, Acrixolimab, Adakitug, Adezkibart, Aducanumab, Afimkibart, Alirocumab, Amlenetug, Amubarvimab, Anifrolumab, Ansipastobart, Anzurstobart, Ascrinvacumab, Atenastobart, Atidortoxumab, Atigotatug, Atinumab, Balonkibart, Balstilimab, Bapotulimab, Batoclimab, Bebtelovimab, Befovacimab, Belrestotug, Berlimatoxumab, Bersanlimab, Bimagrumab, Birinkibart, Bleselumab, Brazikumab, Briakinumab, Brodalumab, Calotatug, Calpurbatug, Camoteskimab, Canakinumab, Carlumab, Casdozokitug, Cepeprubart, Cetrelimab, Cifurtilimab, Cixutumumab, Claseprubart, Clesrovimab, Crebankitug, Crotedumab, Cudarolimab, Dargistotug, Dectrekumab, Demupitamab, Denosumab, Denrakibart, Dibotatug, Drozitumab, Dupilumab, Durvalumab, Eblasakimab, Ebronucimab, Eldelumab, Elgemtumab, Elipovimab, Eltivutabart, Emiltatug, Enlonstobart, Enokizumab, Enoticumab, Erenumab, Ersodetug, Evalstotug, Evinacumab, Evolocumab, Evunzekibart, Exbivirumab, Fezakinumab, Fianlimab, Figitumumab, Firivumab, Firsekibart, Foralumab, Foravirumab, Fulranumab, Gantenerumab, Garetosmab, Gimsilumab, Golimumab, Gotistobart, Greziprubart, Ianalumab, Icrucumab, Idactamab, Imeroprubart, Inclacumab, Indematug, Indenebart, Intetumumab, Ipilimumab, Iratumumab, Iscalimab, Itepekimab, Ivuxolimab, Lanadelumab, Latozinemab, Lemzoparlimab, Lesofavumab, Libevitug, Linavonkibart, Lirilumab, Lodapolimab, Lotivibart, Lunlekitug, Maftivimab, Manelimab, Masavibart, Mavrilimumab, Melrilimab, Micvotabart, Nadecnemab, Namilumab, Narlumosbart, Narsoplimab, Nipocalimab, Nirsevimab, Nisevokitug, Nivisnebart, Nivolumab, Ofatumumab, Ogalvibart, Olaratumab, Olinvacimab, Omoprubart, Opucolimab, Ordesekimab, Orticumab, Osocimab, Oxelumab, Pacibekitug, Pacmilimab, Panitumumab, Panobacumab, Pemivibart, Perenostobart, Pimivalimab, Plutavimab, Precemtabart, Prezalumab, Pritumumab, Pulocimab, Puxitatug, Rapaprutug, Remternetug, Renvistobart, Retavibart, Rilotumumab, Rinucumab, Romlusevimab, Samatatug, Sarilumab, Selicrelumab, Seribantumab, Setrusumab, Sifalimumab, Siltartoxatug, Simaravibart, Sipavibart, Sirukumab, Socazolimab, Sovipostobart, Suptavumab, Suvratoxumab, Tabalumab, Tafolecimab, Tarextumab, Telikibart, Teprotumumab, Teropavimab, Tesidolumab, Tesnatilimab, Tezepelumab, Timolumab, Tisotumab, Tixestobart, Torudokimab, Tosatoxumab, Tovetumab, Tozorakimab, Tralokinumab, Traxivitug, Trinbelimab, Trovostobart, Tuvonralimab, Ulocuplumab, Umesolerbart, Urabrelimab, Ustekinumab, Utomilumab, Varisacumab, Varlilumab, Varokibart, Verekitug, Vesencumab, Vipalanebart, Vixarelimab, Vixticibart, Volagidemab, Xeligekimab, Zalifrelimab, Zanolimumab, Zeluvalimab, Zimberelimab, Zovostotug
2. （phage_display，108）
Abelacimab, Adalimumab, Adecatumumab, Afasevikumab, Alextatug, Alomfilimab, Alsevalimab, Amlitelimab, Anumigilimab, Astegolimab, Atisnolerbart, Avdoralimab, Avelumab, Barecetamab, Belimumab, Beludavimab, Bempikibart, Botensilimab, Bremzalerbart, Canrivitug, Cenvacibart, Cliramitug, Cosibelimab, Crexavibart, Crovalimab, Dalnicastobart, Daxdilimab, Dusigitumab, Duvakitug, Ecleralimab, Efalizumab, Enuzovimab, Erzotabart, Exerenibart, Fasinumab, Felmetatug, Fiztasovimab, Flanvotumab, Fletikumab, Freneslerbart, Fresolimumab, Ganitumab, Garadacimab, Gedivumab, Ginisortamab, Golocdacimab, Gorivitug, Guselkumab, Ibramvibart, Iluzanebart, Izastobart, Lerdelimumab, Letaplimab, Lexatumumab, Lomtegovimab, Lucatumumab, Maridebart, Metelimumab, Mevonlerbart, Mibavademab, Narnatumab, Necitumumab, Negalstobart, Nepuvibart, Nesvacumab, Nurulimab, Nuvustotug, Oberotatug, Odesivimab, Oleclumab, Omodenbamab, Ontamalimab, Onvatilimab, Opicinumab, Ormutivimab, Otilimab, Pamrevlumab, Patritumab, Ponsegromab, Pozelimab, Quisovalimab, Rademikibart, Ramucirumab, Relatlimab, Rinatabart, Robatumumab, Rocatinlimab, Roledumab, Secukinumab, Sintilimab, Sonavibart, Stamulumab, Sudubrilimab, Sugemalimab, Surzebiclimab, Tamgiblimab, Timcevibart, Tiragolumab, Tobevibart, Trabikibart, Tremelimumab, Trevogrumab, Urelumab, Verzistobart, Vilamakitug, Vofatamab, Zalutumumab, Zinlirvimab
3. B （human_b_cell_derived，39）
Actoxumab, Adintrevimab, Alcestobart, Aldastotug, Amrecibart, Ansuvimab, Apitegromab, Atoltivimab, Bamlanivimab, Bentracimab, Bermekimab, Bezlotoxumab, Burosumab, Cemiplimab, Cilgavimab, Cinpanemab, Conatumumab, Daratumumab, Diridavumab, Ebrasodebart, Emapalumab, Etesevimab, Imalumab, Lanerkitug, Lesabelimab, Libivirumab, Marstacimab, Navivumab, Nelistotug, Potravitug, Rafivirumab, Regdanvimab, Rezorstobart, Sotrovimab, Tixagevimab, Vantictumab, Vebanvibart, Vopikitug, Vulinacimab
"""

categories = {}
current_cat = None
for line in data_text.split('\n'):
    if line.startswith('1.') or line.startswith('2.') or line.startswith('3.'):
        current_cat = line.split('（')[1].split('，')[0]
        categories[current_cat] = []
    elif line.strip and current_cat:
        abs = [x.strip for x in line.split(',')]
        categories[current_cat].extend(abs)

total_user_abs = sum(len(v) for v in categories.values)
print(f"Total antibodies provided: {total_user_abs}")

master_path1 = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\immunogenicity_panel_136_master.csv'
master_path2 = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_negative_library_by_phase.csv'

def load_master_names(path):
    names = set
    source_map = {}
    ada_found = set
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('antibody_name', '').lower
                if name:
                    names.add(name)
                    if 'discovery_source' in row:
                        source_map[name] = row['discovery_source']
                    elif 'platform' in row:
                        source_map[name] = row['platform']
                    
                    if 'ada_first_pct' in row and row['ada_first_pct'] and str(row['ada_first_pct']).strip != '' and str(row['ada_first_pct']).strip.lower != 'nan':
                        ada_found.add(name)
    return names, source_map, ada_found

names1, source1, ada1 = load_master_names(master_path1)
names2, source2, ada2 = load_master_names(master_path2)

all_db_names = names1.union(names2)
all_ada_names = ada1.union(ada2)

all_source_map = {}
for k, v in source2.items:
    all_source_map[k] = v
for k, v in source1.items:
    all_source_map[k] = v

results = {cat: {'found_ada': [], 'no_ada': [], 'source_mismatch': [], 'not_in_db': []} for cat in categories}

for cat, abs_list in categories.items:
    for ab in abs_list:
        ab_low = ab.lower
        if ab_low in all_ada_names:
            results[cat]['found_ada'].append(ab)
        elif ab_low in all_db_names:
            results[cat]['no_ada'].append(ab)
        else:
            results[cat]['not_in_db'].append(ab)
            
        if ab_low in all_source_map:
            db_source = all_source_map[ab_low].lower
            # Simple heuristic check, can be refined
            if cat == 'transgenic_animal' and 'phage' in db_source:
                results[cat]['source_mismatch'].append((ab, cat, db_source))
            if cat == 'phage_display' and ('transgenic' in db_source or 'mouse' in db_source):
                results[cat]['source_mismatch'].append((ab, cat, db_source))

for cat, data in results.items:
    print(f"\n--- {cat} ---")
    print(f"Total: {len(categories[cat])}")
    print(f"Has ADA data: {len(data['found_ada'])}")
    print(f"In DB but NO ADA data: {len(data['no_ada'])}")
    print(f"Not in DB: {len(data['not_in_db'])}")
    if data['source_mismatch']:
        print(f"Source Mismatch count: {len(data['source_mismatch'])}")
        # print("Mismatches:", data['source_mismatch'])

