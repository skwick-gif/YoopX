from data.api_fetchers import fetch_via_apis
from config.keys_loader import load_keys

keys = load_keys()
print('loaded keys', {k: bool(v) for k,v in keys.items()})

# try a single ticker with providers from keys
df, meta = fetch_via_apis('AAPL', None, providers=['polygon','alphavantage'], keys=keys)
print('meta:', meta)
print('df rows:', len(df) if df is not None else 'None')
