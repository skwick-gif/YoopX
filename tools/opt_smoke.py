import os, sys
ROOT = os.path.abspath('.')
# Ensure project root is on sys.path so imports like `logic` and `data` resolve
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# load small sample from data or data backup
cand = None
for d in ('data','data backup'):
    p = os.path.join(ROOT,d)
    if os.path.isdir(p):
        files = [os.path.join(p,f) for f in sorted(os.listdir(p)) if f.lower().endswith('.json')]
        if files:
            cand = files[0]
            break
if not cand:
    print('no sample found')
    sys.exit(2)
import pandas as pd
import importlib.util
du_path = os.path.join(ROOT, 'data', 'data_utils.py')
df = None
if os.path.isfile(du_path):
    spec = importlib.util.spec_from_file_location('data.data_utils', du_path)
    du = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(du)
    if hasattr(du, 'load_json'):
        try:
            df = du.load_json(cand)
        except Exception:
            df = None
if df is None:
    # Fallback: let pandas attempt to read JSON/CSV. Use orient='records' to handle list-of-dicts.
    try:
        df = pd.read_json(cand, orient='records')
    except Exception:
        try:
            df = pd.read_csv(cand)
        except Exception as e:
            print('Failed to load sample file:', e)
            sys.exit(2)

import importlib.util
opt_path = os.path.join(ROOT, 'tools', 'optimize_runner.py')
spec = importlib.util.spec_from_file_location('optimize_runner', opt_path)
optm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(optm)
run_optimization = optm.run_optimization
backend_path = os.path.join(ROOT, 'backend.py')
specb = importlib.util.spec_from_file_location('backend', backend_path)
bem = importlib.util.module_from_spec(specb)
specb.loader.exec_module(bem)
param_grid_from_ranges = bem.param_grid_from_ranges

base_params = {}
grid = param_grid_from_ranges({'fast':[8,10,2], 'slow':[20,22,2]})
res = run_optimization(df, 'SMA Cross', base_params, grid[:2], folds=1, oos_frac=0.2, objective='Sharpe', max_workers=1)
print('Done, got', len(res), 'results')
for r in res:
    print(r.get('avg_score'), r.get('params'))
