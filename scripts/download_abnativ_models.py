import os
import requests
from pathlib import Path

ZENODO_RECORD = "17295347"
BASE_URL = f"https://zenodo.org/record/{ZENODO_RECORD}/files"
PRETRAINED_MODELS_DIR = os.path.expanduser("~\\AppData\\Local\\abnativ\\models\\pretrained_models")

filenames = [
    "vhh2_model.ckpt",
    "vh2_model.ckpt",
    "vl2_model.ckpt",
    "vpaired2_model.ckpt",
    "vlambda_model.ckpt",
    "vkappa_model.ckpt",
    "vh_model.ckpt",
    "vhh_model.ckpt",
    "vh2_rhesus_model.ckpt",
]

def download_file(url, target):
    print(f"Downloading {url} to {target}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(target, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def main():
    os.makedirs(PRETRAINED_MODELS_DIR, exist_ok=True)
    for fname in filenames:
        target = os.path.join(PRETRAINED_MODELS_DIR, fname)
        if not os.path.exists(target):
            url = f"{BASE_URL}/{fname}?download=1"
            try:
                download_file(url, target)
                print(f"✔ Downloaded {fname}")
            except Exception as e:
                print(f"✘ Failed to download {fname}: {e}")
        else:
            print(f"✔ {fname} already exists")

if __name__ == "__main__":
    main()
