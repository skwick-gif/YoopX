"""Evaluation & monitoring utilities for live prediction tracking.

Functions:
  backfill_realized_outcomes(pred_log_path, data_map, horizons) -> updates prediction log with realized label when due.
  compute_live_metrics(pred_log_path) -> aggregate precision/recall/AUC-like proxy metrics.
"""
from __future__ import annotations
import os, json, math, statistics, datetime
from typing import Dict, Any, List

def _iter_jsonl(path: str):
    if not os.path.exists(path):
        return
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def backfill_realized_outcomes(pred_log_path: str, data_map: Dict[str, Any], today: str|None=None) -> int:
    """Add realized labels for predictions whose horizon date has passed.
    A realized label is 1 if close at future_due[h] >= prior close * (1+0.01) (placeholder rule), else 0.
    Returns number of entries updated.
    """
    if not os.path.exists(pred_log_path):
        return 0
    tmp_path = pred_log_path + '.tmp'
    updated = 0
    if today is None:
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    today_dt = datetime.datetime.strptime(today,'%Y-%m-%d')
    with open(tmp_path,'w',encoding='utf-8') as out:
        for rec in _iter_jsonl(pred_log_path):
            try:
                if 'realized' not in rec and rec.get('future_due') and rec.get('symbol') in data_map and rec.get('price'):
                    all_due = rec['future_due']
                    sym = rec['symbol']
                    df = data_map.get(sym)
                    realized_map = {}
                    all_done = True
                    for hz, due_str in all_due.items():
                        try:
                            due_dt = datetime.datetime.strptime(due_str,'%Y-%m-%d')
                        except Exception:
                            due_dt = None
                        if not due_dt or due_dt > today_dt:
                            all_done = False
                            continue
                        # compute horizon label
                        try:
                            import pandas as _pd
                            tgt_row = df[df.index >= _pd.to_datetime(due_dt)].head(1)
                            if not tgt_row.empty:
                                # placeholder: success if Close >= entry_price *1.01
                                entry_price = float(rec.get('price'))
                                close_col = None
                                for c in tgt_row.columns:
                                    if c.lower()=='close':
                                        close_col = c; break
                                if close_col is None:
                                    # pick first numeric
                                    for c in tgt_row.columns:
                                        try:
                                            float(tgt_row[c].iloc[0]); close_col = c; break
                                        except Exception:
                                            continue
                                if close_col:
                                    future_close = float(tgt_row[close_col].iloc[0])
                                    realized_map[hz] = 1 if future_close >= entry_price*1.01 else 0
                        except Exception:
                            continue
                    if realized_map and all_done:
                        rec['realized'] = realized_map
                        updated += 1
                out.write(json.dumps(rec,ensure_ascii=False)+'\n')
            except Exception:
                out.write(json.dumps(rec,ensure_ascii=False)+'\n')
    try:
        os.replace(tmp_path, pred_log_path)
    except Exception:
        pass
    return updated

def compute_live_metrics(pred_log_path: str) -> Dict[str, Any]|None:
    if not os.path.exists(pred_log_path):
        return None
    preds = []
    for rec in _iter_jsonl(pred_log_path):
        try:
            if 'realized' in rec and rec.get('prob') is not None:
                # use primary prob vs aggregated label heuristic (mean across horizons realized if multi)
                realized_map = rec.get('realized')
                if isinstance(realized_map, dict) and realized_map:
                    label = statistics.mean(realized_map.values())
                    # binarize mean >0 (if any horizon success) for placeholder metric
                    label_bin = 1 if any(v==1 for v in realized_map.values()) else 0
                else:
                    label_bin = None
                preds.append((float(rec.get('prob')), label_bin))
        except Exception:
            continue
    preds = [p for p in preds if p[1] is not None]
    if not preds:
        return None
    try:
        import numpy as _np
        arr_p = _np.array([p[0] for p in preds])
        arr_y = _np.array([p[1] for p in preds])
        # simple threshold 0.5 metrics
        pred_bin = (arr_p >= 0.5).astype(int)
        tp = ((pred_bin==1)&(arr_y==1)).sum(); fp=((pred_bin==1)&(arr_y==0)).sum(); fn=((pred_bin==0)&(arr_y==1)).sum(); tn=((pred_bin==0)&(arr_y==0)).sum()
        prec = tp/(tp+fp) if (tp+fp)>0 else 0.0
        rec = tp/(tp+fn) if (tp+fn)>0 else 0.0
        f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0.0
        # approximate AUC via pairwise method (fallback if sklearn not installed in prod)
        try:
            from sklearn.metrics import roc_auc_score
            auc = float(roc_auc_score(arr_y, arr_p))
        except Exception:
            pos = arr_p[arr_y==1]; neg = arr_p[arr_y==0]
            if len(pos)==0 or len(neg)==0:
                auc = None
            else:
                wins = 0
                for p in pos:
                    wins += (neg < p).sum() + 0.5*(neg==p).sum()
                auc = wins / (len(pos)*len(neg))
        return {'count': int(len(arr_p)), 'precision': round(prec,4), 'recall': round(rec,4), 'f1': round(f1,4), 'auc': round(auc,4) if auc is not None else None}
    except Exception:
        return None

def summarize_recent(pred_log_path: str, last_n: int = 200) -> Dict[str, Any]|None:
    if not os.path.exists(pred_log_path):
        return None
    lines = []
    with open(pred_log_path,'r',encoding='utf-8') as f:
        for line in f: lines.append(line)
    if not lines:
        return None
    subset = lines[-last_n:]
    pos = 0; total=0
    for line in subset:
        try:
            rec = json.loads(line)
            if 'prob' in rec:
                total += 1
                if isinstance(rec.get('prob'), (int,float)) and rec.get('prob')>=0.5:
                    pos +=1
        except Exception:
            continue
    if total==0:
        return None
    return {'recent_preds': total, 'pct_ge_0_5': round(pos/total,3)}
