"""Load API keys: prefer environment variables, fallback to config/keys.json.

Environment variable names:
- POLYGON_API_KEY
- ALPHAVANTAGE_API_KEY
- MARKETSTACK_API_KEY
- TWEKVEDATA_API_KEY

The loader returns a dict mapping provider->key (empty string if missing).
"""
from pathlib import Path
import os
import json


def load_keys():
    keys = {
        'polygon': os.environ.get('POLYGON_API_KEY', '').strip(),
        'alphavantage': os.environ.get('ALPHAVANTAGE_API_KEY', '').strip(),
        'marketstack': os.environ.get('MARKETSTACK_API_KEY', '').strip(),
        'twelvedata': os.environ.get('TWELVEDATA_API_KEY', '').strip(),
    }

    # if any key missing, try config/keys.json
    if not all(keys.values()):
        cfg = Path(__file__).resolve().parent / 'keys.json'
        if cfg.exists():
            try:
                j = json.loads(cfg.read_text(encoding='utf-8'))
                for k in ['polygon', 'alphavantage', 'marketstack', 'twelvedata']:
                    if not keys.get(k):
                        v = (j.get(k) or '').strip()
                        keys[k] = v
            except Exception:
                pass

    return keys


if __name__ == '__main__':
    print(load_keys())
