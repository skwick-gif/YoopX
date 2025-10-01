import os, json, time, hashlib
from typing import Dict, Any
import pandas as pd

BASE_DIR = os.path.join('ml','feature_store')
os.makedirs(BASE_DIR, exist_ok=True)
META_PATH = os.path.join(BASE_DIR,'meta.json')

def _hash_symbol(symbol: str):
    return hashlib.sha1(symbol.encode('utf-8')).hexdigest()[:12]

def put_features(symbol: str, feats: Dict[str, Any]):
    if not isinstance(feats, dict):
        return
    sid = _hash_symbol(symbol)
    path = os.path.join(BASE_DIR, f'{sid}.json')
    rec = {'symbol': symbol, 'ts': time.time(), 'features': feats}
    try:
        with open(path,'w',encoding='utf-8') as f:
            json.dump(rec,f,ensure_ascii=False)
    except Exception:
        pass

def get_features(symbol: str):
    try:
        sid = _hash_symbol(symbol)
        path = os.path.join(BASE_DIR,f'{sid}.json')
        if os.path.exists(path):
            with open(path,'r',encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        return None
    return None

def snapshot_catalog():
    out = []
    try:
        for fn in os.listdir(BASE_DIR):
            if fn.endswith('.json') and fn!='meta.json':
                try:
                    with open(os.path.join(BASE_DIR,fn),'r',encoding='utf-8') as f:
                        data = json.load(f)
                    out.append({'symbol': data.get('symbol'), 'age_sec': time.time()-data.get('ts',0), 'feature_count': len(data.get('features') or {})})
                except Exception:
                    continue
    except Exception:
        return out
    return out

def compute_drift(latest_feats: Dict[str, Any], ref_stats: Dict[str, Any]):
    """Return mean absolute z-score across overlapping features."""
    if not latest_feats or not ref_stats:
        return None
    zs = []
    for k,v in latest_feats.items():
        if k in ref_stats:
            st = ref_stats[k]
            mean = st.get('mean'); std = st.get('std') or 0
            try:
                if std and isinstance(mean,(int,float)) and isinstance(v,(int,float)):
                    zs.append(abs((v-mean)/std))
            except Exception:
                continue
    if not zs:
        return None
    return sum(zs)/len(zs)
