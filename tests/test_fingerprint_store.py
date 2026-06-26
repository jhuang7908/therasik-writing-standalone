from core.fingerprint import DEFAULT_RELEASE_ID, FingerprintStore


def test_default_release_has_expected_families_and_core_counts():
    store = FingerprintStore.load_default()

    assert store.release.release_id == DEFAULT_RELEASE_ID
    assert store.list_families() == (
        "ada_immunogenicity",
        "bispecific_multispecific",
        "single_domain_vh_vhh",
        "vhvl_igg",
    )

    assert store.get_cohort("clinical_vhh_42").count == 42
    assert store.get_cohort("engineered_vh_24").count == 24
    assert store.get_cohort("single_vh_structural_nr_73").count == 73
    assert store.get_cohort("humanized_igg_458").count == 458
    assert store.get_cohort("genetically_human_igg_384").count == 384
    assert store.get_cohort("bispecific_igg_like_75").count == 75
    assert store.get_cohort("bispecific_scfv_like_50").count == 50
    assert store.get_cohort("ada_panel_136").count == 136


def test_reserved_cohorts_are_hidden_by_default():
    store = FingerprintStore.load_default()

    visible_ids = {c.cohort_id for c in store.list_cohorts("vhvl_igg")}
    all_ids = {c.cohort_id for c in store.list_cohorts("vhvl_igg", include_reserved=True)}

    assert "phage_display" not in visible_ids
    assert "phage_display" in all_ids
    assert store.get_cohort("phage_display").status == "reserved"
    assert not store.get_cohort("phage_display").design_support_allowed


def test_resolve_reports_fallback_explicitly():
    store = FingerprintStore.load_default()

    resolved = store.resolve(molecule_family="vhvl_igg", cohort_id="phage_display")

    assert resolved.fallback_used
    assert resolved.matched is not None
    assert resolved.matched.cohort_id == "humanized_igg_458"
    assert resolved.warning


def test_raw_single_vh_is_not_percentile_enabled():
    store = FingerprintStore.load_default()
    raw = store.get_cohort("single_vh_raw_138")

    assert raw.status == "raw_only"
    assert raw.count == 138
    assert not raw.design_support_allowed
    assert not raw.threshold_support_allowed
