# Small dry-run network check for daily update logic
# This script uses the same date_from logic as the worker: last_date+1 or default 2024-01-01

from data.fetchers import fetch_yahoo_since, fetch_scrape_since
from data.data_utils import get_last_date_for_ticker
import pandas as pd
import sys

DATA_DIR = 'data backup'  # adjust if your data root is different

TICKERS = ['A', 'MSFT', 'TSLA', 'AMZN', 'GOOGL']

print('Starting dry-run network check...')
for t in TICKERS:
    last = None
    try:
        last = get_last_date_for_ticker(DATA_DIR, t)
    except Exception as e:
        print(f'{t}: error checking last date: {e}')

    if last is not None:
        try:
            ld = pd.to_datetime(last, utc=True)
            date_from = (ld + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        except Exception:
            date_from = '2024-01-01'
    else:
        date_from = '2024-01-01'

    print(f"Ticker {t}: last={last} => date_from={date_from}")

    # try yfinance first
    df, meta = fetch_yahoo_since(t, date_from)
    print(f" yahoo: rows={meta.get('n_rows')} meta={meta.get('error') if meta.get('error') else meta.get('source')} ")
    if (df is None or df.empty) and meta.get('error'):
        df2, meta2 = fetch_scrape_since(t, date_from)
        print(f" scrape: rows={meta2.get('n_rows')} meta={meta2.get('error') if meta2.get('error') else meta2.get('source')}")

print('Dry-run network check complete.')
