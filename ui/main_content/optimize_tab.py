# ...existing imports...

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit, QSpinBox, QComboBox, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog, QLineEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from ui.main_content.dialogs.data_config_dialog import DataConfigDialog
from ui.main_content.dialogs.strategy_config_dialog import StrategyConfigDialog

class OptimizeTab(QWidget):
	run_optimize_requested = Signal(dict)
    
	def __init__(self):
		super().__init__()
		self.setup_ui()
		self.worker_thread = None
        
	def setup_ui(self):
		layout = QVBoxLayout(self)
		settings_layout = QHBoxLayout()
		left_settings = QGroupBox("הגדרות אופטימיזציה")
		left_layout = QVBoxLayout(left_settings)
		self.ranges_edit = QTextEdit()
		self.ranges_edit.setMaximumHeight(160)
		self.ranges_edit.setPlainText('{\n  "fast": [8, 20, 4],\n  "slow": [20, 40, 4]\n}')
		self.universe_limit_spin = QSpinBox()
		self.universe_limit_spin.setRange(0, 10000)
		self.universe_limit_spin.setValue(50)
		self.folds_spin = QSpinBox()
		self.folds_spin.setRange(1, 10)
		self.folds_spin.setValue(3)
		left_layout.addWidget(QLabel("Parameter Ranges (JSON):"))
		left_layout.addWidget(self.ranges_edit)

		# checkpoint file chooser
		cp_layout = QHBoxLayout()
		self.checkpoint_edit = QLineEdit()
		self.checkpoint_edit.setPlaceholderText('Optional checkpoint file (e.g. ./opt_checkpoint.csv)')
		# Explain checkpoint behavior: file is appended as combos complete and used to resume later
		self.checkpoint_edit.setToolTip('Optional checkpoint CSV file. Results are appended as each combo completes so runs can be resumed later (file will be created if missing).')
		cp_browse = QPushButton('Browse...')
		def _browse_cp():
			p, _ = QFileDialog.getSaveFileName(self, 'Checkpoint file', 'opt_checkpoint.csv', 'CSV Files (*.csv)')
			if p:
				self.checkpoint_edit.setText(p)
		cp_browse.clicked.connect(_browse_cp)
		cp_browse.setToolTip('Choose a checkpoint CSV file (will be created/appended).')
		cp_layout.addWidget(QLabel('Checkpoint:'))
		cp_layout.addWidget(self.checkpoint_edit)
		cp_layout.addWidget(cp_browse)
		left_layout.addLayout(cp_layout)
		left_layout.addWidget(QLabel("Universe limit:"))
		left_layout.addWidget(self.universe_limit_spin)
		left_layout.addWidget(QLabel("Folds:"))
		left_layout.addWidget(self.folds_spin)
		right_settings = QGroupBox("יעד אופטימיזציה")
		right_layout = QVBoxLayout(right_settings)
		self.objective_combo = QComboBox()
		self.objective_combo.addItems(["Sharpe", "CAGR", "Return/DD", "WinRate", "Trades"])
		self.max_results_spin = QSpinBox()
		self.max_results_spin.setRange(1, 200)
		self.max_results_spin.setValue(50)
		self.run_optimize_btn = QPushButton("הרץ OPTIMIZE")
		self.run_optimize_btn.setObjectName("primary_button")
		self.run_optimize_btn.clicked.connect(self.run_optimize)
		self.cfg_data_btn = QPushButton('Configure Data')
		self.cfg_data_btn.setObjectName('secondary_button')
		self.cfg_data_btn.clicked.connect(self.open_data_config)
		self.cfg_strategy_btn = QPushButton('Configure Strategy')
		self.cfg_strategy_btn.setObjectName('secondary_button')
		self.cfg_strategy_btn.clicked.connect(self.open_strategy_config)
		self.cancel_btn = QPushButton("ביטול")
		self.cancel_btn.setObjectName("secondary_button")
		self.cancel_btn.clicked.connect(self.cancel_optimize)
		self.cancel_btn.setVisible(False)
		right_layout.addWidget(QLabel("Objective:"))
		right_layout.addWidget(self.objective_combo)
		right_layout.addWidget(QLabel("Show top:"))
		right_layout.addWidget(self.max_results_spin)
		right_layout.addWidget(self.run_optimize_btn)
		right_layout.addWidget(self.cfg_data_btn)
		right_layout.addWidget(self.cfg_strategy_btn)
		right_layout.addWidget(self.cancel_btn)
		right_layout.addStretch()
		settings_layout.addWidget(left_settings)
		settings_layout.addWidget(right_settings)
		self.progress_bar = QProgressBar()
		self.progress_bar.setVisible(False)
		self.results_table = QTableWidget()
		self.setup_results_table()
		download_layout = QHBoxLayout()
		download_layout.addStretch()
		self.download_btn = QPushButton("הורד CSV")
		self.download_btn.setObjectName("secondary_button")
		self.download_btn.clicked.connect(self.download_results)
		download_layout.addWidget(self.download_btn)
		layout.addLayout(settings_layout)
		layout.addWidget(self.progress_bar)
		layout.addWidget(self.results_table, 1)
		layout.addLayout(download_layout)

	def setup_results_table(self):
		headers = ["Rank", "Params", "Score", "Sharpe", "CAGR%", "MaxDD%", "WinRate%", "Trades", "Universe", "Folds"]
		self.results_table.setColumnCount(len(headers))
		self.results_table.setHorizontalHeaderLabels(headers)
		header = self.results_table.horizontalHeader()
		header.setStretchLastSection(True)

	def run_optimize(self):
		params = {
			'ranges_json': self.ranges_edit.toPlainText(),
			'universe_limit': self.universe_limit_spin.value(),
			'folds': self.folds_spin.value(),
			'objective': self.objective_combo.currentText(),
			'max_results': self.max_results_spin.value()
		}
		# include checkpoint path if set
		cp = self.checkpoint_edit.text().strip() if hasattr(self, 'checkpoint_edit') else ''
		if cp:
			params['checkpoint'] = cp
		self.run_optimize_requested.emit(params)

	def start_optimize_worker(self, params, data_map):
		# guard: don't start if already running
		if self.worker_thread and getattr(self.worker_thread, 'isRunning', lambda: False)():
			return
		# lazy import to avoid import-time Qt dependency issues
		try:
			from ui.main_content.worker_thread import WorkerThread
		except Exception:
			# fallback to relative import if executed as a package
			from .worker_thread import WorkerThread

		self.worker_thread = WorkerThread('optimize', params, data_map)
		# wire signals
		self.worker_thread.progress_updated.connect(self.update_progress)
		self.worker_thread.status_updated.connect(self.update_status)
		self.worker_thread.results_ready.connect(self.update_results)
		self.worker_thread.error_occurred.connect(self.show_error)
		# when finished, ensure thread is cleaned up
		self.worker_thread.finished_work.connect(self._on_worker_finished)

		self.show_progress(True)
		self.worker_thread.start()

	def cancel_optimize(self):
		# request cancellation and wait for thread to finish
		if self.worker_thread:
			try:
				self.worker_thread.cancel()
				# do not block UI thread indefinitely; wait briefly
				self.worker_thread.wait(2000)
			except Exception:
				pass
			# hide progress immediately; final cleanup occurs on finished signal
			self.show_progress(False)
			self.worker_thread = None
			
		else:
			self.show_progress(False)
			

	def _on_worker_finished(self):
		# Called from the worker thread context when finished_work emitted.
		# Ensure we join the thread and reset state on the main thread.
		try:
			wt = self.worker_thread
			if wt is not None:
				# if the thread is still running, attempt a graceful quit/wait
				try:
					wt.quit()
				except Exception:
					pass
				try:
					wt.wait(2000)
				except Exception:
					pass
				self.worker_thread = None
		finally:
			# ensure UI reflects idle state
			self.show_progress(False)

	def show_progress(self, show=True):
		self.progress_bar.setVisible(show)
		self.run_optimize_btn.setEnabled(not show)
		self.cancel_btn.setVisible(show)
		if show:
			self.progress_bar.setValue(0)

	def update_progress(self, value):
		self.progress_bar.setValue(value)

	def update_status(self, status):
		# set status if available
		try:
			self.status_label.setText(status)
		except Exception:
			return

	def update_results(self, results):
		self.show_progress(False)
		self.results_table.setRowCount(len(results))
		# ...existing code for populating results...
		# populate rows if needed (basic fallback)
		for row, result in enumerate(results):
			keys = ['rank', 'params', 'score', 'sharpe', 'cagr', 'max_dd', 'win_rate', 'trades', 'universe', 'folds']
			for col, key in enumerate(keys):
				value = result.get(key, '')
				if key == 'params':
					text = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
				elif isinstance(value, (int, float)) and key not in ['rank', 'trades', 'universe', 'folds']:
					text = f"{value:.3f}"
				else:
					text = str(value)
				item = QTableWidgetItem(text)
				self.results_table.setItem(row, col, item)

	def show_error(self, error):
		self.show_progress(False)
		QMessageBox.critical(self, "שגיאה", f"שגיאה באופטימיזציה: {error}")

	def download_results(self):
		if self.results_table.rowCount() == 0:
			QMessageBox.information(self, "מידע", "אין תוצאות להורדה")
			return
		file_path, _ = QFileDialog.getSaveFileName(self, "שמור קובץ", "optimize_results.csv", "CSV Files (*.csv)")
		if file_path:
			with open(file_path, 'w', encoding='utf-8') as f:
				headers = []
				for col in range(self.results_table.columnCount()):
					headers.append(self.results_table.horizontalHeaderItem(col).text())
				f.write(','.join(headers) + '\n')
				for row in range(self.results_table.rowCount()):
					row_data = []
					for col in range(self.results_table.columnCount()):
						item = self.results_table.item(row, col)
						row_data.append(item.text() if item else '')
					f.write(','.join(row_data) + '\n')
			QMessageBox.information(self, "הצלחה", f"הקובץ נשמר בהצלחה: {file_path}")

	def open_data_config(self):
		dlg = DataConfigDialog(self)
		if dlg.exec():
			p = dlg.path_edit.text().strip()
			if p:
				main = self.parentWidget().parentWidget()
				if main and hasattr(main, 'on_load_data'):
					main.on_load_data({'path': p})

	def open_strategy_config(self):
		dlg = StrategyConfigDialog(self)
		if dlg.exec():
			try:
				self._last_strategy_params = getattr(dlg, 'parsed_params', None) or {}
			except Exception:
				self._last_strategy_params = {}
# OptimizeTab UI and logic

