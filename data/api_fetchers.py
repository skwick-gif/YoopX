"""API-based fetchers for historical daily OHLCV.

This module provides small adapters for Polygon and AlphaVantage and a convenience
`fetch_via_apis` function that will try providers in order until data is returned.

It expects API keys to be provided by the caller (or via environment variables in tests).
"""
from typing import Tuple, Dict, Optional, List
import pandas as pd
import time
import requests
import datetime
from data.rate_limiter import GLOBAL_RATE_LIMITER
import os

INSECURE_MODE = os.environ.get('QD_DISABLE_SSL_VERIFY') == '1'

# Use the shared global limiter
_RATE_LIMITER = GLOBAL_RATE_LIMITER


def _retry_get(url, params=None, headers=None, attempts=3, timeout=20):
    last_exc = None
    backoff = 1.0
    for i in range(attempts):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout, verify=not INSECURE_MODE)
            # handle rate-limit style responses gracefully
            if r.status_code in (429, 503):
                # check Retry-After header if present
                ra = r.headers.get('Retry-After')
                try:
                    wait = float(ra) if ra is not None else backoff
                except Exception:
                    wait = backoff
                time.sleep(wait)
                backoff = min(backoff * 2, 60)
                last_exc = Exception(f'HTTP {r.status_code}')
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
    raise last_exc


def fetch_polygon_since(ticker: str, date_from: Optional[str], api_key: str) -> Tuple[pd.DataFrame, Dict]:
    meta = {'source': 'polygon', 'ticker': ticker, 'fetched_at': datetime.datetime.utcnow().isoformat() + 'Z', 'n_rows': 0, 'insecure': INSECURE_MODE}
    if not api_key:
        meta['error'] = 'missing polygon api key'
        return pd.DataFrame(), meta
    try:
        _RATE_LIMITER.wait('polygon')
        t = ticker.strip().upper()
        # polygon expects yyyy-mm-dd for from/to, and unix timestamps in ms for t in results
        # Prefer caller-provided start; if missing or unparseable, default to 2024-01-01
        try:
            if date_from:
                start = pd.to_datetime(date_from).strftime('%Y-%m-%d')
            else:
                start = '2024-01-01'
        except Exception:
            start = '2024-01-01'
        end = (pd.Timestamp.utcnow().strftime('%Y-%m-%d'))
        url = f'https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{start}/{end}'
        params = {'adjusted': 'true', 'sort': 'asc', 'limit': 50000, 'apiKey': api_key}
        r = _retry_get(url, params=params)
        try:
            j = r.json()
        except Exception as e:
            meta['error'] = f'invalid json from polygon: {e}'
            return pd.DataFrame(), meta
        results = j.get('results') or []
        if not results:
            meta['n_rows'] = 0
            return pd.DataFrame(), meta
        rows = []
        for rec in results:
            # t is unix ms
            dt = pd.to_datetime(rec.get('t'), unit='ms', utc=True)
            rows.append({'date': dt, 'open': rec.get('o'), 'high': rec.get('h'), 'low': rec.get('l'), 'close': rec.get('c'), 'adj_close': rec.get('c'), 'volume': rec.get('v')})
        df = pd.DataFrame(rows)
        meta['n_rows'] = int(len(df))
        return df, meta
    except Exception as e:
        meta['error'] = str(e)
        return pd.DataFrame(), meta


def fetch_alphavantage_since(ticker: str, date_from: Optional[str], api_key: str) -> Tuple[pd.DataFrame, Dict]:
    meta = {'source': 'alphavantage', 'ticker': ticker, 'fetched_at': datetime.datetime.utcnow().isoformat() + 'Z', 'n_rows': 0, 'insecure': INSECURE_MODE}
    if not api_key:
        meta['error'] = 'missing alphavantage api key'
        return pd.DataFrame(), meta
    try:
        _RATE_LIMITER.wait('alphavantage')
        t = ticker.strip().upper()
        url = 'https://www.alphavantage.co/query'
        params = {'function': 'TIME_SERIES_DAILY_ADJUSTED', 'symbol': t, 'outputsize': 'compact', 'apikey': api_key}
        r = _retry_get(url, params=params)
        try:
            j = r.json()
        except Exception as e:
            meta['error'] = f'invalid json from alphavantage: {e}'
            return pd.DataFrame(), meta
        series = j.get('Time Series (Daily)') or j.get('Time Series (Daily)')
        if not series:
            # handle error message
            meta['error'] = j.get('Note') or j.get('Error Message') or 'no data'
            return pd.DataFrame(), meta
        rows = []
        for date_str, vals in series.items():
            dt = pd.to_datetime(date_str).tz_localize('UTC')
            try:
                open_v = float(vals.get('1. open'))
            except Exception:
                open_v = None
            try:
                high_v = float(vals.get('2. high'))
            except Exception:
                high_v = None
            try:
                low_v = float(vals.get('3. low'))
            except Exception:
                low_v = None
            try:
                close_v = float(vals.get('4. close'))
            except Exception:
                close_v = None
            try:
                adj_v = float(vals.get('5. adjusted close') or vals.get('5. adjusted close'))
            except Exception:
                adj_v = close_v
            try:
                vol_v = float(vals.get('6. volume') or vals.get('6. volume'))
            except Exception:
                vol_v = None
            rows.append({'date': dt, 'open': open_v, 'high': high_v, 'low': low_v, 'close': close_v, 'adj_close': adj_v, 'volume': vol_v})
        df = pd.DataFrame(rows)
        df = df.sort_values('date')
        meta['n_rows'] = int(len(df))
        return df, meta
    except Exception as e:
        meta['error'] = str(e)
        return pd.DataFrame(), meta


def fetch_via_apis(ticker: str, date_from: Optional[str], providers: Optional[List[str]] = None, keys: Optional[Dict[str, str]] = None) -> Tuple[pd.DataFrame, Dict]:
    """Try providers in order until one returns data.

    providers: list of provider names in lower-case: 'polygon', 'alphavantage'
    keys: mapping provider->api_key
    """
    if providers is None:
        providers = ['polygon', 'alphavantage']
    keys = keys or {}
    last_meta = {}
    for p in providers:
        # throttle per-provider
        try:
            _RATE_LIMITER.wait(p)
        except Exception:
            pass
        if p == 'polygon':
            df, meta = fetch_polygon_since(ticker, date_from, keys.get('polygon') or '')
        elif p == 'alphavantage' or p == 'alpha':
            df, meta = fetch_alphavantage_since(ticker, date_from, keys.get('alphavantage') or '')
        else:
            meta = {'error': f'unknown provider {p}'}
            df = pd.DataFrame()
        last_meta = meta
        if df is not None and not df.empty:
            meta['used_provider'] = p
            return df, meta
        # If provider returned an error that looks like a rate-limit / Note, increase backoff
        err = (meta or {}).get('error')
        if err and any(k in str(err).lower() for k in ('note', 'rate', 'limit', '429')):
            try:
                # double the interval, cap at 120s
                current = _RATE_LIMITER.min_intervals.get(p, _RATE_LIMITER.min_intervals.get('api', 5.0))
                new = min(current * 2, 120.0)
                _RATE_LIMITER.set_interval(p, new)
                meta['backoff_applied'] = new
            except Exception:
                pass
    # none returned data
    last_meta['used_provider'] = None
    return pd.DataFrame(), last_meta
