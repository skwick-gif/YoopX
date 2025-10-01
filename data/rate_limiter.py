"""Simple provider-aware rate limiter.
Provides per-provider minimum interval enforcement (sleep-based). This is conservative
and intended to avoid hitting free-tier API limits.
"""
import time
from threading import Lock
from typing import Dict


class ProviderRateLimiter:
    """Keep track of last call timestamps per provider and enforce min intervals.

    min_intervals: dict provider -> seconds between calls
    """
    def __init__(self, min_intervals: Dict[str, float] = None):
        # sensible conservative defaults
        defaults = {
            'yahoo': 0.5,        # small pause for yfinance
            'scrape': 1.0,       # scraping endpoint: 1s between requests
            'polygon': 0.5,      # polygon often supports higher rates; keep small gap
            'alphavantage': 12.0,# AlphaVantage free: 5 requests per minute -> 12s
            'api': 5.0,          # generic API fallback
        }
        self.min_intervals = defaults if min_intervals is None else {**defaults, **min_intervals}
        self._last_call = {k: 0.0 for k in self.min_intervals.keys()}
        self._lock = Lock()

    def wait(self, provider: str):
        provider = provider.lower() if provider else 'api'
        interval = self.min_intervals.get(provider, self.min_intervals.get('api', 1.0))
        with self._lock:
            now = time.time()
            last = self._last_call.get(provider, 0.0)
            need = last + interval - now
            if need > 0:
                time.sleep(need)
                now = time.time()
            self._last_call[provider] = now

    def set_interval(self, provider: str, seconds: float):
        with self._lock:
            self.min_intervals[provider] = float(seconds)
            if provider not in self._last_call:
                self._last_call[provider] = 0.0


# Shared global limiter for the process. Import this in other modules to
# ensure rate-limit timing is coordinated across threads and modules.
GLOBAL_RATE_LIMITER = ProviderRateLimiter()
