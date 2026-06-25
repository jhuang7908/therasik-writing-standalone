"""

InSynBio console pricing SSOT (single source of truth).



Sync targets (must match):

  - api/static/pricing.html          (public rate card)

  - api/static/console.html          (REGISTRY.credits + serviceCreditCost)

  - api/static/therasik_console.html (REGISTRY.credits + serviceCreditCost)

  - api/routers/assistant.py         (brief/detail + free turns)

  - api/routers/auth.py              (signup wallet via TRIAL_SIGNUP_CREDITS)

  - Web_Projects/insynbio_com/insynbio_product_whitepaper_en.html (marketing copy)



Offline services (VAM, CDR redesign, AF2, HADDOCK, petization): no public price;

console shows credits=0 and "contact for quote" only.



Owner decisions 2026-05-31:

  - Knowledge atlases: $5.00 (500 credits) each

  - Bispecific VHH CMC: $100 (10,000 credits)

  - Signup: 30,000 credits (~$300 PAYG); .edu +20%; coupons separate

  - CMC: one service — snapshot 10k OR full developability+Smart-CMC 25k (not two products)

  - ADA: no billable service; assistant + ADA atlas reference only

"""



from __future__ import annotations



from typing import Any, Dict



PRICING_VERSION = "2026-05-31-owner-v3"



# ── Exchange rate ─────────────────────────────────────────────────────────────

CREDITS_PER_CNY = 50

USD_PER_1000_CREDITS = 10

CREDITS_PER_USD = 100



# ── Signup & assistant ────────────────────────────────────────────────────────

TRIAL_SIGNUP_CREDITS = 30_000

TRIAL_SIGNUP_EDU_BONUS_PCT = 0.20

TRIAL_ASSISTANT_FREE_TURNS = 10

ASSISTANT_BRIEF_CREDITS = 30

ASSISTANT_DETAIL_CREDITS = 120



# ── Knowledge hub ($5.00 per atlas lookup / export) ───────────────────────────

KNOWLEDGE_ATLAS_CREDITS = 500



# ── Humanization baseline (standard VH/VL = 1.0×) ─────────────────────────────

BASELINE_HUMANIZATION_CREDITS = 20_000



VHVL_HUMANIZATION_CREDITS: Dict[str, int] = {

    "quick_preview": 10_000,

    "standard_delivery": 20_000,

    "enhanced_rescue": 30_000,

}



VHH_HUMANIZATION_CREDITS: Dict[str, int] = {

    "quick_preview": 15_000,

    "standard_delivery": 30_000,

    "enhanced_rescue": 45_000,

}



# ── CMC (one service: snapshot-only vs developability + Smart-CMC) ───────────

CMC_SNAPSHOT_CREDITS = 10_000

CMC_SMART_ADDON_CREDITS = 15_000  # UI label: addon on top of snapshot

CMC_DEVELOPABILITY_CREDITS = CMC_SNAPSHOT_CREDITS + CMC_SMART_ADDON_CREDITS  # 25k total



# ── Subscriptions (USD) ───────────────────────────────────────────────────────

SUBSCRIPTIONS: Dict[str, Dict[str, Any]] = {

    "lab": {

        "monthly_usd": 149,

        "annual_usd": 1490,

        "monthly_credits": 80_000,

        "humanizations_per_month": 4,

    },

    "pro": {

        "monthly_usd": 399,

        "annual_usd": 3990,

        "monthly_credits": 220_000,

        "humanizations_per_month": 11,

    },

    "company": {

        "monthly_usd": 799,

        "annual_usd": 7990,

        "monthly_credits": 220_000,

        "humanizations_per_month": 11,

        "price_multiplier_vs_pro": 2,

        "note": "Same monthly credits as Pro; premium is commercial-use license + seats",

    },

}



# Console service id → default credits (before UI dynamic overrides)

