
# backend.py — with Optimization tab support (grid-search + walk-forward)
from __future__ import annotations
import os, json, math, itertools
from typing import List, Dict, Any, Iterable, Tuple

import pandas as pd
import numpy as np
import backtrader as bt

# Optional modules
try:
    import yfinance as yf
except Exception:
    yf = None
try:
    import talib as ta
except Exception:
    ta = None

# -------------------------
# Data utils
# -------------------------
REQ_COLS = ["Open","High","Low","Close"]

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower(): c for c in df.columns}
    aliases = {"open":"Open","o":"Open","high":"High","h":"High","low":"Low","l":"Low",
               "close":"Close","c":"Close","adj close":"Adj Close","adj_close":"Adj Close",
               "volume":"Volume","v":"Volume","date":"Date"}
    rename_map = {cols[k]:v for k,v in aliases.items() if k in cols}
    if rename_map: df = df.rename(columns=rename_map)
    for rc in REQ_COLS:
        if rc not in df.columns: raise ValueError(f"Missing column: {rc}")
    if "Adj Close" not in df.columns: df["Adj Close"] = df["Close"]
    if "Volume" not in df.columns: df["Volume"] = 0
    return df

def load_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    cols = {c.lower(): c for c in df.columns}
    for cand in ("date","datetime","timestamp"):
        if cand in cols: date_col = cols[cand]; break
    else: raise ValueError("CSV missing date/datetime column")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col)
    return _standardize_columns(df).sort_index()

def load_json(file) -> pd.DataFrame:
    raw = file.read() if hasattr(file, "read") else open(file,"rb").read()
    obj = json.loads(raw.decode("utf-8", errors="ignore"))
    daily = obj.get("price",{}).get("yahoo",{}).get("daily",[])
    if isinstance(daily,list) and daily:
        df = pd.DataFrame(daily)
        df = df.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','adj_close':'Adj Close','volume':'Volume','date':'Date'})
        if 'Date' not in df.columns: raise ValueError("Missing date in yahoo.daily")
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).set_index('Date')
        return _standardize_columns(df).sort_index()
    if isinstance(obj,list):
        df = pd.DataFrame(obj)
        cols = {c.lower(): c for c in df.columns}
        for cand in ("date","datetime","timestamp","time"):
            if cand in cols: date_col = cols[cand]; break
        else: raise ValueError("JSON list missing date/datetime")
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col]).set_index(date_col)
        return _standardize_columns(df).sort_index()
    raise ValueError("Unrecognized JSON schema")

def maybe_adjust_with_adj(df: pd.DataFrame, use_adj: bool) -> pd.DataFrame:
    if use_adj and 'Adj Close' in df.columns:
        factor = df['Adj Close'] / df['Close'].replace(0, np.nan)
        factor = factor.replace([np.inf,-np.inf], np.nan).fillna(1.0)
        for c in ['Open','High','Low','Close']:
            df[c] = df[c]*factor
    return df

