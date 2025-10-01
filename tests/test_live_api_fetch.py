"""Live API fetch test using Polygon and AlphaVantage keys from environment.

Set environment variables POLYGON_API_KEY and/or ALPHAVANTAGE_API_KEY before running.
"""
import os
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.api_fetchers import fetch_via_apis
from config.keys_loader import load_keys


def pick_random_tickers(n=5):
    data_dir = Path('data backup')
    files = [p.name for p in data_dir.iterdir() if p.suffix.lower() == '.json']
    names = [f[:-5] for f in files]
    random.shuffle(names)
    return names[:n]


def main():
    providers = ['polygon', 'alphavantage']
    keys = load_keys()
    tickers = pick_random_tickers(5)
    date_from = (datetime.utcnow() - timedelta(days=180)).strftime('%Y-%m-%d')
    print('Using providers order:', providers)
    print('API keys found:', {k: bool(v) for k, v in keys.items()})
    results = []
    for t in tickers:
        print(f"Fetching {t} from APIs since {date_from} ...")
        df, meta = fetch_via_apis(t, date_from, providers=providers, keys=keys)
        n = int(len(df)) if df is not None else 0
        print(f"Result {t}: rows={n}, meta={meta}\n")
        results.append({'ticker': t, 'rows': n, 'meta': meta})

    print('Summary:')
    for r in results:
        print(r)


if __name__ == '__main__':
    main()