SERVICE_CREDITS: Dict[str, int] = {

    # Knowledge hub

    "clinical-atlas": KNOWLEDGE_ATLAS_CREDITS,

    "target-atlas": KNOWLEDGE_ATLAS_CREDITS,

    "ada-atlas": KNOWLEDGE_ATLAS_CREDITS,

    "cmc-reference-atlas": KNOWLEDGE_ATLAS_CREDITS,

    # VH/VL

    "vhvl-humanization": VHVL_HUMANIZATION_CREDITS["standard_delivery"],

    "vhvl-recheck": 5_000,

    "segmentation-vhvl": 0,

    "fv-structural": 2_500,

    "cdna-optimization-igg": 1_000,

    # VHH

    "vhh-structural": 2_500,

    "vhh-segmentation": 0,

    "vhh-humanization": VHH_HUMANIZATION_CREDITS["standard_delivery"],

    "vhh-recheck": 5_000,

    "vh-to-vhh-conversion": 25_000,

    "cdna-optimization-vhh": 1_000,

    # Bispecific

    "bispecific-assembler": 12_000,

    "bispecific-tandem-assembler": 12_000,

    "tandem-smartlink": 5_000,

    "bispecific-analyzer": 5_000,

    "bispecific-vhh-cmc": 10_000,

    # CAR-T (all scenario entry points)

    "car-t-assembler": 10_000,

    "cart-exvivo-hema": 10_000,

    "cart-exvivo-solid": 10_000,

    "cart-exvivo-auto": 10_000,

    "cart-invivo-solid": 10_000,

    "cart-invivo-blood": 10_000,

    "cart-invivo-neuro": 10_000,

    "cart-invivo-auto": 10_000,

    "cart-invivo-multi": 10_000,

    # CMC — same debit whether via igg/vhh snapshot UI or cmc-optimization entry

    "igg-cmc-snapshot": CMC_SNAPSHOT_CREDITS,

    "vhh-cmc-snapshot": CMC_SNAPSHOT_CREDITS,

    "cmc-optimization": CMC_DEVELOPABILITY_CREDITS,

}



# Offline / internal — not on public pricing page

OFFLINE_SERVICE_IDS = frozenset({

    "af2-multimer",

    "haddock-peptide",

    "virtual-affinity-maturation",

    "cdr-redesign",

    "cart-vaccine-projects",

    "petization",

})





def humanization_credits(chain: str, mode: str) -> int:

    """chain: 'vhvl' | 'vhh'; mode: quick_preview | standard_delivery | enhanced_rescue."""

    table = VHH_HUMANIZATION_CREDITS if chain == "vhh" else VHVL_HUMANIZATION_CREDITS

    return int(table.get(mode, table["standard_delivery"]))





def cmc_snapshot_credits(*, smart: bool = False) -> int:

    return CMC_DEVELOPABILITY_CREDITS if smart else CMC_SNAPSHOT_CREDITS





def signup_credits_for_email(*, edu: bool = False) -> int:

    base = TRIAL_SIGNUP_CREDITS

    if edu:

        base = int(base * (1 + TRIAL_SIGNUP_EDU_BONUS_PCT))

    return base





def usd_to_credits(amount_usd: int) -> int:

    return int(amount_usd) * CREDITS_PER_USD





def pricing_catalog() -> Dict[str, Any]:

    return {

        "version": PRICING_VERSION,

        "rate": {

            "usd_per_1000_credits": USD_PER_1000_CREDITS,

            "credits_per_usd": CREDITS_PER_USD,

            "label": "$10 = 1,000 credits",

        },

        "trial_signup_credits": TRIAL_SIGNUP_CREDITS,

        "trial_signup_edu_bonus_pct": TRIAL_SIGNUP_EDU_BONUS_PCT,

        "trial_assistant_free_turns": TRIAL_ASSISTANT_FREE_TURNS,

        "knowledge_atlas_credits": KNOWLEDGE_ATLAS_CREDITS,

        "baseline_humanization_credits": BASELINE_HUMANIZATION_CREDITS,

        "humanization_vhvl": VHVL_HUMANIZATION_CREDITS,

        "humanization_vhh": VHH_HUMANIZATION_CREDITS,

        "cmc_snapshot_credits": CMC_SNAPSHOT_CREDITS,

        "cmc_developability_credits": CMC_DEVELOPABILITY_CREDITS,

        "cmc_smart_addon_credits": CMC_SMART_ADDON_CREDITS,

        "subscriptions": SUBSCRIPTIONS,

        "assistant": {

            "brief_credits": ASSISTANT_BRIEF_CREDITS,

            "detail_credits": ASSISTANT_DETAIL_CREDITS,

        },

        "service_credits": SERVICE_CREDITS,

        "offline_service_ids": sorted(OFFLINE_SERVICE_IDS),

        "notes": {

            "ada": "No billable ADA design service; use ADA Clinical Atlas + AI assistant",

            "cmc": "One CMC service: 10k snapshot or 25k with Smart-CMC (single debit)",

            "petization": "Internal only — not customer-facing",

            "ai_writing": "write.insynbio.com — no shared wallet credits yet",

        },

    }


