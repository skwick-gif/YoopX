
# main.py — wires Scan, Backtest, Optimize models
import os, sys
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from backend import Controller, ScanListModel, BtListModel, OptListModel

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("QuantDesk")
    app.setOrganizationName("YourOrg")

    engine = QQmlApplicationEngine()

    scan_model = ScanListModel()
    bt_model = BtListModel()
    opt_model = OptListModel()
    ctrl = Controller(scan_model, bt_model, opt_model)

    engine.rootContext().setContextProperty("scanModel", scan_model)
    engine.rootContext().setContextProperty("btModel", bt_model)
    engine.rootContext().setContextProperty("optModel", opt_model)
    engine.rootContext().setContextProperty("controller", ctrl)

    qml_path = os.path.join(os.path.dirname(__file__), "qml", "Main.qml")
    engine.load(QUrl.fromLocalFile(qml_path))
    if not engine.rootObjects():
        sys.exit("Failed to load QML")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
