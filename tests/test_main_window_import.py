# Headless import/instantiation test for the main Qt window
# This test creates a QApplication and instantiates QuantDeskMainWindow without exec()
# to catch import-time and __init__ errors in the UI code.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

# Import main window module and instantiate
from main_window import QuantDeskMainWindow

app = QApplication.instance() or QApplication([])
# prevent automatic loader thread from starting by making the app think the default data folder is missing
import os
default_data_folder = str(Path(__file__).resolve().parent.parent / 'data backup')
_real_isdir = os.path.isdir
def _patched_isdir(p):
    try:
        if os.path.abspath(p) == os.path.abspath(default_data_folder):
            return False
    except Exception:
        pass
    return _real_isdir(p)
os.path.isdir = _patched_isdir

# instantiate but don't show the window
w = QuantDeskMainWindow()
# restore original isdir implementation
os.path.isdir = _real_isdir
print('Main window instantiated successfully')

# Simple cleanup: find any attributes on the main window that look like QThreads
def _stop_worker_threads_simple(obj):
    # breadth-first traverse attributes and QObject children to find running threads
    seen = set()
    stack = [obj]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        # inspect attributes
        for name in dir(current):
            try:
                val = getattr(current, name)
            except Exception:
                continue
            # If it's a QThread-like object, attempt to stop it
            if hasattr(val, 'isRunning') and callable(getattr(val, 'isRunning')):
                try:
                    running = val.isRunning()
                except Exception:
                    running = False
                if running:
                    try:
                        if hasattr(val, 'cancel') and callable(getattr(val, 'cancel')):
                            val.cancel()
                    except Exception:
                        pass
                    try:
                        val.quit()
                    except Exception:
                        pass
                    try:
                        val.wait(2000)
                    except Exception:
                        pass
            # if val has QObject children, add them to the stack
            try:
                children = []
                if hasattr(val, 'children') and callable(getattr(val, 'children')):
                    children = val.children() or []
                for c in children:
                    stack.append(c)
            except Exception:
                pass


_stop_worker_threads_simple(w)
try:
    w.deleteLater()
except Exception:
    pass
try:
    app.quit()
except Exception:
    pass
