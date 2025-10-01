import os
import random
import json
import pprint

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def find_data_folder():
    # prefer folder that actually contains data files
    candidates = ['data', 'data backup']
    for candidate in candidates:
        p = os.path.join(ROOT, candidate)
        if os.path.isdir(p):
            files = [f for f in os.listdir(p) if f.lower().endswith(('.json', '.csv', '.parquet'))]
            if files:
                return p
    # fallback to first existing
    for candidate in candidates:
        p = os.path.join(ROOT, candidate)
        if os.path.isdir(p):
            return p
    return None


def load_df(path):
    import pandas as pd
    # try to import loaders from data/data_utils.py via file path
    load_json = None
    load_csv = None
    import os
    import random
    import json
    import pprint

    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


    def find_data_folder():
        # prefer folder that actually contains data files
        candidates = ['data', 'data backup']
        for candidate in candidates:
            p = os.path.join(ROOT, candidate)
            if os.path.isdir(p):
                files = [f for f in os.listdir(p) if f.lower().endswith(('.json', '.csv', '.parquet'))]
                if files:
                    return p
        # fallback to first existing
        for candidate in candidates:
            p = os.path.join(ROOT, candidate)
            if os.path.isdir(p):
                return p
        return None


    def load_df(path):
        import pandas as pd
        # try to import loaders from data/data_utils.py via file path
        load_json = None
        load_csv = None
        try:
            import importlib.util, sys
            if ROOT not in sys.path:
                sys.path.insert(0, ROOT)
            du_path = os.path.join(ROOT, 'data', 'data_utils.py')
            if os.path.isfile(du_path):
                spec = importlib.util.spec_from_file_location('data.data_utils', du_path)
                du = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(du)
                load_json = getattr(du, 'load_json', None)
                load_csv = getattr(du, 'load_csv', None)
        except Exception:
            load_json = None
            load_csv = None

        if path.lower().endswith('.json'):
            if load_json:
                try:
                    return load_json(path)
                except Exception:
                    pass
            try:
                return pd.read_json(path)
            except Exception:
                return None
        if path.lower().endswith('.csv'):
            if load_csv:
                try:
                    return load_csv(path)
                except Exception:
                    pass
            try:
                return pd.read_csv(path)
            except Exception:
                return None
        if path.lower().endswith('.parquet'):
            return pd.read_parquet(path)
        return None


    def main():
        data_folder = find_data_folder()
        if not data_folder:
            print('No data folder found (checked data, data backup)')
            return

        files = [f for f in os.listdir(data_folder) if f.lower().endswith(('.json', '.csv', '.parquet'))]
        if not files:
            print('No data files found in', data_folder)
            return

        # pick 2 random files
        picks = random.sample(files, min(2, len(files)))
        data_map = {}
        for f in picks:
            path = os.path.join(data_folder, f)
            sym = os.path.splitext(f)[0]
            try:
                df = load_df(path)
                data_map[sym] = df
                print(f'Loaded {sym} from {f}, rows={len(df) if df is not None else None}')
            except Exception as e:
                print('Failed to load', f, e)

        # import backend; load backend.py from project root if not importable from sys.path
        backend = None
        try:
            import backend as _b
            backend = _b
        except Exception:
            try:
                import importlib.util, sys
                if ROOT not in sys.path:
                    sys.path.insert(0, ROOT)
                backend_path = os.path.join(ROOT, 'backend.py')
                if os.path.isfile(backend_path):
                    spec = importlib.util.spec_from_file_location('backend', backend_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    backend = mod
                else:
                    print('Cannot import backend.py — please ensure backend.py exists in the project root')
                    return
            except Exception as e:
                print('Cannot import backend.py:', e)
                return

        if backend is None:
            print('No backend available')
            return

        patterns = ['ENGULFING', 'DOJI', 'HAMMER']
        results = []
        for sym, df in data_map.items():
            for pat in random.sample(patterns, 2):
                try:
                    now, age, price = backend.scan_signal(df, pat, {'lookback': 30})
                    results.append({'symbol': sym, 'pattern': pat, 'now': now, 'age': age, 'price': price})
                except Exception as e:
                    results.append({'symbol': sym, 'pattern': pat, 'error': str(e)})

        pprint.pprint(results)


    if __name__ == '__main__':
        main()
