
# backend.py — with Optimization tab support (grid-search + walk-forward)
from __future__ import annotations
import os, json, math, itertools
from typing import List, Dict, Any, Iterable, Tuple

import pandas as pd
import numpy as np
import backtrader as bt
import json

# Optional modules
try:
    import yfinance as yf
except Exception:
    yf = None
try:
    import talib as ta
except Exception:
    ta = None

# Split imports
from logic.strategies import STRAT_MAP
from logic.indicators import ema, sma, atr, macd, stoch, bbands
from data.data_utils import _standardize_columns, load_csv, load_json, maybe_adjust_with_adj
# from utils.helpers import ... # Add helper imports as needed

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


class TradeListAnalyzer(bt.Analyzer):
    """Simple analyzer that collects per-trade details (entry/exit datetime, prices, size, pnl).
    This is defensive: it extracts attributes when available and falls back gracefully.
    """
    def __init__(self):
        self.trades = []

    def notify_trade(self, trade):
        # record only closed trades
        try:
            if not trade.isclosed:
                return
            # extract datetimes where available
            try:
                odt = trade.open_datetime(0)
            except Exception:
                try:
                    odt = trade.open_datetime()
                except Exception:
                    odt = None
            try:
                cdt = trade.close_datetime(0)
            except Exception:
                try:
                    cdt = trade.close_datetime()
                except Exception:
                    cdt = None

            # extract numeric values if present
            entry_price = None
            exit_price = None
            size = None
            profit = None
            try:
                entry_price = float(getattr(trade, 'open_price', None) or getattr(trade, 'price', None) or None)
            except Exception:
                entry_price = None
            try:
                exit_price = float(getattr(trade, 'close_price', None) or getattr(trade, 'price', None) or None)
            except Exception:
                exit_price = None
            try:
                size = float(getattr(trade, 'size', None) or 0)
            except Exception:
                size = None
            try:
                profit = float(getattr(trade, 'pnl', None) or getattr(trade, 'pnlcomm', None) or None)
            except Exception:
                profit = None

            self.trades.append({
                'entry_date': str(odt) if odt is not None else None,
                'exit_date': str(cdt) if cdt is not None else None,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'size': size,
                'profit': profit
            })
        except Exception:
            # keep the analyzer robust — never raise
            pass

    def get_analysis(self):
        return self.trades


class EquityCurveAnalyzer(bt.Analyzer):
    """Capture broker equity value each bar plus running max and drawdown percentage.

    get_analysis returns dict with keys: 'datetime' (list of ISO strings),
    'equity' (list of floats), 'drawdown_pct' (list of floats: positive numbers, not negative),
    'max_drop_pct' (single float), 'max_equity' (float).
    """
    def __init__(self):
        self._dts = []
        self._equity = []
        self._dd = []
        self._high = None
        self._max_drop = 0.0

    def next(self):  # called each bar
        try:
            dt = None
            try:
                dt = self.strategy.datetime.datetime(0)
            except Exception:
                # fallback attempt
                try:
                    dt = self.strategy.data.datetime.datetime(0)
                except Exception:
                    dt = None
            val = float(self.strategy.broker.getvalue())
            if self._high is None or val > self._high:
                self._high = val
            dd = 0.0
            if self._high and self._high > 0:
                dd = (self._high - val) / self._high * 100.0
            if dd > self._max_drop:
                self._max_drop = dd
            self._dts.append(dt.isoformat() if dt else None)
            self._equity.append(val)
            self._dd.append(dd)
        except Exception:
            pass

    def get_analysis(self):
        return {
            'datetime': self._dts,
            'equity': self._equity,
            'drawdown_pct': self._dd,
            'max_drop_pct': self._max_drop,
            'max_equity': self._high,
        }

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
        # Simple heuristic placeholders for additional patterns (approximate / coarse):
        if "HARAMI" in selected:
            # small body inside previous large opposite body
            prev_body = (c.shift(1)-o.shift(1)).abs(); cur_body = (c-o).abs()
            inside = (c <= c.shift(1)) & (c >= o.shift(1)) | (c >= c.shift(1)) & (c <= o.shift(1))
            cond = (cur_body < prev_body*0.6) & inside
            if cond.iloc[start_idx:].any(): out.append("HARAMI*")
        if "MORNINGSTAR" in selected:
            # crude: three-bar pattern: large down, small indecision, large up closing into first bar body
            if len(c) > 3:
                a = c.shift(2); b = c.shift(1); cur = c
                down = (a < o.shift(2))  # previous bar bearish close
                small = ( (b - o.shift(1)).abs() < (a - o.shift(2)).abs()*0.4 )
                up = (cur > o) & (cur - o > (o.shift(2)-a)*0.5)
                cond = down & small & up
                if cond.iloc[start_idx:].any(): out.append("MORNINGSTAR*")
        if "SHOOTINGSTAR" in selected:
            # long upper shadow, small real body near low
            body = (c-o).abs(); upper = (h - c.combine(o, max)); lower = (o.combine(c, min) - l)
            cond = (upper > body*2.5) & (lower < body*0.5)
            if cond.iloc[start_idx:].any(): out.append("SHOOTINGSTAR*")
        if "PIERCING" in selected:
            # approximation: bullish close penetrating >=50% of previous bearish body after gap down
            prev_body = (o.shift(1)-c.shift(1))
            gap = o < c.shift(1)
            penetrate = (c - c.shift(1)) >= (prev_body*0.5)
            cond = gap & penetrate
            if cond.iloc[start_idx:].any(): out.append("PIERCING*")
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

