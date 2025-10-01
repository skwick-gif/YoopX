import json, datetime, os, threading
from pathlib import Path
from typing import Dict, Any

_lock = threading.Lock()

LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'ui_events.jsonl'

def write_log(entry: Dict[str, Any]):
    try:
        data = dict(entry)
        if 'ts' not in data:
            data['ts'] = datetime.datetime.utcnow().isoformat() + 'Z'
        line = json.dumps(data, ensure_ascii=False)
        with _lock:
            with open(LOG_FILE, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')
    except Exception:
        pass
