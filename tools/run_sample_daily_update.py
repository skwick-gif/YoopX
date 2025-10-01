"""Run a small two-step daily update for a sample set of tickers.
This script: for each ticker
 - determines last date via get_last_date_for_ticker
 - computes date_from = last+1 or 2024-01-01
 - tries fetch_yahoo_since, then fetch_scrape_since, then fetch_via_apis (using config/keys_loader)
 - writes CSV to tmp_live_fetch/<ticker>.csv
 - calls safe_append_parquet to merge into data backup/_parquet/<ticker>.parquet

Run from repo root with PYTHONPATH set to the repo root.
"""
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.data_utils import get_last_date_for_ticker, safe_append_parquet
from data.fetchers import fetch_yahoo_since, fetch_scrape_since
from data.api_fetchers import fetch_via_apis
from config.keys_loader import load_keys
import pandas as pd
import pathlib

DATA_DIR = 'data backup'
TICKERS = ['A', 'MSFT', 'TSLA']

outdir = pathlib.Path('tmp_live_fetch')
outdir.mkdir(exist_ok=True)
keys = load_keys()

results = []
for t in TICKERS:
    print(f'--- {t} ---')
    last = get_last_date_for_ticker(DATA_DIR, t)
    if last is not None:
        try:
            ld = pd.to_datetime(last, utc=True)
            date_from = (ld + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        except Exception:
            date_from = '2024-01-01'
    else:
        date_from = '2024-01-01'
    print('date_from=', date_from)

    df, meta = fetch_yahoo_since(t, date_from)
    used = None
    if df is None or df.empty:
        if meta.get('error'):
            print('yahoo error:', meta.get('error'))
        # try scrape
        df, meta2 = fetch_scrape_since(t, date_from)
        if df is None or df.empty:
            if meta2.get('error'):
                print('scrape error:', meta2.get('error'))
            # try APIs
            df, meta3 = fetch_via_apis(t, date_from, providers=None, keys=keys)
            used = meta3.get('source') if meta3 else None
            if df is None or df.empty:
                print('api fetch returned no data or error', meta3)
        else:
            used = meta2.get('source')
    else:
        used = meta.get('source')

    nrows = int(len(df)) if df is not None and not df.empty else 0
    print(f'fetched rows={nrows} provider={used or meta.get("source")}')

    if df is not None and not df.empty:
        # write CSV
        fn = outdir / f"{t}.csv"
        try:
            df.to_csv(fn, index=False)
            print('wrote tmp csv ->', str(fn))
        except Exception as e:
            print('failed to write csv', e)
        # attempt safe append
        ok = safe_append_parquet(DATA_DIR, t, df, date_col='date')
        print('merged to parquet:', ok)
    else:
        print('no new data to merge')

    results.append({'ticker': t, 'rows': nrows, 'provider': used})

print('\nSummary:')
for r in results:
    print(r)

print('done')
