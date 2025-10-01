"""Live fetch test: downloads recent daily data for a small set of tickers using our fetchers.

This script performs network calls to Yahoo Finance. Run only when you allow live tests.
"""
from pathlib import Path
from datetime import datetime, timedelta
import os

import sys
from pathlib import Path
# ensure repo root is on sys.path so local packages like `data` can be imported
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.fetchers import fetch_yahoo_since, fetch_scrape_since


def main():
    outdir = Path('tmp_live_fetch')
    outdir.mkdir(exist_ok=True)

    # choose 5 tickers from data backup for testing
    tickers = ['A', 'AMZN', 'MSFT', 'TSLA', 'GOOGL']
    # set date_from to 30 days ago to limit download size
    date_from = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')

    results = []
    for t in tickers:
        print(f"Fetching {t} since {date_from} via yfinance...")
        try:
            df, meta = fetch_yahoo_since(t, date_from)
        except Exception as e:
            print(f"fetch_yahoo_since raised: {e}")
            df, meta = None, {'error': str(e)}

        if df is None or df.empty:
            print(f"yfinance returned empty or error for {t}: {meta.get('error')}")
            print(f"Trying scrape fallback for {t}...")
            try:
                df2, meta2 = fetch_scrape_since(t, date_from)
            except Exception as e:
                print(f"fetch_scrape_since raised: {e}")
                df2, meta2 = None, {'error': str(e)}
            df = df2
            meta = meta2

        n = 0
        if df is not None and not df.empty:
            n = len(df)
            fn = outdir / f"{t}.csv"
            try:
                df.to_csv(fn, index=False)
            except Exception as e:
                print(f"Failed to write CSV for {t}: {e}")

        print(f"Result {t}: rows={n}, meta={meta}\n")
        results.append({'ticker': t, 'rows': n, 'meta': meta})

    print("Summary:")
    for r in results:
        print(r)


if __name__ == '__main__':
    main()