def _run_backtest_single(df: pd.DataFrame, strategy_name: str, params: dict,
                         start_cash: float, commission: float, slippage_perc: float,
                         figscale: float, x_margin: float, scheme_colors=None, plot: bool = False):
    """Run a single-dataframe backtest and return (figs, summary).
    Internal helper used by the public `run_backtest` which can dispatch
    either a single dataframe or a map of symbol->dataframes.
    """
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
    # Attach our simple TradeListAnalyzer to extract per-trade rows
    try:
        cerebro.addanalyzer(TradeListAnalyzer, _name='trade_list')
    except Exception:
        # if for any reason analyzer registration fails, continue without it
        pass
    cerebro.addanalyzer(bt.analyzers.Returns, _name='rets')
    try:
        cerebro.addanalyzer(EquityCurveAnalyzer, _name='equity_curve')
    except Exception:
        pass

    results = cerebro.run()
    strat = results[0]

    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', float('nan'))
    dd = strat.analyzers.dd.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    rets = strat.analyzers.rets.get_analysis()
    try:
        eq_analysis = strat.analyzers.equity_curve.get_analysis()
    except Exception:
        eq_analysis = {}
    summary = dict(
        Final_Value=cerebro.broker.getvalue(),
        Sharpe=sharpe,
        MaxDD_pct=dd.get('max', {}).get('drawdown', float('nan')),
        MaxDD_len=dd.get('max', {}).get('len', float('nan')),
        Trades=trades.get('total', {}).get('total', 0),
        WinRate_pct=(100.0 * trades.get('won', {}).get('total', 0) / max(1, trades.get('total', {}).get('total', 1))),
        CAGR_pct=rets.get('rnorm100', float('nan')),
        equity_series=[(dt, v) for dt, v in zip(eq_analysis.get('datetime', []), eq_analysis.get('equity', []))] if eq_analysis else [],
        drawdown_series=[(dt, ddv) for dt, ddv in zip(eq_analysis.get('datetime', []), eq_analysis.get('drawdown_pct', []))] if eq_analysis else [],
    )
    # include the raw trade-analyzer output for richer UI diagnostics/trade-detail rendering
    try:
        summary['trade_analyzer'] = trades
    except Exception:
        # If for any reason the trades structure is not serializable or unexpected, still return summary
        summary['trade_analyzer'] = {}
    # attach the per-trade list from TradeListAnalyzer if available
    try:
        tlist = strat.analyzers.trade_list.get_analysis()
        if isinstance(tlist, list):
            # Enrich trades with derived metrics (hold_days, pct_return, profit_pct)
            import pandas as _pd
            enriched = []
            for tr in tlist:
                if not isinstance(tr, dict):
                    continue
                ed = tr.get('entry_date'); xd = tr.get('exit_date')
                hold_days = None
                try:
                    if ed and xd:
                        ed_dt = _pd.to_datetime(ed, errors='coerce')
                        xd_dt = _pd.to_datetime(xd, errors='coerce')
                        if not _pd.isna(ed_dt) and not _pd.isna(xd_dt):
                            hold_days = (xd_dt - ed_dt).days
                except Exception:
                    hold_days = None
                entry_price = tr.get('entry_price'); exit_price = tr.get('exit_price'); size = tr.get('size'); profit = tr.get('profit')
                pct_return = None
                profit_pct = None
                try:
                    if entry_price is not None and exit_price is not None:
                        pct_return = (float(exit_price) - float(entry_price)) / max(1e-9, float(entry_price)) * 100.0
                except Exception:
                    pct_return = None
                try:
                    if profit is not None and entry_price is not None and size not in (None, 0):
                        denom = abs(float(entry_price) * float(size))
                        if denom > 0:
                            profit_pct = float(profit) / denom * 100.0
                except Exception:
                    profit_pct = None
                tr_new = dict(tr)
                tr_new['hold_days'] = hold_days
                tr_new['pct_return'] = pct_return
                tr_new['profit_pct'] = profit_pct
                enriched.append(tr_new)
            summary['trade_list'] = enriched
    except Exception:
        # ignore if not present
        pass
    figs = []
    # If plot requested, create upgraded matplotlib figure: price + actual equity + drawdown area.
    if plot:
        try:
            import matplotlib
            # Use Agg for headless safety (Qt canvas can still render saved fig if needed)
            try:
                matplotlib.use('Agg')
            except Exception:
                pass
            import matplotlib.pyplot as plt
            eq_pairs = summary.get('equity_series', [])
            dd_pairs = summary.get('drawdown_series', [])
            eq_times = [pd.to_datetime(p[0]) for p in eq_pairs if p[0]]
            eq_vals = [p[1] for p in eq_pairs if p[0]]
            dd_vals = [p[1] for p in dd_pairs if p[0]]
            # two-row layout
            fig, (ax_price, ax_dd) = plt.subplots(2, 1, sharex=True, figsize=(10 * max(0.5, figscale), 7), gridspec_kw={'height_ratios': [3, 1]})
            # Price + Equity (twin axis)
            try:
                ax_price.plot(df.index, df['Close'], label='Close', color='tab:blue', linewidth=1.0)
            except Exception:
                ax_price.plot(df.index, pd.to_numeric(df.iloc[:, 0], errors='coerce'), label='Price', color='tab:blue', linewidth=1.0)
            ax_price.set_ylabel('Price')
            if eq_times and eq_vals:
                ax_eq = ax_price.twinx()
                ax_eq.plot(eq_times, eq_vals, label='Equity', color='tab:orange', linewidth=1.0)
                ax_eq.set_ylabel('Equity')
                # Combine legends
                lines, labels = ax_price.get_legend_handles_labels()
                lines2, labels2 = ax_eq.get_legend_handles_labels()
                ax_price.legend(lines + lines2, labels + labels2, loc='upper left')
            else:
                ax_price.legend(loc='upper left')
            ax_price.set_title(f"{strategy_name} - {getattr(df, 'name', '')}")
            # Drawdown subplot (positive percentages rendered as negative area for visual intuition)
            if eq_times and dd_vals and len(eq_times) == len(dd_vals):
                dd_neg = [-v for v in dd_vals]  # invert for plotting below zero
                ax_dd.fill_between(eq_times, dd_neg, 0, color='tab:red', alpha=0.35, step='pre')
                ax_dd.set_ylabel('Drawdown %')
                ax_dd.set_ylim(min(dd_neg) * 1.05 if dd_neg else -1, 1)
                ax_dd.set_yticks([min(dd_neg) if dd_neg else -1, 0])
            else:
                ax_dd.set_visible(False)
            fig.tight_layout()
            figs = [fig]
        except Exception:
            figs = []

    return figs, summary


