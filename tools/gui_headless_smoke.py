"""Headless smoke test for backend scan/backtest functions.

This avoids Qt entirely: it finds one sample data file, loads it using
`data.data_utils` if available (fallback to pandas), calls `backend.scan_signal`
and `backend.run_backtest`, and prints brief outputs.
"""
import os
import sys
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def find_sample_file():
    candidates = [os.path.join(ROOT, 'data'), os.path.join(ROOT, 'data backup'), os.path.join(ROOT, 'data_backup')]
    for c in candidates:
        if os.path.isdir(c):
            for fname in sorted(os.listdir(c)):
                if fname.lower().endswith(('.json', '.csv', '.parquet')):
                    return os.path.join(c, fname)
    # try root
    for fname in sorted(os.listdir(ROOT)):
        if fname.lower().endswith(('.json', '.csv', '.parquet')):
            return os.path.join(ROOT, fname)
    return None

def load_df(path):
    import pandas as pd
    try:
        # try data.data_utils first
        import importlib.util
        du_path = os.path.join(ROOT, 'data', 'data_utils.py')
        if os.path.isfile(du_path):
            spec = importlib.util.spec_from_file_location('data.data_utils', du_path)
            du = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(du)
            if path.lower().endswith('.json') and hasattr(du, 'load_json'):
                return du.load_json(path)
            if path.lower().endswith('.csv') and hasattr(du, 'load_csv'):
                return du.load_csv(path)
    except Exception:
        pass
    try:
        if path.lower().endswith('.parquet'):
            return pd.read_parquet(path)
        if path.lower().endswith('.json'):
            return pd.read_json(path)
        if path.lower().endswith('.csv'):
            return pd.read_csv(path)
    except Exception as e:
        print('Failed to load with pandas:', e)
    return None


def main():
    sample = find_sample_file()
    if not sample:
        print('No sample file found')
        return
    print('Using sample:', sample)
    df = load_df(sample)
    if df is None:
        print('Failed to load sample into DataFrame')
        return
    try:
        import backend
    except Exception as e:
        print('Failed to import backend:', e)
        return

    # call scan_signal
    try:
        now, age, price = backend.scan_signal(df, 'Donchian Breakout', {'upper':20, 'lower':10})
        print('scan_signal ->', {'now': now, 'age': age, 'price': price})
    except Exception as e:
        print('scan_signal failed:', e)

    # call detect_patterns
    try:
        pats = backend.detect_patterns(df, 30, ['ENGULFING','DOJI'])
        print('detect_patterns ->', pats)
    except Exception as e:
        print('detect_patterns failed:', e)

    # call run_backtest (small, plot=False)
    try:
        figs, summ = backend.run_backtest(df, list(getattr(backend, 'STRAT_MAP', {'SMA Cross': None}).keys())[0], {}, 10000, 0.0005, 0.0005, 1.0, 0.0, None, False)
        print('run_backtest summary keys:', list(summ.keys()))
        # print a few summary fields if present
        print('Final_Value:', summ.get('Final_Value') or summ.get('Final_Value'.lower()) or summ.get('Final_Value'))
    except Exception as e:
        print('run_backtest failed:', e)

if __name__ == '__main__':
    main()
