from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGroupBox,QLabel,QSpinBox,QDoubleSpinBox,QPushButton,QProgressBar,QTableWidget,QTableWidgetItem,QMessageBox,QFileDialog,
                               QToolButton,QStyle)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from ui.worker_thread import WorkerThread
import json

class WalkForwardTab(QWidget):
    run_walkforward_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.worker_thread=None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        settings_layout = QHBoxLayout()
        left = QGroupBox('Walk-Forward הגדרות'); left_l = QVBoxLayout(left)
        self.folds_spin = QSpinBox(); self.folds_spin.setRange(1,12); self.folds_spin.setValue(4)
        self.oos_frac_spin = QDoubleSpinBox(); self.oos_frac_spin.setRange(0.05,0.8); self.oos_frac_spin.setSingleStep(0.05); self.oos_frac_spin.setValue(0.2)
        self.min_trades_spin = QSpinBox(); self.min_trades_spin.setRange(0,10000); self.min_trades_spin.setValue(0)
        for lbl,w in [('Folds:',self.folds_spin),('OOS Fraction:',self.oos_frac_spin),('Min Trades:',self.min_trades_spin)]:
            left_l.addWidget(QLabel(lbl)); left_l.addWidget(w)
        left_l.addStretch()
        right = QGroupBox('הרצה'); right_l = QVBoxLayout(right)
        self.run_btn = QPushButton('הרץ Walk-Forward'); self.run_btn.setObjectName('primary_button'); self.run_btn.clicked.connect(self.run_walkforward)
        self.cancel_btn = QPushButton('ביטול'); self.cancel_btn.setObjectName('secondary_button'); self.cancel_btn.clicked.connect(self.cancel_walkforward); self.cancel_btn.setVisible(False)
        right_l.addWidget(self.run_btn); right_l.addWidget(self.cancel_btn); right_l.addStretch()
        settings_layout.addWidget(left); settings_layout.addWidget(right)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        self.results_table = QTableWidget(); self._setup_results_table()
        help_btn = QToolButton()
        try:
            help_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        except Exception:
            help_btn.setText('?')
        help_btn.setToolTip('עזרה - Walkforward')
        from ui.shared.help_viewer import show_markdown_dialog
        help_btn.clicked.connect(lambda: show_markdown_dialog(self,'docs/walkforward_tab.md','Walkforward Help'))
        layout.addLayout(settings_layout); layout.addWidget(help_btn); layout.addWidget(self.progress_bar); layout.addWidget(self.results_table,1)
        dl_layout = QHBoxLayout(); dl_layout.addStretch(); self.download_btn = QPushButton('הורד CSV'); self.download_btn.setObjectName('secondary_button'); self.download_btn.clicked.connect(self.download_results); dl_layout.addWidget(self.download_btn)
        layout.addLayout(dl_layout)

    def _setup_results_table(self):
        headers=['Symbol','Strategy','Fold','Train Start','Train End','Test Start','Test End','Sharpe','CAGR%','MaxDD%','WinRate%','Trades']
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)

    def run_walkforward(self):
        params={'folds': self.folds_spin.value(),'oos_frac': self.oos_frac_spin.value(),'min_trades': self.min_trades_spin.value()}
        self.run_walkforward_requested.emit(params)

    def start_walkforward_worker(self, params, data_map):
        if self.worker_thread and self.worker_thread.isRunning(): return
        self.worker_thread = WorkerThread('walkforward', params, data_map)
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.results_ready.connect(self.update_results)
        self.worker_thread.error_occurred.connect(self.show_error)
        self.show_progress(True); self.worker_thread.start()

    def cancel_walkforward(self):
        if self.worker_thread:
            self.worker_thread.cancel(); self.show_progress(False)

    def show_progress(self, show=True):
        self.progress_bar.setVisible(show); self.run_btn.setEnabled(not show); self.cancel_btn.setVisible(show)
        if show: self.progress_bar.setValue(0)

    def update_progress(self, v): self.progress_bar.setValue(v)

    def update_results(self, results):
        self.show_progress(False)
        self.results_table.setRowCount(len(results))
        for r,row in enumerate(results):
            keys=['symbol','strategy','fold','train_start','train_end','test_start','test_end','sharpe','cagr','max_dd','win_rate','trades']
            for c,k in enumerate(keys):
                val=row.get(k,'')
                if isinstance(val,(int,float)) and k not in ['fold','trades']:
                    txt=f"{val:.4f}" if k not in ['trades'] else str(val)
                else:
                    txt=str(val)
                item=QTableWidgetItem(txt)
                if k=='sharpe' and isinstance(val,(int,float)) and val>1.0:
                    item.setBackground(QColor(198,246,213))
                self.results_table.setItem(r,c,item)
        try:
            from run_repo.run_repository import save_run
            save_run('walkforward', {'folds': self.folds_spin.value(), 'oos_frac': self.oos_frac_spin.value()}, results, tags={'rows': len(results)})
        except Exception:
            pass

    def show_error(self,error):
        self.show_progress(False); QMessageBox.critical(self,'שגיאה',f'שגיאת Walk-Forward: {error}')

    def download_results(self):
        if self.results_table.rowCount()==0:
            QMessageBox.information(self,'מידע','אין תוצאות'); return
        fp,_=QFileDialog.getSaveFileName(self,'שמור קובץ','walkforward_results.csv','CSV Files (*.csv)')
        if not fp: return
        with open(fp,'w',encoding='utf-8') as f:
            headers=[self.results_table.horizontalHeaderItem(i).text() for i in range(self.results_table.columnCount())]
            f.write(','.join(headers)+'\n')
            for r in range(self.results_table.rowCount()):
                vals=[]
                for c in range(self.results_table.columnCount()):
                    it=self.results_table.item(r,c); vals.append(it.text() if it else '')
                f.write(','.join(vals)+'\n')
        QMessageBox.information(self,'הצלחה',f'נשמר: {fp}')
    # Help handled by shared utility
