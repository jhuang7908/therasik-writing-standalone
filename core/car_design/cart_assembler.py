"""
CAR-T Assembler — v758 Vector & Multi-Transcript Architecture
============================================================
Replaces the prior single-CAR + flat-cassette model with a full vector
representation: each construct is now an ordered list of *transcripts*,
each with its own promoter / 5'UTR / 3'UTR / WPRE / polyA, and each
transcript can contain multiple ORFs joined by 2A peptides or IRES.

Key changes vs v757:
- Multi-costim (tandem) supported via comma-separated `costim` or list.
- `cassettes` list (CartCassetteSpec) is the primary cassette input; each
  cassette declares its `linker_to_prev` ∈ {T2A,P2A,F2A,E2A,IRES,new_promoter}.
  The engine groups cassettes into transcripts: same-transcript when
  linker is 2A/IRES, new transcript when linker is `new_promoter`.
- Legacy flat slots (safety/armored/reg/logic/engmod) still accepted —
  converted to cassettes with default T2A linker.
- Each transcript carries its own promoter/polyA/UTR/WPRE metadata so the
  Step-4 UI can render the full regulatory chain per transcript.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from api.models import (
    CartAssemblerRequest, CartAssemblerResult,
    CartComponentDetail, CartTranscript, CartCassetteSpec,
)

# ── Human codon table for AA → cDNA back-translation (single high-frequency codon) ──
# Source: Kazusa human codon-usage table (Homo sapiens); picks most frequent codon per AA.
_AA_TO_CODON = {
    "A":"GCC","R":"CGG","N":"AAC","D":"GAC","C":"TGC","E":"GAG","Q":"CAG","G":"GGC",
    "H":"CAC","I":"ATC","L":"CTG","K":"AAG","M":"ATG","F":"TTC","P":"CCC","S":"AGC",
    "T":"ACC","W":"TGG","Y":"TAC","V":"GTG","*":"TGA",
}

# Canonical self-cleaving 2A peptide sequences (with GSG spacer for cleavage efficiency).
# Source: Liu et al., Sci Rep 7, 2193 (2017); de Felipe (2002).
_TWO_A_PEPTIDES = {
    "T2A": "GSGEGRGSLLTCGDVEENPGP",   # Thosea asigna virus 2A
    "P2A": "GSGATNFSLLKQAGDVEENPGP",  # Porcine teschovirus 2A — best cleavage efficiency
    "F2A": "GSGVKQTLNFDLLKLAGDVESNPGP",  # Foot-and-mouth disease virus 2A
    "E2A": "GSGQCTNYALLKLAGDVESNPGP",   # Equine rhinitis A virus 2A
}

# IRES is a non-coding DNA element, not translated. Engine inserts a marker
# in the cDNA-level concatenation but does NOT add residues to the protein.
_IRES_PLACEHOLDER_DNA = "<<IRES>>"   # surfaced in cdna with delimiter, not codon-substituted

# Default regulatory elements by vector mode. User-supplied values override these.
_VECTOR_DEFAULTS = {
    "lentivirus":  {"promoter": "EF1a_Promoter", "polyA": "BGH_polyA",  "wpre": "WPRE", "utr_5": None,        "utr_3": None},
    "retrovirus":  {"promoter": "MSCV_LTR",      "polyA": "BGH_polyA",  "wpre": None,   "utr_5": None,        "utr_3": None},
    "aav":         {"promoter": "EF1a_Promoter", "polyA": "SV40_polyA", "wpre": None,   "utr_5": None,        "utr_3": None},
    "mRNA-LNP":    {"promoter": "T7_Promoter",   "polyA": "120A_tail",  "wpre": None,   "utr_5": "HBA1_5UTR", "utr_3": "HBA1_3UTR"},
    "transposon":  {"promoter": "EF1a_Promoter", "polyA": "BGH_polyA",  "wpre": None,   "utr_5": None,        "utr_3": None},
}


def _backtranslate(aa: str) -> str:
    """Back-translate an AA string to cDNA using the most-frequent human codon per residue."""
    if not aa:
        return ""
    return "".join(_AA_TO_CODON.get(ch, "NNN") for ch in aa.upper())


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
REGISTRY_PATH = CONFIG_DIR / "cart_components_registry.json"


class CartAssemblerEngine:
    def __init__(self):
        self.registry: Dict[str, Dict[str, Any]] = {}
        self._load_registry()

    def _load_registry(self):
        if not REGISTRY_PATH.exists():
            return
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for element in data.get("elements", []):
                element_id = element.get("id", "").lower()
                if element_id:
                    self.registry[element_id] = element
        except Exception as e:
            print(f"[CartAssembler] Failed to load registry: {e}")

    # ── helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _clean_sequence(seq: str) -> str:
        return re.sub(r"[^A-Z]", "", (seq or "").upper())

    def _registry_name(self, comp_id: Optional[str]) -> Optional[str]:
        """Return display name for a registry ID, or None if not found."""
        if not comp_id:
            return None
        e = self.registry.get(comp_id.lower())
        return e.get("name") if e else None

    def _resolve_component(self, input_str: str, category: str) -> Optional[CartComponentDetail]:
        input_str = (input_str or "").strip()
        if not input_str:
            return None

        # Registry hit
        elem = self.registry.get(input_str.lower())
        if elem:
            status = elem.get("sequence_status")
            seq = elem.get("sequence") or ""
            if status == "VERIFIED" and seq:
                return CartComponentDetail(
                    category=category,
                    provided_input=input_str,
                    resolved_name=elem.get("name", input_str),
                    sequence=self._clean_sequence(seq),
                    source="registry",
                    tier=elem.get("regulatory_tier", "T3"),
                    registry_id=elem.get("id"),
                )
            return CartComponentDetail(
                category=category,
                provided_input=input_str,
                resolved_name=elem.get("name", input_str),
                sequence="",
                source="registry_stub",
                tier=elem.get("regulatory_tier", "T3"),
                registry_id=elem.get("id"),
                warnings=[
                    f"Registry hit '{elem.get('id')}' has sequence_status={status or 'UNKNOWN'}; "
                    "no sequence available. Pick a verified alternative or paste a custom sequence."
                ],
            )

        # Custom AA sequence path
        cleaned = self._clean_sequence(input_str)
        if not cleaned:
            return CartComponentDetail(
                category=category, provided_input=input_str,
                resolved_name="Invalid Sequence", sequence="",
                source="custom", tier="Custom",
                warnings=[f"Provided input for {category} is neither a known ID nor a valid amino-acid sequence."],
            )
        return CartComponentDetail(
            category=category, provided_input="Custom Sequence",
            resolved_name=f"Custom {category}", sequence=cleaned,
            source="custom", tier="Custom",
        )

    def _process(self, field_val: Optional[str], category: str,
                 sink: List[CartComponentDetail],
                 warnings: List[str]) -> List[CartComponentDetail]:
        """Resolve a comma-separated slot value into a list of CartComponentDetail."""
        out: List[CartComponentDetail] = []
        if not field_val:
            return out
        for part in [x.strip() for x in field_val.split(",") if x.strip()]:
            detail = self._resolve_component(part, category)
            if detail:
                out.append(detail)
                sink.append(detail)
                if detail.warnings:
                    warnings.extend(detail.warnings)
        return out

    # ── cassette normalisation ────────────────────────────────────────────────
    @staticmethod
    def _legacy_to_cassettes(request: CartAssemblerRequest) -> List[CartCassetteSpec]:
        """Convert the legacy safety/armored/reg/logic/engmod fields to CartCassetteSpec.
        All legacy cassettes default to T2A → same transcript as the CAR ORF.
        The 'reg' (regulatory) slot is INTENTIONALLY skipped — promoters and IRES
        belong to the new vector_mode / cassette.linker_to_prev plumbing.
        """
        out: List[CartCassetteSpec] = []
        for slot_id, category in [
            ("safety",  "Safety Switch"),
            ("armored", "Armored Payload"),
            ("logic",   "Logic Gate"),
            ("engmod",  "Engineering Module"),
        ]:
            val = (getattr(request, slot_id, None) or "").strip()
            if val:
                out.append(CartCassetteSpec(id=val, category=category, linker_to_prev="T2A"))
        return out

    @staticmethod
    def _resolve_vector_defaults(request: CartAssemblerRequest) -> Dict[str, Optional[str]]:
        base = dict(_VECTOR_DEFAULTS.get(request.vector_mode, _VECTOR_DEFAULTS["lentivirus"]))
        if request.promoter is not None: base["promoter"] = request.promoter or None
        if request.polyA    is not None: base["polyA"]    = request.polyA    or None
        if request.wpre     is not None: base["wpre"]     = request.wpre     or None
        if request.utr_5    is not None: base["utr_5"]    = request.utr_5    or None
        if request.utr_3    is not None: base["utr_3"]    = request.utr_3    or None
        return base

    def _build_transcript_orf(self, name: str, kind: str,
                              orfs: List[List[CartComponentDetail]],
                              inner_linkers: List[str],
                              vec_defaults: Dict[str, Optional[str]],
                              override_promoter: Optional[str] = None) -> CartTranscript:
        """Assemble one transcript from a list of ORFs and the linker types BETWEEN them.

        - orfs[i] is the ordered component list for ORF i.
        - inner_linkers[i] joins ORF i to ORF i+1 (one of '2A' name or 'IRES').
        - 2A: protein-level GSG..NPGP peptide inserted between adjacent ORF AA strings;
              cDNA includes the back-translated 2A codons.
        - IRES: NO protein insertion (separate ribosome re-init); cDNA marker only.
        """
        assert len(inner_linkers) == max(0, len(orfs) - 1)
        # Flatten components for the transcript record
        flat_components: List[CartComponentDetail] = []
        for orf in orfs:
            flat_components.extend(orf)

        protein_parts: List[str] = []
        cdna_parts: List[str] = []

        for i, orf_comps in enumerate(orfs):
            aa = "".join(c.sequence for c in orf_comps if c.sequence)
            protein_parts.append(aa)
            cdna_parts.append(_backtranslate(aa))
            if i < len(inner_linkers):
                lk = inner_linkers[i]
                if lk in _TWO_A_PEPTIDES:
                    peptide = _TWO_A_PEPTIDES[lk]
                    protein_parts.append(peptide)
                    cdna_parts.append(_backtranslate(peptide))
                elif lk == "IRES":
                    cdna_parts.append(_IRES_PLACEHOLDER_DNA)

        protein_seq = "".join(protein_parts)
        cdna_seq    = "".join(cdna_parts)

        return CartTranscript(
            name=name, kind=kind, components=flat_components,
            protein_sequence=protein_seq, cdna_sequence=cdna_seq,
            protein_length=len(protein_seq), cdna_length=len(cdna_seq),
            promoter=override_promoter or vec_defaults.get("promoter"),
            utr_5=vec_defaults.get("utr_5"),
            utr_3=vec_defaults.get("utr_3"),
            wpre=vec_defaults.get("wpre"),
            polyA=vec_defaults.get("polyA"),
            inner_linkers=inner_linkers,
            orf_count=len(orfs),
        )

    # ── main entry ─────────────────────────────────────────────────────────────
    def assemble(self, request: CartAssemblerRequest) -> CartAssemblerResult:
        all_components: List[CartComponentDetail] = []
        warnings: List[str] = []
        vec_defaults = self._resolve_vector_defaults(request)

        # ── CAR ORF (Transcript 1, ORF 1) ────────────────────────────────────
        sp_input = request.sp or "CD8a_SP"
        car_orf_comps: List[CartComponentDetail] = []
        car_orf_comps += self._process(sp_input, "Signal Peptide", all_components, warnings)
        car_orf_comps += self._process(request.binder, "Binder", all_components, warnings)
        car_orf_comps += self._process(request.hinge,  "Hinge",  all_components, warnings)
        car_orf_comps += self._process(request.tm,     "Transmembrane", all_components, warnings)
        # Costim: now supports comma-separated tandem (e.g. "CD28_cyto,4-1BB_cyto")
        car_orf_comps += self._process(request.costim, "Costimulatory", all_components, warnings)
        car_orf_comps += self._process(request.activation, "Activation", all_components, warnings)

        # Linker info-only (not inserted into chain — internal to scFv binder)
        if request.linker:
            self._process(request.linker, "scFv Linker", all_components, warnings)

        # ── Cassette list normalization ─────────────────────────────────────
        cassettes: List[CartCassetteSpec] = list(request.cassettes or [])
        if not cassettes:
            cassettes = self._legacy_to_cassettes(request)

        # ── Group cassettes into transcripts based on linker_to_prev ─────────
        # Transcript-1 = CAR ORF. Its 'next' linker (i.e. the linker connecting
        # CAR ORF to the FIRST cassette) is taken from cassette[0].linker_to_prev.
        # A 'new_promoter' linker on cassette[i] starts a NEW transcript.
        transcripts: List[CartTranscript] = []

        # transcript_orfs: list of (ORF components, inner_linker_type_before_NEXT_ORF or None)
        # We accumulate into the *current* transcript; on 'new_promoter' we flush.
        cur_orfs: List[List[CartComponentDetail]] = [car_orf_comps]
        cur_links: List[str] = []
        cur_promoter_override: Optional[str] = None  # transcript-1 uses vec_defaults

        def _flush(name: str, kind: str, promoter_override: Optional[str]):
            if not cur_orfs:
                return
            t = self._build_transcript_orf(
                name=name, kind=kind,
                orfs=cur_orfs[:], inner_linkers=cur_links[:],
                vec_defaults=vec_defaults,
                override_promoter=promoter_override,
            )
            transcripts.append(t)

        car_name = f"{request.project_name} CAR ORF"
        next_transcript_idx = 2  # for naming Transcript 2, 3, ...

        for cas in cassettes:
            cas_comps: List[CartComponentDetail] = []
            # Per-cassette signal peptide (optional)
            if cas.sp:
                cas_comps += self._process(cas.sp, "Signal Peptide", all_components, warnings)
            cas_comps += self._process(cas.id, cas.category or "Cassette", all_components, warnings)
            if not cas_comps:
                continue  # skip empty / unresolved
            linker = (cas.linker_to_prev or "T2A").upper() if cas.linker_to_prev != "new_promoter" else "new_promoter"
            if linker in ("T2A", "P2A", "F2A", "E2A", "IRES"):
                # Same transcript: add as new ORF, link with this linker type
                cur_links.append(linker)
                cur_orfs.append(cas_comps)
            elif linker == "new_promoter":
                # Flush current transcript, start a new one with this cassette
                if len(transcripts) == 0:
                    _flush(car_name, "car_orf", None)
                else:
                    _flush(f"Transcript {next_transcript_idx - 1} (cassette)", "cassette", cur_promoter_override)
                next_transcript_idx += 1
                cur_orfs = [cas_comps]
                cur_links = []
                cur_promoter_override = cas.promoter or vec_defaults.get("promoter")
            else:
                warnings.append(f"Unknown linker_to_prev '{cas.linker_to_prev}' on cassette {cas.id}; defaulting to T2A.")
                cur_links.append("T2A")
                cur_orfs.append(cas_comps)

        # Flush the final transcript
        if len(transcripts) == 0:
            _flush(car_name, "car_orf", None)
        else:
            _flush(f"Transcript {next_transcript_idx - 1} (cassette)", "cassette", cur_promoter_override)

        # ── Topology / compatibility checks ─────────────────────────────────
        ids_present = {c.registry_id for c in all_components if c.registry_id}
        cd8_hinge  = ids_present & {"CD8a_Long", "CD8a_Short"}
        cd28_hinge = ids_present & {"CD28_Medium"}
        cd28_tm = "CD28_TM" in ids_present
        cd8_tm  = "CD8a_TM" in ids_present
        if cd8_hinge and cd28_tm:
            warnings.append(
                "Topology: CD8α hinge paired with CD28 TM — uncommon clinically. "
                "Approved pairings are CD8α-hinge+CD8α-TM (Kymriah) or CD28-hinge+CD28-TM (Yescarta)."
            )
        if cd28_hinge and cd8_tm:
            warnings.append(
                "Topology: CD28 hinge paired with CD8α TM — uncommon clinically; "
                "consider CD28-hinge+CD28-TM or CD8α-hinge+CD8α-TM."
            )

        # Costim count advisory
        costim_count = sum(1 for c in all_components if c.category == "Costimulatory")
        if costim_count > 3:
            warnings.append(
                f"{costim_count} costimulatory domains in tandem — clinically tested 2nd-gen has 1, "
                "3rd/4th-gen typically uses 2 (e.g. CD28+4-1BB). >3 is research-stage only."
            )

        custom_count = sum(1 for c in all_components if c.source == "custom")
        if custom_count:
            warnings.append(
                f"{custom_count} custom (non-registry) sequence(s) included — construct cannot be tiered against the SSOT registry."
            )

        # ── Full-vector polyprotein / cDNA view (concat all transcripts) ────
        # Note: this is a "linear view" — it concatenates each transcript's protein
        # sequence with a T2A spacer marker (as a convenience for users wanting one
        # FASTA). For accurate vector design, use each transcript independently.
        full_protein_parts: List[str] = []
        full_cdna_parts: List[str] = []
        for i, t in enumerate(transcripts):
            if i > 0:
                full_protein_parts.append(f"--[next: {t.name}]--")
                full_cdna_parts.append(f"<<--TRANSCRIPT_BOUNDARY({t.promoter or 'no_promoter'})-->>")
            full_protein_parts.append(t.protein_sequence)
            full_cdna_parts.append(t.cdna_sequence)
        full_vector_protein = "".join(full_protein_parts)
        full_vector_cdna    = "".join(full_cdna_parts)

        overall_status = "PASS" if not warnings else "WARN"

        return CartAssemblerResult(
            construct_name=request.project_name,
            full_sequence=transcripts[0].protein_sequence if transcripts else "",
            components=all_components,
            assembly_warnings=warnings,
            overall_status=overall_status,
            transcripts=transcripts,
            full_vector_protein=full_vector_protein,
            full_vector_cdna=full_vector_cdna,
            vector_mode=request.vector_mode,
        )
