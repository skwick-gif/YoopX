"""Check parquet files and last dates for a few sample tickers.
Prints: whether parquet exists, number of rows, first/last date, and sample rows.
"""
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.data_utils import get_last_date_for_ticker
import pandas as pd
import os

DATA_DIR = 'data backup'
TICKS = ['A', 'MSFT', 'TSLA']

print('Checking parquet files in', DATA_DIR)
for t in TICKS:
    pq = Path(DATA_DIR) / '_parquet' / f"{t}.parquet"
    print('\n---', t, '---')
    print('parquet exists:', pq.exists())
    if pq.exists():
        try:
            df = pd.read_parquet(pq)
            print('rows:', len(df))
            # show columns and dtypes
            print('columns:', list(df.columns))
            # try to show first and last date
            dates = None
            for c in ['date', 'Date', 'datetime', 'time']:
                if c in df.columns:
                    dates = pd.to_datetime(df[c], errors='coerce', utc=True)
                    break
            if dates is None:
                try:
                    idx = pd.to_datetime(df.index, errors='coerce', utc=True)
                    dates = idx
                except Exception:
                    dates = None
            if dates is not None and not dates.isna().all():
                print('first date:', str(dates.min()))
                print('last date:', str(dates.max()))
            else:
                print('could not determine date column/index')
            # print head and tail
            print('\nhead:')
            print(df.head(3).to_string(index=False))
            print('\ntail:')
            print(df.tail(3).to_string(index=False))
        except Exception as e:
            print('failed to read parquet:', e)
    else:
        # fallback: check top-level csv/json
        j = Path(DATA_DIR) / f"{t}.json"
        c = Path(DATA_DIR) / f"{t}.csv"
        if j.exists():
            print('found top-level json file')
        if c.exists():
            print('found top-level csv file')
    # print last date via helper
    try:
        ld = get_last_date_for_ticker(DATA_DIR, t)
        print('get_last_date_for_ticker ->', ld)
    except Exception as e:
        print('error calling get_last_date_for_ticker:', e)

print('\nDone.')
