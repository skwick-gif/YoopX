import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import os
# prevent the automatic loader from starting by faking os.path.isdir for the 'data backup' folder
orig_isdir = os.path.isdir
def _fake_isdir(p):
	try:
		if str(p).endswith('data backup'):
			return False
	except Exception:
		pass
	return orig_isdir(p)
os.path.isdir = _fake_isdir
from main_window import QuantDeskMainWindow
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
win = QuantDeskMainWindow()
# restore
os.path.isdir = orig_isdir
# simulate selecting Auto-Discovery tab (index 4)
print('Before emit: sidebar visible =', win.sidebar.isVisible())
win.main_content.tab_changed.emit(4)
print('After emit 4: sidebar visible =', win.sidebar.isVisible())
# simulate selecting Scan tab (index 0)
win.main_content.tab_changed.emit(0)
print('After emit 0: sidebar visible =', win.sidebar.isVisible())
# cleanup
try:
	win.main_content.stop_all_workers()
except Exception:
	pass
# aggressively stop known threads (loader_thread etc.)
try:
	lt = getattr(win.main_content, 'loader_thread', None)
	if lt is not None:
		try:
			lt.quit()
		except Exception:
			pass
		try:
			lt.wait(2000)
		except Exception:
			pass
		try:
			if lt.isRunning():
				lt.terminate()
				lt.wait(1000)
		except Exception:
			pass
except Exception:
	pass

win.close()
win.deleteLater()
app.processEvents()
import time
time.sleep(0.2)
app.quit()
print('Done')
