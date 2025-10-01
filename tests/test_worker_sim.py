import os, sys, traceback
proj_root = os.getcwd()
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from data.data_utils import load_json
import backend

# load first two json files from data backup
folder = os.path.join('data backup')
files = [f for f in os.listdir(folder) if f.lower().endswith('.json')]
files = files[:2]
print('files to test:', files)

data_map = {}
for f in files:
    p = os.path.join(folder, f)
    df = load_json(p)
    sym = os.path.splitext(f)[0].upper()
    data_map[sym] = df

strategies = list(getattr(backend, 'STRAT_MAP', {}).keys())[:3]
print('strategies to test:', strategies)

results = []
for sym, df in data_map.items():
    for strat in strategies:
        try:
            res = backend.run_backtest(df, strat, {}, 10000, 0.001, 0.001, 1.0, 0.05, None, False)
            summary = res[1] if isinstance(res, tuple) and len(res) > 1 else (res if isinstance(res, dict) else {})
            _l = {k.lower(): v for k, v in summary.items()}
            def sv(*cands, default=0):
                for c in cands:
                    if c in _l:
                        return _l[c]
                return default
            r = {
                'symbol': sym,
                'strategy': strat,
                'final_value': sv('final_value','finalvalue','final_value','finalvalue', default=0),
                'sharpe': sv('sharpe','sharperatio', default=0),
                'max_dd': sv('max_dd','maxdd','maxdd_pct','maxdd_pct', default=0),
                'win_rate': sv('win_rate','winrate','winrate_pct','win_rate_pct', default=0),
                'trades': sv('trades','total_trades','trades_total', default=0),
                'cagr': sv('cagr','cagr_pct','cagrpct', default=0)
            }
            print('OK', r)
            results.append(r)
        except Exception as e:
            tb = traceback.format_exc()
            print('ERROR', sym, strat, e)
            print(tb)

print('done, produced', len(results), 'results')
