"""Parse Supplementary Figure 1 spaced VHH lines into linear sequences."""
from __future__ import annotations

AA = frozenset("ACDEFGHIKLMNPQRSTVWY")


def spaced_row_to_seq(row: str) -> str:
    """Row is the spaced amino-acid segment only (no clone id, no hinge tail)."""
    parts = row.split()
    out: list[str] = []
    for p in parts:
        if p == "-" or p == "–":
            continue
        pu = p.upper().strip()
        if pu == "X" or all(c in AA for c in pu):
            out.extend(list(pu))
        # skip unrecognized tokens
    return "".join(out)


# Lines copied from Harmsen supplementary PDF (Data Sheet 1), Fig 1
SUPPLEMENT_ROWS: dict[str, str] = {
    "G3": "Q V Q L Q E S G G G L V Q A G G S L R L S C A A S G R T F S N - - Y V MGW F RQ A P G K E R E F V S A I SW NG V S T F Y A D S V K G R F T I S RD N A K N T V Y L Q M N S L K P E D T A V Y Y C A A D E R F V V R - - - - - - - - - - - Y N YWG Q G T Q V T V S S G",
    "G6": "Q V Q L Q E S G G A L V Q P G G S L R L S C A A S G F P F S A - - Y D M TW V RQ A P G Q G L EW V S T I H K S G G I T T Y A D S V K G R F T I S RD N A K N T L Y L Q M N N L E S E D T A V Y Y C A K A L R A H N S D Y V G R N A - - - - L G SWG E G T L V T V S S D",
    "G13": "Q V Q L Q E S G G G L V Q P G G S L R L S C E A S G F T F D D - - Y G M SW V RQ A P G K G L EW V S S L T P NG G S T Y Y A D S V K G R F T I S RD N A K N T L Y L Q M N S L K P E D T A L Y Y C A K N S Y Y G A - - - - - - - - - - - - MD YWG K G T L V T V S S A",
    "G18": "Q V Q L Q Q S G G G L V Q P G G S L R L S C A A S G F T F S S - - Y A M SW V RQ A P G K G L EW V S A I N S G G D I I S Y A D S V K G R F T I S RD N A K N T L Y L Q M N S L K P E D T A V Y Y C A K S P I V R T Y G G - - - - - - - - - Y D YWG Q G T Q V T V S S B",
    "G19": "Q V Q L Q Q S G G G L V Q P G G S L R L S C A A S G F T F S S - - Y A M SW V RQ A P G K G L EW V S A I N S G G G S T S Y A D S V K G R F T I S RD N A K N T L Y L Q M N S L K P E D T A V Y Y C A K D F D PWG V G T G G - - - - - - - Y D YWG Q G T Q V T V S S C",
    "G23": "Q V Q L Q E S G G G L V Q A G G S L R L S C A A S G R A F G S - - Y T M NW F RQ A P G K E RD F V A G I M S S G M N TW Y A D S V K G R F T I S RD N A K N T V Y L Q M N S L K P E D T A V Y Y C A S R P R S T M T S G R Y L - - - - - - Y D YWG Q G T Q V T V S S E",
    "G24": "Q V Q L Q Q S G G G L V Q A G G S L R L S C A A S G R T F S T - - Y N I AW F RQ A P G K E R E F V T A I TWG S G N T Y Y A D S V K G R F T I S RD N A K N T V F L Q M N S L K P D D T A V Y Y C A A R R S L G P T M A F A - - - - - - - Y E YWG Q G T Q V T V S S F",
    "G7": "Q V Q L Q E S G P G L V K P S Q T L S L T C T V S G G S I T T T A Y AW SW I RQ P P G K G L EWMG A I R F D G T T - D Y S P S L K S R I S I S RD T S N N Q F S L RM S S V T P E D T A V Y Y C A R Y G V V S D HG G - - - - - - - - - L D YWG Q G T Q V T V S S H",
    "sdAb-31": "Q V Q L V E S G P G L V K P S Q T L S L T C T V S G A S I T T A D Y TW SW I RQ P P G K A L EWMG A T D Y S G Y D - Y Y R P H L K S R A S I S RD T S K N Q F T L Q L T S V T P E D T A V Y Y C A RG R R A G S N R R S D - - - - - - - Y D FWG Q G T Q V T V S S X",
    "sdAb-32": "Q V Q L V E S G P G L V K P S Q T L S L I C T V S G G S I T S S G Y YW SW I RQ S P G K G L EW I G T I G F D D F H - Y Y S P S L K S R S S I S RD T S K N Q I T L Q L S S V T P E D T A V Y Y C A RD K L P L G G T RW S E - - - - - - Y D SWG Q G T Q V T V S S Y",
    "A2": "Q V Q L Q Q S G G G L V Q A G G S L R L S C A A S G R F F S R - - Q V MGW F RQ A P G K D R E F V G V I SWD NG V T F Y S D S V K G R F T M S R E I A K K T V H L Q M N S L K P E D T A V Y Y C A A G N A L H S R Y Y S P S K - - - - - Y D YWG P G T Q V T V S S E",
    "A4": "Q V Q L Q Q S G G G L V Q A G G S L R L A C A A S G R T L S S - - Y V MGW F RQ A P G K E R E F V A A I SW S G G S T Y Y A D S V K G R F T I S RD N A K N T V Y L Q M N S L K P E D T A V Y Y C A A T L RG S N R Y Y S G R V - - - - - Y D YWG Q G T Q V T V S S B",
    "A6": "Q V Q L Q E S G G R L V Q A E D S L R L S C A A S G R T F V S - - Y D MGW F RQ A P G K E R E F V A A I NW RG Y T T D Y V D S V K G R F F I S RD I A K S T V Y L Q M N N L K P E D T A V Y Y C A A RQ M S G S S R Y S P P G R V G - - Y D FWG Q G T Q V T V S S C",
    "A7": "Q V Q L Q Q S G G G L V Q A G D S L R L S C A A S G R A F N Y - - Y T MGW F RQ A P G K E R E F V A K I YWD G G S T I Y A D S V K G R F T I S I D N A K N T V Y L Q M N S L K P E D T A V Y Y C A A D P S F Y P F R - - - - - - - - - - P K YWG Q G T Q V T V S S F",
    "A12": "Q V Q L Q E S G G G L V Q A G G S L R L S C A A S G R T F S Y - - Y P M AW F RQ A P G Q E R E F V A A I I G A D T T - Y Y A D S L K G R F T I S RD N A K N M V Y L Q M N S L K P E D T A V Y Y C A A R N T YW S D V Y Y R E G Q - - - - Y T NWG Q G T Q V T V S S D",
    "A16": "Q V Q L Q E S G G G V V Q A G G S L R L S C A A S G R T V S S - - S A MGW F R L A P G K E R E F V V G I S R S G G S I F Y A D S V K G R F T I S R K N A K N T V D L Q M N S L K P E D T A V Y Y C A A G Y R P G Y G D Y G R V F Y R E D E Y D DWG Q G T Q V T V S S A",
}


def main() -> None:
    for k in sorted(SUPPLEMENT_ROWS):
        s = spaced_row_to_seq(SUPPLEMENT_ROWS[k])
        print(f"{k}\t{len(s)}\t{s}")


if __name__ == "__main__":
    main()
