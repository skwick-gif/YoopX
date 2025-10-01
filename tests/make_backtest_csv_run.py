from data.data_utils import load_json
import backend, os
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
