"""
Reference retrieval and verification subpackage.

Three layers (must always run in this order):

  Layer 1 — pubmed_client / crossref_client
            real-world lookup against NCBI eutils and CrossRef
  Layer 2 — verify
            embedding-based semantic check that the retrieved
            article actually matches the topic phrase Claude requested
  Layer 3 — format
            deterministic, journal-specific reference rendering
            via journal_specs.format_reference (no LLM)

The LLM is NEVER allowed to produce PMID, DOI, or formatted citation
text directly.  It can only emit topic placeholders that this package
resolves into real identifiers.
"""
