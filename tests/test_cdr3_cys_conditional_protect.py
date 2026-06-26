from core.vhh_humanization import get_cdr3_aware_protected_positions


def test_extra_long_cdr3_adds_49_only_when_cys_pair_detected:
    with_pair = get_cdr3_aware_protected_positions(
        24,
        "S1",
        cdr3_seq="AAACGGGGGGGGCYYY",
    )
    without_pair = get_cdr3_aware_protected_positions(
        24,
        "S1",
        cdr3_seq="AAACGGGGGGGGAYYY",
    )

    assert 49 in with_pair["protected_positions"]
    assert any("Pos 49 " in x for x in with_pair["dynamic_upgrades"])

    assert 49 not in without_pair["protected_positions"]
    assert any("Pos 49 not added" in x for x in without_pair["dynamic_upgrades"])


def test_regex_is_case_insensitive_via_upper_normalization:
    lower_seq = "aacgggggggggcyyy"  # contains c....c motif in lowercase
    out = get_cdr3_aware_protected_positions(24, "S1", cdr3_seq=lower_seq)
    assert 49 in out["protected_positions"]


def test_long_cdr3_gt17_also_protects_49_when_cys_pair_detected:
    out = get_cdr3_aware_protected_positions(
        19,
        "S1",
        cdr3_seq="AAACGGGGGGGGCYYY",
    )
    assert 49 in out["protected_positions"]
