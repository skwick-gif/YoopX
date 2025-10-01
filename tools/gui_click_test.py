#!/usr/bin/env python3
"""GUI click test: instantiate MainContent, load sample files, programmatically click Run buttons
for Scan and Backtest, wait for results_ready, and print confirmation."""
import os, sys, traceback
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

import time

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
    result = {'rows': None}
    def on_res(rows):
        result['rows'] = rows
    try:
        worker.results_ready.connect(on_res)
        worker.error_occurred.connect(lambda e: print('Worker error:', e))
    except Exception as e:
        print('Failed to connect signals:', e)
        return None
    waited = 0.0
    while result['rows'] is None and waited < timeout:
        QTest.qWait(200)
        waited += 0.2
    return result['rows']


def run_click_test():
    app = QApplication([])
    mc = MainContent()
    samples = find_samples()
    if not samples:
        print('No sample data found; aborting')
        return
    mc.data_map = load_map(samples)
    print('Loaded symbols:', list(mc.data_map.keys()))

    # Simulate clicking Scan run button
    print('\n-- Clicking Scan Run button --')
    try:
        scan_btn = mc.scan_tab.run_scan_btn
        QTest.mouseClick(scan_btn, 1)
    except Exception as e:
        print('Click failed, calling run_scan directly:', e)
        try:
            mc.scan_tab.run_scan()
        except Exception as e2:
            print('Direct run_scan failed:', e2)
    sw = getattr(mc.scan_tab, 'worker_thread', None)
    if sw:
        rows = wait_for_worker(sw, timeout=30.0)
        print('Scan rows:', len(rows) if rows else 'None')
    else:
        print('No Scan worker created')

    QTest.qWait(500)

    # Simulate clicking Backtest run button
    print('\n-- Clicking Backtest Run button --')
    try:
        bt_btn = mc.backtest_tab.run_backtest_btn
        QTest.mouseClick(bt_btn, 1)
    except Exception as e:
        print('Click failed, calling run_backtest directly:', e)
        try:
            mc.backtest_tab.run_backtest()
        except Exception as e2:
            print('Direct run_backtest failed:', e2)
    bw = getattr(mc.backtest_tab, 'worker_thread', None)
    if bw:
        rows = wait_for_worker(bw, timeout=60.0)
        print('Backtest rows:', len(rows) if rows else 'None')
    else:
        print('No Backtest worker created')

    # Clean up
    try:
        mc.close()
    except Exception:
        pass
    try:
        app.quit()
    except Exception:
        pass

if __name__ == '__main__':
    run_click_test()
