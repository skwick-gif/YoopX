"""Repair parquet files by flattening nested/multiindex columns and normalizing the date column.

Usage: run from repo root. The script will process a list of tickers (default sample) and overwrite
parquet files atomically after cleaning.
"""
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd
import os

DATA_DIR = Path('data backup')
PQ_DIR = DATA_DIR / '_parquet'
TICKS = ['A', 'MSFT', 'TSLA']

def flatten_table_to_df(pq_path: Path) -> pd.DataFrame:
    # Read with pyarrow and flatten nested columns
    table = pq.read_table(str(pq_path))
    try:
        flat = table.flatten()
    except Exception:
        flat = table
    df = flat.to_pandas()
    # normalize column names
    new_cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            parts = [str(x) for x in c if x is not None and x != '']
            new_cols.append('_'.join(parts) if parts else str(c))
        else:
            new_cols.append(str(c))
    df.columns = new_cols
    return df


def ensure_date_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    # find a date-like column
    date_col = None
    for c in d.columns:
        if 'date' in c.lower() or c.lower() in ('datetime', 'time'):
            date_col = c
            break
    if date_col is None:
        # try index
        try:
            idx = pd.to_datetime(d.index, errors='coerce', utc=True)
            if not idx.isna().all():
                d = d.reset_index()
                d['date'] = idx
            else:
                d['date'] = pd.NaT
        except Exception:
            d['date'] = pd.NaT
    else:
        try:
            d['date'] = pd.to_datetime(d[date_col], errors='coerce', utc=True)
        except Exception:
            d['date'] = pd.to_datetime(d[date_col], errors='coerce')
    # drop NaT dates
    try:
        d = d.dropna(subset=['date'])
    except Exception:
        pass
    # drop duplicates by date, keep last
    try:
        d = d.drop_duplicates(subset=['date'], keep='last')
    except Exception:
        pass
    # sort
    try:
        d = d.sort_values('date').reset_index(drop=True)
    except Exception:
        d = d.reset_index(drop=True)
    return d


def repair_one(ticker: str) -> bool:
    pq_path = PQ_DIR / f"{ticker}.parquet"
    if not pq_path.exists():
        print(f"{ticker}: parquet not found, skipping")
        return False
    print(f"Repairing {ticker}: reading {pq_path}")
    try:
        df = flatten_table_to_df(pq_path)
    except Exception as e:
        print(f"{ticker}: failed to read parquet via pyarrow: {e}")
        return False
    print(f"{ticker}: read {len(df)} rows, columns={list(df.columns)[:8]}")
    df2 = ensure_date_and_clean(df)
    print(f"{ticker}: after clean rows={len(df2)} last_date={df2['date'].max() if not df2.empty else 'None'}")
    # write back atomically
    tmp = str(pq_path) + '.tmp'
    try:
        df2.to_parquet(tmp, index=False)
        os.replace(tmp, str(pq_path))
        print(f"{ticker}: repaired and wrote parquet")
        return True
    except Exception as e:
        print(f"{ticker}: failed to write parquet: {e}")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


if __name__ == '__main__':
    for t in TICKS:
        repair_one(t)
    print('Done.')
