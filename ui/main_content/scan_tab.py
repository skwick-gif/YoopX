# ...existing imports...

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFrame, QVBoxLayout, QLabel, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

class ScanTab(QWidget):
	run_scan_requested = Signal(dict)
	settings_changed = Signal(dict)
    
	def __init__(self):
		super().__init__()
		self.setup_ui()
		self.worker_thread = None
        
	def setup_ui(self):
		main_layout = QHBoxLayout(self)
		# ...existing code for ScanTab setup_ui...
		# Left panel - Settings
		settings_panel = QFrame()
		settings_panel.setObjectName("card")
		settings_panel.setMaximumWidth(300)
		settings_layout = QVBoxLayout(settings_panel)
		settings_title = QLabel("הגדרות סריקה")
		settings_title.setObjectName("section_title")
		self.patterns_edit = QTextEdit()
		self.patterns_edit.setMaximumHeight(80)
		self.patterns_edit.setPlaceholderText("ENGULFING,DOJI,HAMMER...")
		self.lookback_spin = QSpinBox()
		self.lookback_spin.setRange(5, 200)
		self.lookback_spin.setValue(30)
		self.rr_target_combo = QComboBox()
		self.rr_target_combo.addItems(["2xATR", "Boll mid", "Donchian high"])
		self.min_rr_spin = QDoubleSpinBox()
		self.min_rr_spin.setRange(0.0, 10.0)
		self.min_rr_spin.setSingleStep(0.1)
		self.run_scan_btn = QPushButton("הרץ SCAN")
		self.run_scan_btn.setObjectName("primary_button")
		self.run_scan_btn.clicked.connect(self.run_scan)
		self.cancel_btn = QPushButton("ביטול")
		self.cancel_btn.setObjectName("secondary_button")
		self.cancel_btn.clicked.connect(self.cancel_scan)
		self.cancel_btn.setVisible(False)
		self.status_label = QLabel("")
		self.status_label.setObjectName("status_info")
		settings_layout.addWidget(settings_title)
		settings_layout.addWidget(QLabel("דפוסי נרות:"))
		settings_layout.addWidget(self.patterns_edit)
		settings_layout.addWidget(QLabel("Lookback (ימים):"))
		settings_layout.addWidget(self.lookback_spin)
		settings_layout.addWidget(QLabel("RR Target:"))
		settings_layout.addWidget(self.rr_target_combo)
		settings_layout.addWidget(QLabel("Min R:R:"))
		settings_layout.addWidget(self.min_rr_spin)
		settings_layout.addWidget(self.run_scan_btn)
		settings_layout.addWidget(self.cancel_btn)
		settings_layout.addWidget(self.status_label)
		settings_layout.addStretch()
		# Right panel - Results
		results_panel = QFrame()
		results_panel.setObjectName("card")
		results_layout = QVBoxLayout(results_panel)
		# create the stop and download buttons so they exist when the header is built
		self.stop_btn = QPushButton("עצור")
		self.stop_btn.setObjectName('secondary_button')
		self.stop_btn.clicked.connect(self.cancel_scan)
		self.stop_btn.setEnabled(False)
		self.download_btn = QPushButton("הורד CSV")
		self.download_btn.setObjectName("secondary_button")
		self.download_btn.clicked.connect(self.download_results)
		# Settings button opens a dialog so the left settings panel can be removed later
		self.settings_btn = QPushButton("הגדרות / Settings")
		self.settings_btn.setObjectName("secondary_button")
		self.settings_btn.clicked.connect(self.open_settings_dialog)
		# make sure the button is visible and easy to find (match Backtest)
		try:
			self.settings_btn.setVisible(True)
			self.settings_btn.setFixedWidth(160)
			self.settings_btn.setToolTip('פתח הגדרות Backtest / Open Backtest Settings')
			self.settings_btn.setStyleSheet('font-weight:600; padding:6px;')
		except Exception:
			pass
		results_header = QHBoxLayout()
		results_title = QLabel("תוצאות סריקה")
		results_title.setObjectName("section_title")
		# move important actions to the top header so the settings card can be removed
		# Settings and Run buttons are added here so they're always visible while expanding the results area.
		results_header.addWidget(results_title)
		results_header.addStretch()
		# add Settings and Run buttons to the header
		try:
			results_header.addWidget(self.settings_btn)
		except Exception:
			pass
		try:
			results_header.addWidget(self.run_scan_btn)
		except Exception:
			pass
		# stop button (visible) so the user can cancel a running job
		try:
			results_header.addWidget(self.stop_btn)
		except Exception:
			pass
		# download button
		results_header.addWidget(self.download_btn)
		# progress bar and small header status handled below
		self.progress_bar = QProgressBar()
		self.progress_bar.setVisible(False)
		self.results_table = QTableWidget()
		self.setup_results_table()
		results_layout.addLayout(results_header)
		# add a small top toolbar to make settings button extra prominent (same as Backtest)
		try:
			toolbar = QHBoxLayout()
			toolbar.addStretch()
			results_layout.insertLayout(0, toolbar)
		except Exception:
			pass
		results_layout.addWidget(self.progress_bar)
		results_layout.addWidget(self.results_table)
		# Keep settings_panel around for now but hide it — settings are edited via dialog
		settings_panel.setVisible(False)
		main_layout.addWidget(settings_panel)
		main_layout.addWidget(results_panel, 1)

	def open_settings_dialog(self):
		# Reuse the Backtest settings dialog so Scan can edit shared params
		from ui.main_content.dialogs.backtest_settings_dialog import BacktestSettingsDialog
		# Gather current values from the (hidden) left panel as defaults for scan-specific defaults
		current = {
			'symbols': '',
			'universe_limit': 0,
			'min_trades': 0,
			'start_date': '',
			'end_date': '',
			'use_adj': True,
			'min_volume': 0,
			'min_close': 0,
			'start_cash': 10000,
			'commission': 0.0005,
			'slippage': 0.0005,
			'strategies': []
		}
		dlg = BacktestSettingsDialog(self)
		dlg.set_values(current)
		if dlg.exec():
			try:
				vals = dlg.get_values()
				# Emit settings_changed so MainContent can store shared params
				try:
					self.settings_changed.emit(vals)
				except Exception:
					pass
			except Exception:
				pass

	def setup_results_table(self):
		headers = ["Symbol", "Pass", "Signal NOW", "Signal Age", "Price", "R:R", "Patterns"]
		self.results_table.setColumnCount(len(headers))
		self.results_table.setHorizontalHeaderLabels(headers)
		header = self.results_table.horizontalHeader()
		header.setStretchLastSection(True)

	def run_scan(self):
		params = {
			'patterns': self.patterns_edit.toPlainText(),
			'lookback': self.lookback_spin.value(),
			'rr_target': self.rr_target_combo.currentText(),
			'min_rr': self.min_rr_spin.value()
		}
		# show progress UI and enable stop button
		self.show_progress(True)
		try:
			self.stop_btn.setEnabled(True)
		except Exception:
			pass
		self.run_scan_requested.emit(params)

	def start_scan_worker(self, params, data_map):
		from ui.main_content.worker_thread import WorkerThread
		if self.worker_thread and self.worker_thread.isRunning():
			return
		self.worker_thread = WorkerThread("scan", params, data_map)
		self.worker_thread.progress_updated.connect(self.update_progress)
		self.worker_thread.status_updated.connect(self.update_status)
		self.worker_thread.results_ready.connect(self.update_results)
		self.worker_thread.error_occurred.connect(self.show_error)
		self.show_progress(True)
		self.worker_thread.start()
		try:
			self.stop_btn.setEnabled(True)
		except Exception:
			pass

	def cancel_scan(self):
		if self.worker_thread:
			self.worker_thread.cancel()
			self.show_progress(False)
			try:
				self.stop_btn.setEnabled(False)
			except Exception:
				pass
		else:
			# ensure UI reset even if no worker
			self.show_progress(False)
	def show_progress(self, show=True):
		self.progress_bar.setVisible(show)
		self.run_scan_btn.setEnabled(not show)
		self.cancel_btn.setVisible(show)
		if show:
			self.progress_bar.setValue(0)

	def update_progress(self, value):
		self.progress_bar.setValue(value)

	def update_status(self, status):
		self.status_label.setText(status)

	def update_results(self, results):
		self.show_progress(False)
		self.status_label.setText(f"נמצאו {len(results)} תוצאות")
		self.results_table.setRowCount(len(results))
		for row, result in enumerate(results):
			for col, key in enumerate(['symbol', 'pass', 'signal', 'age', 'price', 'rr', 'patterns']):
				item = QTableWidgetItem(str(result.get(key, '')))
				if key == 'pass':
					if result.get(key) == 'Pass':
						item.setBackground(QColor(198, 246, 213))
					elif result.get(key) == 'Fail':
						item.setBackground(QColor(254, 215, 215))
				self.results_table.setItem(row, col, item)

	def show_error(self, error):
		self.show_progress(False)
		QMessageBox.critical(self, "שגיאה", f"שגיאה בסריקה: {error}")

	def download_results(self):
		if self.results_table.rowCount() == 0:
			QMessageBox.information(self, "מידע", "אין תוצאות להורדה")
			return
		file_path, _ = QFileDialog.getSaveFileName(self, "שמור קובץ", "scan_results.csv", "CSV Files (*.csv)")
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
# ScanTab UI and logic

