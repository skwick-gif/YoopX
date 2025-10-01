"""Dry-run test for DailyUpdateWorker: runs the worker.run() directly with merge_mode='none'
so no merges occur; fetched CSVs are written to tmp_live_fetch/."""
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.daily_update_worker import DailyUpdateWorker
from data.data_utils import get_catalog
import random


def pick_sample_tickers(data_dir='data backup', n=5):
    cat = get_catalog(data_dir)
    if cat is not None and 'ticker' in cat.columns:
        names = list(cat['ticker'].astype(str))
    else:
        # fallback: pick files
        p = Path(data_dir)
        names = [f.stem for f in p.glob('*.json')][:200]
    random.shuffle(names)
    return names[:n]


def main():
    data_dir = 'data backup'
    tickers = pick_sample_tickers(data_dir, 5)
    print('Sample tickers:', tickers)
    worker = DailyUpdateWorker(data_dir, merge_mode='none')
    # connect signals for simple printing
    worker.progress.connect(lambda p: print('Progress', p))
    worker.status.connect(lambda s: print('Status:', s))
    def done_cb(ticker, success, meta):
        print('Ticker done:', ticker, 'success=', success, 'meta=', meta)
    worker.ticker_done.connect(done_cb)
    def finished_cb(summary):
        print('Finished summary:', summary)
    worker.finished.connect(finished_cb)

    # run directly (synchronous) to test logic without QThread
    worker.run()


if __name__ == '__main__':
    main()
"""Dry-run test for DailyUpdateWorker: runs worker.run() directly with dry_run=True
so it fetches only missing data for tickers in the folder and writes CSVs to tmp_live_fetch/ for inspection.
"""
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data.daily_update_worker import DailyUpdateWorker


def main():
    data_dir = 'data backup'
    w = DailyUpdateWorker(data_dir, dry_run=True)
    # run synchronously (worker is designed to be used in a QThread but run() is callable)
    w.run()
    print('Dry run complete. Check tmp_live_fetch/ for CSVs and console for status signals.')


if __name__ == '__main__':
    main()
