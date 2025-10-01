"""Rebuild parquet for a given ticker from tmp_live_fetch/<T>.csv (if present).
Usage: py -3 tools/rebuild_parquet_from_csv.py A
"""
import sys
from pathlib import Path
import pandas as pd
import os

if len(sys.argv) < 2:
    print('Usage: rebuild_parquet_from_csv.py <TICKER>')
    sys.exit(2)

ticker = sys.argv[1]
repo = Path(__file__).resolve().parents[1]
csvp = repo / 'tmp_live_fetch' / f"{ticker}.csv"
parq_dir = repo / 'data backup' / '_parquet'
parq_dir.mkdir(parents=True, exist_ok=True)
parq = parq_dir / f"{ticker}.parquet"

if not csvp.exists():
    print('CSV not found:', csvp)
    sys.exit(1)

print('Reading', csvp)
df = pd.read_csv(csvp)
# flatten column names
new_cols = []
for c in df.columns:
    if isinstance(c, tuple):
        parts = [str(x) for x in c if x is not None and x != '']
        new_cols.append('_'.join(parts) if parts else str(c))
    else:
        new_cols.append(str(c))
df.columns = new_cols

# find date column
date_col = None
for c in df.columns:
    if 'date' in c.lower() or c.lower() in ('datetime', 'time'):
        date_col = c
        break
if date_col is None:
    # try index
    try:
        df = df.reset_index()
        date_col = 'index'
    except Exception:
        pass

if date_col is None:
    print('Could not determine date column; aborting')
    sys.exit(2)

print('Using date column:', date_col)
try:
    df['date'] = pd.to_datetime(df[date_col], errors='coerce', utc=True)
except Exception:
    df['date'] = pd.to_datetime(df[date_col], errors='coerce')

# drop rows without date
df = df.dropna(subset=['date'])
# dedupe and sort
try:
    df = df.drop_duplicates(subset=['date'], keep='last')
except Exception:
    pass
try:
    df = df.sort_values('date').reset_index(drop=True)
except Exception:
    df = df.reset_index(drop=True)

# write parquet atomically
tmp = str(parq) + '.tmp'
print('Writing', parq)
try:
    df.to_parquet(tmp, index=False)
    os.replace(tmp, str(parq))
    print('Wrote parquet', parq)
    sys.exit(0)
except Exception as e:
    print('Failed to write parquet:', e)
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass
    sys.exit(3)
