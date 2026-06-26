# Replace fake Webster ref with Brown et al.; copy v10 docx but replace only word/document.xml
# so the package matches Microsoft Word expectations (all members preserved).
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Antibody_Engineer_Suite
SRC = ROOT / "_NGF_v10_incoming.docx"
OUT = ROOT / "_NGF_v12.docx"
DOCS = Path.home() / "Documents" / "TheraPet_NGF_Proposal_v12.docx"

OLD = (
    '<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/>'
    '<w:numId w:val="{bullets-0}"/></w:numPr><w:spacing w:after="40" w:before="40" w:line="320"/>'
    "</w:pPr><w:r><w:rPr><w:rFonts w:ascii=\"SimSun\" w:cs=\"SimSun\" w:eastAsia=\"SimSun\" w:hAnsi=\"SimSun\"/>"
    '<w:b w:val="false"/><w:bCs w:val="false"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
    "<w:t xml:space=\"preserve\">Webster RP, Anderson GI, Gearing DP. *Canine brief pain inventory (CBPI) in dogs with osteoarthritis.* ， pivotal field trial </w:t></w:r></w:p>"
)


def make_list_para(text: str) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/>'
        '<w:numId w:val="{bullets-0}"/></w:numPr><w:spacing w:after="40" w:before="40" w:line="320"/>'
        "</w:pPr><w:r><w:rPr><w:rFonts w:ascii=\"SimSun\" w:cs=\"SimSun\" w:eastAsia=\"SimSun\" w:hAnsi=\"SimSun\"/>"
        '<w:b w:val="false"/><w:bCs w:val="false"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
        f'<w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
    )


T1 = (
    "Brown DC, Boston R, Coyne JC, Farrar JT. A novel approach to the use of animals in studies of pain: "
    "validation of the canine brief pain inventory in canine bone cancer. *Pain Med.* 2009, 10(1): 133-142. "
    "PMID: 18823385. DOI: 10.1111/j.1526-4637.2008.00513.x（CBPI ，）"
)
T2 = (
    "Brown DC, Boston RC, Coyne JC, Farrar JT. Ability of the Canine Brief Pain Inventory to detect response to "
    "treatment in dogs with osteoarthritis. *J Am Vet Med Assoc.* 2008, 233(8): 1278-1283. PMID: 19180716. "
    "DOI: 10.2460/javma.233.8.1278（CBPI ，/）"
)
NEW_PARAS = make_list_para(T1) + make_list_para(T2)


def main() -> int:
    if not SRC.is_file():
        print("Missing source:", SRC)
        return 1
    with zipfile.ZipFile(SRC, "r") as zin, zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in zin.namelist():
            b = zin.read(name)
            if name == "word/document.xml":
                text = b.decode("utf-8")
                if OLD not in text:
                    print("OLD block not in document.xml")
                    return 1
                b = text.replace(OLD, NEW_PARAS, 1).encode("utf-8")
            # Preserve per-member metadata from the source archive
            zout.writestr(zin.getinfo(name), b)
    if DOCS.parent.is_dir():
        shutil.copy2(OUT, DOCS)
        print("Copy:", DOCS)
    # Verify
    with zipfile.ZipFile(OUT) as z:
        assert "Webster" not in z.read("word/document.xml").decode("utf-8")
        assert len(z.namelist()) == len(zipfile.ZipFile(SRC).namelist())
    print("Wrote:", OUT, "(member count = source)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