# -------------------------
# Indicators (pandas)
# -------------------------
def ema(s: pd.Series, n: int) -> pd.Series: return s.ewm(span=n, adjust=False).mean()
def sma(s: pd.Series, n: int) -> pd.Series: return s.rolling(n).mean()

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df['Close'].shift(1)
    tr = pd.concat([(df['High']-df['Low']).abs(), (df['High']-pc).abs(), (df['Low']-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def macd(close: pd.Series, fast=12, slow=26, signal=9):
    fast_ = ema(close, fast); slow_ = ema(close, slow)
    macd_line = fast_ - slow_
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def stoch(df: pd.DataFrame, k=14, d=3):
    low_min = df['Low'].rolling(k).min()
    high_max = df['High'].rolling(k).max()
    k_line = 100*(df['Close']-low_min)/(high_max-low_min).replace(0,np.nan)
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

def bbands(close: pd.Series, n=20, k=2.0):
    ma = sma(close, n)
    sd = close.rolling(n).std()
    upper = ma + k*sd
    lower = ma - k*sd
    width = (upper - lower)/ma
    return upper, ma, lower, width

# -------------------------
# Strategies (Backtrader)
# -------------------------
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

# -------------------------
# SCAN + PATTERNS
# -------------------------
def scan_signal(df: pd.DataFrame, strategy: str, params: dict):
    close = df['Close']
    if strategy in ("SMA Cross","EMA Cross"):
        f = sma(close, int(params.get('fast',10))) if strategy=="SMA Cross" else ema(close, int(params.get('fast',10)))
        s = sma(close, int(params.get('slow',20))) if strategy=="SMA Cross" else ema(close, int(params.get('slow',20)))
        cr = np.sign((f - s))
        now = "Buy" if cr.iloc[-1] > 0 and cr.iloc[-2] <= 0 else ("Sell" if cr.iloc[-1] < 0 and cr.iloc[-2] >= 0 else "Hold")
        diff = (cr != cr.shift(1))
        idx = diff[::-1].idxmax()
        age = (len(df.index) - 1) - df.index.get_loc(idx)
        return now, int(age), float(close.loc[idx])
    if strategy == "Donchian Breakout":
        hh = df['High'].rolling(int(params.get('upper',20))).max().shift(1)
        ll = df['Low'].rolling(int(params.get('lower',10))).min().shift(1)
        buy_now = close.iloc[-1] > hh.iloc[-1]
        sell_now = close.iloc[-1] < ll.iloc[-1]
        now = "Buy" if buy_now else ("Sell" if sell_now else "Hold")
        sig_series = pd.Series(0, index=df.index)
        sig_series[close > hh] = 1; sig_series[close < ll] = -1
        change = (sig_series != sig_series.shift(1))
        idx = change[::-1].idxmax()
        age = (len(df.index)-1) - df.index.get_loc(idx)
        return now, int(age), float(close.loc[idx])
    if strategy == "MACD Trend":
        m, s, h = macd(close, int(params.get('fast',12)), int(params.get('slow',26)), int(params.get('signal',9)))
        ema_tr = ema(close, int(params.get('ema_trend',200)))
        buy_now = (close.iloc[-1] > ema_tr.iloc[-1]) and (m.iloc[-1] > s.iloc[-1]) and (m.iloc[-2] <= s.iloc[-2])
        sell_now = (m.iloc[-1] < s.iloc[-1]) and (m.iloc[-2] >= s.iloc[-2]) or (close.iloc[-1] < ema_tr.iloc[-1])
        now = "Buy" if buy_now else ("Sell" if sell_now else "Hold")
        sig = np.where((m > s) & (m.shift(1) <= s.shift(1)), 1, np.where((m < s) & (m.shift(1) >= s.shift(1)), -1, 0))
        change = (pd.Series(sig, index=df.index) != 0)
        if change.any():
            idx = change[::-1].idxmax()
            age = (len(df.index)-1) - df.index.get_loc(idx)
            return now, int(age), float(close.loc[idx])
        return now, 0, float(close.iloc[-1])
    if strategy == "RSI(2) @ Bollinger":
        if ta:
            rsi2 = ta.RSI(close.values, timeperiod=int(params.get('rsi_p',2)))
            rsi2 = pd.Series(rsi2, index=close.index)
        else:
            r = close.pct_change()
            up = r.clip(lower=0).rolling(int(params.get('rsi_p',2))).sum()
            down = (-r.clip(upper=0)).rolling(int(params.get('rsi_p',2))).sum()
            rs = up / (down + 1e-9)
            rsi2 = 100 - (100 / (1 + rs))
        mid = close.rolling(int(params.get('bb_p',20))).mean()
        sd = close.rolling(int(params.get('bb_p',20))).std()
        lb = mid - float(params.get('bb_k',2.0))*sd
        buy_now = (rsi2.iloc[-1] <= float(params.get('rsi_buy',10))) and (close.iloc[-1] <= lb.iloc[-1])
        now = "Buy" if buy_now else "Hold"
        cond = (rsi2 <= float(params.get('rsi_buy',10))) & (close <= lb)
        if cond.any():
            idx = cond.iloc[::-1].idxmax()
            age = (len(df.index)-1) - df.index.get_loc(idx)
            return now, int(age), float(close.loc[idx])
        return now, 0, float(close.iloc[-1])
    return "Hold", 0, float(close.iloc[-1])

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
    if df.empty or not selected: return out
    o,h,l,c = df['Open'], df['High'], df['Low'], df['Close']
    start_idx = max(0, len(df)-lookback)
    window = slice(start_idx, None)
    if ta:
        for name in selected:
            fn = getattr(ta, PATTERN_FUNCS.get(name,""), None)
            if fn is None: continue
            vals = fn(o.values, h.values, l.values, c.values)
            if len(vals) == 0: continue
            if (vals[window] != 0).any(): out.append(name)
    else:
        if "ENGULFING" in selected:
            body_prev = (c.shift(1)-o.shift(1)).abs()
            body_now = (c-o).abs()
            cond = (body_now > body_prev) & (((c>o)&(c.shift(1)<o.shift(1))) | ((c<o)&(c.shift(1)>o.shift(1))))
            if cond.iloc[start_idx:].any(): out.append("ENGULFING*")
        if "DOJI" in selected:
            rng = (h-l); body = (c-o).abs()
            cond = (body/rng < 0.1)
            if cond.iloc[start_idx:].any(): out.append("DOJI*")
        if "HAMMER" in selected:
            body = (c-o).abs(); lower_shadow = (o.combine(c, max) - l)
            upper_shadow = (h - o.combine(c, min))
            cond = (lower_shadow > 2*body) & (upper_shadow < body)
            if cond.iloc[start_idx:].any(): out.append("HAMMER*")
    return out

# -------------------------
# Backtest runner
# -------------------------
def add_optional_datas(cerebro: bt.Cerebro, use_regime: bool, use_weekly: bool, df_main: pd.DataFrame):
    if use_regime and yf is not None:
        try:
            spy = yf.download("SPY", start=df_main.index.min().strftime("%Y-%m-%d"), end=None, progress=False, auto_adjust=False)
            spy = spy.rename(columns={'Open':'Open','High':'High','Low':'Low','Close':'Close','Adj Close':'Adj Close','Volume':'Volume'})
            spy.index.name = 'Date'
            cerebro.adddata(bt.feeds.PandasData(dataname=spy), name='SPY')
        except Exception:
            pass
    if use_weekly:
        data_w = bt.feeds.PandasData(dataname=df_main)
        cerebro.adddata(data_w, name='DAILY')
        cerebro.resampledata(data_w, timeframe=bt.TimeFrame.Weeks, compression=1, name='WEEKLY')

def run_backtest(df: pd.DataFrame, strategy_name: str, params: dict,
                 start_cash: float, commission: float, slippage_perc: float,
                 figscale: float, x_margin: float, scheme_colors=None, plot: bool = False):
    cerebro = bt.Cerebro(stdstats=True)
    strat_cls = STRAT_MAP[strategy_name]
    cerebro.addstrategy(strat_cls, **params)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    add_optional_datas(cerebro, params.get('use_regime', False), params.get('use_weekly_filter', False), df)
    cerebro.broker.set_cash(start_cash)
    if commission > 0: cerebro.broker.setcommission(commission=commission)
    if slippage_perc > 0: cerebro.broker.set_slippage_perc(perc=slippage_perc)

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
        Final_Value=cerebro.broker.getvalue(),
        Sharpe=sharpe,
        MaxDD_pct=dd.get('max', {}).get('drawdown', float('nan')),
        MaxDD_len=dd.get('max', {}).get('len', float('nan')),
        Trades=trades.get('total', {}).get('total', 0),
        WinRate_pct=(100.0 * trades.get('won', {}).get('total', 0) / max(1, trades.get('total', {}).get('total', 1))),
        CAGR_pct=rets.get('rnorm100', float('nan')),
    )
    return [], summary

# -------------------------
# Optimization
# -------------------------
def param_grid_from_ranges(ranges: Dict[str, Any]) -> List[Dict[str, Any]]:
    """ranges example: {"fast":[8,20,4], "slow":[20,60,10], "ema_trend":[100,200,50]} or discrete list: {"bb_k":[1.5,2.0,2.5]}"""
    grid = []
    keys = []
    values = []
    for k, spec in ranges.items():
        keys.append(k)
        if isinstance(spec, list) and len(spec) == 3 and all(isinstance(x,(int,float)) for x in spec):
            start, stop, step = spec
            seq = []
            v = start
            while (step>0 and v <= stop) or (step<0 and v >= stop):
                seq.append(round(v,6))
                v = v + step
            values.append(seq)
        elif isinstance(spec, list):
            values.append(spec)
        else:
            values.append([spec])
    import itertools
    for combo in itertools.product(*values):
        grid.append({k: combo[i] for i,k in enumerate(keys)})
    return grid

def walk_forward_splits(n: int, folds: int, oos_frac: float):
    """Return list of (train_start, train_end, test_start, test_end) indices for time series of length n."""
    folds = max(1, int(folds)); oos_frac = min(0.8, max(0.05, float(oos_frac)))
    test_len = max(5, int(n * oos_frac))
    splits = []
    anchor = n - test_len
    step = max(10, int((anchor) / max(1, folds)))
    for start in range(0, anchor, step):
        train_end = min(anchor, start + step)
        if train_end <= start+20: continue
        splits.append((start, train_end, train_end, min(n, train_end + test_len)))
    if not splits:
        splits.append((0, anchor, anchor, n))
    return splits

def objective_score(summary: Dict[str, Any], objective: str) -> float:
    if not summary: return -1e9
    sharpe = summary.get("Sharpe") or 0.0
    cagr = summary.get("CAGR_pct") or 0.0
    dd = summary.get("MaxDD_pct") or 0.0
    win = summary.get("WinRate_pct") or 0.0
    trades = summary.get("Trades") or 0
    if objective == "Sharpe": return float(sharpe)
    if objective == "CAGR": return float(cagr)
    if objective == "Return/DD": return float(cagr) / max(1e-6, float(dd))
    if objective == "WinRate": return float(win)
    if objective == "Trades": return float(trades)
    return float(sharpe)

# ------------ Qt bridge --------------
from PySide6.QtCore import QObject, Slot, Signal, QAbstractListModel, Qt, QModelIndex

class DictListModel(QAbstractListModel):
    def __init__(self, roles: List[str], parent=None):
        super().__init__(parent)
        self._roles = roles
        self._items: List[Dict[str, Any]] = []
        self._role_ids = {Qt.UserRole + i + 1: name.encode('utf-8') for i, name in enumerate(self._roles)}

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None
        name = self._role_ids.get(role, None)
        if name is None:
            return None
        key = name.decode('utf-8')
        return self._items[row].get(key)

    def roleNames(self):
        return self._role_ids

    def setRows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._items = rows
        self.endResetModel()

class ScanListModel(DictListModel):
    def __init__(self, parent=None):
        roles = ["Symbol","Pass","SignalNOW","SignalAge","PriceAtSignal","RR","Patterns"]
        super().__init__(roles, parent)

class BtListModel(DictListModel):
    def __init__(self, parent=None):
        roles = ["Symbol","Final_Value","Sharpe","MaxDD_pct","WinRate_pct","Trades","CAGR_pct"]
        super().__init__(roles, parent)

class OptListModel(DictListModel):
    def __init__(self, parent=None):
        roles = ["Rank","Params","Score","Sharpe","CAGR_pct","MaxDD_pct","WinRate_pct","Trades","Universe","Folds"]
        super().__init__(roles, parent)

class Controller(QObject):
    statusChanged = Signal(str)

    def __init__(self, scan_model: ScanListModel, bt_model: BtListModel, opt_model: OptListModel):
        super().__init__()
        self.scan_model = scan_model
        self.bt_model = bt_model
        self.opt_model = opt_model

    def _load_from_folder(self, folder: str, use_adj: bool, start_date: str|None):
        symbols, data_map = [], {}
        if not os.path.isdir(folder):
            return symbols, data_map
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.json','.csv'))]
        for fn in files:
            path = os.path.join(folder, fn)
            try:
                with open(path, 'rb') as f:
                    df = load_csv(f) if fn.lower().endswith('.csv') else load_json(f)
            except Exception as e:
                continue
            sym = fn.replace('.json','').replace('.csv','').upper()
            if fn.lower().endswith('.json'):
                try:
                    with open(path, 'r', encoding='utf-8') as ft:
                        obj = json.load(ft)
                        if isinstance(obj, dict) and isinstance(obj.get('ticker',None), str):
                            sym = obj['ticker'].upper()
                except Exception:
                    pass
            if start_date:
                df = df.loc[pd.to_datetime(df.index) >= pd.to_datetime(start_date)]
            df = maybe_adjust_with_adj(df.copy(), use_adj).sort_index()
            symbols.append(sym); data_map[sym] = df
        return symbols, data_map

    @Slot(str, bool, str, str, int, int, int, int, int, int, float, bool, bool, str, float, float, float, float, float, float, str, bool, bool, float, bool, bool, float, float, int, str)
    def runScan(self,
                data_dir: str, use_adj: bool, start_date: str,
                strategy_name: str,
                fast: int, slow: int, ema_tr: int,
                don_up: int, don_dn: int,
                rsi_p: int, rsi_buy: int, rsi_exit: int,
                bb_p: int, bb_k: float,
                use_regime: bool, weekly_filter: bool,
                sizing_mode: str, stake: float, risk_pct: float, atr_p: float, atr_mult: float,
                rr_min: float, rr_target: str,
                macd_cross: bool, bb_squeeze: bool, bb_thr: float,
                breakout: bool, stoch_cross: bool, adx_min: float, atr_min: float,
                lookback: int, patterns_csv: str):
        try:
            symbols, data_map = self._load_from_folder(data_dir, use_adj, start_date if start_date else None)
            rows = []
            pats = [p.strip().upper() for p in patterns_csv.split(',') if p.strip()]
            for sym, df in data_map.items():
                if len(df) < max(60, fast, slow, ema_tr, don_up, don_dn, bb_p, rsi_p)+5:
                    rows.append(dict(Symbol=sym, Pass=False, SignalNOW="N/A", SignalAge=0, PriceAtSignal=float('nan'), RR=0.0, Patterns="few bars"))
                    continue
                base_params = dict(
                    fast=int(fast), slow=int(slow), ema_trend=int(ema_tr),
                    upper=int(don_up), lower=int(don_dn),
                    rsi_p=int(rsi_p), rsi_buy=int(rsi_buy), rsi_exit=int(rsi_exit),
                    bb_p=int(bb_p), bb_k=float(bb_k),
                    use_regime=bool(use_regime), use_weekly_filter=bool(weekly_filter),
                    use_atr_sizer=(sizing_mode=="ATR risk %"), risk_pct=float(risk_pct),
                    atr_period=int(atr_p), atr_mult=float(atr_mult),
                    stake=int(stake), long_only=True,
                    stop_loss_pct=0.0, take_profit_pct=0.0,
                )
                sig_now, sig_age, price_at = scan_signal(df, strategy_name, base_params)

                close = df['Close']
                m, s, h = macd(close)
                bbU, bbM, bbL, bbW = bbands(close, n=bb_p, k=bb_k)
                K, D = stoch(df)
                atrv = atr(df)

                conds = []
                if macd_cross: conds.append((m.iloc[-1] > s.iloc[-1]) and (m.iloc[-2] <= s.iloc[-2]))
                if bb_squeeze: conds.append(bbW.iloc[-1] <= (bb_thr/100.0 if bb_thr>1 else bb_thr))
                if breakout: conds.append(close.iloc[-1] > (bbU.iloc[-1] if not np.isnan(bbU.iloc[-1]) else 1e99))
                if stoch_cross: conds.append((K.iloc[-1] > D.iloc[-1]) and (K.iloc[-2] <= D.iloc[-2]))
                if atr_min > 0:
                    atr_pct = (atrv.iloc[-1] / max(1e-9, close.iloc[-1]))*100.0
                    conds.append(atr_pct >= atr_min)

                if adx_min > 0:
                    if ta is not None:
                        adx_val = float(ta.ADX(df['High'].values, df['Low'].values, df['Close'].values, timeperiod=14)[-1])
                        conds.append(adx_val >= adx_min)
                    else:
                        conds.append(False)

                pat_list = detect_patterns(df, int(lookback), pats) if pats else []

                stop_dist = float(atrv.iloc[-1]) * float(atr_mult)
                entry_price = float(close.iloc[-1])
                stop_price = max(0.0001, entry_price - stop_dist)
                if rr_target == "boll_mid":
                    mid = close.rolling(int(bb_p)).mean()
                    target_price = float(mid.iloc[-1]) if not np.isnan(mid.iloc[-1]) else entry_price + stop_dist
                elif rr_target == "donchian_high":
                    hh = df['High'].rolling(int(don_up)).max()
                    target_price = float(hh.iloc[-1]) if not np.isnan(hh.iloc[-1]) else entry_price + stop_dist
                else:
                    target_price = entry_price + 2.0*float(atrv.iloc[-1])
                rr = (target_price - entry_price) / max(1e-9, (entry_price - stop_price))
                if rr_min > 0: conds.append(rr >= rr_min)

                pass_now = all(conds) if conds else True
                rows.append(dict(
                    Symbol=sym, Pass=pass_now,
                    SignalNOW=sig_now, SignalAge=int(sig_age),
                    PriceAtSignal=round(price_at, 4), RR=round(rr, 2),
                    Patterns=",".join(pat_list)
                ))
            rows = sorted(rows, key=lambda r: (not r["Pass"], -r.get("RR", 0.0), r["Symbol"]))
            self.scan_model.setRows(rows)
            self.statusChanged.emit(f"Scan done: {len(rows)} rows")
        except Exception as e:
            self.statusChanged.emit(f"ERROR: {e}")

    @Slot(str, bool, str, str, int, int, int, int, int, int, float, bool, bool, str, float, float, float, float, float)
    def runBacktest(self,
                    data_dir: str, use_adj: bool, start_date: str,
                    strategy_name: str,
                    fast: int, slow: int, ema_tr: int,
                    don_up: int, don_dn: int,
                    rsi_p: int, rsi_buy: int, rsi_exit: int,
                    bb_p: int, bb_k: float,
                    use_regime: bool, weekly_filter: bool,
                    sizing_mode: str, stake: float, risk_pct: float, atr_p: float, atr_mult: float):
        try:
            symbols, data_map = self._load_from_folder(data_dir, use_adj, start_date if start_date else None)
            params = dict(
                fast=int(fast), slow=int(slow), ema_trend=int(ema_tr),
                upper=int(don_up), lower=int(don_dn),
                rsi_p=int(rsi_p), rsi_buy=int(rsi_buy), rsi_exit=int(rsi_exit),
                bb_p=int(bb_p), bb_k=float(bb_k),
                use_regime=bool(use_regime), use_weekly_filter=bool(weekly_filter),
                use_atr_sizer=(sizing_mode=="ATR risk %"), risk_pct=float(risk_pct),
                atr_period=int(atr_p), atr_mult=float(atr_mult),
                stake=int(stake), long_only=True,
                stop_loss_pct=0.0, take_profit_pct=0.0,
            )
            rows = []
            for sym, df in data_map.items():
                _, summary = run_backtest(df, strategy_name, params,
                                          start_cash=10000.0, commission=0.0005, slippage_perc=0.0005,
                                          figscale=0.01, x_margin=0.0, scheme_colors=None, plot=False)
                row = {"Symbol": sym}
                row.update({
                    "Final_Value": round(summary.get("Final_Value", 0.0), 2),
                    "Sharpe": summary.get("Sharpe", None),
                    "MaxDD_pct": round(summary.get("MaxDD_pct", 0.0), 2) if summary.get("MaxDD_pct") is not None else None,
                    "WinRate_pct": round(summary.get("WinRate_pct", 0.0), 2),
                    "Trades": int(summary.get("Trades", 0)),
                    "CAGR_pct": round(summary.get("CAGR_pct", 0.0), 2) if summary.get("CAGR_pct") is not None else None
                })
                rows.append(row)
            rows = sorted(rows, key=lambda r: (-float('%.6f' % (r.get("Sharpe") or 0)), r["Symbol"]))
            self.bt_model.setRows(rows)
            self.statusChanged.emit(f"Backtest done: {len(rows)} rows")
        except Exception as e:
            self.statusChanged.emit(f"ERROR: {e}")

    @Slot(str, bool, str, str, str, int, float, int, float, int)
    def runOptimize(self,
                    data_dir: str, use_adj: bool, start_date: str,
                    strategy_name: str,
                    ranges_json: str,         # e.g. {"fast":[8,20,4],"slow":[20,60,10]} or {"bb_k":[1.5,2.0,2.5]}
                    universe_limit: int,      # max symbols from folder
                    oos_frac: float,          # test size fraction per fold (e.g., 0.2)
                    folds: int,               # number of walk-forward folds
                    min_trades: int,          # constraint
                    objective: int            # 0=Sharpe,1=CAGR,2=Return/DD,3=WinRate,4=Trades
                    ):
        try:
            objective_map = {0:"Sharpe",1:"CAGR",2:"Return/DD",3:"WinRate",4:"Trades"}
            objective_name = objective_map.get(int(objective), "Sharpe")

            symbols, data_map = self._load_from_folder(data_dir, use_adj, start_date if start_date else None)
            symbols = symbols[:max(1,int(universe_limit))] if universe_limit > 0 else symbols

            ranges = json.loads(ranges_json) if ranges_json.strip() else {}
            grid = param_grid_from_ranges(ranges)
            if not grid:
                self.statusChanged.emit("ERROR: טווחי פרמטרים ריקים")
                return

            results = []
            for params in grid:
                scores = []
                agg_summ = {"Sharpe":0.0,"CAGR_pct":0.0,"MaxDD_pct":0.0,"WinRate_pct":0.0,"Trades":0}
                count = 0
                for sym in symbols:
                    df = data_map[sym]
                    n = len(df)
                    if n < 150: continue
                    splits = walk_forward_splits(n, folds, oos_frac)
                    for (tr_s, tr_e, te_s, te_e) in splits:
                        sub = df.iloc[tr_s:te_e].copy()
                        _, summ = run_backtest(sub, strategy_name, params,
                                               start_cash=10000.0, commission=0.0005, slippage_perc=0.0005,
                                               figscale=0.01, x_margin=0.0, scheme_colors=None, plot=False)
                        if (summ.get("Trades") or 0) < min_trades:
                            continue
                        score = objective_score(summ, objective_name)
                        scores.append(score)
                        for k in ("Sharpe","CAGR_pct","MaxDD_pct","WinRate_pct","Trades"):
                            v = summ.get(k, 0.0) or 0.0
                            agg_summ[k] += float(v)
                        count += 1
                if not scores:
                    continue
                mean_score = float(np.mean(scores))
                if count > 0:
                    for k in agg_summ:
                        agg_summ[k] = agg_summ[k] / count
                results.append({
                    "Params": json.dumps(params),
                    "Score": round(mean_score, 4),
                    "Sharpe": round(agg_summ["Sharpe"], 4),
                    "CAGR_pct": round(agg_summ["CAGR_pct"], 4),
                    "MaxDD_pct": round(agg_summ["MaxDD_pct"], 4),
                    "WinRate_pct": round(agg_summ["WinRate_pct"], 2),
                    "Trades": int(agg_summ["Trades"]),
                    "Universe": len(symbols),
                    "Folds": len(walk_forward_splits(1000, folds, oos_frac))
                })
            results = sorted(results, key=lambda r: -r["Score"])[:50]
            for i, r in enumerate(results, start=1):
                r["Rank"] = i
            self.opt_model.setRows(results)
            self.statusChanged.emit(f"Optimize done: {len(results)} combos")
        except Exception as e:
            self.statusChanged.emit(f"ERROR: {e}")
