import os, json, time, hashlib, csv, datetime
from typing import Any, Dict, List

BASE_DIR = os.path.join('run_repo','runs')
META_INDEX = os.path.join('run_repo','index.json')

os.makedirs(BASE_DIR, exist_ok=True)

def _hash_params(params: Dict[str, Any]) -> str:
    try:
        ser = json.dumps(params, sort_keys=True, default=str)
    except Exception:
        ser = str(params)
    return hashlib.sha256(ser.encode('utf-8')).hexdigest()[:16]

def _utc_ts():
    return datetime.datetime.utcnow().isoformat()+"Z"

def save_run(run_type: str, params: Dict[str, Any], results: Any, tags: Dict[str, Any] | None = None) -> str:
    """Persist a run (backtest / optimize / walkforward) with deterministic hash folder.
    Returns run_id (hash)."""
    if not isinstance(params, dict):
        params = {'raw': str(params)}
    run_hash = _hash_params({'type': run_type, 'params': params})
    folder = os.path.join(BASE_DIR, f"{run_type}_{run_hash}")
    os.makedirs(folder, exist_ok=True)
    meta = {
        'run_id': run_hash,
        'type': run_type,
        'created_utc': _utc_ts(),
        'params': params,
        'tags': tags or {},
        'rows': None,
    }
    # write results
    if isinstance(results, list):
        meta['rows'] = len(results)
        # store as json
        try:
            with open(os.path.join(folder,'results.json'),'w',encoding='utf-8') as f:
                json.dump(results,f,ensure_ascii=False,indent=2)
        except Exception:
            pass
        # also store csv (best effort)
        try:
            if results and isinstance(results[0], dict):
                cols = sorted({k for r in results for k in r.keys()})
                with open(os.path.join(folder,'results.csv'),'w',newline='',encoding='utf-8') as f:
                    w = csv.writer(f)
                    w.writerow(cols)
                    for r in results:
                        w.writerow([r.get(c,'') for c in cols])
        except Exception:
            pass
    else:
        try:
            with open(os.path.join(folder,'results.txt'),'w',encoding='utf-8') as f:
                f.write(str(results))
        except Exception:
            pass
    # write meta
    try:
        with open(os.path.join(folder,'meta.json'),'w',encoding='utf-8') as f:
            json.dump(meta,f,ensure_ascii=False,indent=2)
    except Exception:
        pass
    # update global index (append style)
    try:
        idx = []
        if os.path.exists(META_INDEX):
            with open(META_INDEX,'r',encoding='utf-8') as f:
                idx = json.load(f) or []
        idx.insert(0, {k: meta[k] for k in ('run_id','type','created_utc','rows')})
        # keep only last 500
        if len(idx) > 500:
            idx = idx[:500]
        with open(META_INDEX,'w',encoding='utf-8') as f:
            json.dump(idx,f,ensure_ascii=False,indent=2)
    except Exception:
        pass
    return run_hash

def list_runs(limit: int = 50):
    try:
        if os.path.exists(META_INDEX):
            with open(META_INDEX,'r',encoding='utf-8') as f:
                data = json.load(f) or []
            return data[:limit]
    except Exception:
        return []
    return []

def load_run(run_id: str):
    try:
        for name in os.listdir(BASE_DIR):
            if name.endswith(run_id):
                folder = os.path.join(BASE_DIR,name)
                meta_path = os.path.join(folder,'meta.json')
                res_path = os.path.join(folder,'results.json')
                meta = {}
                results = None
                try:
                    if os.path.exists(meta_path):
                        with open(meta_path,'r',encoding='utf-8') as f:
                            meta = json.load(f)
                except Exception: pass
                try:
                    if os.path.exists(res_path):
                        with open(res_path,'r',encoding='utf-8') as f:
                            results = json.load(f)
                except Exception: pass
                return meta, results
    except Exception:
        return None, None
    return None, None
