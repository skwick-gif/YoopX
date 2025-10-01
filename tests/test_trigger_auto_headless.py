"""Headless test: trigger MainContent.on_run_auto_discovery with a tiny DataFrame to ensure the worker starts
and doesn't crash the UI due to thread lifetime issues.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from main_content import MainContent
import pandas as pd

app = QApplication.instance() or QApplication([])
mc = MainContent()
# prepare a tiny data_map with one synthetic symbol
idx = pd.date_range('2020-01-01', periods=10, freq='D')
df = pd.DataFrame({'Date': idx, 'Open': 1.0, 'High': 1.0, 'Low': 1.0, 'Close': 1.0, 'Volume': 100}, index=idx)
mc.data_map = {'TEST': df}

params = {'min_trades': 0, 'apply_bar_filters': False}
try:
    mc.on_run_auto_discovery(params)
    print('Triggered auto_discovery worker successfully')
except Exception as e:
    import traceback
    traceback.print_exc()
    print('Error triggering worker:', e)

# attempt to stop worker if present
try:
    w = getattr(mc, 'auto_discovery_worker', None)
    if w:
        try:
            # request graceful cancellation
            if hasattr(w, 'cancel') and callable(getattr(w, 'cancel')):
                try:
                    w.cancel()
                except Exception:
                    pass
            # give worker time to stop
            try:
                w.quit()
            except Exception:
                pass
            try:
                stopped = w.wait(10000)  # wait up to 10s
                if not stopped:
                    print('Warning: worker did not stop within timeout')
            except Exception:
                pass
        except Exception:
            pass
except Exception:
    pass

try:
    mc.deleteLater()
except Exception:
    pass
try:
    app.quit()
except Exception:
    pass
