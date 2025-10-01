"""Data normalization utilities for converting raw JSON price files
into a stable ML-ready Parquet layer.

Goals:
 - One-time (and incremental) materialization of expanded OHLCV data
 - Eliminate repeated JSON schema branching at training time
 - Provide deterministic column set & Date index
 - Allow quick validation & summary stats

Directory layout produced (default):
    <data_folder>/_mlready/<SYMBOL>.parquet
    <data_folder>/_mlready/_summary.json

Each parquet contains columns: Date (implicit index), Open, High, Low, Close, Adj Close, Volume (+ any extras preserved)
"""
from __future__ import annotations
import os, json, time
from typing import Dict, Any, Optional, List
import pandas as pd

try:
    from .data_utils import load_json, maybe_adjust_with_adj
except Exception:  # fallback relative import pattern
    from data.data_utils import load_json, maybe_adjust_with_adj  # type: ignore

def _safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default

def normalize_price_json_folder(
    folder: str,
    out_dir: Optional[str] = None,
    min_rows: int = 5,
    use_adj: bool = True,
    overwrite: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Normalize all JSON files in folder into Parquet for fast ML ingestion.

    Parameters
    ----------
    folder : str
        Source directory containing *.json files (one per symbol).
    out_dir : str | None
        Target directory for Parquet output. Defaults to ``folder/_mlready``.
    min_rows : int
        Skip symbols whose expanded history has fewer than this many rows.
    use_adj : bool
        If True, applies adjustment logic (replace Close with Adj Close if present).
    overwrite : bool
        If False, will skip symbols whose Parquet already exists and is newer than source JSON.
    limit : int | None
        Optional cap on number of files processed (debugging / sampling).

    Returns
    -------
    dict summary with counts and basic stats.
    """
    start_ts = time.time()
    src_files = [f for f in os.listdir(folder) if f.lower().endswith('.json')]
    src_files.sort()
    if limit is not None:
        src_files = src_files[:limit]
    out_dir = out_dir or os.path.join(folder, '_mlready')
    os.makedirs(out_dir, exist_ok=True)

    processed = 0
    written = 0
    skipped_existing = 0
    skipped_small = 0
    errors: List[str] = []
    symbols_written: List[str] = []
    for i, fname in enumerate(src_files):
        sym = os.path.splitext(fname)[0]
        src_path = os.path.join(folder, fname)
        tgt_path = os.path.join(out_dir, f"{sym}.parquet")
        try:
            if (not overwrite) and os.path.exists(tgt_path):
                try:
                    if os.path.getmtime(tgt_path) >= os.path.getmtime(src_path):
                        skipped_existing += 1
                        continue
                except Exception:
                    pass
            df = load_json(src_path)
            if df is None or getattr(df, 'empty', True):
                errors.append(f"{sym}: empty after load")
                continue
            if use_adj:
                try:
                    df = maybe_adjust_with_adj(df, True)
                except Exception:
                    pass
            # enforce minimum rows
            if len(df) < min_rows:
                skipped_small += 1
                continue
            # ensure sorted by index if datetime
            try:
                if df.index.name and hasattr(df.index, 'dtype_str'):
                    df = df.sort_index()
            except Exception:
                pass
            # write parquet (index preserved as Date column automatically by pandas if reset)
            try:
                df_reset = df.reset_index()
            except Exception:
                df_reset = df
            try:
                df_reset.to_parquet(tgt_path, index=False)
                written += 1
                symbols_written.append(sym)
            except Exception as e:
                errors.append(f"{sym}: write failed {e}")
        except Exception as e:
            errors.append(f"{sym}: {e}")
        finally:
            processed += 1

    summary = {
        'processed': processed,
        'written': written,
        'skipped_existing': skipped_existing,
        'skipped_small': skipped_small,
        'errors': errors,
        'symbols': symbols_written,
        'seconds': round(time.time() - start_ts, 2)
    }
    try:
        with open(os.path.join(out_dir, '_summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return summary

__all__ = ['normalize_price_json_folder']
