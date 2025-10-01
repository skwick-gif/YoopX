import json, os, threading
from typing import Any, Dict

SETTINGS_PATH = 'config/ui_settings.json'
_lock = threading.Lock()

DEFAULTS = {
    'ml_model': 'rf',
    'ml_min_prob': 0.0,
    'auto_rescan': True,
    'scan_settings_geometry': None,
}

def load_settings() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_PATH):
        return DEFAULTS.copy()
    try:
        with open(SETTINGS_PATH,'r',encoding='utf-8') as f:
            data = json.load(f)
        merged = DEFAULTS.copy(); merged.update(data or {})
        return merged
    except Exception:
        return DEFAULTS.copy()

def save_settings(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with _lock:
        try:
            with open(SETTINGS_PATH,'w',encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
