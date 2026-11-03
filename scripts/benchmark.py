"""Time the matcher on synthetic names (random words plus injected typos).

Run from the repo root:  python scripts/benchmark.py --n 20000
"""

import argparse
import random
import string
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dedup import candidate_pairs, cluster, find_duplicate_pairs, normalize  # noqa: E402


def synthetic_names(n: int, dup_share: float = 0.2, seed: int = 0) -> list[str]:
    rng = random.Random(seed)
    words = ["".join(rng.choices(string.ascii_lowercase, k=rng.randint(4, 9))) for _ in range(3000)]
    suffixes = ["Inc", "LLC", "Corp", "Partners", "Capital", "Group", ""]
    n_dup = int(n * dup_share)
    base = [f"{rng.choice(words).title()} {rng.choice(words).title()} {rng.choice(suffixes)}".strip()
            for _ in range(n - n_dup)]

    def typo(s: str) -> str:
        i = rng.randrange(len(s))
        return s[:i] + s[i + 1:]

    return base + [typo(rng.choice(base)) for _ in range(n_dup)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    args = ap.parse_args()

    names = synthetic_names(args.n)
    start = time.time()
    uniq = list(dict.fromkeys(names))
    n_candidates = len(candidate_pairs([normalize(x) for x in uniq]))
    pairs = find_duplicate_pairs(names)
    cluster(names, pairs)
    elapsed = time.time() - start
    all_pairs = len(uniq) * (len(uniq) - 1) // 2
    print(f"names={len(names):,} unique={len(uniq):,} candidate_pairs={n_candidates:,} "
          f"all_pairs={all_pairs:,} matched_pairs={len(pairs):,} seconds={elapsed:.1f}")


if __name__ == "__main__":
    main()
