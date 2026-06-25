import sys, json, math
print("Python:", sys.version)

import mhcflurry
print("MHCflurry version:", mhcflurry.__version__)

from mhcflurry import Class1PresentationPredictor
p = Class1PresentationPredictor.load()
print("Loaded OK")
print("Predictor alleles sample:", p.supported_alleles[:5])

# Test with single peptide
df = p.predict(peptides=["VVVGADGVGK", "VVVGAGGVGK"], alleles=["HLA-A*11:01", "HLA-A*11:01"])
print("predict() result type:", type(df))
print("Columns:", list(df.columns))
print(df.to_string())
