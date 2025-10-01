
# app_v8.py — self-contained helpers for Streamlit/Web UI
# Provides:
#   - load_csv, load_json, maybe_adjust_with_adj
#   - indicators (ema/sma/atr/macd/stoch/bbands)
#   - detect_patterns, scan_signal
#   - Backtrader strategies (STRAT_MAP)
#   - run_backtest(df, params, start_cash=..., commission=..., slippage_perc=..., plot=False) -> (figs, summary)
#
# Notes:
# - params MUST include "strategy_name" (e.g. "SMA Cross", "EMA Cross", ...).
# - Other optional keys: fast, slow, ema_trend, upper, lower, rsi_p, rsi_buy, rsi_exit, bb_p, bb_k,
#                        use_regime, weekly_filter, use_atr_sizer, risk_pct, atr_period, atr_mult,
#                        stake, long_only, stop_loss_pct, take_profit_pct
from __future__ import annotations
import io, os, json, math
from typing import Dict, Any, List, Tuple

import pandas as pd
import numpy as np

import backtrader as bt

# Optional deps
try:
    import talib as ta
except Exception:
    ta = None

try:
    import yfinance as yf
except Exception:
    yf = None

# --------------------
# IO + standardization
# --------------------
REQ_COLS = ["Open","High","Low","Close"]

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower(): c for c in df.columns}
    aliases = {
        "open":"Open","o":"Open",
        "high":"High","h":"High",
        "low":"Low","l":"Low",
        "close":"Close","c":"Close",
        "adj close":"Adj Close","adj_close":"Adj Close","adjclose":"Adj Close",
        "volume":"Volume","v":"Volume",
        "date":"Date","datetime":"Date","timestamp":"Date","time":"Date"
    }
    rename_map = {cols[k]: v for k,v in aliases.items() if k in cols}
    if rename_map:
        df = df.rename(columns=rename_map)
    # require O/H/L/C
    for rc in REQ_COLS:
        if rc not in df.columns:
            raise ValueError(f"Missing required column: {rc}")
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]
    if "Volume" not in df.columns:
        df["Volume"] = 0
    return df

def load_csv(file) -> pd.DataFrame:
    """file can be path or file-like"""
    if isinstance(file, (str, os.PathLike)):
        df = pd.read_csv(file)
    else:
        df = pd.read_csv(file)
    cols = {c.lower(): c for c in df.columns}
    date_col = None
    for cand in ("date","datetime","timestamp"):
        if cand in cols: date_col = cols[cand]; break
    if not date_col:
        raise ValueError("CSV missing date/datetime column")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col)
    return _standardize_columns(df).sort_index()

def load_json(file) -> pd.DataFrame:
    """Supports your Yahoo-like schema or json-list of bars"""
    raw = file.read() if hasattr(file, "read") else open(file, "rb").read()
    obj = json.loads(raw.decode("utf-8", errors="ignore"))
    # schema A: {"ticker": "...", "price": {"yahoo": {"daily": [ {open,high,low,close,adj_close,volume,date}, ... ]}}}
    daily = None
    if isinstance(obj, dict):
        price = obj.get("price", {})
        yahoo = price.get("yahoo", {}) if isinstance(price, dict) else {}
        daily = yahoo.get("daily", [])
    if isinstance(daily, list) and daily:
        df = pd.DataFrame(daily)
        rename = {'open':'Open','high':'High','low':'Low','close':'Close','adj_close':'Adj Close','volume':'Volume','date':'Date'}
        df = df.rename(columns=rename)
        if "Date" not in df.columns:
            raise ValueError("JSON yahoo.daily missing 'date'")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date")
        return _standardize_columns(df).sort_index()
    # schema B: list of dicts
    if isinstance(obj, list) and obj:
        df = pd.DataFrame(obj)
        cols = {c.lower(): c for c in df.columns}
        date_col = None
        for cand in ("date","datetime","timestamp","time"):
            if cand in cols: date_col = cols[cand]; break
        if not date_col:
            raise ValueError("JSON list missing date/datetime/time column")
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).set_index(date_col)
        return _standardize_columns(df).sort_index()
    raise ValueError("Unrecognized JSON schema")

