import pandas as pd

from dedup import cluster, find_duplicate_pairs, normalize


def test_normalize_handles_suffixes_punctuation_and_accents():
    assert normalize("Summit Ridge Corporation") == "summit ridge"
    assert normalize("Summit Ridge Corp.") == "summit ridge"
    assert normalize("Birch Creek Advisors L.L.C.") == "birch creek advisors"
    assert normalize("Harbor & Pine") == "harbor and pine"
    assert normalize("Café Lumière") == "cafe lumiere"
    assert normalize(None) == ""


def test_suffix_only_name_is_not_emptied():
    assert normalize("Company") == "co"


def test_reordered_and_misspelled_names_match():
    pairs = find_duplicate_pairs(
        ["Birch Creek Advisors", "Advisors Birch Creek", "Nortwind Capital", "Northwind Capital"],
        threshold=85,
    )
    matched = {frozenset(p) for p in pairs[["name_1", "name_2"]].itertuples(index=False)}
    assert frozenset({"Birch Creek Advisors", "Advisors Birch Creek"}) in matched
    assert frozenset({"Nortwind Capital", "Northwind Capital"}) in matched


def test_distinct_names_do_not_match_at_default_threshold():
    # At 85, "Ironwood Analytics" vs "Redwood Analytics" scores 85.7 because the
    # shared word inflates similarity. The default threshold of 90 separates them.
    pairs = find_duplicate_pairs(["Ironwood Analytics", "Redwood Analytics", "Bluefield Credit Union",
                                  "Bluefield Partners"], threshold=90)
    assert pairs.empty


def test_cluster_picks_most_frequent_spelling():
    names = ["Summit Ridge Corp", "Summit Ridge Corp", "Summit Ridge Corporation", "Cedar Valley Bank"]
    pairs = find_duplicate_pairs(names, threshold=90)
    clusters = cluster(names, pairs).set_index("name")
    assert clusters.loc["Summit Ridge Corporation", "canonical_name"] == "Summit Ridge Corp"
    assert clusters.loc["Cedar Valley Bank", "cluster_size"] == 1


def test_sample_file_runs():
    df = pd.read_csv("data/sample_companies.csv")
    pairs = find_duplicate_pairs(df["Company Name"], threshold=85)
    assert len(pairs) > 0
