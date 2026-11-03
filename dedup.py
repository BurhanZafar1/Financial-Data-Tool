"""Fuzzy duplicate detection for company and contact name fields.

Pipeline:
  1. Normalize each name (case, accents, punctuation, "&", legal suffixes).
  2. Block: only compare names that share a 4-character token prefix,
     so the number of comparisons grows far slower than n^2.
  3. Score each candidate pair with token-sort similarity (0 to 100),
     which tolerates typos and word reordering.
  4. Cluster pairs above the threshold with union-find and pick a
     canonical spelling for each cluster.

Usage:
  python dedup.py data/sample_companies.csv --column "Company Name" --threshold 90
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from typing import Iterable

import pandas as pd
from rapidfuzz import fuzz

# Legal and structural suffixes, mapped to one canonical form.
SUFFIXES = {
    "corporation": "corp", "corp": "corp",
    "incorporated": "inc", "inc": "inc",
    "company": "co", "co": "co",
    "limited": "ltd", "ltd": "ltd",
    "llc": "llc", "llp": "llp", "lp": "lp", "plc": "plc",
    "holdings": "holdings", "group": "group",
}
# Tokens too generic to be useful as blocking keys.
STOP_TOKENS = {"the", "and", "of"} | set(SUFFIXES.values())

_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")


def normalize(name: object, drop_suffixes: bool = True) -> str:
    """Return a comparison-ready version of a name."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = unicodedata.normalize("NFKD", str(name))
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b([a-z])\.(?=[a-z]\.)", r"\1", s)  # l.l.c. -> llc.
    s = _PUNCT.sub(" ", s)
    tokens = [SUFFIXES.get(t, t) for t in _SPACE.split(s.strip()) if t]
    if drop_suffixes:
        core = [t for t in tokens if t not in SUFFIXES.values()]
        tokens = core or tokens  # never reduce a name to nothing
    return " ".join(tokens)


def similarity(a: str, b: str) -> float:
    """Token-sort similarity on already normalized strings (0 to 100)."""
    return fuzz.token_sort_ratio(a, b)


def _blocking_keys(norm: str) -> set[str]:
    keys = {t[:4] for t in norm.split() if t not in STOP_TOKENS and len(t) >= 2}
    return keys or {norm[:4]}


def candidate_pairs(norms: list[str], max_block: int = 2000) -> set[tuple[int, int]]:
    """Index pairs that share at least one blocking key.

    Blocks larger than max_block are skipped to bound runtime; names in
    such a block are still compared through their other keys.
    """
    blocks: dict[str, list[int]] = defaultdict(list)
    for i, n in enumerate(norms):
        if n:
            for k in _blocking_keys(n):
                blocks[k].append(i)
    pairs: set[tuple[int, int]] = set()
    for members in blocks.values():
        if 1 < len(members) <= max_block:
            pairs.update(combinations(members, 2))
    return pairs


def find_duplicate_pairs(names: Iterable[object], threshold: float = 90) -> pd.DataFrame:
    """Score candidate pairs of unique names and keep those >= threshold."""
    uniq = list(dict.fromkeys(str(n) for n in names if not pd.isna(n) and str(n).strip()))
    norms = [normalize(n) for n in uniq]
    rows = []
    for i, j in candidate_pairs(norms):
        score = 100.0 if norms[i] == norms[j] else similarity(norms[i], norms[j])
        if score >= threshold:
            rows.append((uniq[i], uniq[j], round(score, 1)))
    out = pd.DataFrame(rows, columns=["name_1", "name_2", "similarity"])
    return out.sort_values(["similarity", "name_1"], ascending=[False, True]).reset_index(drop=True)


def cluster(names: Iterable[object], pairs: pd.DataFrame) -> pd.DataFrame:
    """Group names connected by matched pairs; return name -> cluster mapping.

    The canonical name of a cluster is its most frequent spelling in the
    input (ties broken by first appearance).
    """
    raw = [str(n) for n in names if not pd.isna(n) and str(n).strip()]
    counts = Counter(raw)
    order = list(dict.fromkeys(raw))
    parent = {n: n for n in order}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs[["name_1", "name_2"]].itertuples(index=False):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    groups: dict[str, list[str]] = defaultdict(list)
    for n in order:
        groups[find(n)].append(n)

    rows = []
    for cid, members in enumerate(groups.values(), start=1):
        canonical = max(members, key=lambda m: (counts[m], -order.index(m)))
        for m in members:
            rows.append((m, cid, canonical, len(members)))
    return pd.DataFrame(rows, columns=["name", "cluster_id", "canonical_name", "cluster_size"])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Find near-duplicate names in a CSV column.")
    p.add_argument("csv", help="input CSV path")
    p.add_argument("--column", default="Company Name", help="column to deduplicate")
    p.add_argument("--threshold", type=float, default=90, help="minimum similarity, 0 to 100")
    p.add_argument("--pairs-out", help="optional path to write matched pairs")
    p.add_argument("--clusters-out", help="optional path to write name-to-cluster mapping")
    args = p.parse_args(argv)

    df = pd.read_csv(args.csv)
    if args.column not in df.columns:
        print(f"Column '{args.column}' not found. Available: {', '.join(df.columns)}", file=sys.stderr)
        return 1

    names = df[args.column].tolist()
    pairs = find_duplicate_pairs(names, args.threshold)
    clusters = cluster(names, pairs)
    multi = clusters[clusters.cluster_size > 1]

    print(f"Rows: {len(df)}  unique names: {clusters.shape[0]}  "
          f"matched pairs: {len(pairs)}  duplicate clusters: {multi.cluster_id.nunique()}")
    if not pairs.empty:
        print(pairs.to_string(index=False))
    if args.pairs_out:
        pairs.to_csv(args.pairs_out, index=False)
    if args.clusters_out:
        clusters.to_csv(args.clusters_out, index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
