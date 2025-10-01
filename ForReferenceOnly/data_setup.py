# data_setup.py
# Utilities for building a fast catalog from a directory of per-ticker JSON files,
# converting them to Parquet, and exposing on-demand loaders + Streamlit UI.
#
# Designed to be pasted or imported in your Streamlit app (app.py).
# Dependencies: pandas, pyarrow (for parquet), (optional) polars
#
# How to use in app.py (minimal):
#   import data_setup as ds
#   ds.render_data_setup_ui()
#   # Later:
#   catalog = st.session_state.get("catalog_df")
#   data = ds.load_tickers_on_demand(["AAPL","MSFT"], date_from="2024-01-01")
#
# NOTE:
# - This module is schema-flexible and will try common JSON layouts (records list, {"data": [...]}, NDJSON lines).
# - It preserves *all* fields to Parquet to keep your rich dataset intact.
# - For speed in scans/backtests, request a subset of columns via `columns=` and a date filter.

from __future__ import annotations

import os
import io
import json
import math
import time
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Iterable, Any
from datetime import datetime

import pandas as pd

# Try to use Polars if available for faster Parquet IO (optional)
try:
    import polars as pl
    _HAS_POLARS = True
except Exception:
    _HAS_POLARS = False

# ---------------- Configuration ----------------

# Heuristics for detecting date and key financial fields in your JSONs
DATE_CANDIDATES = ["date", "Date", "timestamp", "time", "Time", "datetime", "Datetime"]
TICKER_FROM_FILENAME = True  # infer ticker from filename when a field is missing
TICKER_FIELD_CANDIDATES = ["ticker", "symbol", "Ticker", "Symbol"]

# Where to place derived artifacts relative to your data_dir
PARQUET_SUBDIR = "_parquet"
CATALOG_SUBDIR = "_catalog"
CATALOG_BASENAME = "catalog"

# Default columns many quant workflows need (optional; you can request any subset later)
DEFAULT_NUMERIC_COLS = ["open", "high", "low", "close", "volume", "Open", "High", "Low", "Close", "Volume"]

# Concurrency
def _recommended_workers() -> int:
    try:
        import multiprocessing as mp
        cpu = os.cpu_count() or 4
    except Exception:
        cpu = 4
    return max(4, min(8, cpu * 4))

# ---------------- Helpers ----------------

def _list_json_files(root: str) -> List[str]:
    out = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".json") or f.lower().endswith(".ndjson"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)

def _infer_ticker_from_filename(path: str) -> str:
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return name.upper().replace(" ", "_")

def _safe_stat(path: str) -> Tuple[int, float]:
    try:
        st = os.stat(path)
        return st.st_size, st.st_mtime
    except Exception:
        return -1, 0.0

def _json_to_dataframe(path: str) -> pd.DataFrame:
    """
    Robust reader that tries multiple JSON styles:
      1) A list[dict] of rows
      2) {"data": list[dict]} wrapper
      3) NDJSON (one json object per line)
      4) A dict with nested structures -> json_normalize
    Returns an empty DF if nothing works.
    """
    try:
        # First try normal JSON
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            if len(raw) == 0:
                return pd.DataFrame()
            if isinstance(raw[0], dict):
                return pd.DataFrame(raw)
            # List of scalars -> wrap
            return pd.DataFrame({ "value": raw })
        if isinstance(raw, dict):
            # Common wrapper key
            if "data" in raw and isinstance(raw["data"], list):
                return pd.DataFrame(raw["data"])
            # Flatten dict
            return pd.json_normalize(raw)
    except json.JSONDecodeError:
        # Maybe NDJSON
        try:
            lines = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line:
                        continue
                    lines.append(json.loads(line))
            if lines:
                return pd.DataFrame(lines)
        except Exception:
            pass
    except Exception:
        pass
    # Last resort: empty
    return pd.DataFrame()

