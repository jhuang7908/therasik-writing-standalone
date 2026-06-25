import csv
import os
import pandas as pd

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'

# data text same as before, from user prompt
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
        for a in [x.strip for x in line.split(',') if x.strip]:
            user_abs[a.lower] = {'name': a, 'category': current_cat}

master_df = pd.read_csv(master_path)
master_names = set(master_df['antibody_name'].str.lower.dropna)
ada_found = set(master_df[master_df['ada_first_pct'].notna]['antibody_name'].str.lower.dropna)

candidates = []
for ab_low, info in user_abs.items:
    if ab_low not in ada_found:
        # Check if in negative library for metadata
        # Just populate bare minimum if not in master
        meta_phase = 'Unknown'
        meta_target = 'Unknown'
        if ab_low in master_names:
            row = master_df[master_df['antibody_name'].str.lower == ab_low].iloc[0]
            meta_phase = row.get('clinical_phase', 'Unknown')
            meta_target = row.get('target', 'Unknown')
            
        candidates.append({
            'antibody_name': info['name'],
            'discovery_source': info['category'],
            'target': meta_target,
            'clinical_phase': meta_phase,
            'indication': 'Unknown'
        })

print(f"Total candidates still lacking ADA data: {len(candidates)}")

df_c = pd.DataFrame(candidates)
df_c['ada_pct'] = ''
df_c['assay'] = ''
df_c['evidence_source'] = ''

output_csv_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch9_and_10_candidates.csv'
df_top46 = df_c.head(46)
df_top46.to_csv(output_csv_path, index=False)
print(f"Saved {len(df_top46)} true remaining candidates to {output_csv_path}")

# Print the first 5 for web searching
print("\nFirst 5 candidates to search:")
for idx, row in df_top46.head(5).iterrows:
    print(f"- {row['antibody_name']}")
