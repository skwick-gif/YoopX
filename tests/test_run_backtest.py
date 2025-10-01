import os, sys, traceback

print('cwd:', os.getcwd())
# Ensure project root is on sys.path so local packages (like data) can be imported
proj_root = os.getcwd()
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
try:
    import data.data_utils as du
    print('imported data.data_utils ok, functions:', [n for n in dir(du) if not n.startswith('_')])
except Exception as e:
    print('Failed to import data.data_utils:', e)
    traceback.print_exc()
    sys.exit(1)

try:
    import backend
    print('imported backend ok')
except Exception as e:
    print('Failed to import backend:', e)
    traceback.print_exc()
    sys.exit(1)

# find one json file from data backup folder
p = os.path.join('data backup', 'A.json')
if not os.path.isfile(p):
    p = next((os.path.join('data backup', f) for f in os.listdir('data backup') if f.lower().endswith('.json')), None)
print('test file:', p)

try:
    df = du.load_json(p)
    print('df shape', getattr(df, 'shape', None), 'index dtype', getattr(df.index, 'dtype', None))
except Exception as e:
    print('Failed to load json into DataFrame:', e)
    traceback.print_exc()
    sys.exit(1)

try:
    res = backend.run_backtest(df, 'SMA Cross', {}, 10000, 0.001, 0.001, 1.0, 0.05, None, False)
    print('run_backtest returned type:', type(res))
    if isinstance(res, tuple):
        print('tuple len', len(res))
        print('summary keys', list(res[1].keys()))
    elif isinstance(res, dict):
        print('summary keys', list(res.keys()))
    else:
        print(res)
except Exception as e:
    print('Exception from backend.run_backtest:', e)
    traceback.print_exc()
    sys.exit(1)
