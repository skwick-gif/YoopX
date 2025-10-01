"""
Instantiate the full main window and print whether Backtest filters are present.
"""
from pathlib import Path
import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication

app = QApplication([])
import main_window
win = main_window.QuantDeskMainWindow()
mc = win.main_content
bt = mc.backtest_tab

print('BacktestTab class:', bt.__class__.__module__, bt.__class__.__name__)

expected_attrs = ['symbols_edit', 'start_cash_spin', 'commission_spin', 'slippage_spin',
                  'universe_limit_spin', 'min_trades_spin', 'start_date_edit', 'end_date_edit',
                  'use_adj_check', 'progress_bar', 'results_table']

found = {}
for a in expected_attrs:
    found[a] = hasattr(bt, a)

print('Found attributes:')
for k, v in found.items():
    print(f'  {k}:', 'YES' if v else 'NO')

# Print some detailed values if present
if hasattr(bt, 'symbols_edit'):
    try:
        print('symbols_edit placeholder:', bt.symbols_edit.placeholderText())
    except Exception:
        pass
if hasattr(bt, 'use_adj_check'):
    try:
        print('use_adj_check checked:', bt.use_adj_check.isChecked())
    except Exception:
        pass

# Clean exit without leaving threads running
try:
    # request worker shutdown to avoid 'QThread: Destroyed while thread ... still running'
    try:
        mc.stop_all_workers(timeout=2000)
    except Exception:
        pass
    win.close()
except Exception:
    pass
app.quit()
