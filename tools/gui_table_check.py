#!/usr/bin/env python3
"""Check that Scan and Backtest QTableWidgets are populated after workers finish."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from main_content import MainContent


def find_samples(max_files=3):
    candidates = [os.path.join(ROOT, 'data'), os.path.join(ROOT, 'data backup'), ROOT]
    for c in candidates:
        if os.path.isdir(c):
            files = [os.path.join(c, f) for f in sorted(os.listdir(c)) if f.lower().endswith(('.json', '.csv', '.parquet'))]
            if files:
                return files[:max_files]
    return []


def load_map(paths):
    import pandas as pd
    out = {}
    for p in paths:
        key = os.path.splitext(os.path.basename(p))[0]
        df = None
        try:
            if p.lower().endswith('.parquet'):
                df = pd.read_parquet(p)
            elif p.lower().endswith('.json'):
                df = pd.read_json(p)
            elif p.lower().endswith('.csv'):
                df = pd.read_csv(p)
        except Exception:
            df = None
        out[key] = df
    return out


def wait_for_worker(worker, timeout=30.0):
    from PySide6.QtTest import QTest
    result = {'rows': None}
    def on_res(rows):
        result['rows'] = rows
    worker.results_ready.connect(on_res)
    waited = 0.0
    while result['rows'] is None and waited < timeout:
        QTest.qWait(200)
        waited += 0.2
    return result['rows']


def run_check():
    app = QApplication([])
    mc = MainContent()
    samples = find_samples()
    if not samples:
        print('No sample data found; aborting')
        return
    mc.data_map = load_map(samples)
    print('Loaded symbols:', list(mc.data_map.keys()))

    # Start scan
    scan_params = {'patterns': 'ENGULFING,DOJI', 'lookback': 30}
    mc.scan_tab.start_scan_worker(scan_params, mc.data_map)
    sw = getattr(mc.scan_tab, 'worker_thread', None)
    if sw:
        rows = wait_for_worker(sw, timeout=30.0)
        print('scan_worker emitted rows:', len(rows) if rows else None)
    else:
        print('No scan worker')

    # After worker finishes, inspect the table rowCount
    try:
        print('Scan table rows:', mc.scan_tab.results_table.rowCount())
    except Exception as e:
        print('Failed to read scan table rows:', e)

    # Start backtest
    bt_params = {'start_cash': 10000.0, 'commission': 0.0005, 'slippage': 0.0005, 'symbols': ','.join(list(mc.data_map.keys()))}
    mc.backtest_tab.start_backtest_worker(bt_params, mc.data_map)
    bw = getattr(mc.backtest_tab, 'worker_thread', None)
    if bw:
        rows = wait_for_worker(bw, timeout=60.0)
        print('backtest_worker emitted rows:', len(rows) if rows else None)
    else:
        print('No backtest worker')

    try:
        print('Backtest table rows:', mc.backtest_tab.results_table.rowCount())
    except Exception as e:
        print('Failed to read backtest table rows:', e)

    try:
        mc.close()
    except Exception:
        pass
    try:
        app.quit()
    except Exception:
        pass

if __name__ == '__main__':
    run_check()
