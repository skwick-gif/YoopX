import sys, os, time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

# Ensure project root on path
ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT_PARENT = os.path.abspath(os.path.join(ROOT, '..'))
if ROOT_PARENT not in sys.path:
    sys.path.insert(0, ROOT_PARENT)

from main_window import QuantDeskMainWindow

def pump_events(duration_sec: float, app):
    end = time.time() + duration_sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)

def main():
    os.environ['QD_HEADLESS_TEST'] = '1'
    app = QApplication.instance() or QApplication(sys.argv)
    win = QuantDeskMainWindow()

    print('[TEST] Waiting for data loader to finish...', flush=True)
    waited = 0.0
    while waited < 25.0:
        app.processEvents()
        if not getattr(win.main_content, '_data_loading', False):
            break
        time.sleep(0.2)
        waited += 0.2
    symbols = list((getattr(win.main_content, 'data_map', {}) or {}).keys())
    print(f'[TEST] Data loading flag cleared after {waited:.1f}s; symbols={len(symbols)}')
    sample_symbols = symbols[:3]
    if not sample_symbols and symbols:
        sample_symbols = symbols[:1]
    if not sample_symbols:
        # inject fake symbol with minimal dummy OHLCV for testing auto-discovery path
        import pandas as pd
        import numpy as np
        idx = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=120, freq='D')
        df = pd.DataFrame({
            'Open': np.linspace(90,100,len(idx)),
            'High': np.linspace(91,101,len(idx)),
            'Low':  np.linspace(89,99,len(idx)),
            'Close': np.linspace(90,100,len(idx)) + np.sin(np.arange(len(idx)))/2,
            'Volume': np.random.randint(100000,200000,size=len(idx))
        }, index=idx)
        win.main_content.data_map['FAKE1'] = df
        sample_symbols = ['FAKE1']
        print('[TEST] Injected synthetic symbol FAKE1 for test run')
    if not sample_symbols:
        print('[TEST] No symbols loaded; aborting functional run.')
        return

    tab = win.main_content.auto_discovery_tab

    # Verify buttons enabled before run
    buttons = {
        'run': tab.run_btn,
        'export': tab.export_btn,
        'log': tab.show_log_btn,
        'grid': tab.cfg_grid_btn,
        'data': tab.cfg_data_btn,
        'strategy': tab.cfg_strategy_btn,
    }
    for name, btn in buttons.items():
        print(f'[TEST] Button {name} enabled={btn.isEnabled()} visible={btn.isVisible()}')

    # Prepare params (single strategy, tiny grid) for quick run
    params = {
        'symbols': sample_symbols,
        'strategies': ['SMA Cross'],
        'grid_json': '{"fast":[5,10],"slow":[20]}',
        'min_trades': 1,
        'apply_bar_filters': False,
        'objective': 'Sharpe'
    }
    progress_values = []
    orig_update = tab.update_progress
    def capture_progress(v):
        progress_values.append(v)
        orig_update(v)
    tab.update_progress = capture_progress

    print('[TEST] Starting auto-discovery run...')
    win.main_content.on_run_auto_discovery(params)
    start = time.time()
    finished = False
    while time.time() - start < 30:
        app.processEvents()
        w = getattr(win.main_content, 'auto_discovery_worker', None)
        if w is None or not w.isRunning():
            finished = True
            break
        time.sleep(0.05)

    rows = getattr(tab, '_last_results', [])
    print(f'[TEST] Finished={finished} rows={len(rows)} progress_samples={len(progress_values)} last_progress={(progress_values[-1] if progress_values else None)}')
    for r in rows[:3]:
        print('[TEST] Row:', r)

    # Post-run button states (run should be re-enabled)
    print(f'[TEST] Run button re-enabled={tab.run_btn.isEnabled()}')
    print(f'[TEST] Progress bar visible after run={tab.progress_bar.isVisible()}')

    win.close()
    app.quit()

if __name__ == '__main__':
    main()
