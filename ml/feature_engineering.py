import pandas as pd
import numpy as np
from typing import Dict, Any, List
from logic.indicators import sma, ema, atr, macd, stoch, bbands

BASIC_FEATURES = [
    'ret_1','ret_5','ret_10','volatility_10','volatility_20','atr_pct','sma_fast_rel','sma_slow_rel',
    'macd_hist','stoch_k','stoch_d','bb_width','rsi2'
]

def compute_features(df: pd.DataFrame, params: Dict[str, Any]|None=None) -> pd.DataFrame:
    """Compute a standardized feature matrix for a price DataFrame.
    Returns a DataFrame aligned with df.index containing engineered numeric features.
    Assumes df has columns: Open High Low Close (case sensitive).
    """
    if df is None or df.empty or 'Close' not in df.columns:
        return pd.DataFrame()
    close = df['Close']
    high = df.get('High', close)
    low = df.get('Low', close)
    # returns & volatility
    ret_1 = close.pct_change()
    ret_5 = close.pct_change(5)
    ret_10 = close.pct_change(10)
    vol10 = ret_1.rolling(10).std()
    vol20 = ret_1.rolling(20).std()
    # ATR percent
    try:
        atrv = atr(df, 14)
        atr_pct = atrv / close
    except Exception:
        atr_pct = pd.Series(np.nan, index=close.index)
    # moving averages relative
    sma_fast = sma(close, 10)
    sma_slow = sma(close, 50)
    sma_fast_rel = sma_fast / close - 1
    sma_slow_rel = sma_slow / close - 1
    # macd
    try:
        m, s, h = macd(close, 12, 26, 9)
    except Exception:
        m = s = h = pd.Series(np.nan, index=close.index)
    # stochastic
    try:
        K, D = stoch(df)
    except Exception:
        K = D = pd.Series(np.nan, index=close.index)
    # bollinger
    try:
        upper, lower = bbands(close, 20, 2)
        mid = (upper+lower)/2
        bb_width = (upper - lower)/mid
    except Exception:
        bb_width = pd.Series(np.nan, index=close.index)
    # RSI2 lightweight
    r = close.pct_change()
    up = r.clip(lower=0).rolling(2).sum()
    down = (-r.clip(upper=0)).rolling(2).sum()
    rs = up / (down + 1e-9)
    rsi2 = 100 - (100 / (1 + rs))
    feats = pd.DataFrame({
        'ret_1': ret_1,
        'ret_5': ret_5,
        'ret_10': ret_10,
        'volatility_10': vol10,
        'volatility_20': vol20,
        'atr_pct': atr_pct,
        'sma_fast_rel': sma_fast_rel,
        'sma_slow_rel': sma_slow_rel,
        'macd_hist': h,
        'stoch_k': K,
        'stoch_d': D,
        'bb_width': bb_width,
        'rsi2': rsi2,
    })
    return feats

def label_future_return(close: pd.Series, horizon: int = 5, threshold: float = 0.02) -> pd.Series:
    """Binary label: 1 if future return over horizon >= threshold, else 0.
    Returns a Series aligned to current bar (label shifted backward so it's predictive)."""
    fut_ret = close.shift(-horizon) / close - 1
    label = (fut_ret >= threshold).astype(int)
    return label

def build_training_frame(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.02) -> pd.DataFrame:
    feats = compute_features(df)
    if feats.empty: return feats
    y = label_future_return(df['Close'], horizon=horizon, threshold=threshold)
    out = feats.copy()
    out['label'] = y
    out = out.dropna()
    return out

def build_training_frames_multi(df: pd.DataFrame, horizons: List[int], threshold: float = 0.02) -> Dict[int, pd.DataFrame]:
    """Return a dict of horizon -> training frame (features + label) for each requested horizon.
    Reuses the same feature matrix for efficiency.
    """
    feats = compute_features(df)
    if feats.empty:
        return {}
    frames: Dict[int, pd.DataFrame] = {}
    for h in horizons:
        try:
            y = label_future_return(df['Close'], horizon=h, threshold=threshold)
            out = feats.copy(); out['label'] = y; out = out.dropna()
            if not out.empty:
                frames[h] = out
        except Exception:
            continue
    return frames
