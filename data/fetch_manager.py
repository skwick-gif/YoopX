"""Unified multi-provider fetch orchestration.

This module centralises the logic for downloading daily OHLCV candles for a
single ticker with a clear fallback chain and rich metadata about failures.

Providers order (by default):
  1. yfinance (fast, bulk capable)
  2. Yahoo CSV scrape endpoint (lightweight single HTTP GET)
  3. API providers (Polygon / AlphaVantage) – optional, only if keys + enabled

Design goals:
  * Deterministic – attempt each provider at most once per call
  * Cancellation friendly – honour a supplied `cancel_cb` to abort early
  * Structured meta – accumulate error chain for diagnostics
  * SSL certificate resilience – detect certificate errors and skip retry loops
  * Easy future extension – provider functions are small + registered

Public function:
    fetch_ohlcv_with_fallback(ticker, date_from, use_apis=True, cancel_cb=None)
        -> (df, meta)

`meta` keys:
    ticker, requested_from, provider_used, n_rows, fetched_at,
    errors: list[ { provider, error } ],
    chain: textual summary, cert_error (bool), api_attempted(bool)
"""
from __future__ import annotations

from typing import Optional, Callable, Dict, List, Tuple
import datetime
try:
    from cache.cache_manager import get as cache_get, put as cache_put
except Exception:
    def cache_get(*a, **k):
        return None
    def cache_put(*a, **k):
        return None
import pandas as pd
import os

INSECURE_MODE = os.environ.get('QD_DISABLE_SSL_VERIFY') == '1'

from data.rate_limiter import GLOBAL_RATE_LIMITER

try:
    from data.fetchers import fetch_yahoo_since, fetch_scrape_since
except Exception:  # defensive – we still want module import to succeed
    def fetch_yahoo_since(t, d):
        return pd.DataFrame(), {'error': 'fetchers import failed'}
    def fetch_scrape_since(t, d):
        return pd.DataFrame(), {'error': 'fetchers import failed'}

CERT_ERROR_TOKENS = [
    "ssl",
    "certificate verify failed",
    "certificate",
    "certificat",  # partial to match different languages
    "self signed",
    "unable to get local issuer",
    "tls",
    "handshake failure",
    "sslv3",
    "err_cert",
]


def _is_cert_error(msg: Optional[str]) -> bool:
    if not msg:
        return False
    m = str(msg).lower()
    return any(tok in m for tok in CERT_ERROR_TOKENS)


def fetch_ohlcv_with_fallback(
    ticker: str,
    date_from: Optional[str],
    use_apis: bool = True,
    cancel_cb: Optional[Callable[[], bool]] = None,
    providers: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict]:
    """Attempt multi-source fetch returning first successful DataFrame.

    providers: explicit provider order override (subset of ['yahoo','scrape','api']).
    cancel_cb: function returning True if operation should abort early.
    """
    order = providers or ["yahoo", "scrape", "api"]
    # Allow environment override when not explicitly passed
    if not providers:
        env_order = os.environ.get('QD_PROVIDER_ORDER')
        if env_order:
            cand = [p.strip() for p in env_order.split(',') if p.strip()]
            if cand:
                order = cand
    out_meta: Dict = {
        'ticker': ticker,
        'requested_from': date_from,
        'provider_used': None,
        'n_rows': 0,
        'fetched_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'errors': [],
        'chain': '',
        'cert_error': False,
        'api_attempted': False,
        'insecure': INSECURE_MODE,
        'order': order,
    }
    # Helper to short-circuit if cancelled
    def _cancelled() -> bool:
        try:
            return bool(cancel_cb and cancel_cb())
        except Exception:
            return False

    df_ok: Optional[pd.DataFrame] = None
    # First try cache (no provider hits if fresh)
    try:
        cached = cache_get(ticker, date_from, None, True)
        if cached is not None and not cached.empty:
            out_meta['provider_used'] = 'cache'
            out_meta['n_rows'] = int(len(cached))
            out_meta['chain'] = 'cache'
            return cached, out_meta
    except Exception:
        pass
    errors_chain: List[str] = []

    for prov in order:
        if _cancelled():
            errors_chain.append('cancelled')
            break
        if prov == 'yahoo':
            # allow env opt-out (e.g. flaky corporate SSL MITM)
            if os.environ.get('QD_NO_YF') == '1':
                errors_chain.append('yahoo:disabled')
                continue
            # In insecure mode yfinance internally still verifies SSL; allow attempt but skip quickly on cert errors
            try:
                GLOBAL_RATE_LIMITER.wait('yahoo')
            except Exception:
                pass
            df, meta = fetch_yahoo_since(ticker, date_from)
            if df is not None and not df.empty and not meta.get('error'):
                df_ok = df; out_meta['provider_used'] = 'yahoo'; break
            err = meta.get('error')
            if _is_cert_error(err):
                out_meta['cert_error'] = True
            out_meta['errors'].append({'provider': 'yahoo', 'error': err})
            errors_chain.append(f"yahoo:{err or 'empty'}")
        elif prov == 'scrape':
            try:
                GLOBAL_RATE_LIMITER.wait('scrape')
            except Exception:
                pass
            df, meta = fetch_scrape_since(ticker, date_from)
            if df is not None and not df.empty and not meta.get('error'):
                df_ok = df; out_meta['provider_used'] = 'scrape'; break
            err = meta.get('error')
            if _is_cert_error(err):
                out_meta['cert_error'] = True
            out_meta['errors'].append({'provider': 'scrape', 'error': err})
            errors_chain.append(f"scrape:{err or 'empty'}")
        elif prov == 'api' and use_apis:
            out_meta['api_attempted'] = True
            try:
                GLOBAL_RATE_LIMITER.wait('api')
            except Exception:
                pass
            try:
                from data.api_fetchers import fetch_via_apis
                from config.keys_loader import load_keys
                keys = load_keys()
                df, meta = fetch_via_apis(ticker, date_from, providers=None, keys=keys)
                if df is not None and not df.empty and not meta.get('error'):
                    df_ok = df; out_meta['provider_used'] = meta.get('source') or 'api'; break
                err = (meta or {}).get('error')
                if _is_cert_error(err):
                    out_meta['cert_error'] = True
                out_meta['errors'].append({'provider': 'api', 'error': err})
                errors_chain.append(f"api:{err or 'empty'}")
            except Exception as e:
                if _is_cert_error(str(e)):
                    out_meta['cert_error'] = True
                out_meta['errors'].append({'provider': 'api', 'error': str(e)})
                errors_chain.append(f"api:{e}")
        else:
            # provider not recognised or intentionally skipped
            continue

    if df_ok is None:
        out_meta['chain'] = ' -> '.join(errors_chain)
        return pd.DataFrame(), out_meta

    out_meta['n_rows'] = int(len(df_ok))
    # store to cache (best effort)
    try:
        cache_put(ticker, df_ok, date_from, None, True)
    except Exception:
        pass
    out_meta['chain'] = ' -> '.join(errors_chain) if errors_chain else out_meta['provider_used']
    return df_ok, out_meta


__all__ = [
    'fetch_ohlcv_with_fallback'
]
