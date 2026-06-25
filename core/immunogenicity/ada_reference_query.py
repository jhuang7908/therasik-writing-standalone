"""
ADA Reference Query Tool
========================
Local clinical ADA reference database — for comparative analysis
when a client brings a new antibody target.

Usage:
    from core.immunogenicity.ada_reference_query import ADAReference
    db = ADAReference()
    db.query_target("PD-1")
    db.query_disease("autoimmune")
    db.compare_fc("IgG4")
    db.full_report("anti-IL-17A", route="SC", fc="IgG1")
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re

KB = Path(__file__).parent.parent.parent / "data/immunogenicity_knowledge_base"
MASTER = KB / "master/ada_master_136_curated.csv"


class ADAReference:
    """
    Local clinical ADA reference database (n=136 therapeutic antibodies).
    Tier A: 94 entries (PMID/FDA-anchored)
    Tier B: 36 entries (URL-verified)
    Tier C: 6 entries (excluded from comparisons by default)
    """

    def __init__(self, exclude_tier_c: bool = True):
        self.df = pd.read_csv(MASTER)
        self.df["ada_pct"] = pd.to_numeric(self.df["ada_first_pct"], errors="coerce")
        if exclude_tier_c:
            self.df = self.df[self.df["evidence_tier"].isin(["A", "B"])].copy()
        self.n = len(self.df)
        print("ADA Reference DB loaded: {} antibodies (Tier A+B)".format(self.n))

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _summary_row(self, sub, label=""):
        ada = sub["ada_pct"].dropna()
        if len(ada) == 0:
            return
        print("  {} n={:2d} | ADA median={:.1f}%  mean={:.1f}%  range={:.1f}–{:.1f}%".format(
            label.ljust(40), len(ada), ada.median(), ada.mean(), ada.min(), ada.max()))

    def _table(self, sub, cols=None, title=""):
        if title:
            print("\n── {} ──".format(title))
        if cols is None:
            cols = ["antibody_name", "origin", "targets", "ada_pct", "ada_value_display",
                    "evidence_tier", "fc_isotype", "fc_engineering",
                    "route_curated", "half_life_days",
                    "immunosuppressant_context", "assay_generation",
                    "indication_text"]
        show = [c for c in cols if c in sub.columns]
        sub_show = sub[show].copy()
        sub_show = sub_show.sort_values("ada_pct", ascending=False)
        pd.set_option("display.max_colwidth", 45)
        pd.set_option("display.width", 200)
        print(sub_show.to_string(index=False))

    # ── Query methods ─────────────────────────────────────────────────────────

    def query_target(self, target_keyword: str, verbose: bool = True):
        """
        Find all antibodies in the DB targeting a given antigen.
        target_keyword: e.g. "PD-1", "IL-17", "VEGF", "HER2", "TNF"
        """
        pat = re.compile(target_keyword, re.IGNORECASE)
        mask = self.df["targets"].apply(
            lambda x: bool(pat.search(str(x))))
        sub = self.df[mask].copy()

        print("\n" + "="*70)
        print("TARGET QUERY: '{}' — {} matches".format(target_keyword, len(sub)))
        print("="*70)

        if len(sub) == 0:
            print("  No matches found.")
            return sub

        self._summary_row(sub, "All matching")
        for org in ["natural", "engineered"]:
            s = sub[sub["origin"] == org]
            if len(s):
                self._summary_row(s, "  " + org)

        if verbose:
            self._table(sub, title="Detailed comparison")

        return sub

    def query_disease(self, disease_keyword: str, verbose: bool = True):
        """
        Find all antibodies by disease class or indication keyword.
        e.g. "autoimmune", "oncology", "infectious", "neurology"
        """
        pat = re.compile(disease_keyword, re.IGNORECASE)
        mask = (self.df["disease_class_curated"].apply(lambda x: bool(pat.search(str(x)))) |
                self.df["indication_text"].apply(lambda x: bool(pat.search(str(x)))))
        sub = self.df[mask].copy()

        print("\n" + "="*70)
        print("DISEASE QUERY: '{}' — {} matches".format(disease_keyword, len(sub)))
        print("="*70)
        if len(sub) == 0:
            print("  No matches found.")
            return sub

        self._summary_row(sub, "All matching")

        print("\n  By route:")
        for route in sub["route_curated"].dropna().unique():
            s = sub[sub["route_curated"] == route]
            self._summary_row(s, "    " + route)

        if verbose:
            self._table(sub, title="Detailed comparison")

        return sub

    def compare_fc(self, fc_type: str = None, verbose: bool = True):
        """
        Compare ADA rates by Fc type or engineering status.
        fc_type: "IgG1", "IgG2", "IgG4", "afucosylated", "YTE", "LALA", "silenced"
        Pass None to see the full Fc breakdown.
        """
        print("\n" + "="*70)
        print("Fc ENGINEERING COMPARISON")
        print("="*70)

        if fc_type:
            pat = re.compile(fc_type, re.IGNORECASE)
            mask = (self.df["fc_isotype"].apply(lambda x: bool(pat.search(str(x)))) |
                    self.df["fc_engineering"].apply(lambda x: bool(pat.search(str(x)))) |
                    self.df["fc_effector_status"].apply(lambda x: bool(pat.search(str(x)))))
            sub = self.df[mask].copy()
            print("Filter: '{}'  — {} matches".format(fc_type, len(sub)))
            if verbose:
                self._table(sub, title="Fc='{}' antibodies".format(fc_type))
            return sub

        # Full Fc breakdown
        print("\n  By Fc effector status:")
        for eff in ["normal", "reduced", "silenced", "enhanced"]:
            s = self.df[self.df["fc_effector_status"].str.contains(eff, case=False, na=False)]
            if len(s):
                self._summary_row(s, "    " + eff)

        print("\n  By Fc isotype:")
        for iso in ["G1", "G2", "G4"]:
            s = self.df[self.df["fc_isotype"].str.contains(iso, case=False, na=False)]
            if len(s):
                self._summary_row(s, "    IgG" + iso[-1])

        return self.df

    def compare_route(self, verbose: bool = True):
        """Compare ADA rates by administration route."""
        print("\n" + "="*70)
        print("ROUTE COMPARISON")
        print("="*70)
        print("  (Note: SC tends to provoke higher ADA than IV — partially an assay effect)\n")
        for route in ["IV", "SC", "IM"]:
            s = self.df[self.df["route_curated"].str.contains(route, case=False, na=False)]
            self._summary_row(s, "  " + route)

    # ── Main client report ────────────────────────────────────────────────────

    def full_report(self,
                    target_keyword: str,
                    route: str = None,
                    fc: str = None,
                    disease: str = None,
                    top_n: int = 10):
        """
        Generate a full clinical reference report for a client's antibody target.

        Parameters
        ----------
        target_keyword : target antigen keyword, e.g. "IL-17", "PD-1"
        route          : optional route filter, e.g. "SC", "IV"
        fc             : optional Fc filter, e.g. "IgG4", "YTE"
        disease        : optional disease class filter
        top_n          : how many most-relevant comparators to show
        """
        DIVIDER = "=" * 72

        print("\n" + DIVIDER)
        print("  ADA CLINICAL REFERENCE REPORT")
        print("  Target: {}{}{}{}".format(
            target_keyword,
            " | Route: " + route if route else "",
            " | Fc: " + fc if fc else "",
            " | Disease: " + disease if disease else ""))
        print("  Database: {} Tier A+B antibodies | InSynBio ADA Knowledge Base".format(self.n))
        print(DIVIDER)

        # 1. Target match
        pat = re.compile(target_keyword, re.IGNORECASE)
        mask = self.df["targets"].apply(lambda x: bool(pat.search(str(x))))
        target_hits = self.df[mask].copy()

        print("\n[1] SAME-TARGET ANTIBODIES  (n={})".format(len(target_hits)))
        if len(target_hits):
            ada = target_hits["ada_pct"].dropna()
            if len(ada):
                print("    ADA median={:.1f}%  mean={:.1f}%  range={:.1f}–{:.1f}%".format(
                    ada.median(), ada.mean(), ada.min(), ada.max()))
            cols = ["antibody_name", "origin", "ada_pct", "ada_value_display",
                    "evidence_tier", "fc_engineering",
                    "route_curated", "half_life_days",
                    "immunosuppressant_context", "indication_text"]
            show = [c for c in cols if c in target_hits.columns]
            print(target_hits[show].sort_values("ada_pct", ascending=False).to_string(index=False))
        else:
            print("    No exact target match. Proceeding to disease-class comparators.")

        # 2. Disease class comparators
        search_dc = disease or ""
        if not search_dc and len(target_hits):
            search_dc = str(target_hits["disease_class_curated"].mode().iloc[0]).split("(")[0].strip()

        if search_dc:
            dc_pat = re.compile(search_dc.split("_")[0], re.IGNORECASE)
            dc_mask = (self.df["disease_class_curated"].apply(
                           lambda x: bool(dc_pat.search(str(x)))) &
                       ~mask)
            dc_hits = self.df[dc_mask].copy()
            print("\n[2] SAME DISEASE CLASS: '{}' (excluding same-target, n={})".format(
                search_dc, len(dc_hits)))
            if len(dc_hits):
                ada2 = dc_hits["ada_pct"].dropna()
                if len(ada2):
                    print("    ADA median={:.1f}%  mean={:.1f}%  range={:.1f}–{:.1f}%".format(
                        ada2.median(), ada2.mean(), ada2.min(), ada2.max()))
                cols2 = ["antibody_name", "origin", "ada_pct", "ada_value_display",
                         "evidence_tier", "fc_engineering",
                         "route_curated", "half_life_days",
                         "immunosuppressant_context", "indication_text"]
                show2 = [c for c in cols2 if c in dc_hits.columns]
                print(dc_hits[show2].sort_values("ada_pct", ascending=False)
                      .head(top_n).to_string(index=False))

        # 3. Route / Fc context
        print("\n[3] KEY CLINICAL CONTEXT FACTORS")
        print("    (from database benchmarks, n={})\n".format(self.n))

        # Route comparison
        for r_val in ["IV", "SC", "IM"]:
            s = self.df[self.df["route_curated"].str.contains(r_val, case=False, na=False)]
            ada_r = s["ada_pct"].dropna()
            if len(ada_r):
                print("    Route {:5s}: median={:5.1f}%  mean={:5.1f}%  (n={})".format(
                    r_val, ada_r.median(), ada_r.mean(), len(ada_r)))

        # Fc effector status
        print()
        for eff, label in [("normal", "IgG1 normal effector"),
                            ("reduced", "IgG4/IgG2 reduced effector"),
                            ("silenced", "Fc-silenced (LALA/null)")]:
            s = self.df[self.df["fc_effector_status"].str.contains(eff, case=False, na=False)]
            ada_f = s["ada_pct"].dropna()
            if len(ada_f):
                print("    Fc {:35s}: median={:5.1f}%  (n={})".format(
                    label, ada_f.median(), len(ada_f)))

        # 4. Assay caveat
        print("\n[4] ASSAY & INTERPRETATION CAVEATS")
        print("""    • Modern ECL/tiered drug-tolerant assays detect ~3-5× more ADA than
      older ELISA/bridging assays. ADA rates for antibodies approved post-2015
      are systematically higher regardless of intrinsic immunogenicity.
    • MTX co-medication (RA context) suppresses ADA by 30-50%.
    • SC administration typically yields 2-3× higher ADA than same drug IV.
    • Oncology ADA rates are artifactually lower due to shortened follow-up
      and immune suppression from chemotherapy.
    • Clinical ADA ≠ immunogenicity risk: ADA with no neutralizing activity
      or PK impact is often clinically irrelevant.""")

        print("\n" + DIVIDER)
        print("  Evidence tiers in this report:")
        print("  Tier A = PMID/FDA-anchored (most reliable)")
        print("  Tier B = URL-verified (ADA value confirmed; narrative may be paraphrased)")
        print("  Source: InSynBio ADA Knowledge Base v1.0  |  data/immunogenicity_knowledge_base/")
        print(DIVIDER + "\n")

        return target_hits


if __name__ == "__main__":
    db = ADAReference()

    # Example 1: client brings anti-PD-1 antibody
    print("\n" + "#"*72)
    print("# EXAMPLE 1: Anti-PD-1 antibody (new candidate)")
    print("#"*72)
    db.full_report("PD-1", route="IV", fc="IgG4")

    # Example 2: anti-IL-17 antibody (SC, IgG1 or IgG4)
    print("\n" + "#"*72)
    print("# EXAMPLE 2: Anti-IL-17A antibody (SC, autoimmune)")
    print("#"*72)
    db.full_report("IL17", route="SC", disease="autoimmune")

    # Example 3: simple target lookup
    print("\n" + "#"*72)
    print("# EXAMPLE 3: Anti-VEGF comparators")
    print("#"*72)
    db.query_target("VEGF")