def maybe_adjust_with_adj(df: pd.DataFrame, use_adj: bool) -> pd.DataFrame:
    if use_adj and "Adj Close" in df.columns:
        factor = df["Adj Close"] / df["Close"].replace(0, np.nan)
        factor = factor.replace([np.inf, -np.inf], np.nan).fillna(1.0)
        for c in ["Open","High","Low","Close"]:
            df[c] = df[c] * factor
    return df

# ---------------
# Indicators (pd)
# ---------------
def ema(s: pd.Series, n: int) -> pd.Series: return s.ewm(span=n, adjust=False).mean()
def sma(s: pd.Series, n: int) -> pd.Series: return s.rolling(n).mean()

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["Close"].shift(1)
    tr1 = (df["High"] - df["Low"]).abs()
    tr2 = (df["High"] - pc).abs()
    tr3 = (df["Low"] - pc).abs()
    tr = pd.concat([tr1,tr2,tr3], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def macd(close: pd.Series, fast=12, slow=26, signal=9):
    fast_ = ema(close, fast); slow_ = ema(close, slow)
    macd_line = fast_ - slow_
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def stoch(df: pd.DataFrame, k=14, d=3):
    low_min = df["Low"].rolling(k).min()
    high_max = df["High"].rolling(k).max()
    k_line = 100 * (df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

def bbands(close: pd.Series, n=20, k=2.0):
    ma = sma(close, n)
    sd = close.rolling(n).std()
    upper = ma + k*sd
    lower = ma - k*sd
    width = (upper - lower) / ma
    return upper, ma, lower, width

# -----------------------------
# Candlestick pattern detection
# -----------------------------
PATTERN_FUNCS = {
    "ENGULFING": "CDLENGULFING",
    "HAMMER": "CDLHAMMER",
    "DOJI": "CDLDOJI",
    "HARAMI": "CDLHARAMI",
    "MORNINGSTAR": "CDLMORNINGSTAR",
    "SHOOTINGSTAR": "CDLSHOOTINGSTAR",
    "PIERCING": "CDLPIERCING",
}

def detect_patterns(df: pd.DataFrame, lookback: int, selected: List[str]) -> List[str]:
    out = []
    if df.empty or not selected:
        return out
    o,h,l,c = df["Open"], df["High"], df["Low"], df["Close"]
    start_idx = max(0, len(df)-int(lookback))
    window = slice(start_idx, None)
    if ta:
        for name in selected:
            fn = getattr(ta, PATTERN_FUNCS.get(name, ""), None)
            if fn is None:
                continue
            vals = fn(o.values, h.values, l.values, c.values)
            if len(vals) == 0:
                continue
            if (vals[window] != 0).any():
                out.append(name)
    else:
        # Minimal heuristic fallbacks when TA-Lib is not available
        if "ENGULFING" in selected:
            body_prev = (c.shift(1) - o.shift(1)).abs()
            body_now = (c - o).abs()
            cond = (body_now > body_prev) & (((c>o)&(c.shift(1)<o.shift(1))) | ((c<o)&(c.shift(1)>o.shift(1))))
            if cond.iloc[start_idx:].any(): out.append("ENGULFING*")
        if "DOJI" in selected:
            rng = (h-l); body = (c-o).abs()
            cond = (body / rng < 0.1)
            if cond.iloc[start_idx:].any(): out.append("DOJI*")
        if "HAMMER" in selected:
            body = (c-o).abs(); lower = (o.combine(c, max) - l); upper = (h - o.combine(c, min))
            cond = (lower > 2*body) & (upper < body)
            if cond.iloc[start_idx:].any(): out.append("HAMMER*")
    return out

# -----------------------------
# Quick signal detector (pd)
# -----------------------------
def scan_signal(df: pd.DataFrame, strategy_name: str, params: Dict[str, Any]):
    close = df["Close"]
    if strategy_name in ("SMA Cross","EMA Cross"):
        fast = int(params.get("fast", 10)); slow = int(params.get("slow", 20))
        f = sma(close, fast) if strategy_name=="SMA Cross" else ema(close, fast)
        s = sma(close, slow) if strategy_name=="SMA Cross" else ema(close, slow)
        cr = np.sign(f - s)
        now = "Buy" if cr.iloc[-1] > 0 and cr.iloc[-2] <= 0 else ("Sell" if cr.iloc[-1] < 0 and cr.iloc[-2] >= 0 else "Hold")
        diff = (cr != cr.shift(1))
        idx = diff.iloc[::-1].idxmax()
        age = (len(df.index) - 1) - df.index.get_loc(idx)
        return now, int(age), float(close.loc[idx])
    if strategy_name == "Donchian Breakout":
        up = int(params.get("upper", 20)); dn = int(params.get("lower", 10))
        hh = df["High"].rolling(up).max().shift(1)
        ll = df["Low"].rolling(dn).min().shift(1)
        buy_now = close.iloc[-1] > hh.iloc[-1]
        sell_now = close.iloc[-1] < ll.iloc[-1]
        now = "Buy" if buy_now else ("Sell" if sell_now else "Hold")
        sig = pd.Series(0, index=df.index); sig[close>hh]=1; sig[close<ll]=-1
        change = (sig != sig.shift(1))
        idx = change.iloc[::-1].idxmax()
        age = (len(df.index) - 1) - df.index.get_loc(idx)
        return now, int(age), float(close.loc[idx])
    if strategy_name == "MACD Trend":
        fast = int(params.get("fast",12)); slow=int(params.get("slow",26)); signal=int(params.get("signal",9))
        ema_tr = int(params.get("ema_trend",200))
        m, s, h = macd(close, fast, slow, signal)
        trend = ema(close, ema_tr)
        buy_now = (close.iloc[-1] > trend.iloc[-1]) and (m.iloc[-1] > s.iloc[-1]) and (m.iloc[-2] <= s.iloc[-2])
        sell_now = (m.iloc[-1] < s.iloc[-1]) and (m.iloc[-2] >= s.iloc[-2]) or (close.iloc[-1] < trend.iloc[-1])
        now = "Buy" if buy_now else ("Sell" if sell_now else "Hold")
        sig = np.where((m > s) & (m.shift(1) <= s.shift(1)), 1, np.where((m < s) & (m.shift(1) >= s.shift(1)), -1, 0))
        change = (pd.Series(sig, index=df.index) != 0)
        if change.any():
            idx = change.iloc[::-1].idxmax()
            age = (len(df.index)-1) - df.index.get_loc(idx)
            return now, int(age), float(close.loc[idx])
        return now, 0, float(close.iloc[-1])
    if strategy_name == "RSI(2) @ Bollinger":
        rsi_p = int(params.get("rsi_p",2)); rsi_buy=float(params.get("rsi_buy",10))
        bb_p = int(params.get("bb_p",20)); bb_k = float(params.get("bb_k",2.0))
        if ta:
            rsi2 = pd.Series(ta.RSI(close.values, timeperiod=rsi_p), index=close.index)
        else:
            r = close.pct_change()
            up = r.clip(lower=0).rolling(rsi_p).sum()
            down = (-r.clip(upper=0)).rolling(rsi_p).sum()
            rs = up / (down + 1e-9)
            rsi2 = 100 - (100 / (1 + rs))
        mid = close.rolling(bb_p).mean(); sd = close.rolling(bb_p).std()
        lb = mid - bb_k*sd
        buy_now = (rsi2.iloc[-1] <= rsi_buy) and (close.iloc[-1] <= lb.iloc[-1])
        now = "Buy" if buy_now else "Hold"
        cond = (rsi2 <= rsi_buy) & (close <= lb)
        if cond.any():
            idx = cond.iloc[::-1].idxmax()
            age = (len(df.index)-1) - df.index.get_loc(idx)
            return now, int(age), float(close.loc[idx])
        return now, 0, float(close.iloc[-1])
    return "Hold", 0, float(df["Close"].iloc[-1])

# -----------------------------
# Backtrader strategies
# -----------------------------
class BaseStrategy(bt.Strategy):
    params = (
        ('stake', 1),
        ('long_only', True),
        ('stop_loss_pct', 0.0),
        ('take_profit_pct', 0.0),
        ('use_atr_sizer', False),
        ('risk_pct', 0.01),
        ('atr_period', 14),
        ('atr_mult', 2.0),
        ('use_regime', False),
        ('regime_ma', 200),
        ('use_weekly_filter', False),
        ('weekly_ma', 200),
    )
    def __init__(self):
        self.entry_price = None
        self.atr = bt.ind.ATR(period=self.p.atr_period)
        self.data_w = None
        for d in self.datas:
            if d._name == 'WEEKLY':
                self.data_w = d
        if self.data_w is not None:
            self.wema = bt.ind.EMA(self.data_w.close, period=self.p.weekly_ma)
        self.spy = None
        for d in self.datas:
            if d._name == 'SPY':
                self.spy = d
        if self.spy is not None:
            self.spy_ma = bt.ind.EMA(self.spy.close, period=self.p.regime_ma)

    def _ok_regime(self):
        if not self.p.use_regime or self.spy is None: return True
        if len(self.spy) == 0: return True
        return self.spy.close[0] > self.spy_ma[0]

    def _ok_weekly(self):
        if not self.p.use_weekly_filter or self.data_w is None: return True
        if len(self.data_w) == 0: return True
        return self.data_w.close[0] > self.wema[0]

    def _size(self):
        if not self.p.use_atr_sizer:
            return int(self.p.stake)
        cash = self.broker.getcash()
        a = max(1e-9, self.atr[0])
        risk_per_share = a * self.p.atr_mult
        risk_amount = max(0.0, cash * self.p.risk_pct)
        size = int(risk_amount / max(1e-9, risk_per_share))
        return max(1, size)

    def _risk_checks(self):
        if self.entry_price is None: return
        c = self.data.close[0]
        if self.p.stop_loss_pct > 0:
            if self.position.size > 0 and c <= self.entry_price*(1-self.p.stop_loss_pct): self.close()
        if self.p.take_profit_pct > 0:
            if self.position.size > 0 and c >= self.entry_price*(1+self.p.take_profit_pct): self.close()

class SmaCross(BaseStrategy):
    params = (('fast', 10), ('slow', 20))
    def __init__(self):
        super().__init__()
        self.fast = bt.ind.SMA(period=self.p.fast)
        self.slow = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast, self.slow)
    def next(self):
        if not self._ok_regime() or not self._ok_weekly(): return
        if not self.position:
            if self.crossover > 0: self.buy(size=self._size()); self.entry_price = self.data.close[0]
            elif not self.p.long_only and self.crossover < 0: self.sell(size=self._size()); self.entry_price = self.data.close[0]
        else:
            self._risk_checks()
            if self.crossover < 0 and self.position.size > 0: self.close()
            elif self.crossover > 0 and self.position.size < 0: self.close()

class EmaCross(SmaCross):
    params = (('fast', 10), ('slow', 20))
    def __init__(self):
        BaseStrategy.__init__(self)
        self.fast = bt.ind.EMA(period=self.p.fast)
        self.slow = bt.ind.EMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(self.fast, self.slow)

class DonchianBreakout(BaseStrategy):
    params = (('upper', 20), ('lower', 10))
    def __init__(self):
        super().__init__()
        self.hh = bt.ind.Highest(self.data.high, period=self.p.upper)
        self.ll = bt.ind.Lowest(self.data.low, period=self.p.lower)
    def next(self):
        if not self._ok_regime() or not self._ok_weekly(): return
        c = self.data.close[0]
        if not self.position:
            if c > self.hh[-1]: self.buy(size=self._size()); self.entry_price = c
        else:
            self._risk_checks()
            if c < self.ll[-1]: self.close()

class MACDTrend(BaseStrategy):
    params = (('ema_trend', 200), ('fast', 12), ('slow', 26), ('signal', 9))
    def __init__(self):
        super().__init__()
        self.ema_trend = bt.ind.EMA(period=self.p.ema_trend)
        macd_ = bt.ind.MACD(self.data.close, period_me1=self.p.fast, period_me2=self.p.slow, period_signal=self.p.signal)
        self.macd = macd_.macd; self.signal = macd_.signal
    def next(self):
        if not self._ok_regime() or not self._ok_weekly(): return
        c = self.data.close[0]
        if not self.position:
            if c > self.ema_trend[0] and self.macd[0] > self.signal[0] and self.macd[-1] <= self.signal[-1]:
                self.buy(size=self._size()); self.entry_price = c
        else:
            self._risk_checks()
            if self.macd[0] < self.signal[0] or c < self.ema_trend[0]: self.close()

class RSIBBMeanRev(BaseStrategy):
    params = (('rsi_p', 2), ('rsi_buy', 10), ('rsi_exit', 60), ('bb_p', 20), ('bb_k', 2.0))
    def __init__(self):
        super().__init__()
        self.rsi = bt.ind.RSI(self.data.close, period=self.p.rsi_p)
        self.bb_mid = bt.ind.SMA(self.data.close, period=self.p.bb_p)
        self.bb_sd = bt.ind.StdDev(self.data.close, period=self.p.bb_p)
        self.bb_low = self.bb_mid - self.p.bb_k*self.bb_sd
    def next(self):
        if not self._ok_regime() or not self._ok_weekly(): return
        c = self.data.close[0]
        if not self.position:
            if self.rsi[0] <= self.p.rsi_buy and c <= self.bb_low[0]:
                self.buy(size=self._size()); self.entry_price = c
        else:
            self._risk_checks()
            if self.rsi[0] >= self.p.rsi_exit or c >= self.bb_mid[0]: self.close()

STRAT_MAP = {
    "SMA Cross": SmaCross,
    "EMA Cross": EmaCross,
    "Donchian Breakout": DonchianBreakout,
    "MACD Trend": MACDTrend,
    "RSI(2) @ Bollinger": RSIBBMeanRev,
}

# -----------------------------
# Backtest runner
# -----------------------------
def _add_optional_datas(cerebro: bt.Cerebro, params: Dict[str, Any], df_main: pd.DataFrame):
    if params.get("use_regime", False) and yf is not None:
        try:
            spy = yf.download("SPY", start=df_main.index.min().strftime("%Y-%m-%d"), progress=False, auto_adjust=False)
            spy = spy.rename(columns={'Adj Close':'Adj Close'})
            spy.index.name = "Date"
            cerebro.adddata(bt.feeds.PandasData(dataname=spy), name="SPY")
        except Exception:
            pass
    if params.get("weekly_filter", False):
        data_w = bt.feeds.PandasData(dataname=df_main)
        cerebro.adddata(data_w, name="DAILY")
        cerebro.resampledata(data_w, timeframe=bt.TimeFrame.Weeks, compression=1, name="WEEKLY")

def run_backtest(df: pd.DataFrame, params: Dict[str, Any],
                 start_cash: float = 10000.0,
                 commission: float = 0.0005,
                 slippage_perc: float = 0.0005,
                 plot: bool = False) -> Tuple[List[Any], Dict[str, Any]]:
    """Return (figs, summary). 'params' must include 'strategy_name'."""
    strategy_name = params.get("strategy_name", "SMA Cross")
    strat_cls = STRAT_MAP.get(strategy_name, SmaCross)

    cerebro = bt.Cerebro(stdstats=True)
    # map common fields into Backtrader strategy kwargs
    kwargs = {}
    for k in ("fast","slow","ema_trend","upper","lower","rsi_p","rsi_buy","rsi_exit","bb_p","bb_k",
              "use_regime","weekly_filter","use_atr_sizer","risk_pct","atr_period","atr_mult",
              "stake","long_only","stop_loss_pct","take_profit_pct"):
        if k in params: kwargs[k if k!="weekly_filter" else "use_weekly_filter"] = params[k]
    cerebro.addstrategy(strat_cls, **kwargs)

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    _add_optional_datas(cerebro, params, df)

    cerebro.broker.set_cash(float(start_cash))
    if commission > 0: cerebro.broker.setcommission(commission=float(commission))
    if slippage_perc > 0: cerebro.broker.set_slippage_perc(perc=float(slippage_perc))

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='dd')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='rets')

    results = cerebro.run()
    strat = results[0]

    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', float('nan'))
    dd = strat.analyzers.dd.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    rets = strat.analyzers.rets.get_analysis()

    summary = dict(
        Final_Value=float(cerebro.broker.getvalue()),
        Sharpe=float(sharpe) if sharpe is not None else float('nan'),
        MaxDD_pct=dd.get('max', {}).get('drawdown', float('nan')),
        MaxDD_len=dd.get('max', {}).get('len', float('nan')),
        Trades=trades.get('total', {}).get('total', 0),
        WinRate_pct=(100.0 * trades.get('won', {}).get('total', 0) / max(1, trades.get('total', {}).get('total', 1))),
        CAGR_pct=rets.get('rnorm100', float('nan')),
    )

    figs: List[Any] = []
    if plot:
        # Lightweight figure with Close + indicator lines + signal markers (pd-based, not bt plot)
        import matplotlib.pyplot as plt
        c = df["Close"]
        fig, ax = plt.subplots(figsize=(10,4))
        ax.plot(c.index, c.values, label="Close")
        if strategy_name in ("SMA Cross","EMA Cross"):
            fast = int(params.get("fast", 10)); slow = int(params.get("slow", 20))
            f = sma(c, fast) if strategy_name=="SMA Cross" else ema(c, fast)
            s = sma(c, slow) if strategy_name=="SMA Cross" else ema(c, slow)
            ax.plot(f.index, f.values, label=f"Fast({fast})")
            ax.plot(s.index, s.values, label=f"Slow({slow})")
            # signals
            cr = np.sign(f - s)
            buys = (cr > 0) & (cr.shift(1) <= 0)
            sells = (cr < 0) & (cr.shift(1) >= 0)
            ax.scatter(c.index[buys], c[buys], marker="^")
            ax.scatter(c.index[sells], c[sells], marker="v")
        elif strategy_name == "Donchian Breakout":
            up = int(params.get("upper",20)); dn = int(params.get("lower",10))
            hh = df["High"].rolling(up).max()
            ll = df["Low"].rolling(dn).min()
            ax.plot(hh.index, hh.values, label=f"Highest({up})")
            ax.plot(ll.index, ll.values, label=f"Lowest({dn})")
        elif strategy_name == "MACD Trend":
            ema_tr = int(params.get("ema_trend",200))
            tr = ema(c, ema_tr)
            ax.plot(tr.index, tr.values, label=f"EMA({ema_tr})")
        elif strategy_name == "RSI(2) @ Bollinger":
            bb_p = int(params.get("bb_p",20)); bb_k=float(params.get("bb_k",2.0))
            up, mid, low, w = bbands(c, bb_p, bb_k)
            ax.plot(up.index, up.values, label=f"BB_up({bb_p},{bb_k})")
            ax.plot(mid.index, mid.values, label=f"BB_mid({bb_p})")
            ax.plot(low.index, low.values, label=f"BB_low({bb_p},{bb_k})")
        ax.legend(loc="best"); ax.set_title(strategy_name); ax.grid(True, alpha=0.2)
        figs.append(fig)

    return figs, summary
