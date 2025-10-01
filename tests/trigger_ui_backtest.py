import sys, os
proj = os.getcwd()
if proj not in sys.path:
    sys.path.insert(0, proj)
from main_content import MainWindow
from PySide6.QtWidgets import QApplication
import pandas as pd

app = QApplication([])
win = MainWindow()
# Prepare parameters: use default current_params and backtest params
params = {'start_cash':10000,'commission':0.0005,'slippage':0.0005}
# ensure we have data loaded in win.data_map (use existing data backup)
# load two files if empty
if not getattr(win, 'data_map', None):
    win.data_map = {}
    folder = os.path.join('data backup')
    files = [f for f in os.listdir(folder) if f.lower().endswith('.json')][:2]
    from data.data_utils import load_json
    for f in files:
        win.data_map[os.path.splitext(f)[0].upper()] = load_json(os.path.join(folder,f))

win.on_run_backtest(params)
print('triggered on_run_backtest; worker started (if UI event loop running)')
# Since worker runs in QThread and we don't run the event loop here, we will instead call backend.run_backtest directly
import backend
sym, df = next(iter(win.data_map.items()))
res = backend.run_backtest(df, list(getattr(backend,'STRAT_MAP',[]))[0], {}, 10000, 0.0005, 0.0005, 1.0, 0.05, None, False)
print('direct run_backtest returned summary keys:', list(res[1].keys()))
