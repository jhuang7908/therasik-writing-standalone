def clean_sequence(seq: str) -> str:
    """、，"""
    valid = set("ACDEFGHIKLMNPQRSTVWY")
    seq = seq.upper.strip
    seq = "".join(c for c in seq if c in valid)
    return seq





















