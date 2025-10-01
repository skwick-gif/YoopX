from PySide6.QtWidgets import (QWidget,QHBoxLayout,QFrame,QVBoxLayout,QLabel,QDoubleSpinBox,QLineEdit,QPushButton,
                               QProgressBar,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,
                               QToolButton,QStyle)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from ui.worker_thread import WorkerThread

class BacktestTab(QWidget):
    run_backtest_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        settings_panel = QFrame(); settings_panel.setObjectName('card'); settings_panel.setMaximumWidth(300)
        settings_layout = QVBoxLayout(settings_panel)
        title = QLabel('הגדרות בק-טסט'); title.setObjectName('section_title')
        self.start_cash_spin = QDoubleSpinBox(); self.start_cash_spin.setRange(1000,1000000); self.start_cash_spin.setValue(10000); self.start_cash_spin.setSuffix(' $')
        self.commission_spin = QDoubleSpinBox(); self.commission_spin.setRange(0,0.01); self.commission_spin.setValue(0.0005); self.commission_spin.setDecimals(6)
        self.slippage_spin = QDoubleSpinBox(); self.slippage_spin.setRange(0,0.02); self.slippage_spin.setValue(0.0005); self.slippage_spin.setDecimals(6)
        self.symbols_edit = QLineEdit(); self.symbols_edit.setPlaceholderText('אופציונלי: AAPL,MSFT')
        self.run_backtest_btn = QPushButton('הרץ BACKTEST'); self.run_backtest_btn.setObjectName('primary_button'); self.run_backtest_btn.clicked.connect(self.run_backtest)
        self.cancel_btn = QPushButton('ביטול'); self.cancel_btn.setObjectName('secondary_button'); self.cancel_btn.clicked.connect(self.cancel_backtest); self.cancel_btn.setVisible(False)
        settings_layout.addWidget(title)
        for lbl,w in [('הון התחלתי:',self.start_cash_spin),('רשום טיקרים (אופציונלי):',self.symbols_edit),('עמלות:',self.commission_spin),('החלקה:',self.slippage_spin)]:
            settings_layout.addWidget(QLabel(lbl)); settings_layout.addWidget(w)
        settings_layout.addWidget(self.run_backtest_btn); settings_layout.addWidget(self.cancel_btn); settings_layout.addStretch()
        results_panel = QFrame(); results_panel.setObjectName('card'); results_layout = QVBoxLayout(results_panel)
        header = QHBoxLayout(); title2 = QLabel('תוצאות בק-טסט'); title2.setObjectName('section_title')
        help_btn = QToolButton()
        try:
            help_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        except Exception:
            help_btn.setText('?')
        help_btn.setToolTip('עזרה - Backtest')
        from ui.shared.help_viewer import show_markdown_dialog
        help_btn.clicked.connect(lambda: show_markdown_dialog(self,'docs/backtest_tab.md','Backtest Help'))
        self.download_btn = QPushButton('הורד CSV'); self.download_btn.setObjectName('secondary_button'); self.download_btn.clicked.connect(self.download_results)
        self.filter_btn = QPushButton('סינון'); self.filter_btn.setObjectName('secondary_button'); self.filter_btn.clicked.connect(self.show_filters)
        self.bench_summary_btn = QPushButton('Benchmark Summary'); self.bench_summary_btn.setObjectName('secondary_button'); self.bench_summary_btn.clicked.connect(self.export_benchmark_summary)
        header.addWidget(title2); header.addStretch(); header.addWidget(help_btn); header.addWidget(self.filter_btn); header.addWidget(self.bench_summary_btn); header.addWidget(self.download_btn)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        self.results_table = QTableWidget(); self._setup_results_table()
        results_layout.addLayout(header); results_layout.addWidget(self.progress_bar); results_layout.addWidget(self.results_table)
        main_layout.addWidget(settings_panel); main_layout.addWidget(results_panel,1)

    def _setup_results_table(self):
        headers = ["Symbol","Strategy","Final Value","Sharpe","Alpha","InfoRatio","Max DD%","Win Rate%","Trades","CAGR%","Benchmark","Show Chart","Passed Strategies"]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)

    def run_backtest(self):
        params = {'start_cash': self.start_cash_spin.value(),'commission': self.commission_spin.value(),'slippage': self.slippage_spin.value()}
        if self.symbols_edit.text().strip(): params['symbols'] = self.symbols_edit.text().strip()
        self.run_backtest_requested.emit(params)

    def start_backtest_worker(self, params, data_map):
        if self.worker_thread and self.worker_thread.isRunning(): return
        symbol_text = params.get('symbols') if params and isinstance(params,dict) and params.get('symbols') else self.symbols_edit.text()
        filtered_map = data_map
        if symbol_text and symbol_text.strip():
            requested = [s.strip().upper() for s in symbol_text.split(',') if s.strip()]
            filtered_map = {k:v for k,v in data_map.items() if k.upper() in requested}
            if not filtered_map:
                QMessageBox.warning(self,'אזהרה',f'לא נמצאו סמלים: {symbol_text}')
                return
        self.worker_thread = WorkerThread('backtest', params, filtered_map)
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.status_updated.connect(lambda s: None)
        self.worker_thread.results_ready.connect(self.update_results)
        self.worker_thread.error_occurred.connect(self.show_error)
        self.show_progress(True); self.worker_thread.start()
        try: self.worker_thread.finished.connect(lambda: self._on_worker_finished())
        except Exception: pass

    def cancel_backtest(self):
        if self.worker_thread:
            self.worker_thread.cancel(); self.worker_thread.quit(); self.worker_thread.wait(2000)
            self.show_progress(False)

    def show_progress(self, show=True):
        self.progress_bar.setVisible(show); self.run_backtest_btn.setEnabled(not show); self.cancel_btn.setVisible(show)
        if show: self.progress_bar.setValue(0)

    def update_progress(self, v): self.progress_bar.setValue(v)

    def update_results(self, results):
        self.show_progress(False)
        self.results_table.setRowCount(len(results))
        for row, result in enumerate(results):
            keys = ['symbol','strategy','final_value','sharpe','alpha','info_ratio','max_dd','win_rate','trades','cagr','benchmark','show_chart','passed_strategies']
            for col,key in enumerate(keys):
                val = result.get(key,'')
                item = QTableWidgetItem(str(val))
                if key == 'sharpe':
                    try:
                        if float(val) > 1.0: item.setBackground(QColor(198,246,213))
                    except Exception: pass
                if key == 'alpha':
                    try:
                        if float(val) > 0: item.setBackground(QColor(210,245,210))
                        elif float(val) < 0: item.setBackground(QColor(245,220,220))
                    except Exception: pass
                self.results_table.setItem(row,col,item)
        # Persist run (best effort)
        try:
            from run_repo.run_repository import save_run
            save_run('backtest', {}, results, tags={'rows': len(results)})
        except Exception:
            pass

    def show_error(self, error):
        self.show_progress(False); QMessageBox.critical(self,'שגיאה',f'שגיאה בבק-טסט: {error}')

    def _on_worker_finished(self):
        self.show_progress(False); self.worker_thread = None

    def download_results(self):
        if self.results_table.rowCount()==0:
            QMessageBox.information(self,'מידע','אין תוצאות להורדה'); return
        file_path,_ = QFileDialog.getSaveFileName(self,'שמור קובץ','backtest_results.csv','CSV Files (*.csv)')
        if file_path:
            with open(file_path,'w',encoding='utf-8') as f:
                headers=[self.results_table.horizontalHeaderItem(c).text() for c in range(self.results_table.columnCount())]
                f.write(','.join(headers)+'\n')
                for r in range(self.results_table.rowCount()):
                    row_data=[]
                    for c in range(self.results_table.columnCount()):
                        it=self.results_table.item(r,c); row_data.append(it.text() if it else '')
                    f.write(','.join(row_data)+'\n')
            QMessageBox.information(self,'הצלחה',f'הקובץ נשמר: {file_path}')

    def export_benchmark_summary(self):
        if self.results_table.rowCount()==0:
            QMessageBox.information(self,'מידע','אין תוצאות'); return
        # aggregate alpha/info ratio
        alphas = []
        infos = []
        bench_syms = set()
        for r in range(self.results_table.rowCount()):
            def _val(col_name):
                for c in range(self.results_table.columnCount()):
                    if self.results_table.horizontalHeaderItem(c).text().lower()==col_name:
                        it=self.results_table.item(r,c); return it.text() if it else ''
                return ''
            try:
                a = float(_val('alpha'))
                alphas.append(a)
            except Exception:
                pass
            try:
                ir = float(_val('inforatio'))
                infos.append(ir)
            except Exception:
                pass
            bench_syms.add(_val('benchmark'))
        if not alphas and not infos:
            QMessageBox.information(self,'מידע','אין מדדי Benchmark זמינים'); return
        avg_alpha = sum(alphas)/len(alphas) if alphas else None
        avg_ir = sum(infos)/len(infos) if infos else None
        msg = 'Benchmark Summary:\n'
        if avg_alpha is not None: msg += f"Avg Alpha: {avg_alpha:.4f}\n"
        if avg_ir is not None: msg += f"Avg Info Ratio: {avg_ir:.4f}\n"
        msg += f"Benchmarks: {', '.join([b for b in bench_syms if b]) or '—'}"
        QMessageBox.information(self,'Benchmark', msg)

    def show_filters(self):
        QMessageBox.information(self,'מידע','מסך סינון טרם הופרד מהקובץ המקורי')

    def apply_shared_params(self, params: dict):
        # Placeholder to receive shared params later
        pass

    # The unified main_content may call these legacy interface helpers; provide safe stubs.
    def set_strategy_params(self, params: dict):
        # No-op placeholder; extended backtest UI not yet ported.
        pass

    def start_backtest_worker(self, params, data_map):
        # Reuse existing run_backtest logic but with passed params
        try:
            self.run_backtest_requested.emit(params or {})
        except Exception:
            pass

    # Per-tab help removed (using shared help_viewer.show_markdown_dialog)
