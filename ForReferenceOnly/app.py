from __future__ import annotations
import shutil

import os, io, json, math, itertools, time, datetime as dt
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

import app_v8 as base

# Optional (IBKR)
try:
    from ib_insync import IB, Stock, MarketOrder, util
    IB_AVAILABLE = True
except Exception:
    IB_AVAILABLE = False

st.set_page_config(page_title="QuantDesk — Web", layout="wide")


# ---------------------------
# Parquet Cache Helpers (with policy)
# ---------------------------
def _parquet_paths(dirpath: str):
    cache_dir = os.path.join(dirpath, ".qd_parquet")
    if not os.path.isdir(cache_dir):
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass
    return cache_dir

def _load_from_cache_or_source(path: str, use_adj: bool, policy: str = "auto"):
    """policy: 'auto' (use cache if fresh), 'parquet' (require cache), 'source' (ignore cache)."""
    low = path.lower()
    src_mtime = os.path.getmtime(path)
    cache_dir = _parquet_paths(os.path.dirname(path))
    sym = os.path.basename(path).replace(".json","").replace(".csv","").upper()
    pq_path = os.path.join(cache_dir, f"{sym}.parquet")

    def _read_source():
        with open(path, "rb") as f:
            df_local = base.load_csv(f) if low.endswith(".csv") else base.load_json(f)
        df_local = base.maybe_adjust_with_adj(df_local.copy(), use_adj).sort_index()
        return df_local

    try:
        if policy == "source":
            return _read_source()
        if policy == "parquet":
            if os.path.exists(pq_path):
                return pd.read_parquet(pq_path)
            else:
                raise FileNotFoundError(f"Missing parquet for {sym} under policy 'parquet'")
        # auto policy
        if os.path.exists(pq_path) and os.path.getmtime(pq_path) >= src_mtime:
            return pd.read_parquet(pq_path)
        # else read source and refresh cache
        df = _read_source()
        if len(df) >= 1:
            try:
                df.to_parquet(pq_path, index=True)
            except Exception:
                pass
        return df
    except Exception:
        # fallback
        return _read_source()

# ---------------------------
# Helpers
# ---------------------------
def _standardize_rr_target(name: str) -> str:
    name = (name or "").lower().strip()
    if "boll" in name: return "Boll mid"
    if "donch" in name: return "Donchian high"
    return "2xATR"

def rr_from_atr(df: pd.DataFrame, atr_mult: float, target_mode: str="2xATR",
                bb_p: int=20, bb_k: float=2.0, don_up: int=20) -> float:
    c = df["Close"].iloc[-1]
    atrv = base.atr(df).iloc[-1]
    stop_dist = atrv * float(atr_mult)
    if target_mode == "2xATR":
        target = c + 2.0*atrv
    elif target_mode == "Boll mid":
        mid = df["Close"].rolling(int(bb_p)).mean().iloc[-1]
        target = mid if not math.isnan(mid) else c + stop_dist
    else:  # Donchian high
        hh = df["High"].rolling(int(don_up)).max().iloc[-1]
        target = hh if not math.isnan(hh) else c + stop_dist
    rr = (target - c) / max(1e-9, stop_dist)
    return float(rr)

def _load_dir(dirpath: str, use_adj: bool, start_date: str|None) -> Tuple[List[str], Dict[str, pd.DataFrame]]:
    syms, data_map = [], {}
    if not dirpath or not os.path.isdir(dirpath):
        return syms, data_map
    for fn in os.listdir(dirpath):
        low = fn.lower()
        if not (low.endswith(".json") or low.endswith(".csv")):
            continue
        path = os.path.join(dirpath, fn)
        try:
            with open(path, "rb") as f:
                df = base.load_csv(f) if low.endswith(".csv") else base.load_json(f)
        except Exception as e:
            # skip unreadable files silently
            continue
        sym = fn.replace(".json","").replace(".csv","").upper()
        if low.endswith(".json"):
            try:
                with open(path, "r", encoding="utf-8") as ft:
                    obj = json.load(ft)
                    if isinstance(obj, dict) and isinstance(obj.get("ticker",None), str):
                        sym = obj["ticker"].upper()
            except Exception:
                pass
        if start_date:
            try:
                df = df.loc[pd.to_datetime(df.index) >= pd.to_datetime(start_date)]
            except Exception:
                pass
        df = base.maybe_adjust_with_adj(df.copy(), use_adj).sort_index()
        if len(df) >= 20:
            syms.append(sym); data_map[sym] = df
    return syms, data_map

@st.cache_data(show_spinner=False)
def cache_load_dir(dirpath: str, use_adj: bool, start_date: str|None):
    return _load_dir(dirpath, use_adj, start_date)



from concurrent.futures import ThreadPoolExecutor, as_completed

def load_dir_with_progress(dirpath: str, use_adj: bool, start_date: str|None, policy: str, fast_load: bool = True, max_workers: int = 4):
    syms, data_map = [], {}
    if not dirpath or not os.path.isdir(dirpath):
        return syms, data_map
    files = [fn for fn in os.listdir(dirpath) if fn.lower().endswith((".json",".csv"))]
    total = max(1, len(files))
    bar = st.sidebar.progress(0.0, text="טוען נתונים...")
    start_t = time.time()

    def worker(fn):
        path = os.path.join(dirpath, fn)
        try:
            df = _load_from_cache_or_source(path, use_adj, policy=policy)
            sym = fn.replace(".json","").replace(".csv","").upper()
            if fn.lower().endswith(".json"):
                try:
                    with open(path, "r", encoding="utf-8") as ft:
                        obj = json.load(ft)
                        if isinstance(obj, dict) and isinstance(obj.get("ticker",None), str):
                            sym = obj["ticker"].upper()
                except Exception:
                    pass
            if start_date:
                try:
                    df = df.loc[pd.to_datetime(df.index) >= pd.to_datetime(start_date)]
                except Exception:
                    pass
            df = df.sort_index()
            if len(df) >= 20:
                return sym, df
        except Exception:
            pass
        return None

    done = 0
    if fast_load:
        with ThreadPoolExecutor(max_workers=int(max_workers)) as ex:
            futures = [ex.submit(worker, fn) for fn in files]
            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    sym, df = res
                    syms.append(sym); data_map[sym] = df
                done += 1
                pct = done/total
                elapsed = time.time() - start_t
                rem = (elapsed/pct - elapsed) if pct>0 else 0.0
                try:
                    bar.progress(pct, text=f"טוען… {done}/{total} ({pct*100:.1f}%) | זמן נותר: {rem:,.0f}s")
                except Exception:
                    pass
    else:
        for i, fn in enumerate(files, start=1):
            res = worker(fn)
            if res:
                sym, df = res
                syms.append(sym); data_map[sym] = df
            pct = i/total
            elapsed = time.time() - start_t
            rem = (elapsed/pct - elapsed) if pct>0 else 0.0
            try:
                bar.progress(pct, text=f"טוען… {i}/{total} ({pct*100:.1f}%) | זמן נותר: {rem:,.0f}s")
            except Exception:
                pass

    try:
        bar.empty()
    except Exception:
        pass
    return syms, data_map

