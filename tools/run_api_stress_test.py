"""Run a small stress test of API fetchers to validate rate-limiter/backoff behavior.
Writes a timestamped log to tools/api_stress_test.log
"""
from pathlib import Path
import sys
from datetime import datetime, timedelta
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.api_fetchers import fetch_via_apis
from config.keys_loader import load_keys
import time

LOG = Path('tools') / 'api_stress_test.log'
keys = load_keys()

# small sample tickers (existing in data backup)
TICKERS = ['A', 'MSFT', 'TSLA', 'AMZN', 'GOOGL']
# date_from recent to limit rows
date_from = (datetime.utcnow() - timedelta(days=90)).strftime('%Y-%m-%d')

with LOG.open('a', encoding='utf-8') as f:
    f.write(f"\n--- api_stress_test run at {datetime.utcnow().isoformat()}Z ---\n")
    for t in TICKERS:
        start = time.time()
        f.write(f"{datetime.utcnow().isoformat()}Z START {t} date_from={date_from}\n")
        try:
            df, meta = fetch_via_apis(t, date_from, providers=None, keys=keys)
            elapsed = time.time() - start
            f.write(f"{datetime.utcnow().isoformat()}Z END {t} rows={len(df) if df is not None else 0} meta={meta} elapsed={elapsed:.2f}s\n")
        except Exception as e:
            elapsed = time.time() - start
            f.write(f"{datetime.utcnow().isoformat()}Z ERROR {t} exc={e} elapsed={elapsed:.2f}s\n")
        # small pause between ticks to validate limiter across calls
        time.sleep(0.5)

print('stress test complete; see', str(LOG))
