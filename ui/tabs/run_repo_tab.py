from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTableWidget,QTableWidgetItem,QMessageBox,
                               QToolButton,QStyle)
from PySide6.QtCore import Signal
from run_repo.run_repository import list_runs, load_run

class RunRepoTab(QWidget):
    load_run_requested = Signal(str)
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh_runs()
    def _build_ui(self):
        layout = QVBoxLayout(self)
        btn_bar = QHBoxLayout(); self.refresh_btn = QPushButton('רענן'); self.refresh_btn.clicked.connect(self.refresh_runs)
        self.load_btn = QPushButton('טען נבחר'); self.load_btn.clicked.connect(self._load_selected)
        help_btn = QToolButton()
        try:
            help_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        except Exception:
            help_btn.setText('?')
        help_btn.setToolTip('עזרה - Runs')
        from ui.shared.help_viewer import show_markdown_dialog
        help_btn.clicked.connect(lambda: show_markdown_dialog(self,'docs/run_repo_tab.md','Run Repo Help'))
        btn_bar.addWidget(self.refresh_btn); btn_bar.addWidget(self.load_btn); btn_bar.addWidget(help_btn); btn_bar.addStretch(); layout.addLayout(btn_bar)
        self.table = QTableWidget(); self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(['Run ID','Type','UTC','Rows'])
        layout.addWidget(self.table,1)
    def refresh_runs(self):
        runs = list_runs(200)
        self.table.setRowCount(len(runs))
        for r,row in enumerate(runs):
            for c,k in enumerate(['run_id','type','created_utc','rows']):
                it = QTableWidgetItem(str(row.get(k,'')))
                self.table.setItem(r,c,it)
    def _load_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self,'מידע','בחר ריצה')
            return
        run_id = self.table.item(row,0).text()
        if not run_id:
            return
        self.load_run_requested.emit(run_id)
    # Help handled by shared show_markdown_dialog
