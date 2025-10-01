"""Ensemble & meta-learning utilities.

Provides:
  optimize_equal_weighted(models_meta) -> baseline mean AUC.
  optimize_linear_weights(models_meta) -> grid search for weights maximizing AUC (fallback to average AUC proxy if labels differ).
  train_meta_model(models_meta) -> logistic regression stacking meta-model on aligned validation probabilities.

models_meta: list of dicts each containing:
  'name': identifier ('rf','xgb','lgbm')
  'val_probs': list[float]
  'val_labels': list[int]
  'auc': optional precomputed auc
All arrays must align length-wise for stacking (only rows where all models have a prob retained).
"""
from __future__ import annotations
from typing import List, Dict, Any
import math, json, os

def _compute_auc(probs, labels):
    try:
        from sklearn.metrics import roc_auc_score
        return float(roc_auc_score(labels, probs))
    except Exception:
        return None

def optimize_equal_weighted(models_meta: List[Dict[str, Any]]):
    aucs = [m.get('auc') for m in models_meta if isinstance(m.get('auc'), (int,float))]
    if not aucs:
        return {'mean_auc': None}
    return {'mean_auc': sum(aucs)/len(aucs)}

def optimize_linear_weights(models_meta: List[Dict[str, Any]], step: float = 0.1):
    # Only proceed if all have same length val_probs and labels
    aligned = []
    base_len = None
    for m in models_meta:
        vp = m.get('val_probs'); vl = m.get('val_labels')
        if not vp or not vl or len(vp) != len(vl):
            return {'weights': None, 'auc': None, 'reason': 'inconsistent validation shapes'}
        if base_len is None:
            base_len = len(vp)
        if len(vp) != base_len:
            return {'weights': None, 'auc': None, 'reason': 'length mismatch across models'}
        aligned.append(m)
    if not aligned:
        return {'weights': None, 'auc': None}
    import numpy as np
    labels = np.array(aligned[0]['val_labels'], dtype=int)
    probs_matrix = np.vstack([m['val_probs'] for m in aligned])  # shape (M, N)
    best_auc = -1; best_w = None
    grid_vals = [round(x,2) for x in list(np.arange(0,1+1e-9, step))]
    # constrain sum to 1 within tolerance
    for w_rf in grid_vals:
        for w_x in grid_vals:
            for w_l in grid_vals:
                s = w_rf + w_x + w_l
                if abs(s - 1.0) > 1e-6:
                    continue
                w = [w_rf, w_x, w_l]
                combined = np.average(probs_matrix, axis=0, weights=w)
                auc = _compute_auc(combined, labels)
                if auc is not None and auc > best_auc:
                    best_auc = auc; best_w = w
    return {'weights': best_w, 'auc': best_auc}

def train_meta_model(models_meta: List[Dict[str, Any]]):
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
    except Exception:
        return {'meta_model': None, 'auc': None, 'reason': 'sklearn missing'}
    # align validation sets: only keep indices where all models have probabilities
    val_lengths = [len(m.get('val_probs') or []) for m in models_meta]
    if not val_lengths or len(set(val_lengths)) != 1:
        return {'meta_model': None, 'auc': None, 'reason': 'mismatched val lengths'}
    labels = models_meta[0].get('val_labels')
    if not labels:
        return {'meta_model': None, 'auc': None, 'reason': 'no labels'}
    X = np.vstack([m['val_probs'] for m in models_meta]).T  # shape (N, M)
    y = labels
    try:
        lr = LogisticRegression(max_iter=500)
        lr.fit(X, y)
        auc = _compute_auc(lr.predict_proba(X)[:,1], y)
        return {'meta_model': lr, 'auc': auc}
    except Exception as e:
        return {'meta_model': None, 'auc': None, 'reason': str(e)}

def persist_ensemble_artifacts(root_dir: str, weights: Dict[str,float]|None, meta_auc: float|None):
    try:
        os.makedirs(root_dir, exist_ok=True)
        data = {'weights': weights, 'meta_auc': meta_auc}
        with open(os.path.join(root_dir,'ensemble.json'),'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
    except Exception:
        pass
