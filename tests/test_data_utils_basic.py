import os, sys
proj_root = os.getcwd()
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from data.data_utils import load_json
import pandas as pd

folder = os.path.join('data backup')
files = [f for f in os.listdir(folder) if f.lower().endswith('.json')]
if not files:
    raise SystemExit('no json files to test')

p = os.path.join(folder, files[0])
df = load_json(p)
assert isinstance(df, pd.DataFrame), 'load_json must return DataFrame'
# must have at least Close column
assert 'Close' in df.columns or 'Adj Close' in df.columns, f'No Close/Adj Close in {files[0]}'
# index should be datetime-like or convertible
try:
    assert pd.api.types.is_datetime64_any_dtype(df.index) or pd.to_datetime(df.index, errors='coerce').notna().any()
except Exception:
    assert False, 'Index is not datetime-like'

print('test_data_utils_basic: OK')