def run_backtest(df: Any, strategy_name: str, params: dict,
                 start_cash: float, commission: float, slippage_perc: float,
                 figscale: float, x_margin: float, scheme_colors=None, plot: bool = False):
    """Public backtest runner. Accepts either a single pandas.DataFrame (legacy)
    or a mapping/dict of symbol->DataFrame for multi-symbol batch runs.

    For multi-symbol runs the function will run each symbol independently and
    aggregate the summaries into a dict with a `per_symbol` key containing
    the individual summaries. This keeps the implementation simple and
    backward-compatible while enabling universe runs.
    """
    # If given a mapping of symbols to DataFrames, run each symbol separately
    if isinstance(df, dict):
        aggregated = {'per_symbol': {}, 'summary': {}}
        figs_all = []
        for sym, d in df.items():
            try:
                figs, summ = _run_backtest_single(d, strategy_name, params,
                                                  start_cash, commission, slippage_perc,
                                                  figscale, x_margin, scheme_colors, plot)
                aggregated['per_symbol'][sym] = summ
                if figs:
                    figs_all.extend(figs)
            except Exception as e:
                aggregated['per_symbol'][sym] = {'error': str(e)}
        # Provide a small aggregated summary (sum of final values, simple stats)
        try:
            total_value = sum([v.get('Final_Value', 0) for v in aggregated['per_symbol'].values() if isinstance(v, dict)])
            aggregated['summary']['Total_Final_Value'] = total_value
        except Exception:
            aggregated['summary']['Total_Final_Value'] = None
        return figs_all, aggregated

    # Otherwise assume a single dataframe and run as before
    return _run_backtest_single(df, strategy_name, params,
                                start_cash, commission, slippage_perc,
                                figscale, x_margin, scheme_colors, plot)

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