def _pick_first_existing(cols: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    s = set(cols)
    for c in candidates:
        if c in s:
            return c
    return None

def _coerce_datetime(df: pd.DataFrame, date_col: Optional[str]) -> Tuple[pd.DataFrame, Optional[str]]:
    if date_col is None:
        # Try to detect
        date_col = _pick_first_existing(df.columns, DATE_CANDIDATES)
    if date_col is None:
        return df, None
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
    except Exception:
        # Try numeric epoch seconds
        try:
            df[date_col] = pd.to_datetime(df[date_col].astype("float64"), unit="s", errors="coerce", utc=True)
        except Exception:
            return df, None
    return df, date_col

def _ensure_sorted(df: pd.DataFrame, date_col: Optional[str]) -> pd.DataFrame:
    if date_col and date_col in df.columns:
        try:
            return df.sort_values(by=date_col, kind="mergesort", na_position="last").reset_index(drop=True)
        except Exception:
            return df
    return df

def _detect_ticker(df: pd.DataFrame, path: str) -> Optional[str]:
    col = _pick_first_existing(df.columns, TICKER_FIELD_CANDIDATES)
    if col and df[col].notna().any():
        v = str(df[col].dropna().iloc[0]).strip().upper()
        if v:
            return v
    if TICKER_FROM_FILENAME:
        return _infer_ticker_from_filename(path)
    return None

def _parquet_path_for(data_dir: str, ticker: str) -> str:
    return os.path.join(data_dir, PARQUET_SUBDIR, f"{ticker}.parquet")

def _catalog_paths_for(data_dir: str) -> Tuple[str, str]:
    cat_dir = os.path.join(data_dir, CATALOG_SUBDIR)
    os.makedirs(cat_dir, exist_ok=True)
    return os.path.join(cat_dir, f"{CATALOG_BASENAME}.parquet"), os.path.join(cat_dir, f"{CATALOG_BASENAME}.json")

def _write_parquet(df: pd.DataFrame, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Prefer polars if available for speed
    if _HAS_POLARS:
        pl.from_pandas(df).write_parquet(out_path)
    else:
        df.to_parquet(out_path, index=False)

def _read_parquet(in_path: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
    if _HAS_POLARS:
        if columns is None:
            return pl.read_parquet(in_path).to_pandas()
        return pl.read_parquet(in_path, columns=columns).to_pandas()
    return pd.read_parquet(in_path, columns=columns)

@dataclass
class CatalogEntry:
    ticker: str
    src_path: str
    parquet_path: str
    n_rows: int
    n_cols: int
    min_date: Optional[str]
    max_date: Optional[str]
    date_col: Optional[str]
    filesize_bytes: int
    last_modified: float
    fields: List[str]

def _summarize_df(df: pd.DataFrame, date_col: Optional[str]) -> Tuple[int, int, Optional[str], Optional[str]]:
    n_rows = int(df.shape[0])
    n_cols = int(df.shape[1])
    min_d = max_d = None
    if date_col and date_col in df.columns and n_rows > 0:
        s = df[date_col].dropna()
        if not s.empty:
            try:
                min_d = s.min().strftime("%Y-%m-%d")
                max_d = s.max().strftime("%Y-%m-%d")
            except Exception:
                min_d = max_d = None
    return n_rows, n_cols, min_d, max_d

def _process_single_json(path: str, data_dir: str) -> Optional[CatalogEntry]:
    size, mtime = _safe_stat(path)
    df = _json_to_dataframe(path)
    if df is None or df.empty:
        # still record the file
        ticker = _infer_ticker_from_filename(path)
        return CatalogEntry(
            ticker=ticker, src_path=path, parquet_path=_parquet_path_for(data_dir, ticker),
            n_rows=0, n_cols=0, min_date=None, max_date=None, date_col=None,
            filesize_bytes=size, last_modified=mtime, fields=[]
        )
    # Date handling
    df, date_col = _coerce_datetime(df, None)
    df = _ensure_sorted(df, date_col)

    ticker = _detect_ticker(df, path) or _infer_ticker_from_filename(path)

    # Write parquet (preserve all columns)
    pq_path = _parquet_path_for(data_dir, ticker)
    try:
        _write_parquet(df, pq_path)
    except Exception as e:
        # Fallback: keep only primitive columns convertible by pyarrow
        df2 = df.copy()
        for c in df2.columns:
            try:
                # Try to force to string for exotic types
                if isinstance(df2[c].iloc[0] if len(df2)>0 else "", (list, dict)):
                    df2[c] = df2[c].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x)
            except Exception:
                pass
        _write_parquet(df2, pq_path)

    n_rows, n_cols, min_d, max_d = _summarize_df(df, date_col)

    return CatalogEntry(
        ticker=ticker,
        src_path=path,
        parquet_path=pq_path,
        n_rows=n_rows,
        n_cols=n_cols,
        min_date=min_d,
        max_date=max_d,
        date_col=date_col,
        filesize_bytes=size,
        last_modified=mtime,
        fields=[str(c) for c in df.columns]
    )

def build_or_refresh_catalog(data_dir: str, show_progress: bool=False, progress_cb=None) -> pd.DataFrame:
    """
    Scans data_dir for JSON files, converts each to Parquet (if changed),
    and creates a catalog parquet + json with per-file metadata.
    """
    assert os.path.isdir(data_dir), f"Data folder does not exist: {data_dir}"
    files = _list_json_files(data_dir)
    if not files:
        raise FileNotFoundError(f"No JSON files found under: {data_dir}")

    entries: List[CatalogEntry] = []
    total = len(files)

    # Load existing catalog to avoid reprocessing unchanged files (optional simple skip by mtime & size)
    cat_parquet, cat_json = _catalog_paths_for(data_dir)
    existing = None
    if os.path.exists(cat_json):
        try:
            with open(cat_json, "r", encoding="utf-8") as f:
                existing = { row["src_path"]: row for row in json.load(f) if isinstance(row, dict) and "src_path" in row }
        except Exception:
            existing = None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    workers = _recommended_workers()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = []
        for i, path in enumerate(files, 1):
            size, mtime = _safe_stat(path)
            if existing:
                prev = existing.get(path)
                if prev and int(prev.get("filesize_bytes", -1)) == size and float(prev.get("last_modified", 0.0)) == mtime:
                    # unchanged -> just reuse the previous row (no re-write of parquet)
                    def _reuse(prev_row=prev):
                        return CatalogEntry(
                            ticker=prev_row.get("ticker"),
                            src_path=prev_row.get("src_path"),
                            parquet_path=prev_row.get("parquet_path"),
                            n_rows=int(prev_row.get("n_rows", 0)),
                            n_cols=int(prev_row.get("n_cols", 0)),
                            min_date=prev_row.get("min_date"),
                            max_date=prev_row.get("max_date"),
                            date_col=prev_row.get("date_col"),
                            filesize_bytes=int(prev_row.get("filesize_bytes", -1)),
                            last_modified=float(prev_row.get("last_modified", 0.0)),
                            fields=list(prev_row.get("fields", [])),
                        )
                    futures.append(ex.submit(_reuse))
                    continue
            futures.append(ex.submit(_process_single_json, path, data_dir))

        done = 0
        for fut in as_completed(futures):
            ent = fut.result()
            if ent is not None:
                entries.append(ent)
            done += 1
            if show_progress and progress_cb:
                progress_cb(done, total)

    # Build DataFrame
    cat_rows = []
    for e in entries:
        cat_rows.append({
            "ticker": e.ticker,
            "src_path": e.src_path,
            "parquet_path": e.parquet_path,
            "n_rows": e.n_rows,
            "n_cols": e.n_cols,
            "min_date": e.min_date,
            "max_date": e.max_date,
            "date_col": e.date_col,
            "filesize_bytes": e.filesize_bytes,
            "last_modified": e.last_modified,
            "fields": e.fields,
        })
    catalog_df = pd.DataFrame(cat_rows).sort_values("ticker").reset_index(drop=True)

    # Save catalog artifacts
    os.makedirs(os.path.join(data_dir, CATALOG_SUBDIR), exist_ok=True)
    try:
        # Save parquet
        if _HAS_POLARS:
            pl.from_pandas(catalog_df).write_parquet(cat_parquet)
        else:
            catalog_df.to_parquet(cat_parquet, index=False)
    except Exception:
        pass

    with open(cat_json, "w", encoding="utf-8") as f:
        json.dump(cat_rows, f, ensure_ascii=False, indent=2)

    return catalog_df

# ---------------- Public API: Loading & Filtering ----------------

def get_catalog(data_dir: str) -> Optional[pd.DataFrame]:
    cat_parquet, cat_json = _catalog_paths_for(data_dir)
    if os.path.exists(cat_parquet):
        try:
            return _read_parquet(cat_parquet)
        except Exception:
            pass
    if os.path.exists(cat_json):
        try:
            with open(cat_json, "r", encoding="utf-8") as f:
                return pd.DataFrame(json.load(f))
        except Exception:
            return None
    return None

def filter_catalog(
    catalog_df: pd.DataFrame,
    min_rows: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    must_have_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    df = catalog_df.copy()
    if min_rows:
        df = df[df["n_rows"] >= int(min_rows)]
    if start_date and "max_date" in df:
        df = df[df["max_date"].fillna("") >= start_date]
    if end_date and "min_date" in df:
        df = df[df["min_date"].fillna("") <= end_date]
    if must_have_cols:
        df = df[df["fields"].apply(lambda cols: all(col in set(cols) for col in must_have_cols))]
    return df.reset_index(drop=True)

def load_tickers_on_demand(
    tickers: List[str],
    data_dir: Optional[str] = None,
    catalog_df: Optional[pd.DataFrame] = None,
    columns: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Load a subset of tickers on demand from Parquet with optional column and date filters.
    """
    if catalog_df is None:
        assert data_dir, "Provide data_dir or catalog_df"
        catalog_df = get_catalog(data_dir)
        assert catalog_df is not None, "Catalog not found. Run build_or_refresh_catalog first."

    colmap = { r["ticker"]: r["parquet_path"] for _, r in catalog_df.iterrows() }
    date_col_map = { r["ticker"]: r.get("date_col") for _, r in catalog_df.iterrows() }

    out: Dict[str, pd.DataFrame] = {}
    for t in tickers:
        pq = colmap.get(t)
        if not pq or not os.path.exists(pq):
            continue
        df = _read_parquet(pq, columns=columns)
        dcol = date_col_map.get(t)
        if dcol and dcol in df.columns:
            # Ensure datetime (could be lost through pandas <-> arrow sometimes)
            try:
                if not pd.api.types.is_datetime64_any_dtype(df[dcol]):
                    df[dcol] = pd.to_datetime(df[dcol], errors="coerce", utc=True)
            except Exception:
                pass
            if date_from:
                df = df[df[dcol] >= pd.to_datetime(date_from, utc=True)]
            if date_to:
                # inclusive
                dt_to = pd.to_datetime(date_to, utc=True)
                df = df[df[dcol] <= dt_to]
            df = df.sort_values(by=dcol).reset_index(drop=True)
        out[t] = df
    return out

# ---------------- Streamlit UI Section ----------------

def render_data_setup_ui():
    """
    Drop-in UI you can call from app.py to build/refresh the catalog & parquet with one button.
    """
    try:
        import streamlit as st
    except Exception:
        raise RuntimeError("render_data_setup_ui requires Streamlit. Install and run inside a Streamlit app.")

    st.subheader("📁 טעינת נתונים לבניית קטלוג + המרה ל-Parquet (JSON → Parquet)")
    data_dir = st.text_input("נתיב לתיקיית הנתונים (JSON, קובץ לכל מניה)", value=st.session_state.get("data_dir", ""))
    col1, col2 = st.columns([1,1])
    with col1:
        do_build = st.button("⚙️ צור/רענן קטלוג + המרת Parquet", type="primary")
    with col2:
        show_stats = st.checkbox("הצג סיכום קטלוג לאחר העיבוד", value=True)

    if do_build:
        assert data_dir.strip(), "יש להזין נתיב תקין לתיקיית נתונים."
        st.info("מתחיל סריקה והמרה... (הרצה ראשונית עלולה לקחת זמן)")
        prog = st.progress(0.0)
        status = st.empty()

        def _progress(done, total):
            prog.progress(done/total)
            status.write(f"מעבד קובץ {done} מתוך {total}")

        t0 = time.time()
        catalog_df = build_or_refresh_catalog(data_dir, show_progress=True, progress_cb=_progress)
        dt = time.time() - t0
        st.success(f"סיום. נמצאו {len(catalog_df)} קבצים/מניות. זמן ריצה: {dt:,.1f} שנ׳")
        st.session_state["data_dir"] = data_dir
        st.session_state["catalog_df"] = catalog_df
        st.session_state["parquet_dir"] = os.path.join(data_dir, PARQUET_SUBDIR)

        if show_stats:
            with st.expander("סיכום קטלוג"):
                st.dataframe(catalog_df[["ticker","n_rows","min_date","max_date","parquet_path"]], use_container_width=True)

    # Quick helpers for later steps
    st.divider()
    st.caption("טיפ: לאחר בניית הקטלוג, מסכים של סריקה/Backtest יכולים לקרוא `st.session_state['catalog_df']` ולטעון נתונים נקודתית דרך `load_tickers_on_demand`.")

# ---------------- Daily Update Scaffold (Optional) ----------------

def plan_daily_update(data_dir: str) -> Dict[str, Any]:
    """
    Returns a lightweight plan for updating each ticker daily (placeholder for your fetch logic).
    The idea: read catalog -> last date per ticker -> produce plan of 'next_date_to_fetch'.
    """
    cat = get_catalog(data_dir)
    assert cat is not None, "Catalog not found"
    plan = []
    for _, row in cat.iterrows():
        max_date = row.get("max_date")
        try:
            last = pd.to_datetime(max_date).date() if pd.notna(max_date) else None
        except Exception:
            last = None
        plan.append({
            "ticker": row["ticker"],
            "src_path": row["src_path"],
            "parquet_path": row["parquet_path"],
            "last_date_present": str(last) if last else None,
            "next_date_to_fetch": None if not last else str(last),  # replace with last+1 day if you fetch by daily cadence
        })
    return {"data_dir": data_dir, "plan": plan}

if __name__ == "__main__":
    # Simple CLI to build catalog: python data_setup.py /path/to/data
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", help="Root directory with per-ticker JSON files")
    args = ap.parse_args()
    df = build_or_refresh_catalog(args.data_dir, show_progress=True, progress_cb=lambda d,t: None)
    print(df.head(10).to_markdown(index=False))
