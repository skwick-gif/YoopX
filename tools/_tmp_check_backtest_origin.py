from PySide6.QtWidgets import QApplication
import sys
from pathlib import Path

# Ensure project root is on sys.path so top-level imports like `main_content`
# and `ui.*` resolve when running this script from tools/.
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

app = QApplication([])
import main_content
mc = main_content.MainContent()
print(mc.backtest_tab.__class__.__module__, mc.backtest_tab.__class__.__name__)
app.quit()
