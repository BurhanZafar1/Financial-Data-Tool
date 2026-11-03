# Company Name Duplicate Finder

Flags near-duplicate company and contact names in CRM exports so analysts can merge records instead of hunting for them by hand.

## The problem

CRM, ticketing and deal-tracking systems accumulate the same entity under several spellings: "Summit Ridge Corp." and "Summit Ridge Corporation", "Harbor & Pine" and "Harbor and Pine", or a dropped letter. Exact-match filters miss all of these. The result is double counting in reports, duplicate outreach, and a slow manual cleanup before any analysis can start. Small teams (development offices, lean deal teams, research assistants assembling a panel from several sources) feel this most because nobody owns data hygiene full time.

## What it does

- Normalizes names: case, accents, punctuation, "&" vs "and", and legal suffixes (Inc, LLC, Corp, Ltd, Co).
- Scores candidate pairs from 0 to 100 with token-sort similarity, which tolerates typos and reordered words.
- Groups matches into clusters and suggests a canonical spelling (the most frequent one in the file).
- Exports matched pairs and a copy of the original data with a `canonical_name` column for review.
- Runs as a Streamlit app (upload a CSV, pick a column, adjust the threshold) or as a command-line tool.

## How it works

1. **Normalize** each unique name (`dedup.normalize`).
2. **Block.** Comparing every pair of 20,000 names means about 200 million comparisons. Instead, each name is indexed by the first four characters of each meaningful word, and only names sharing a key are compared.
3. **Score** candidate pairs with `rapidfuzz.fuzz.token_sort_ratio` and keep those at or above the threshold.
4. **Cluster** with union-find so that A matches B and B matches C land in one group.

The logic lives in `dedup.py` and is independent of the UI, so it can be imported into a notebook or pipeline.

## Quickstart

```bash
git clone https://github.com/BurhanZafar1/financial-data-tool.git
cd financial-data-tool
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

python dedup.py data/sample_companies.csv          # command line
streamlit run app.py                               # web app
pytest -q                                          # tests
python scripts/benchmark.py --n 20000              # timing on synthetic data
```

CLI options: `--column` (default `Company Name`), `--threshold` (default 90), `--pairs-out`, `--clusters-out`.

## Configuration

None required. No API keys, no network calls; data stays on your machine.

## Example output

On the included synthetic sample (`data/sample_companies.csv`, 20 rows, all fictional names):

```
Rows: 20  unique names: 19  matched pairs: 11  duplicate clusters: 5
                         name_1                          name_2  similarity
           Advisors Birch Creek        Birch Creek Advisors LLC       100.0
           Birch Creek Advisors            Advisors Birch Creek       100.0
               Café Lumière LLC                    Cafe Lumiere       100.0
         Harbor & Pine Holdings        Harbor and Pine Holdings       100.0
       Summit Ridge Corporation               Summit Ridge Corp       100.0
     Northwind Capital Partners       Nortwind Capital Partners        98.0
     ...
```

`scripts/benchmark.py` on 20,000 synthetic names (random words with injected typos) on a cloud Linux VM:

```
names=20,000 unique=19,973 candidate_pairs=257,214 all_pairs=199,450,378 matched_pairs=3,468 seconds=3.1
```

Blocking cut the comparisons by roughly 775 times. Timing will vary by machine and data.

## Choosing a threshold

At 85, "Ironwood Analytics" and "Redwood Analytics" score 85.7 because the shared word inflates similarity. The default of 90 separates them while still catching single-letter typos (98) and suffix or reordering variants (100). Treat the output as a review queue, not an automatic merge.

## Limitations and next steps

- No labeled ground truth is included, so precision and recall are not measured. Next step: hand-label a sample of pairs and report precision and recall by threshold.
- Blocking misses pairs whose every word has a typo in its first four characters.
- Abbreviations that change the letters ("IBM" vs "International Business Machines") are not matched. A small alias table would cover common cases.
- Single-field matching only. Combining name with email domain, address or ZIP code would cut false positives.

## License

MIT. See [LICENSE](LICENSE).
