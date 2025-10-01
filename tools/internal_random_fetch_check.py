import os, random, json, sys, math, traceback
import pandas as pd
from datetime import datetime, timedelta

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))
base_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(base_dir)
sys.path.insert(0, root_dir)

from data.data_utils import list_tickers_from_folder, get_last_date_for_ticker
from data.fetch_manager import fetch_ohlcv_with_fallback

DATA_DIR = os.path.join(root_dir, 'data backup')
SAMPLE_SIZE = 6
MAX_ATTEMPTS = 20
random.seed()

if not os.path.isdir(DATA_DIR):
    print("DATA_DIR not found:", DATA_DIR)
    sys.exit(1)

all_tickers = list_tickers_from_folder(DATA_DIR)
if not all_tickers:
    print("No tickers discovered under data backup")
    sys.exit(1)

random.shuffle(all_tickers)

chosen = []
tried = 0
while len(chosen) < SAMPLE_SIZE and tried < MAX_ATTEMPTS and all_tickers:
    t = all_tickers.pop()
    # simple filter: avoid extremely short symbols that sometimes cause provider issues
    if not t or len(t) < 2:
        continue
    chosen.append(t)
    tried += 1

print(f"Chosen tickers ({len(chosen)}): {', '.join(chosen)}")

results = []
for t in chosen:
    last_date = get_last_date_for_ticker(DATA_DIR, t)
    # choose a date_from 30 days before last (or fallback start) to force some data return
    if last_date is not None:
        try:
            dt_last = pd.to_datetime(last_date, utc=True)
            date_from = (dt_last - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
        except Exception:
            date_from = '2024-01-01'
    else:
        date_from = '2024-01-01'

    df, meta = fetch_ohlcv_with_fallback(t, date_from, use_apis=True)
    ok = df is not None and not df.empty
    row_count = int(len(df)) if ok else 0
    first_date = str(df['date'].min()) if ok and 'date' in df.columns else None
    last_date_new = str(df['date'].max()) if ok and 'date' in df.columns else None
    # basic continuity check (rough) over last 15 business days
    continuity_flag = None
    missing_days = None
    if ok and 'date' in df.columns:
        try:
            dsub = df.sort_values('date').tail(40)  # last 40 rows
            dates_norm = dsub['date'].dt.normalize().tolist()
            bd_range = pd.bdate_range(start=dates_norm[0], end=dates_norm[-1]) if dates_norm else []
            have = set(dates_norm)
            missing = [d for d in bd_range if d not in have]
            missing_days = [d.strftime('%Y-%m-%d') for d in missing]
            continuity_flag = len(missing) <= max(2, int(len(bd_range)*0.1))
        except Exception:
            pass
    results.append({
        'ticker': t,
        'requested_from': date_from,
        'provider_used': meta.get('provider_used'),
        'rows': row_count,
        'first_date': first_date,
        'last_date': last_date_new,
        'continuity_ok': continuity_flag,
        'missing_recent_days': missing_days[:8] if missing_days else [],
        'cert_error': meta.get('cert_error'),
        'error_chain': meta.get('chain'),
        'had_error': not ok,
    })

# Summary
successes = sum(1 for r in results if not r['had_error'] and r['rows'] > 0)
print('\nSUMMARY:')
print(f"  Success {successes}/{len(results)}")
providers = {}
for r in results:
    providers[r['provider_used']] = providers.get(r['provider_used'], 0) + 1
print('  Providers distribution:', providers)

# Pretty print each result
for r in results:
    print('\n---', r['ticker'], '---')
    for k,v in r.items():
        if k == 'ticker':
            continue
        print(f"{k}: {v}")

# Export JSON if needed
os.makedirs('logs', exist_ok=True)
with open('logs/internal_random_fetch_check.json','w',encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('\nSaved detailed results to logs/internal_random_fetch_check.json')
