# Run DailyUpdateWorker.run() synchronously on a small sample
from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.daily_update_worker import DailyUpdateWorker
from data.data_utils import list_tickers_from_folder

DATA_DIR = 'data backup'
# pick a small sample of tickers
all_t = list_tickers_from_folder(DATA_DIR)[:5]
print('sample tickers:', all_t)

w = DailyUpdateWorker(DATA_DIR, merge_mode='two-step', use_apis=True)
# connect simple print callbacks
w.progress.connect(lambda p: print('progress', p))
w.status.connect(lambda s: print('status', s))

def on_ticker(t, ok, meta):
    print('ticker_done', t, ok, meta.get('merge') if isinstance(meta, dict) else meta)

w.ticker_done.connect(on_ticker)

w.run()
print('done')
