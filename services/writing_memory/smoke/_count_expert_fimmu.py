"""Count words/refs in expert Front Immunol 2024 article (fetched HTML text)."""
import re
from pathlib import Path

FIMMU = Path(
    r"C:\Users\NextVivo\.cursor\projects\d-InSynBio-AI-Research-Antibody-Engineer-Suite"
    r"\agent-tools\6fbc5edc-9d3b-4bcb-bfb3-d0f17667791a.txt"
)


def wc(t: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'-]+", t))


def main() -> None:
    text = FIMMU.read_text(encoding="utf-8")
    ref_block = text.split("## References")[1].split("## Summary")[0]
    ref_nums = [int(x) for x in re.findall(r"^\n(\d+)\n", ref_block, re.M)]
    n_refs = max(ref_nums) if ref_nums else 0

    abstract = text.split("## Abstract")[1].split("## 1 Introduction")[0]
    intro = text.split("## 1 Introduction")[1].split("## 2 Materials")[0]
    methods = text.split("## 2 Materials and methods")[1].split("## 3 Results")[0]
    results = text.split("## 3 Results")[1].split("## 4 Discussion")[0]
    discussion = text.split("## 4 Discussion")[1].split("## Statements")[0]
    main = intro + methods + results + discussion

    print("source", "Front. Immunol. 2024;15:1419117 [verified]")
    print("doi", "10.3389/fimmu.2024.1419117")
    print("reference_count", n_refs)
    print("abstract_words", wc(abstract))
    print("introduction_words", wc(intro))
    print("methods_words", wc(methods))
    print("results_words", wc(results))
    print("discussion_words", wc(discussion))
    print("main_text_words", wc(main))
    print("total_body_words", wc(abstract) + wc(main))


if __name__ == "__main__":
    main()
