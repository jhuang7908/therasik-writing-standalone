import pandas as pd
df = pd.read_excel(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\thera_export.xlsx', nrows=5)
print(df.columns.tolist())
