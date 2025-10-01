import os
import sys

# ensure project root is on sys.path so top-level imports like `backend` work when
# running this script from the tests/ directory
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication
import backend
from ui.main_content.backtest_tab import BacktestTab
from ui.main_content.dialogs.backtest_settings_dialog import BacktestSettingsDialog

app = QApplication([])

# prepare tab and dialog
tab = BacktestTab()
dlg = BacktestSettingsDialog()

# pick one strategy from backend.STRAT_MAP if available
keys = list(getattr(backend, 'STRAT_MAP', {}).keys())
if keys:
    chosen = keys[:1]
else:
    chosen = []

vals = {
    'symbols': 'AAPL,MSFT',
    'universe_limit': 0,
    'min_trades': 0,
    'start_date': '',
    'end_date': '',
    'use_adj': True,
    'min_volume': 0,
    'min_close': 0,
    'start_cash': 10000,
    'commission': 0.0005,
    'slippage': 0.0005,
    'strategies': chosen,
    'strategy_params': {k: {} for k in chosen}
}

# set dialog values and read them back
dlg.set_values(vals)
out = dlg.get_values()
print('Dialog get_values() ->', out)

# apply to tab similarly to open_settings_dialog
try:
    tab.symbols_edit.setText(out.get('symbols',''))
    tab.universe_limit_spin.setValue(int(out.get('universe_limit',0) or 0))
    tab.min_trades_spin.setValue(int(out.get('min_trades',0) or 0))
    from PySide6.QtCore import QDate
    if out.get('start_date'):
        tab.start_date_edit.setDate(QDate.fromString(out.get('start_date'),'yyyy-MM-dd'))
    if out.get('end_date'):
        tab.end_date_edit.setDate(QDate.fromString(out.get('end_date'),'yyyy-MM-dd'))
    tab.use_adj_check.setChecked(bool(out.get('use_adj', True)))
    tab.min_volume_spin.setValue(float(out.get('min_volume',0) or 0))
    tab.min_close_spin.setValue(float(out.get('min_close',0) or 0))
    tab.start_cash_spin.setValue(float(out.get('start_cash',10000)))
    tab.commission_spin.setValue(float(out.get('commission',0.0005)))
    tab.slippage_spin.setValue(float(out.get('slippage',0.0005)))
except Exception as e:
    print('Error applying values to BacktestTab widgets:', e)

# store selected strategies and params
tab._last_strategy_list = out.get('strategies', [])
tab._last_strategy_params = out.get('strategy_params', {}) or {}

# connect to the signal to capture emitted params
def on_run(params):
    print('run_backtest_requested emitted with:')
    for k, v in params.items():
        print('  ', k, ':', v)
    # exit when done
    sys.exit(0)

tab.run_backtest_requested.connect(on_run)

# call run_backtest to trigger emission
print('Calling tab.run_backtest()')
try:
    tab.run_backtest()
except Exception as e:
    print('Error running backtest:', e)
    sys.exit(2)

# if signal didn't cause exit, run the app event loop briefly
sys.exit(0)
