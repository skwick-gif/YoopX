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
for name in ['symbols_edit','start_cash_spin','commission_spin','slippage_spin','universe_limit_spin','min_trades_spin','start_date_edit','end_date_edit','min_volume_spin','min_close_spin','run_backtest_btn']:
    w = getattr(bt, name, None)
    if w is None:
        print(name, 'MISSING')
    else:
        try:
            print(name, 'minHeight=', w.minimumHeight())
        except Exception as e:
            print(name, 'err', e)
app.quit()
try:
    mc.stop_all_workers(timeout=2000)
except Exception:
    pass