def load_uploaded_files(files, use_adj: bool, start_date: str|None):
    syms, data_map = [], {}
    for f in files:
        name = f.name
        low = name.lower()
        try:
            df = base.load_csv(f) if low.endswith(".csv") else base.load_json(f)
        except Exception as e:
            continue
        sym = name.replace(".json","").replace(".csv","").upper()
        if low.endswith(".json"):
            try:
                f.seek(0)
                obj = json.load(io.TextIOWrapper(f, encoding="utf-8", errors="ignore"))
                if isinstance(obj, dict) and isinstance(obj.get("ticker",None), str):
                    sym = obj["ticker"].upper()
            except Exception:
                pass
        if start_date:
            try:
                df = df.loc[pd.to_datetime(df.index) >= pd.to_datetime(start_date)]
            except Exception:
                pass
        df = base.maybe_adjust_with_adj(df.copy(), use_adj).sort_index()
        if len(df) >= 20:
            syms.append(sym); data_map[sym] = df
    return syms, data_map

def compute_universe_metrics(data_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for sym, df in data_map.items():
        if df.empty: continue
        close = float(df["Close"].iloc[-1])
        vol = float(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0.0
        adv = float((df["Close"]*df["Volume"]).rolling(20).mean().iloc[-1]) if "Volume" in df.columns else 0.0
        bars = int(len(df))
        rows.append(dict(Symbol=sym, Close=round(close,4), Volume=int(vol), ADV20=int(adv), Bars=bars))
    if not rows:
        return pd.DataFrame(columns=["Symbol","Close","Volume","ADV20","Bars"])
    df = pd.DataFrame(rows).sort_values("Symbol")
    return df

def ensure_presets():
    if "presets" not in st.session_state:
        st.session_state["presets"] = {}   # name -> {"strategy": str, "params": dict}

def apply_preset_to_session(preset: Dict[str, Any]):
    st.session_state["preset_strategy"] = preset.get("strategy")
    st.session_state["preset_params"] = preset.get("params", {})

def current_params(strategy: str, widgets_params: Dict[str, Any], common_params: Dict[str, Any]) -> Dict[str, Any]:
    params = {**widgets_params, **common_params}
    # if override from preset exists — merge (preset wins)
    if st.session_state.get("preset_params"):
        params = {**params, **st.session_state["preset_params"]}
        params["strategy_name"] = st.session_state.get("preset_strategy", params.get("strategy_name", strategy))
    return params

# ---------------------------
# Sidebar: Data source & filters
# ---------------------------
st.sidebar.header("נתונים (מקור)")
source_mode = st.sidebar.radio("בחר מקור", ["Folder", "File(s)"], horizontal=True, key="")
use_adj = st.sidebar.checkbox("Adjusted Close", value=True, key="k_checkbox_adjusted_close_2")
start_date = st.sidebar.text_input("סינון מתאריך (YYYY-MM-DD)", value="", key="k_text_input_yyyy_mm_dd_3")

if source_mode == "Folder":
    # ---- Data path input with default + persistence ----
    data_dir = st.sidebar.text_input("נתיב תיקייה (JSON/CSV)", value=r"C:\MyProjects\REPOs\backtrader\GUI\data backup", key="k_text_input_json_csv_4")
    if "default_data_dir" not in st.session_state:
        st.session_state["default_data_dir"] = data_dir
    else:
        if not data_dir:
            data_dir = st.session_state["default_data_dir"]
        else:
            st.session_state["default_data_dir"] = data_dir

    # ---- Cache policy ----
    policy = st.sidebar.radio("Cache Policy", options=["auto","parquet","source"], index=0, horizontal=True, help="auto=Cache if fresh, parquet=Require cache only, source=Ignore cache", key="cache_policy")
    # ---- Fast loading options ----
    fast_load = st.sidebar.checkbox("טעינה מהירה (Threaded)", value=True, help="טוען קבצים במקביל לשיפור מהירות.", key="k_checkbox_threaded_6")
    max_workers = st.sidebar.number_input("מס' עובדים (Threads)", 1, 64, max(2, os.cpu_count() or 4), 1, key="k_number_input_threads_7")

    # ---- Cache actions ----
    st.sidebar.markdown("---")
    colA, colB, colC = st.sidebar.columns([1,1,1])
    build_now = colA.button("בנה מטמון עכשיו", key="btn_1fd410f3_297")
    validate_now = colB.button("בדיקת מטמון", key="btn_814c4b73_298")
    clear_now = colC.button("נקה מטמון", key="btn_8aa14432_299")

    if build_now and data_dir and os.path.isdir(data_dir):
        files = [fn for fn in os.listdir(data_dir) if fn.lower().endswith((".json",".csv"))]
        total = max(1, len(files))
        bar = st.sidebar.progress(0.0, text="בונה מטמון...")
        start_t = time.time()
        built = 0
        for i, fn in enumerate(files, start=1):
            path = os.path.join(data_dir, fn)
            try:
                _ = _load_from_cache_or_source(path, use_adj=True, policy="auto")
                built += 1
            except Exception:
                pass
            pct = i/total
            elapsed = time.time() - start_t
            remaining = (elapsed/pct - elapsed) if pct>0 else 0.0
            bar.progress(pct, text=f"בונה מטמון… {i}/{total} ({pct*100:.1f}%) | זמן נותר: {remaining:,.0f}s")
        try:
            bar.empty()
        except Exception:
            pass
        st.sidebar.success(f"מטמון נבנה: {built}/{total} קבצים")

    if validate_now and data_dir and os.path.isdir(data_dir):
        cache_dir = _parquet_paths(data_dir)
        files = [fn for fn in os.listdir(data_dir) if fn.lower().endswith((".json",".csv"))]
        missing, stale = [], []
        for fn in files:
            src_path = os.path.join(data_dir, fn)
            sym = fn.replace(".json","").replace(".csv","").upper()
            pq_path = os.path.join(cache_dir, f"{sym}.parquet")
            if not os.path.exists(pq_path):
                missing.append(sym)
            else:
                if os.path.getmtime(pq_path) < os.path.getmtime(src_path):
                    stale.append(sym)
        st.sidebar.info(f"Parquet חסרים: {len(missing)} | מיושנים: {len(stale)}")
        if missing:
            st.sidebar.caption("חסרים: " + ", ".join(missing[:20]) + (" ..." if len(missing)>20 else ""))
        if stale:
            st.sidebar.caption("מיושנים: " + ", ".join(stale[:20]) + (" ..." if len(stale)>20 else ""))

    if clear_now and data_dir and os.path.isdir(data_dir):
        cache_dir = _parquet_paths(data_dir)
        if os.path.isdir(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                st.sidebar.success("המטמון נוקה.")
            except Exception as e:
                st.sidebar.error(f"שגיאה בניקוי: {e}")
        else:
            st.sidebar.info("לא קיים מטמון לניקוי.")

    if st.sidebar.button("טען תיקייה", key="k_button_56a18586_11"):
        syms, data_map = load_dir_with_progress(data_dir, use_adj, start_date if start_date else None, policy, fast_load=bool(fast_load), max_workers=int(max_workers))
        st.session_state["syms"] = syms
        st.session_state["data_map"] = data_map
else:
    if not data_dir:
        data_dir = st.session_state["default_data_dir"]
    else:
        st.session_state["default_data_dir"] = data_dir

# ---- Cache policy ----
policy = st.sidebar.radio("Cache Policy", options=["auto","parquet","source"], index=0, horizontal=True,
                          help="auto=Cache if fresh, parquet=Require cache only, source=Ignore cache", key="k_radio_cache_policy_12")

# ---- Cache actions ----
st.sidebar.markdown("---")
colA, colB, colC = st.sidebar.columns([1,1,1])
build_now = colA.button("בנה מטמון עכשיו", key="btn_1fd410f3_371")
validate_now = colB.button("בדיקת מטמון", key="btn_814c4b73_372")
clear_now = colC.button("נקה מטמון", key="btn_8aa14432_373")

if build_now and data_dir and os.path.isdir(data_dir):
    files = [fn for fn in os.listdir(data_dir) if fn.lower().endswith((".json",".csv"))]
    total = max(1, len(files))
    bar = st.sidebar.progress(0.0, text="בונה מטמון...")
    start_t = time.time()
    built = 0
    for i, fn in enumerate(files, start=1):
        path = os.path.join(data_dir, fn)
        try:
            _ = _load_from_cache_or_source(path, use_adj=True, policy="auto")
            built += 1
        except Exception:
            pass
        pct = i/total
        elapsed = time.time() - start_t
        remaining = (elapsed/pct - elapsed) if pct>0 else 0.0
        bar.progress(pct, text=f"בונה מטמון… {i}/{total} ({pct*100:.1f}%) | זמן נותר: {remaining:,.0f}s")
    try:
        bar.empty()
    except Exception:
        pass
    st.sidebar.success(f"מטמון נבנה: {built}/{total} קבצים")

if validate_now and data_dir and os.path.isdir(data_dir):
    cache_dir = _parquet_paths(data_dir)
    files = [fn for fn in os.listdir(data_dir) if fn.lower().endswith((".json",".csv"))]
    missing, stale = [], []
    for fn in files:
        src_path = os.path.join(data_dir, fn)
        sym = fn.replace(".json","").replace(".csv","").upper()
        pq_path = os.path.join(cache_dir, f"{sym}.parquet")
        if not os.path.exists(pq_path):
            missing.append(sym)
        else:
            if os.path.getmtime(pq_path) < os.path.getmtime(src_path):
                stale.append(sym)
    st.sidebar.info(f"Parquet חסרים: {len(missing)} | מיושנים: {len(stale)}")
    if missing:
        st.sidebar.caption("חסרים: " + ", ".join(missing[:20]) + (" ..." if len(missing)>20 else ""))
    if stale:
        st.sidebar.caption("מיושנים: " + ", ".join(stale[:20]) + (" ..." if len(stale)>20 else ""))

if clear_now and data_dir and os.path.isdir(data_dir):
    cache_dir = _parquet_paths(data_dir)
    if os.path.isdir(cache_dir):
        try:
            shutil.rmtree(cache_dir)
            st.sidebar.success("המטמון נוקה.")
        except Exception as e:
            st.sidebar.error(f"שגיאה בניקוי: {e}")
    else:
        st.sidebar.info("לא קיים מטמון לניקוי.")
    if st.sidebar.button("טען תיקייה", key="k_button_2117d587_16"):
        syms, data_map = cache_load_dir(data_dir, use_adj, start_date if start_date else None)
        st.session_state["syms"] = syms
        st.session_state["data_map"] = data_map
else:
    uploads = st.sidebar.file_uploader("בחר קבצים (JSON/CSV)", type=["json","csv"], accept_multiple_files=True, key="k_file_uploader_json_csv_17")
    if st.sidebar.button("טען קבצים", key="k_button_8a9c4752_18"):
        syms, data_map = load_uploaded_files(uploads or [], use_adj, start_date if start_date else None)
        st.session_state["syms"] = syms
        st.session_state["data_map"] = data_map

syms = st.session_state.get("syms", [])
data_map = st.session_state.get("data_map", {})

st.sidebar.markdown(f"**נטענו {len(syms)} סימבולים**" if syms else "_לא נטענו נתונים_")

st.sidebar.markdown("---")
st.sidebar.header("סינון יקום (אופציונלי)")
min_price = st.sidebar.number_input("מחיר מינימום", 0.0, 100000.0, 0.0, 0.5, key="k_number_input_d1f8ef45_19")
max_price = st.sidebar.number_input("מחיר מקסימום", 0.0, 100000.0, 0.0, 0.5, key="k_number_input_a824a3eb_20")
min_adv = st.sidebar.number_input("מינ' ADV20 ($)", 0.0, 1e9, 0.0, 1000.0, key="k_number_input_adv20_21")
min_bars = st.sidebar.number_input("מינ' מספר נרות", 0, 100000, 0, 10, key="k_number_input_5fafbe57_22")
top_by_adv = st.sidebar.number_input("Top-N לפי ADV20", 0, 100000, 0, 1, key="k_number_input_top_n_adv20_23")

df_uni = compute_universe_metrics(data_map) if syms else pd.DataFrame()
filtered_syms = syms
if not df_uni.empty:
    mask = np.ones(len(df_uni), dtype=bool)
    if min_price > 0: mask &= df_uni["Close"] >= min_price
    if max_price > 0: mask &= df_uni["Close"] <= max_price
    if min_adv > 0: mask &= df_uni["ADV20"] >= min_adv
    if min_bars > 0: mask &= df_uni["Bars"] >= min_bars
    df_f = df_uni.loc[mask].copy()
    if top_by_adv > 0:
        df_f = df_f.sort_values("ADV20", ascending=False).head(int(top_by_adv))
    filtered_syms = df_f["Symbol"].tolist()
    with st.sidebar.expander("תצוגת יקום מסונן", expanded=False):
        st.dataframe(df_f, use_container_width=True, height=240)

use_filtered = st.sidebar.checkbox("להשתמש ביקום המסונן", value=False, key="k_checkbox_dee41570_24")

# ---------------------------
# Sidebar: Strategy & risk
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.header("אסטרטגיה")
strategy = st.sidebar.selectbox("Strategy", ["SMA Cross","EMA Cross","Donchian Breakout","MACD Trend","RSI(2) @ Bollinger"], key="strategy_widget")

with st.sidebar.expander("פרמטרים לאסטרטגיה", expanded=True):
    if strategy in ("SMA Cross","EMA Cross"):
        fast = st.number_input("fast", 2, 400, 10, 1, key="fast")
        slow = st.number_input("slow", 2, 600, 20, 1, key="slow")
        strat_params = {"strategy_name": strategy, "fast": int(fast), "slow": int(slow)}
    elif strategy == "Donchian Breakout":
        upper = st.number_input("upper (N)", 5, 250, 20, 1, key="upper")
        lower = st.number_input("lower (N)", 5, 250, 10, 1, key="lower")
        strat_params = {"strategy_name": strategy, "upper": int(upper), "lower": int(lower)}
    elif strategy == "MACD Trend":
        ema_tr = st.number_input("EMA trend", 20, 600, 200, 5, key="ema_tr")
        fast = st.number_input("MACD fast", 2, 50, 12, 1, key="macd_fast")
        slow = st.number_input("MACD slow", 5, 100, 26, 1, key="macd_slow")
        signal = st.number_input("Signal", 2, 50, 9, 1, key="macd_signal")
        strat_params = {"strategy_name": strategy, "ema_trend": int(ema_tr), "fast": int(fast), "slow": int(slow), "signal": int(signal)}
    else:
        rsi_p = st.number_input("RSI period", 2, 50, 2, 1, key="rsi_p")
        rsi_buy = st.number_input("RSI buy ≤", 1, 50, 10, 1, key="rsi_buy")
        rsi_exit = st.number_input("RSI exit ≥", 10, 100, 60, 1, key="rsi_exit")
        bb_p = st.number_input("BB period", 5, 200, 20, 1, key="bb_p")
        bb_k = st.number_input("BB k", 1.0, 4.0, 2.0, 0.5, key="bb_k")
        strat_params = {"strategy_name": strategy, "rsi_p": int(rsi_p), "rsi_buy": int(rsi_buy), "rsi_exit": int(rsi_exit),
                        "bb_p": int(bb_p), "bb_k": float(bb_k)}

st.sidebar.header("סיכונים/פילטרים")
use_regime = st.sidebar.checkbox("Regime (SPY>EMA200)", value=False, key="use_regime")
weekly_filter = st.sidebar.checkbox("Weekly filter (W>EMA200)", value=False, key="weekly_filter")
stake = st.sidebar.number_input("Fixed stake", 1, 100000, 1, 1, key="stake")
use_atr_sizer = st.sidebar.checkbox("ATR risk % sizing", value=False, key="use_atr_sizer")
risk_pct = st.sidebar.number_input("Risk %", 0.001, 1.0, 0.01, 0.001, key="risk_pct")
atr_period = st.sidebar.number_input("ATR period", 2, 100, 14, 1, key="atr_period")
atr_mult = st.sidebar.number_input("ATR mult (stop)", 0.5, 10.0, 2.0, 0.5, key="atr_mult")

common_params = dict(
    use_regime=bool(use_regime),
    weekly_filter=bool(weekly_filter),
    stake=int(stake),
    use_atr_sizer=bool(use_atr_sizer),
    risk_pct=float(risk_pct),
    atr_period=int(atr_period),
    atr_mult=float(atr_mult),
    long_only=True,
    stop_loss_pct=0.0,
    take_profit_pct=0.0,

)
# Presets (save/load)
ensure_presets()
with st.sidebar.expander("Presets (שמירה/טעינה)", expanded=False):
    name = st.text_input("Preset name", "", key="k_text_input_preset_name_46")
    if st.button("Save preset (from current widgets)", key="k_button_save_preset_from_current_widgets_47") and name:
        st.session_state["presets"][name] = {"strategy": strategy, "params": {**strat_params, **common_params}}
        st.success(f"נשמר preset: {name}")
    if st.session_state["presets"]:
        sel = st.selectbox("Load preset", ["--"] + list(st.session_state["presets"].keys()), key="k_selectbox_load_preset_48")
        if sel != "--":
            apply_preset_to_session(st.session_state["presets"][sel])
            st.info(f"Preset נטען: {sel}. הוא יגבר על ערכי הטפסים עד כפתור Clear.")
    if st.session_state.get("preset_params"):
        if st.button("Clear preset override", key="k_button_clear_preset_override_49"):
            st.session_state.pop("preset_params", None); st.session_state.pop("preset_strategy", None); st.experimental_rerun()
    # Export/Import JSON
    if st.button("Download presets JSON", key="k_button_download_presets_json_50") and st.session_state["presets"]:
        st.download_button("לחץ להורדה", data=json.dumps(st.session_state["presets"], ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name="presets.json", mime="application/json", key="k_download_button_acb8ab03_51")
    uploaded_presets = st.file_uploader("Import presets JSON", type=["json"], key="k_file_uploader_import_presets_json_52")
    if uploaded_presets is not None:
        try:
            st.session_state["presets"] = json.load(uploaded_presets)
            st.success("Presets נטענו.")
        except Exception as e:
            st.error(f"שגיאה בטעינת presets: {e}")

# Final params (with preset override if exists)
params = current_params(strategy, strat_params, common_params)

st.title("QuantDesk — Web")

tab_scan, tab_bt, tab_opt, tab_ib, tab_auto = st.tabs(["🔍 Scan", "📈 Backtest", "🧪 Optimize", "🤖 IBKR Paper", "⚡ Auto-Discovery"])

# Target universe
universe = filtered_syms if (syms and use_filtered) else syms

# ---------------------------
# Tab: Scan
# ---------------------------
with tab_scan:
    left, right = st.columns([1,3])
    with left:
        patterns = st.multiselect("Candles", ["ENGULFING","DOJI","HAMMER","HARAMI","MORNINGSTAR","SHOOTINGSTAR","PIERCING"], default=[], key="k_multiselect_candles_53")
        lookback = st.number_input("Lookback (days)", 5, 200, 30, 1, key="k_number_input_lookback_days_54")
        rr_target = st.selectbox("RR target", ["2xATR","Boll mid","Donchian high"], key="k_selectbox_rr_target_55")
        rr_min = st.number_input("Min R:R", 0.0, 10.0, 0.0, 0.1, key="k_number_input_min_r_r_56")
        run_scan = st.button("Run SCAN", use_container_width=True, key="btn_run_scan_568")
    with right:
        if st.session_state.get("preset_params"):
            st.info("Preset override פעיל. הערכים שבאו מה-Preset גוברים על הטפסים לשלב הסריקה/בק-טסט.")
        st.caption(f"יקום לבדיקה: {len(universe)} סימבולים")
        if df_uni is not None and not df_uni.empty:
            st.caption("סינון לפי מחיר/ADV20/כמות נרות מתבצע בסיידבר (אופציונלי).")

    if run_scan:
        if not universe:
            st.warning("לא נטענו נתונים. טען תיקייה/קבצים תחילה.")
        else:
            rows = []
            bar = st.progress(0)
            for i, sym in enumerate(universe, start=1):
                df = data_map[sym]
                try:
                    sig_now, sig_age, price_at = base.scan_signal(df, params.get("strategy_name", strategy), params)
                except Exception as e:
                    rows.append(dict(Symbol=sym, Pass=False, SignalNOW="ERR", SignalAge=0, PriceAtSignal=np.nan, RR=np.nan, Patterns=str(e)))
                    bar.progress(i/len(universe)); continue
                pat_list = base.detect_patterns(df, int(lookback), [p.upper() for p in patterns]) if patterns else []
                rr = rr_from_atr(df, float(params.get("atr_mult", 2.0)), _standardize_rr_target(rr_target),
                                 bb_p=int(params.get("bb_p",20)), bb_k=float(params.get("bb_k",2.0)),
                                 don_up=int(params.get("upper",20)))
                passed = (rr >= rr_min) if rr_min > 0 else True
                rows.append(dict(Symbol=sym, Pass=bool(passed), SignalNOW=sig_now, SignalAge=int(sig_age),
                                 PriceAtSignal=round(price_at,4), RR=round(rr,2), Patterns=",".join(pat_list)))
                bar.progress(i/len(universe))
            df_scan = pd.DataFrame(rows).sort_values(by=["Pass","RR","Symbol"], ascending=[False, False, True])
            st.session_state["df_scan"] = df_scan
            st.dataframe(df_scan, use_container_width=True, height=520)
            st.download_button("Download CSV", df_scan.to_csv(index=False).encode("utf-8"), file_name="scan_results.csv", mime="text/csv", key="dl_download_csv_600")

# ---------------------------
# Tab: Backtest (table over universe + single chart)
# ---------------------------
with tab_bt:
    colA, colB = st.columns([1,3])
    with colA:
        start_cash = st.number_input("Start cash", 1000.0, 1e9, 10000.0, 100.0, format="%.2f", key="k_number_input_start_cash_59")
        commission = st.number_input("Commission (fraction)", 0.0, 0.01, 0.0005, 0.0001, format="%.6f", key="k_number_input_commission_fraction_60")
        slippage = st.number_input("Slippage (fraction)", 0.0, 0.02, 0.0005, 0.0001, format="%.6f", key="k_number_input_slippage_fraction_61")
        run_bt = st.button("Run BACKTEST (Universe)", use_container_width=True, key="btn_run_backtest_universe_611")
    with colB:
        st.caption(f"מריץ בק-טסט על {len(universe)} סימבולים עם אותם פרמטרים ומחזיר טבלת ביצועים")
        if st.session_state.get("preset_params"):
            st.info("Preset override פעיל גם כאן.")

    if run_bt:
        if not universe:
            st.warning("לא נטענו נתונים. טען תיקייה/קבצים תחילה.")
        else:
            rows = []
            bar = st.progress(0)
            for i, sym in enumerate(universe, start=1):
                df = data_map[sym]
                try:
                    _, summary = base.run_backtest(df, params, start_cash=float(start_cash),
                                                   commission=float(commission), slippage_perc=float(slippage), plot=False)
                    row = {"Symbol": sym,
                           "Final_Value": round(summary.get("Final_Value", 0.0), 2),
                           "Sharpe": summary.get("Sharpe", None),
                           "MaxDD_pct": round(summary.get("MaxDD_pct", 0.0), 2) if summary.get("MaxDD_pct") is not None else None,
                           "WinRate_pct": round(summary.get("WinRate_pct", 0.0), 2),
                           "Trades": int(summary.get("Trades", 0)),
                           "CAGR_pct": round(summary.get("CAGR_pct", 0.0), 2) if summary.get("CAGR_pct") is not None else None}
                    rows.append(row)
                except Exception as e:
                    rows.append({"Symbol": sym, "Final_Value": np.nan, "Sharpe": np.nan, "MaxDD_pct": np.nan,
                                 "WinRate_pct": np.nan, "Trades": 0, "CAGR_pct": np.nan})
                bar.progress(i/len(universe))
            df_bt = pd.DataFrame(rows)
            df_bt = df_bt.sort_values(by=["Sharpe","CAGR_pct","Final_Value"], ascending=[False, False, False])
            st.session_state["df_bt"] = df_bt
            st.dataframe(df_bt, use_container_width=True, height=520)
            st.download_button("Download CSV", df_bt.to_csv(index=False).encode("utf-8"), file_name="backtest_results.csv", mime="text/csv", key="dl_download_csv_644")
    st.markdown("---")
    sym_for_chart = st.selectbox("בחר סימבול לגרף", universe, index=0 if universe else None, key="k_selectbox_b8f58ced_64")
    if st.button("Plot selected", disabled=(not sym_for_chart), key="k_button_plot_selected_65"):
        df = data_map[sym_for_chart]
        figs, summary = base.run_backtest(df, params, start_cash=10000, commission=0.0005, slippage_perc=0.0005, plot=True)
        st.write(f"**{sym_for_chart} — Summary**")
        st.dataframe(pd.DataFrame([summary]), use_container_width=True)
        if figs:
            st.pyplot(figs[0], clear_figure=True)

# ---------------------------
# Optimization helpers
# ---------------------------
def param_grid_from_ranges(ranges: Dict[str, Any]) -> List[Dict[str, Any]]:
    grid = []
    keys, values = [], []
    for k, spec in ranges.items():
        keys.append(k)
        if isinstance(spec, list) and len(spec) == 3 and all(isinstance(x,(int,float)) for x in spec):
            start, stop, step = spec
            if step == 0: step = 1
            seq = []
            v = start
            while (step>0 and v <= stop) or (step<0 and v >= stop):
                seq.append(round(v,6))
                v += step
            values.append(seq)
        elif isinstance(spec, list):
            values.append(spec)
        else:
            values.append([spec])
    for combo in itertools.product(*values):
        grid.append({k: combo[i] for i,k in enumerate(keys)})
    return grid

def walk_forward_splits(n: int, folds: int, oos_frac: float):
    folds = max(1, int(folds))
    oos_frac = min(0.8, max(0.05, float(oos_frac)))
    test_len = max(20, int(n * oos_frac))
    anchor = n - test_len
    if anchor <= 40:
        return [(max(0, n - test_len), n)]
    step = max(20, int(anchor/max(1,folds)))
    splits = []
    for start in range(0, anchor, step):
        te_s = min(anchor, start + step)
        te_e = min(n, te_s + test_len)
        if te_e - te_s >= 20:
            splits.append((te_s, te_e))
    if not splits:
        splits = [(anchor, n)]
    return splits

def objective_score(summary: Dict[str, Any], objective: str) -> float:
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

# ---------------------------
# Tab: Optimize
# ---------------------------
with tab_opt:
    st.caption("מנוע אופטימיזציה (Grid + Walk-Forward) — זהירות: יכול לקחת זמן")
    c1, c2 = st.columns([2,2])
    with c1:
        ranges_json = st.text_area("Parameter Ranges (JSON)",
                                   value='{\n  "fast": [8, 20, 4],\n  "slow": [20, 40, 4],\n  "ema_trend": [100, 200, 50]\n}',
                                   height=160, key="ranges_json")
        uni_limit = st.number_input("Universe limit (0=all)", 0, 10000, min(len(universe), 50) if universe else 50, 1, key="k_number_input_universe_limit_0_all_67")
        folds = st.number_input("Folds", 1, 10, 3, 1, key="k_number_input_folds_68")
        oos_pct = st.number_input("OOS %", 5, 80, 20, 1, key="k_number_input_oos_69")
        min_trades = st.number_input("Min trades per test", 0, 1000, 5, 1, key="k_number_input_min_trades_per_test_70")
    with c2:
        objective = st.selectbox("Objective", ["Sharpe","CAGR","Return/DD","WinRate","Trades"], key="k_selectbox_objective_71")
        max_results = st.number_input("Show top", 1, 200, 50, 1, key="k_number_input_show_top_72")
        run_opt = st.button("Run OPTIMIZE", type="primary", use_container_width=True, key="btn_run_optimize_728")

    if run_opt:
        if not universe:
            st.warning("לא נטענו נתונים. טען תיקייה/קבצים תחילה.")
        else:
            try:
                ranges = json.loads(ranges_json)
            except Exception as e:
                st.error(f"JSON לא חוקי: {e}")
                st.stop()
            grid = param_grid_from_ranges(ranges)
            if not grid:
                st.error("טווחי פרמטרים ריקים")
                st.stop()
            symbols = universe[:max(1, int(uni_limit))] if int(uni_limit) > 0 else universe
            n_tests = 0
            for sym in symbols:
                n = len(data_map[sym])
                n_tests += len(walk_forward_splits(n, int(folds), float(oos_pct)/100.0)) * len(grid)
            if n_tests > 3000:
                st.warning(f"מספר בדיקות גדול מאוד ({n_tests}). שקול לצמצם טווחים/יקום/קיפולים.")

            results = []
            bar = st.progress(0)
            done = 0
            for params_local in grid:
                merged = {**{k:v for k,v in params.items() if k not in params_local}, **params_local,
                          "strategy_name": params.get("strategy_name", strategy)}
                scores = []
                agg = {"Sharpe":0.0,"CAGR_pct":0.0,"MaxDD_pct":0.0,"WinRate_pct":0.0,"Trades":0}
                cnt = 0
                for sym in symbols:
                    df = data_map[sym]
                    splits = walk_forward_splits(len(df), int(folds), float(oos_pct)/100.0)
                    for (te_s, te_e) in splits:
                        sub = df.iloc[te_s:te_e].copy()
                        _, summ = base.run_backtest(sub, merged, start_cash=10000.0, commission=0.0005, slippage_perc=0.0005, plot=False)
                        if (summ.get("Trades") or 0) < int(min_trades):
                            done += 1; bar.progress(min(1.0, done/max(1,n_tests))); continue
                        scores.append(objective_score(summ, objective))
                        for k in agg: agg[k] += float(summ.get(k, 0.0) or 0.0)
                        cnt += 1; done += 1; bar.progress(min(1.0, done/max(1,n_tests)))
                if scores:
                    for k in agg: agg[k] = agg[k]/max(1,cnt)
                    results.append({
                        "Params": json.dumps(params_local),
                        "Score": round(float(np.mean(scores)), 4),
                        "Sharpe": round(agg["Sharpe"], 4),
                        "CAGR_pct": round(agg["CAGR_pct"], 4),
                        "MaxDD_pct": round(agg["MaxDD_pct"], 2),
                        "WinRate_pct": round(agg["WinRate_pct"], 2),
                        "Trades": int(agg["Trades"]),
                        "Universe": len(symbols),
                        "Folds": len(walk_forward_splits(1000, int(folds), float(oos_pct)/100.0))
                    })
            if results:
                df_opt = pd.DataFrame(results).sort_values("Score", ascending=False).head(int(max_results))
                st.session_state["df_opt"] = df_opt
                st.dataframe(df_opt, use_container_width=True, height=500)
                st.download_button("Download CSV", df_opt.to_csv(index=False).encode("utf-8"), file_name="opt_results.csv", mime="text/csv", key="dl_download_csv_788")

                st.markdown("---")
                st.subheader("Apply / Export Best")
                idx = st.number_input("בחר דירוג (Rank) להחלה/ייצוא", 1, int(len(df_opt)), 1, 1, key="k_number_input_rank_75")
                if 1 <= idx <= len(df_opt):
                    row = df_opt.iloc[idx-1]
                    chosen_params = json.loads(row["Params"])
                    # Buttons
                    c1, c2, c3 = st.columns(3)
                    if c1.button("Apply to Scan/Backtest", key="k_button_apply_to_scan_backtest_76"):
                        st.session_state["preset_strategy"] = strategy
                        st.session_state["preset_params"] = {**params, **chosen_params, "strategy_name": strategy}
                        st.success("הוגדר Preset זמני לפרמטרים הטובים. עבור לסריקה/בק-טסט והרץ.")
                    if c2.button("Save as Preset", key="k_button_save_as_preset_77"):
                        ensure_presets()
                        pname = f"{strategy}_best_{int(time.time())}"
                        st.session_state["presets"][pname] = {"strategy": strategy, "params": {**params, **chosen_params, "strategy_name": strategy}}
                        st.success(f"נשמר כ־Preset: {pname}")
                    if c3.button("Export Best Preset JSON", key="k_button_export_best_preset_json_78"):
                        best_payload = {"strategy": strategy, "params": {**params, **chosen_params, "strategy_name": strategy}}
                        st.download_button("הורד JSON", data=json.dumps(best_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                                           file_name="best_preset.json", mime="application/json", key="k_download_button_json_79")
            else:
                st.info("לא נמצאו תוצאות (יתכן ש-min_trades גבוה מדי).")

# ---------------------------
# Tab: IBKR Paper (preview + send)
# ---------------------------
with tab_ib:
    st.caption("הרצה על חשבון Paper של IBKR. נדרש TWS/IB Gateway פתוח עם API מאופשר.")
    if not IB_AVAILABLE:
        st.warning("הספרייה ib-insync לא מותקנת. כדי להפעיל: `pip install ib-insync`.")
    host = st.text_input("Host", value="127.0.0.1", key="k_text_input_host_80")
    port = st.number_input("Port", 1, 65535, 7497, 1, key="k_number_input_port_81")  # TWS paper default 7497, Gateway 4002
    clientId = st.number_input("ClientId", 0, 9999, 111, 1, key="k_number_input_clientid_82")
    c1, c2 = st.columns(2)
    with c1:
        live_universe_mode = st.radio("Symbols", ["Pass from last Scan", "Manual"], horizontal=True, key="k_radio_symbols_83")
        if live_universe_mode == "Manual":
            manual_syms = st.text_input("Symbols (CSV)", value="SPY,AAPL,MSFT", key="k_text_input_symbols_csv_84")
    with c2:
        sizing_mode = st.selectbox("Sizing", ["Fixed $ per symbol","ATR risk %"], index=0, key="k_selectbox_sizing_85")
        if sizing_mode == "Fixed $ per symbol":
            alloc = st.number_input("$ per symbol", 100.0, 1e9, 2000.0, 100.0, format="%.2f", key="k_number_input_per_symbol_86")
        else:
            acct_equity = st.number_input("Account equity (est.)", 1000.0, 1e9, 100000.0, 1000.0, format="%.2f", key="k_number_input_account_equity_est_87")
            risk_pct_live = st.number_input("Risk % per trade", 0.001, 5.0, 0.5, 0.1, key="k_number_input_risk_per_trade_88")

    # Build live list
    live_list = []
    if live_universe_mode == "Pass from last Scan":
        df_scan = st.session_state.get("df_scan", pd.DataFrame())
        live_list = df_scan.loc[df_scan["Pass"]==True, "Symbol"].tolist() if not df_scan.empty else []
    else:
        live_list = [s.strip().upper() for s in (manual_syms or "").split(",") if s.strip()]

    st.write(f"נבחרו {len(live_list)} סימבולים")

    if st.button("Preview Orders", key="k_button_preview_orders_89"):
        if not live_list:
            st.warning("אין סימבולים.")
        else:
            orders = []
            for sym in live_list:
                df = data_map.get(sym)
                if df is None or df.empty: continue
                price = float(df["Close"].iloc[-1])
                if sizing_mode == "Fixed $ per symbol":
                    qty = max(1, int(float(alloc) / max(0.01, price)))
                else:
                    atrv = float(base.atr(df).iloc[-1])
                    stop_dist = max(0.01, atrv * float(params.get("atr_mult", 2.0)))
                    risk_amt = float(acct_equity) * (float(risk_pct_live)/100.0)
                    qty = max(1, int(risk_amt / stop_dist))
                orders.append({"Symbol": sym, "Side": "BUY", "Qty": qty, "LastPrice": round(price, 4)})
            df_prev = pd.DataFrame(orders)
            st.session_state["live_preview"] = df_prev
            st.dataframe(df_prev, use_container_width=True)

    if st.button("Send Orders (Paper)", key="k_button_send_orders_paper_90"):
        df_prev = st.session_state.get("live_preview", pd.DataFrame())
        if df_prev.empty:
            st.warning("אין פקודות בתצוגה מוקדמת. לחץ Preview קודם.")
        elif not IB_AVAILABLE:
            st.error("ib-insync לא מותקן.")
        else:
            try:
                ib = IB()
                ib.connect(host, int(port), clientId=int(clientId), timeout=3)
                for _, row in df_prev.iterrows():
                    contract = Stock(row["Symbol"], 'SMART', 'USD')
                    order = MarketOrder('BUY', int(row["Qty"]))
                    ib.placeOrder(contract, order)
                st.success(f"נשלחו {len(df_prev)} פקודות ל־Paper.")
                ib.disconnect()
            except Exception as e:
                st.error(f"שגיאה בשליחה: {e}")


# ---------------------------
# Tab: Auto-Discovery (Multi-Strategy Grid Search v2)
# ---------------------------
with tab_auto:
    st.subheader("⚡ Auto-Discovery — Multi-Strategy Grid (Tech + Filters)")
    if not syms:
        st.warning("לא נטענו נתונים. טען תיקייה/קבצים תחילה (סיידבר).")
    else:
        # --- Selection controls ---
        all_syms = filtered_syms if (syms and use_filtered) else syms
        sel_syms = st.multiselect("בחר סימבולים", options=all_syms, default=all_syms[:1], key="k_multiselect_5dd5a9b4_91")
        strat_options = ["SMA Cross","EMA Cross","MACD","RSI","Stochastic",
                         "Bollinger Breakout","Bollinger MeanRevert","Donchian Breakout"]
        sel_strats = st.multiselect("בחר אסטרטגיות", options=strat_options, default=strat_options, key="k_multiselect_2c4daf35_92")
        bt_start = st.text_input("תאריך התחלה (YYYY-MM-DD)", value="2024-01-01", key="auto_start")
        bt_end = st.text_input("תאריך סיום (YYYY-MM-DD)", value="", key="auto_end")
        min_trades = st.number_input("סף מינימום עסקאות", 0, 1000, 5, 1, key="k_number_input_7d9689f7_95")

        # Extra-data simple filters (applied on bars)
        c1, c2, c3 = st.columns(3)
        with c1:
            min_price_bar = st.number_input("מחיר מינ' (Close)", 0.0, 1e9, 0.0, 0.1, key="k_number_input_close_96")
        with c2:
            min_vol_bar = st.number_input("נפח מינ' (Volume)", 0.0, 1e12, 0.0, 1000.0, key="k_number_input_volume_97")
        with c3:
            apply_bar_filters = st.checkbox("יישם סינון ברים לפני חישוב", value=False, key="k_checkbox_bd1bd077_98")

        # Manual grid override
        with st.expander("עריכת טווחי Grid ידנית (אופציונלי) — JSON"):
            st.caption("השאר ריק כדי להשתמש בברירות מחדל. דוגמה: {\"MACD\": {\"fast\":[8,12], \"slow\":[26], \"signal\":[9]}}")
            grid_override_json = st.text_area("Grid JSON", value="", height=120, key="k_text_area_grid_json_99")

        run_auto = st.button("הרץ Auto-Discovery", type="primary", key="btn_auto_discovery_920")

        # --- Strategy signal builders ---
        import numpy as np
        import pandas as pd

        def _returns_from_signal(px: pd.Series, signal: pd.Series) -> pd.Series:
            rets = px.pct_change().fillna(0.0) * signal.shift(1).fillna(0.0)
            return rets

        def _metrics_from_rets(rets: pd.Series):
            if len(rets) == 0:
                return dict(CAGR=0.0, Sharpe=0.0, WinRate=0.0, MaxDD=0.0, Trades=0)
            eq = (1.0 + rets).cumprod()
            peak = eq.cummax()
            dd = float((eq/peak - 1.0).min()) if len(eq) else 0.0
            years = max(1e-9, len(rets)/252.0)
            cagr = float(eq.iloc[-1]**(1/years) - 1.0)
            sharpe = float(rets.mean()/rets.std()*np.sqrt(252)) if rets.std()!=0 else 0.0
            trades = int((rets!=0).sum())
            in_pos = rets[rets!=0]
            win_rate = float((in_pos > 0).mean()) if len(in_pos) else 0.0
            return dict(CAGR=cagr, Sharpe=sharpe, WinRate=win_rate, MaxDD=dd, Trades=trades)

        def _sma_cross(px: pd.Series, fast: int, slow: int) -> pd.Series:
            f = px.rolling(fast, min_periods=fast).mean()
            s = px.rolling(slow, min_periods=slow).mean()
            return (f > s).astype(int)

        def _ema_cross(px: pd.Series, fast: int, slow: int) -> pd.Series:
            f = px.ewm(span=fast, adjust=False, min_periods=fast).mean()
            s = px.ewm(span=slow, adjust=False, min_periods=slow).mean()
            return (f > s).astype(int)

        def _macd(px: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
            ema_fast = px.ewm(span=fast, adjust=False, min_periods=fast).mean()
            ema_slow = px.ewm(span=slow, adjust=False, min_periods=slow).mean()
            macd = ema_fast - ema_slow
            sig = macd.ewm(span=signal, adjust=False, min_periods=signal).mean()
            return (macd > sig).astype(int)

        def _rsi(series: pd.Series, period: int) -> pd.Series:
            delta = series.diff()
            up = delta.clip(lower=0)
            down = -delta.clip(upper=0)
            ma_up = up.ewm(alpha=1/period, adjust=False).mean()
            ma_down = down.ewm(alpha=1/period, adjust=False).mean()
            rs = ma_up / ma_down.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            return rsi

        def _rsi_rule(px: pd.Series, period: int, buy_thr: float, sell_thr: float) -> pd.Series:
            r = _rsi(px, period)
            long = pd.Series(0, index=px.index, dtype=int)
            state = 0
            for i in range(len(r)):
                val = r.iloc[i]
                if not np.isfinite(val):
                    long.iloc[i] = state; continue
                if state == 0 and val <= buy_thr:
                    state = 1
                elif state == 1 and val >= sell_thr:
                    state = 0
                long.iloc[i] = state
            return long

        def _stoch(px: pd.Series, high: pd.Series, low: pd.Series, k: int, d: int, ob: float, os: float) -> pd.Series:
            ll = low.rolling(k, min_periods=k).min()
            hh = high.rolling(k, min_periods=k).max()
            pctK = (px - ll) / (hh - ll).replace(0, np.nan) * 100.0
            pctD = pctK.rolling(d, min_periods=d).mean()
            long = pd.Series(0, index=px.index, dtype=int)
            state = 0
            for i in range(len(pctK)):
                k_i = pctK.iloc[i]; d_i = pctD.iloc[i]
                if not (np.isfinite(k_i) and np.isfinite(d_i)):
                    long.iloc[i] = state; continue
                if state == 0 and k_i > d_i and k_i < os:
                    state = 1
                elif state == 1 and k_i < d_i and k_i > ob:
                    state = 0
                long.iloc[i] = state
            return long

        def _bollinger(px: pd.Series, p: int, k: float):
            ma = px.rolling(p, min_periods=p).mean()
            sd = px.rolling(p, min_periods=p).std(ddof=0)
            upper = ma + k*sd
            lower = ma - k*sd
            return ma, upper, lower

        def _bb_breakout(px: pd.Series, p: int, k: float) -> pd.Series:
            ma, upper, lower = _bollinger(px, p, k)
            return (px > upper).astype(int)  # breakout מעל Upper

        def _bb_meanrevert(px: pd.Series, p: int, k: float) -> pd.Series:
            ma, upper, lower = _bollinger(px, p, k)
            long = pd.Series(0, index=px.index, dtype=int)
            state = 0
            for i in range(len(px)):
                u = upper.iloc[i]; l = lower.iloc[i]; m = ma.iloc[i]; price = px.iloc[i]
                if not (np.isfinite(u) and np.isfinite(l) and np.isfinite(m) and np.isfinite(price)):
                    long.iloc[i] = state; continue
                if state == 0 and price < l:   # כניסה מתחת ל-Lower
                    state = 1
                elif state == 1 and price >= m:  # יציאה במעבר ל-MA
                    state = 0
                long.iloc[i] = state
            return long

        def _donchian(px: pd.Series, high: pd.Series, low: pd.Series, n: int) -> pd.Series:
            hh = high.rolling(n, min_periods=n).max()
            ll = low.rolling(n, min_periods=n).min()
            return (px > hh.shift(1)).astype(int)  # פריצה מעל שיא קודם

        # --- Default grids ---
        grid_defs = {
            "SMA Cross": {"fast": [5,10,15,20,25,30], "slow": [40,60,80,100,120,140,160,180,200]},
            "EMA Cross": {"fast": [5,10,15,20,25,30], "slow": [40,60,80,100,120,140,160,180,200]},
            "MACD": {"fast": [8,12,15], "slow": [20,26,35,40], "signal": [5,9,10]},
            "RSI": {"period": [7,10,14,21], "buy_thr": [20,30], "sell_thr": [60,70]},
            "Stochastic": {"k": [5,9,14], "d": [3], "ob": [80], "os": [20,30]},
            "Bollinger Breakout": {"p": [20], "k": [2.0, 2.5, 3.0]},
            "Bollinger MeanRevert": {"p": [20], "k": [2.0, 2.5, 3.0]},
            "Donchian Breakout": {"n": [20, 55]},
        }

        # Apply manual override if provided
        if grid_override_json.strip():
            try:
                overrides = json.loads(grid_override_json)
                for k, v in overrides.items():
                    if k in grid_defs and isinstance(v, dict):
                        grid_defs[k].update(v)
                st.success("עודכנו טווחי Grid לפי ה-JSON.")
            except Exception as e:
                st.error(f"Grid JSON לא תקין: {e}")

        run_click = run_auto
        if run_click:
            if not sel_syms:
                st.warning("בחר לפחות סימבול אחד.")
            elif not sel_strats:
                st.warning("בחר לפחות אסטרטגיה אחת.")
            else:
                rows = []
                total = 0
                for sname in sel_strats:
                    gd = grid_defs[sname]
                    count = 1
                    for v in gd.values():
                        count *= len(v)
                    total += count * len(sel_syms)
                bar = st.progress(0)
                done = 0

                import itertools
                for sym in sel_syms:
                    df = data_map.get(sym)
                    if df is None or df.empty:
                        continue
                    # Date filter
                    if bt_start:
                        df = df.loc[pd.to_datetime(df.index) >= pd.to_datetime(bt_start)]
                    if bt_end:
                        df = df.loc[pd.to_datetime(df.index) <= pd.to_datetime(bt_end)]
                    if df.empty:
                        continue

                    # Apply bar-level filters if asked and columns exist
                    if apply_bar_filters:
                        if min_price_bar > 0 and "Close" in df.columns:
                            df = df[df["Close"].astype(float) >= float(min_price_bar)]
                        if min_vol_bar > 0 and "Volume" in df.columns:
                            df = df[df["Volume"].astype(float) >= float(min_vol_bar)]
                        if df.empty:
                            done += 1; bar.progress(min(1.0, done/max(1,total))); continue

                    px = df["Close"].astype(float)
                    hi = df["High"] if "High" in df.columns else px
                    lo = df["Low"]  if "Low"  in df.columns else px

                    for strat in sel_strats:
                        gd = grid_defs[strat]
                        keys = list(gd.keys())
                        values = [gd[k] for k in keys]
                        for combo in itertools.product(*values):
                            params_local = {keys[i]: combo[i] for i in range(len(keys))}
                            try:
                                if strat == "SMA Cross":
                                    if params_local["fast"] >= params_local["slow"]:
                                        done += 1; bar.progress(min(1.0, done/max(1,total))); continue
                                    sig = _sma_cross(px, params_local["fast"], params_local["slow"])
                                elif strat == "EMA Cross":
                                    if params_local["fast"] >= params_local["slow"]:
                                        done += 1; bar.progress(min(1.0, done/max(1,total))); continue
                                    sig = _ema_cross(px, params_local["fast"], params_local["slow"])
                                elif strat == "MACD":
                                    if params_local["fast"] >= params_local["slow"]:
                                        done += 1; bar.progress(min(1.0, done/max(1,total))); continue
                                    sig = _macd(px, params_local["fast"], params_local["slow"], params_local["signal"])
                                elif strat == "RSI":
                                    sig = _rsi_rule(px, params_local["period"], params_local["buy_thr"], params_local["sell_thr"])
                                elif strat == "Stochastic":
                                    sig = _stoch(px, hi, lo, params_local["k"], params_local["d"], params_local["ob"], params_local["os"])
                                elif strat == "Bollinger Breakout":
                                    sig = _bb_breakout(px, params_local["p"], params_local["k"])
                                elif strat == "Bollinger MeanRevert":
                                    sig = _bb_meanrevert(px, params_local["p"], params_local["k"])
                                else:  # Donchian Breakout
                                    sig = _donchian(px, hi, lo, params_local["n"])

                                rets = _returns_from_signal(px, sig)
                                mets = _metrics_from_rets(rets)
                                if mets["Trades"] >= int(min_trades):
                                    rows.append({
                                        "Symbol": sym,
                                        "Strategy": strat,
                                        "Params": json.dumps(params_local),
                                        **mets
                                    })
                            except Exception:
                                pass
                            finally:
                                done += 1
                                bar.progress(min(1.0, done/max(1,total)))

                res = pd.DataFrame(rows)
                if res.empty:
                    st.warning("אין תוצאות לאחר הסינון (נסה להוריד Min Trades/לבחור טווחים אחרים).")
                else:
                    sort_metric = st.selectbox("מיין לפי", ["Sharpe","CAGR","WinRate","MaxDD","Trades"], index=0, key="k_selectbox_7b96e26c_101")
                    ascending = st.checkbox("סדר עולה?", value=False if sort_metric!="MaxDD" else True, key="k_checkbox_a6e2fdf4_102")
                    res_sorted = res.sort_values(sort_metric, ascending=ascending).reset_index(drop=True)
                    st.dataframe(res_sorted, use_container_width=True, height=520)
                    st.download_button("הורד תוצאות CSV", res_sorted.to_csv(index=False).encode("utf-8"),
                                       file_name="auto_discovery_multi_strategy.csv", mime="text/csv", key="k_download_button_csv_103")

                    st.markdown("---")
                    st.subheader("בחר את הקומבינציה הכי טובה (לסימבול יחיד)")
                    if len(sel_syms) == 1 and not res_sorted.empty:
                        best_by = st.selectbox("בחר מטריקה לבחירה אוטומטית", ["Sharpe","CAGR"], index=0, key="k_selectbox_bf9bf98c_104")
                        top_row = res_sorted.iloc[0]
                        st.write(f"**Top by {best_by}:** {top_row['Strategy']} {top_row['Params']} — Sharpe={top_row['Sharpe']:.2f}, CAGR={top_row['CAGR']:.2%}, Trades={top_row['Trades']}")
                        if st.button("החל על Scan/Backtest כ-Preset", key="k_button_scan_backtest_preset_105"):
                            try:
                                chosen_params = json.loads(top_row["Params"])
                            except Exception:
                                chosen_params = {}
                            st.session_state["preset_strategy"] = top_row["Strategy"]
                            st.session_state["preset_params"] = {**chosen_params, "strategy_name": top_row["Strategy"]}
                            st.success("הוגדר Preset עם הקומבינציה שנבחרה – עבור ל-Scan/Backtest והרץ.")
                    else:
                        st.caption("טיפ: כשבודקים כמה סימבולים — דרג לפי Sharpe וסנן MaxDD/Trades כדי להוציא רעש.")