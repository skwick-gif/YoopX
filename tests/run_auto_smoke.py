"""Smoke test: load 5 random symbol JSONs from 'data backup', run the auto_discovery worker synchronously,
and write results to tests/auto_smoke_results.csv. This script runs headless (no UI).
"""
import os, json, random, csv
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_BACKUP = ROOT / 'data backup'
OUT_CSV = ROOT / 'tests' / 'auto_smoke_results.csv'

# find json files
json_files = [p for p in DATA_BACKUP.iterdir() if p.suffix.lower() == '.json']
if not json_files:
    print('No json files found in', DATA_BACKUP)
    raise SystemExit(1)

chosen = random.sample(json_files, min(5, len(json_files)))
print('Chosen symbols:', [p.name for p in chosen])

data_map = {}
for p in chosen:
    sym = p.stem
    try:
        with open(p, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        daily_list = None
        if isinstance(raw, dict) and 'price' in raw:
            if isinstance(raw['price'], dict) and 'yahoo' in raw['price'] and 'daily' in raw['price']['yahoo']:
                daily_list = raw['price']['yahoo']['daily']
            elif 'daily' in raw['price']:
                daily_list = raw['price']['daily']
        if daily_list is not None:
            df = pd.DataFrame(daily_list)
            # ensure required columns
            for c in ['Date','Open','High','Low','Close','Volume']:
                if c not in df.columns:
                    df[c] = None
            df.index = pd.to_datetime(df['Date'])
        else:
            # fallback: try to build a small OHLCV from available fields
            df = pd.DataFrame([raw])
        data_map[sym] = df
    except Exception as e:
        print('Failed loading', p.name, e)

# run worker synchronously
import sys
sys.path.insert(0, str(ROOT))
from ui.main_content.worker_thread import WorkerThread

params = {
    'min_trades': 0,
    'apply_bar_filters': False,
    'grid_json': '',
}

# instantiate worker and capture emitted results synchronously
w = WorkerThread('auto_discovery', params, data_map)
captured = {}
def _capture(rows):
    captured['rows'] = rows

w.results_ready.connect(_capture)
# call synchronously
w.run_auto_discovery()
rows = captured.get('rows', [])

print('Found', len(rows or []), 'rows')
# write CSV
if rows:
    keys = ['Symbol','Strategy','Params','CAGR','Sharpe','WinRate','MaxDD','Trades']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as cf:
        writer = csv.DictWriter(cf, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            out = {k: r.get(k,'') for k in keys}
            writer.writerow(out)
    print('Wrote', OUT_CSV)
else:
    print('No results to write')
