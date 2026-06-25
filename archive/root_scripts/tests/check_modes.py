import pandas as pd
import sys
import os

# Load the database
file_path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\humanization_assay\thera_human_igG_germline_analysis.xlsx'
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

try:
    df = pd.read_excel(file_path)
except Exception as e:
    print(f"Error reading excel: {e}")
    sys.exit(1)

print("Unique human_origin_mode values:")
print(df['human_origin_mode'].unique())

print("\nUnique Species values (if any):")
if 'Species' in df.columns:
    print(df['Species'].unique())
else:
    print("Column 'Species' not found.")
