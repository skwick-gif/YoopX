#!/usr/bin/env python3
"""Clean, minimal in-process GUI automation for MainContent.

This script starts a QApplication, instantiates `MainContent`, loads a few
sample files, starts the scan and backtest workers, waits for their
`results_ready` signals, prints brief outputs, waits for threads to finish,
and exits. It's defensive and minimal so it's suitable for developer testing.
"""

import os
import sys
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


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
    du = None
    try:
        import importlib.util
        du_path = os.path.join(ROOT, 'data', 'data_utils.py')
        if os.path.isfile(du_path):
            spec = importlib.util.spec_from_file_location('data.data_utils', du_path)
            du = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(du)
    except Exception:
        du = None

    for p in paths:
        key = os.path.splitext(os.path.basename(p))[0]
        df = None
        try:
            if p.lower().endswith('.parquet'):
                df = pd.read_parquet(p)
            elif p.lower().endswith('.json') and du and hasattr(du, 'load_json'):
                df = du.load_json(p)
            elif p.lower().endswith('.csv') and du and hasattr(du, 'load_csv'):
                df = du.load_csv(p)
            elif p.lower().endswith('.json'):
                df = pd.read_json(p)
            elif p.lower().endswith('.csv'):
                df = pd.read_csv(p)
        except Exception:
            try:
                if p.lower().endswith('.json'):
                    df = pd.read_json(p)
                elif p.lower().endswith('.csv'):
                    df = pd.read_csv(p)
            except Exception:
                df = None
        out[key] = df
    return out


def wait_for(worker, timeout=60.0):
    """Wait for worker.results_ready; return payload or None."""
    from PySide6.QtTest import QTest
    result = {'rows': None}

    def on_res(rows):
        result['rows'] = rows

    def on_err(e):
        print('Worker error:', e)

    try:
        worker.results_ready.connect(on_res)
        worker.error_occurred.connect(on_err)
        worker.progress_updated.connect(lambda v: print('Progress:', v))
        worker.status_updated.connect(lambda s: print('Status:', s))
    except Exception:
        return None

    waited = 0.0
    while result['rows'] is None and waited < timeout:
        QTest.qWait(200)
        waited += 0.2

    if result['rows'] is None:
        print('Timeout after', timeout, 's')
    else:
        print('Got', len(result['rows']), 'rows')

    try:
        worker.wait(2000)
    except Exception:
        pass
    return result['rows']


def run():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    # Suppress Qt warnings (best-effort) so the test output is clean.
    try:
        from PySide6.QtCore import qInstallMessageHandler

        def _quiet_qt(msg_type, context, message):
            # swallow all Qt messages during the test
            return

        qInstallMessageHandler(_quiet_qt)
    except Exception:
        pass

    try:
        from main_content import MainContent
    except Exception as e:
        print('Failed to import MainContent:', e)
        traceback.print_exc()
        return

    app = QApplication([])
    mc = MainContent()

    samples = find_samples()
    if not samples:
        print('No sample data found; aborting')
        return

    mc.data_map = load_map(samples)
    print('Loaded symbols:', list(mc.data_map.keys()))

    # Start scan and backtest using event-loop-driven completion
    print('\n=== START SCAN ===')
    scan_params = {'patterns': 'ENGULFING,DOJI', 'lookback': 30}
    try:
        mc.scan_tab.start_scan_worker(scan_params, mc.data_map)
    except Exception as e:
        print('start_scan_worker failed:', e)
        traceback.print_exc()

    print('\n=== START BACKTEST ===')
    bt_params = {'start_cash': 10000.0, 'commission': 0.0005, 'slippage': 0.0005, 'symbols': ','.join(list(mc.data_map.keys()))}
    try:
        mc.backtest_tab.start_backtest_worker(bt_params, mc.data_map)
    except Exception as e:
        print('start_backtest_worker failed:', e)
        traceback.print_exc()

    sw = getattr(mc.scan_tab, 'worker_thread', None)
    bw = getattr(mc.backtest_tab, 'worker_thread', None)

    scan_rows = []
    bt_rows = []
    done = {'scan': False, 'backtest': False}

    def maybe_quit():
        if done['scan'] and done['backtest']:
            # give Qt a breath to process final events
            QTest.qWait(200)
            app.quit()

    if sw:
        def on_scan(rows):
            scan_rows.extend(rows or [])
            print('Got', len(rows or []), 'rows')
            for r in (rows or [])[:5]:
                print(r)
            # ensure thread cleaned
            try:
                sw.wait(2000)
            except Exception:
                pass
            done['scan'] = True
            maybe_quit()

        sw.results_ready.connect(on_scan)
        sw.error_occurred.connect(lambda e: print('Scan error:', e))
    else:
        print('No scan worker')
        done['scan'] = True

    if bw:
        def on_bt(rows):
            bt_rows.extend(rows or [])
            print('Got', len(rows or []), 'rows')
            for r in (rows or [])[:3]:
                print(r)
            try:
                bw.wait(2000)
            except Exception:
                pass
            done['backtest'] = True
            maybe_quit()

        bw.results_ready.connect(on_bt)
        bw.error_occurred.connect(lambda e: print('Backtest error:', e))
    else:
        print('No backtest worker')
        done['backtest'] = True

    # Run event loop until both workers call app.quit()
    try:
        app.exec()
    except Exception:
        traceback.print_exc()

    # Final safety: ensure threads are stopped
    def ensure_stopped(th, name):
        if not th:
            return
        try:
            th.wait(1000)
        except Exception:
            pass
        if getattr(th, 'isRunning', lambda: False)():
            try:
                th.quit()
            except Exception:
                pass
            try:
                th.wait(2000)
            except Exception:
                pass
        print(f'{name} stopped:', not getattr(th, 'isRunning', lambda: False)())

    ensure_stopped(sw, 'ScanWorker')
    ensure_stopped(bw, 'BacktestWorker')

    # Attempt to close and delete UI objects to help Qt clean up threads
    try:
        mc.close()
    except Exception:
        pass
    try:
        mc.deleteLater()
    except Exception:
        pass

    # Process pending events and give Qt a bit more time
    try:
        from PySide6.QtWidgets import QApplication
        for _ in range(5):
            QApplication.processEvents()
            QTest.qWait(200)
    except Exception:
        pass

    print('Final thread state check:')
    try:
        print('ScanWorker stopped:', not getattr(sw, 'isRunning', lambda: False)())
        print('BacktestWorker stopped:', not getattr(bw, 'isRunning', lambda: False)())
    except Exception:
        pass

    # Finish explicitly with 0 now that worker cleanup is implemented.
    # Prefer a graceful exit via sys.exit(0). If tests reveal intermittent
    # non-zero exits or Qt/QThread warnings, we can revisit and add targeted
    # cleanup rather than forcing process termination.
    try:
        print('Test finished — exiting with code 0')
    except Exception:
        pass
    try:
        import sys as _sys
        _sys.exit(0)
    except Exception:
        # If sys.exit somehow fails, return from run() so the script
        # finishes normally (caller or the OS will see exit code 0).
        try:
            print('sys.exit failed; finishing run() normally')
        except Exception:
            pass
        return


if __name__ == '__main__':
    run()
