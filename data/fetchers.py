"""
Simple fetcher implementations.
- fetch_yahoo_since uses yfinance if available to download daily OHLCV rows since a date.

This module is intentionally small and tolerant: if yfinance is not installed or network is unavailable,
fetch functions will return (empty_df, meta) and a descriptive meta['error'].
"""
from typing import Tuple, Dict, Optional
import pandas as pd
import datetime
import os

INSECURE_MODE = os.environ.get('QD_DISABLE_SSL_VERIFY') == '1'

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except Exception:
    _HAS_YFINANCE = False
from data.rate_limiter import GLOBAL_RATE_LIMITER
_RATE_LIMITER = GLOBAL_RATE_LIMITER


def fetch_yahoo_since(ticker: str, date_from: Optional[str]) -> Tuple[pd.DataFrame, Dict]:
    """Fetch daily OHLCV for `ticker` from `date_from` (inclusive) using yfinance.

    Returns (df, meta) where df has columns Date/Open/High/Low/Close/Adj Close/Volume and Date is datetime64.
    """
    meta = {'source': 'yahoo', 'ticker': ticker, 'fetched_at': datetime.datetime.utcnow().isoformat() + 'Z', 'n_rows': 0}
    if not _HAS_YFINANCE:
        meta['error'] = 'yfinance not installed'
        return pd.DataFrame(), meta

    try:
        # rate limit for yahoo/yfinance
        try:
            _RATE_LIMITER.wait('yahoo')
        except Exception:
            pass
        # yfinance expects ticker symbol; ensure no whitespace
        t = str(ticker).strip()
        start = None
        if date_from:
            try:
                start = pd.to_datetime(date_from).strftime('%Y-%m-%d')
            except Exception:
                start = date_from
        # set end to today + 1 to ensure inclusive of last candle
        end = (pd.Timestamp.utcnow().normalize() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        df = yf.download(t, start=start, end=end, progress=False, threads=False)
        if df is None or df.empty:
            meta['n_rows'] = 0
            return pd.DataFrame(), meta
        # rename index to 'date' and reset
        df = df.reset_index()
        # ensure common column names
        df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 'Volume': 'volume'})
        # keep only expected cols
        cols = ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        existing = [c for c in cols if c in df.columns]
        df = df[existing]
        # coerce date
        try:
            df['date'] = pd.to_datetime(df['date'], utc=True)
        except Exception:
            pass
        meta['n_rows'] = int(len(df))
        return df, meta
    except Exception as e:
        meta['error'] = str(e)
        return pd.DataFrame(), meta


def fetch_scrape_since(ticker: str, date_from: Optional[str]) -> Tuple[pd.DataFrame, Dict]:
    """Fetch daily OHLCV using Yahoo's CSV download endpoint (lightweight scraping).

    This uses the public CSV download endpoint at Yahoo Finance and does not require
    the `yfinance` package. It performs a single HTTP GET and parses the returned CSV
    into a pandas DataFrame. If `requests` is not available or the request fails, the
    function returns an empty DataFrame and a meta dict describing the error.

    date_from may be None or a string/Datetime-like. When provided, it will be used as
    the "period1" parameter (inclusive). The function sets period2 to today+1.
    """
    meta = {'source': 'scrape', 'ticker': ticker, 'fetched_at': datetime.datetime.utcnow().isoformat() + 'Z', 'n_rows': 0}
    try:
        import requests
    except Exception:
        meta['error'] = 'requests not installed'
        return pd.DataFrame(), meta

    try:
        # throttle scrape requests
        try:
            _RATE_LIMITER.wait('scrape')
        except Exception:
            pass
        t = str(ticker).strip()
        # compute unix timestamps
        def to_unix(dt):
            try:
                ts = pd.to_datetime(dt)
                # convert to UTC midnight
                return int(pd.Timestamp(ts.tz_localize('UTC') if ts.tzinfo is None else ts).timestamp())
            except Exception:
                # if parsing fails, fallback to 2024-01-01 per user requirement
                return int(pd.Timestamp('2024-01-01', tz='UTC').timestamp())

        # default to 2024-01-01 for new tickers when date_from is None or unparseable
        period1 = int(pd.Timestamp('2024-01-01', tz='UTC').timestamp())
        if date_from:
            period1 = to_unix(date_from)
        # period2 = tomorrow
        period2 = int((pd.Timestamp.utcnow().normalize() + pd.Timedelta(days=1)).timestamp())

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{t}"
        params = {
            'period1': str(period1),
            'period2': str(period2),
            'interval': '1d',
            'events': 'history',
            'includeAdjustedClose': 'true'
        }
        headers = {'User-Agent': 'python-requests/3.x'}
        resp = requests.get(url, params=params, headers=headers, timeout=30, verify=not INSECURE_MODE)
        if resp.status_code != 200:
            meta['error'] = f'HTTP {resp.status_code} when downloading CSV'
            return pd.DataFrame(), meta

        # parse CSV into DataFrame
        from io import StringIO
        s = StringIO(resp.text)
        df = pd.read_csv(s)
        if df is None or df.empty:
            meta['n_rows'] = 0
            return pd.DataFrame(), meta

        # normalize columns
        df = df.rename(columns=lambda c: str(c).strip())
        df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 'Volume': 'volume'})
        cols = ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        existing = [c for c in cols if c in df.columns]
        df = df[existing]
        try:
            df['date'] = pd.to_datetime(df['date'], utc=True)
        except Exception:
            pass
        meta['n_rows'] = int(len(df))
        return df, meta
    except Exception as e:
        meta['error'] = str(e)
        if INSECURE_MODE and any(tok in str(e).lower() for tok in ('ssl', 'certificate')):
            meta['ssl_note'] = 'insecure mode enabled but SSL error still occurred'
        return pd.DataFrame(), meta
