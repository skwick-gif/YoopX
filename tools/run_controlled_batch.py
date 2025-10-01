"""Controlled batch runner for daily update (safe, sequential).
Selects up to N tickers from the data folder and runs the fetch+merge pipeline with shared limiter.
Writes a timestamped log to tools/batch_run_<ts>.log and prints a short summary.
"""
import sys
from pathlib import Path
import random
from datetime import datetime
repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from data.data_utils import list_tickers_from_folder, get_last_date_for_ticker, safe_append_parquet
from data.fetchers import fetch_yahoo_since, fetch_scrape_since
from data.api_fetchers import fetch_via_apis
from data.rate_limiter import GLOBAL_RATE_LIMITER
from config.keys_loader import load_keys
import pandas as pd
import time

OUTDIR = Path('tmp_live_fetch')
OUTDIR.mkdir(exist_ok=True)
LOGDIR = Path('tools')
LOGDIR.mkdir(exist_ok=True)

N = 50
if len(sys.argv) > 1:
    try:
        N = int(sys.argv[1])
    except Exception:
        pass

stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
LOG = LOGDIR / f'batch_run_{stamp}.log'
keys = load_keys()

def run_batch(n=50):
    tickers = list_tickers_from_folder('data backup')
    if not tickers:
        print('No tickers found in data backup')
        return
    random.shuffle(tickers)
    sel = tickers[:n]
    results = []
    with LOG.open('a', encoding='utf-8') as f:
        f.write(f"\n--- batch_run {stamp} N={n} ---\n")
        i = 0
        for t in sel:
            i += 1
            f.write(f"{datetime.utcnow().isoformat()}Z START {t} ({i}/{len(sel)})\n")
            print(f"[{i}/{len(sel)}] Processing {t}...")
            # compute date_from
            last = get_last_date_for_ticker('data backup', t)
            if last is not None:
                try:
                    ld = pd.to_datetime(last, utc=True)
                    date_from = (ld + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                except Exception:
                    date_from = '2024-01-01'
            else:
                date_from = '2024-01-01'
            f.write(f" date_from={date_from}\n")

            meta_used = None
            df = None
            meta = {}
            # yahoo
            try:
                GLOBAL_RATE_LIMITER.wait('yahoo')
            except Exception:
                pass
            try:
                df, meta = fetch_yahoo_since(t, date_from)
            except Exception as e:
                df, meta = None, {'error': str(e)}
            if df is None or df.empty:
                f.write(f" yahoo empty/error: {meta.get('error')}\n")
                # try scrape
                try:
                    GLOBAL_RATE_LIMITER.wait('scrape')
                except Exception:
                    pass
                try:
                    df2, meta2 = fetch_scrape_since(t, date_from)
                except Exception as e:
                    df2, meta2 = None, {'error': str(e)}
                if df2 is not None and not df2.empty:
                    df, meta = df2, meta2
                else:
                    f.write(f" scrape empty/error: {meta2.get('error')}\n")
            else:
                f.write(f" yahoo rows={meta.get('n_rows')}\n")

            # fallback to APIs if still empty
            if (df is None or df.empty):
                if any(keys.values()):
                    try:
                        GLOBAL_RATE_LIMITER.wait('api')
                    except Exception:
                        pass
                    try:
                        df_api, meta_api = fetch_via_apis(t, date_from, providers=None, keys=keys)
                    except Exception as e:
                        df_api, meta_api = None, {'error': str(e)}
                    if df_api is not None and not df_api.empty:
                        df, meta = df_api, meta_api
                        f.write(f" api rows={meta.get('n_rows')} provider={meta.get('used_provider')}\n")
                    else:
                        f.write(f" api empty/error: {meta_api.get('error')}\n")
                else:
                    f.write(' no API keys available for fallback\n')

            nrows = int(len(df)) if df is not None and not df.empty else 0
            f.write(f" fetched_rows={nrows} provider={meta.get('source')}\n")

            merged = False
            if df is not None and not df.empty:
                # write tmp csv
                try:
                    fn = OUTDIR / f"{t}.csv"
                    df.to_csv(fn, index=False)
                    f.write(f" wrote tmp csv {fn}\n")
                except Exception as e:
                    f.write(f" failed to write tmp csv: {e}\n")

                # merge via safe_append_parquet
                try:
                    ok = safe_append_parquet('data backup', t, df, date_col='date')
                    merged = bool(ok)
                    f.write(f" merged: {merged}\n")
                except Exception as e:
                    f.write(f" merge failed: {e}\n")
            else:
                f.write(' no new data to merge\n')

            results.append({'ticker': t, 'rows': nrows, 'provider': meta.get('source'), 'merged': merged, 'meta': meta})
            f.write(f" END {t} summary: rows={nrows} merged={merged}\n")
            # small pause to avoid bursts
            time.sleep(0.5)

    # print short summary
    print('\nBatch complete. Summary:')
    for r in results:
        print(r)
    print('\nDetailed log written to', LOG)

if __name__ == '__main__':
    run_batch(N)
