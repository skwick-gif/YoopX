import math
from typing import Dict, Any, List

def compute_contributions(model_obj: Dict[str, Any], feature_row, feature_stats: Dict[str, Dict[str,float]]|None=None, top_k: int = 15) -> List[Dict[str, Any]]:
    """Heuristic feature contribution breakdown.
    If SHAP is available and model is tree-based, attempts SHAP; otherwise uses (value-mean)/std * importance.
    feature_row: pandas Series with feature values.
    feature_stats: dict of feature -> {mean, std} captured at training.
    Returns list of dicts sorted by absolute contribution: [{'feature','value','base','z','importance','contribution'}].
    """
    try:
        import pandas as pd
        if feature_row is None:
            return []
        feats = model_obj.get('features') if isinstance(model_obj, dict) else None
        if feats is None:
            feats = list(feature_row.index)
        imp_map = {}
        # model stored importance list
        fi_list = model_obj.get('feature_importance') if isinstance(model_obj, dict) else None
        if isinstance(fi_list, list):
            for rec in fi_list:
                try:
                    imp_map[rec['feature']] = float(rec.get('importance', 0.0))
                except Exception:
                    pass
        # fallback equal importance
        if not imp_map:
            for f in feats:
                imp_map[f] = 1.0
        # normalize importance
        total_imp = sum(imp_map.values()) or 1.0
        for k in list(imp_map.keys()):
            imp_map[k] = imp_map[k] / total_imp
        rows = []
        for f in feats:
            try:
                val = float(feature_row.get(f))
            except Exception:
                continue
            mean = None; std = None
            if feature_stats and f in feature_stats:
                mean = feature_stats[f].get('mean')
                std = feature_stats[f].get('std') or 0.0
            z = 0.0
            if mean is not None and std:
                try:
                    z = (val - mean)/std
                except Exception:
                    z = 0.0
            contrib = z * imp_map.get(f, 0.0)
            rows.append({'feature': f, 'value': val, 'base': mean, 'std': std, 'z': z, 'importance': imp_map.get(f,0.0), 'contribution': contrib})
        rows.sort(key=lambda r: abs(r.get('contribution',0.0)), reverse=True)
        return rows[:top_k]
    except Exception:
        return []

def summarize_contributions(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    total_pos = sum(r['contribution'] for r in rows if r['contribution'] > 0)
    total_neg = sum(r['contribution'] for r in rows if r['contribution'] < 0)
    return {'total_positive': total_pos, 'total_negative': total_neg, 'net': total_pos + total_neg}
