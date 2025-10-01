import sys
sys.path.insert(0, r'c:\MyProjects\YoopX Claude')
import pandas as pd
from data.data_utils import get_last_date_for_ticker
from pathlib import Path
for t in ['A','MSFT','TSLA']:
    p = Path('data backup') / '_parquet' / f"{t}.parquet"
    print('---', t, 'parquet exists?', p.exists())
    if p.exists():
        try:
            df = pd.read_parquet(p)
            print('columns:', list(df.columns)[:10])
            print('len:', len(df))
            if 'date' in df.columns:
                try:
                    last = pd.to_datetime(df['date'], errors='coerce', utc=True).max()
                except Exception:
                    last = None
            else:
                # try index
                try:
                    idx = pd.to_datetime(df.index, errors='coerce', utc=True)
                    last = idx.max() if not idx.isna().all() else None
                except Exception:
                    last = None
            print('inferred last date from parquet:', str(last))
        except Exception as e:
            print('failed to read parquet:', e)
    else:
        print('parquet missing')
    # check get_last_date_for_ticker helper
    try:
        helper = get_last_date_for_ticker('data backup', t)
        print('get_last_date_for_ticker returned:', helper)
    except Exception as e:
        print('helper error:', e)
    print()
