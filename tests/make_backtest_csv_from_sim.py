import ast, os
from tests import test_worker_sim

# Re-run the simulation and collect printed OK lines by importing its code isn't straightforward,
# instead we'll call the code in test_worker_sim.py as a module.

import importlib.util
spec = importlib.util.spec_from_file_location('test_worker_sim', 'tests/test_worker_sim.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
# The module prints results; capture by running main function isn't provided, so recreate by calling the same logic

# Instead, we will call the backend directly like the simulation did
from data.data_utils import load_json
import backend

folder = os.path.join('data backup')
files = [f for f in os.listdir(folder) if f.lower().endswith('.json')][:2]
strategies = list(getattr(backend, 'STRAT_MAP', {}).keys())[:3]
rows = []
for f in files:
    p = os.path.join(folder, f)
    df = load_json(p)
    sym = os.path.splitext(f)[0].upper()
    for strat in strategies:
        res = backend.run_backtest(df, strat, {}, 10000, 0.001, 0.001, 1.0, 0.05, None, False)
        summary = res[1] if isinstance(res, tuple) and len(res) > 1 else (res if isinstance(res, dict) else {})
        # normalize
        _l = {k.lower(): v for k, v in summary.items()}
        def sv(*cands, default=''):
            for c in cands:
                if c in _l:
                    return _l[c]
            return default
        rows.append({
            'Symbol': sym,
            'Strategy': strat,
            'Final Value': sv('final_value','finalvalue'),
            'Sharpe': sv('sharpe','sharperatio'),
            'Max DD%': sv('max_dd','maxdd','maxdd_pct'),
            'Win Rate%': sv('win_rate','winrate','winrate_pct'),
            'Trades': sv('trades'),
            'CAGR%': sv('cagr','cagr_pct')
        })

out = 'tests/backtest_sim_output.csv'
with open(out, 'w', encoding='utf-8') as f:
    headers = ['Symbol','Strategy','Final Value','Sharpe','Max DD%','Win Rate%','Trades','CAGR%']
    f.write(','.join(headers) + '\n')
    for r in rows:
        f.write(','.join(str(r[h]) for h in headers) + '\n')
print('wrote', out)
