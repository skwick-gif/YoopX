# ...existing imports...

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFrame, QVBoxLayout, QLabel, QDoubleSpinBox, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog, QSpinBox, QLineEdit, QDateEdit, QCheckBox, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from ui.main_content.dialogs.data_config_dialog import DataConfigDialog
from ui.main_content.dialogs.strategy_config_dialog import StrategyConfigDialog
from ui.main_content.dialogs.backtest_settings_dialog import BacktestSettingsDialog

class BacktestTab(QWidget):
	run_backtest_requested = Signal(dict)
    
	def __init__(self):
		super().__init__()
		self._last_strategy_params = {}
		self.setup_ui()
		self.worker_thread = None
        
	def setup_ui(self):
		main_layout = QHBoxLayout(self)
		# Settings panel (create but hide it; controls moved into the results header)
		settings_panel = QFrame()
		# keep a reference so Qt doesn't delete child widgets when the local variable goes out of scope
		self.settings_panel = settings_panel
		settings_panel.setObjectName("card")
		settings_panel.setMaximumWidth(380)
		settings_panel.setMinimumWidth(300)
		settings_panel_layout = QVBoxLayout(settings_panel)
		settings_panel_layout.setContentsMargins(8,8,8,8)
		settings_panel_layout.setSpacing(6)
		settings_title = QLabel("הגדרות בק-טסט")
		settings_title.setObjectName("section_title")
		# emphasize header visually
		try:
			settings_title.setStyleSheet('font-weight:600; font-size:12px;')
		except Exception:
			pass
		settings_panel_layout.addWidget(settings_title)

		# Scroll area for form fields so buttons stay accessible at bottom
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.NoFrame)
		form_container = QWidget()
		form_layout = QVBoxLayout(form_container)
		form_layout.setContentsMargins(0,0,0,0)
		form_layout.setSpacing(8)
		self.start_cash_spin = QDoubleSpinBox()
		self.start_cash_spin.setRange(1000, 1000000)
		self.start_cash_spin.setValue(10000)
		self.start_cash_spin.setSuffix(" $")
		self.commission_spin = QDoubleSpinBox()
		self.commission_spin.setRange(0, 0.01)
		self.commission_spin.setValue(0.0005)
		self.commission_spin.setDecimals(6)
		self.slippage_spin = QDoubleSpinBox()
		self.slippage_spin.setRange(0, 0.02)
		self.slippage_spin.setValue(0.0005)
		self.slippage_spin.setDecimals(6)
		# ----- Filters (local to Backtest Tab) -----
		# Symbols (optional, comma-separated)
		self.symbols_edit = QLineEdit()
		self.symbols_edit.setPlaceholderText("אופציונלי: רשום טיקרים, מופרדים בפסיק (AAPL,MSFT)")
		# Universe limit (0 = no limit)
		self.universe_limit_spin = QSpinBox()
		self.universe_limit_spin.setRange(0, 10000)
		self.universe_limit_spin.setValue(0)
		# Minimum trades filter
		self.min_trades_spin = QSpinBox()
		self.min_trades_spin.setRange(0, 10000)
		self.min_trades_spin.setValue(0)
		# Date range
		self.start_date_edit = QDateEdit()
		self.start_date_edit.setCalendarPopup(True)
		self.start_date_edit.setDisplayFormat('yyyy-MM-dd')
		self.end_date_edit = QDateEdit()
		self.end_date_edit.setCalendarPopup(True)
		self.end_date_edit.setDisplayFormat('yyyy-MM-dd')
		# Use adjusted close
		self.use_adj_check = QCheckBox('Use adjusted close (if available)')
		self.use_adj_check.setChecked(True)
		# Optional minimum filters
		self.min_volume_spin = QDoubleSpinBox()
		self.min_volume_spin.setRange(0, 1e12)
		self.min_volume_spin.setValue(0)
		self.min_close_spin = QDoubleSpinBox()
		self.min_close_spin.setRange(0, 1e9)
		self.min_close_spin.setValue(0)
		self.run_backtest_btn = QPushButton("הרץ BACKTEST")
		self.run_backtest_btn.setObjectName("primary_button")
		self.run_backtest_btn.clicked.connect(self.run_backtest)
		# small config buttons
		self.cfg_data_btn = QPushButton('Configure Data')
		self.cfg_data_btn.setObjectName('secondary_button')
		self.cfg_data_btn.clicked.connect(self.open_data_config)
		# Replace the old JSON editor Configure Strategy with a unified Settings dialog
		self.settings_btn = QPushButton('Settings')
		self.settings_btn.setObjectName('secondary_button')
		self.settings_btn.clicked.connect(self.open_settings_dialog)
		self.cancel_btn = QPushButton("ביטול")
		self.cancel_btn.setObjectName("secondary_button")
		self.cancel_btn.clicked.connect(self.cancel_backtest)
		self.cancel_btn.setVisible(False)
		# visible Stop button in the results header to allow cancelling a running backtest
		self.stop_btn = QPushButton("עצור")
		self.stop_btn.setObjectName('secondary_button')
		self.stop_btn.clicked.connect(self.cancel_backtest)
		# disabled by default until a run is active
		self.stop_btn.setEnabled(False)
		# header already added to settings_panel_layout

		# Make form inputs slightly taller so values are easier to read on high-DPI
		def _set_tall(w):
			try:
				# slightly taller for readability
				w.setMinimumHeight(36)
			except Exception:
				pass

		# Filters group (top-down) - use form_layout (inside scroll)
		# Filters group (top-down) - use form_layout (inside scroll)
		# build form into the scrollable container so it can shrink without hiding buttons
		form_layout.addWidget(QLabel("רשום טיקרים (אופציונלי):"))
		form_layout.addWidget(self.symbols_edit)
		_set_tall(self.symbols_edit)
		# ensure the edit expands horizontally and is tall enough
		try:
			self.symbols_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		except Exception:
			pass
		form_layout.addWidget(QLabel("מגבלת יקום (0 = אין הגבלה):"))
		form_layout.addWidget(self.universe_limit_spin)
		_set_tall(self.universe_limit_spin)
		try:
			self.universe_limit_spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		except Exception:
			pass
		form_layout.addWidget(QLabel("מינימום עסקאות (0 = אין סינון):"))
		form_layout.addWidget(self.min_trades_spin)
		_set_tall(self.min_trades_spin)
		try:
			self.min_trades_spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		except Exception:
			pass
		form_layout.addWidget(QLabel("טווח תאריכים - התחלה: "))
		form_layout.addWidget(self.start_date_edit)
		_set_tall(self.start_date_edit)
		form_layout.addWidget(QLabel("טווח תאריכים - סוף: "))
		form_layout.addWidget(self.end_date_edit)
		_set_tall(self.end_date_edit)
		try:
			self.start_date_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
			self.end_date_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		except Exception:
			pass
		form_layout.addWidget(self.use_adj_check)
		form_layout.addWidget(QLabel("מינימום נפח ממוצע (0 = אין סינון):"))
		form_layout.addWidget(self.min_volume_spin)
		_set_tall(self.min_volume_spin)
		form_layout.addWidget(QLabel("מינימום מחיר סגירה (0 = אין סינון):"))
		form_layout.addWidget(self.min_close_spin)
		_set_tall(self.min_close_spin)
		# financial params
		form_layout.addWidget(QLabel("הון התחלתי:"))
		form_layout.addWidget(self.start_cash_spin)
		_set_tall(self.start_cash_spin)
		form_layout.addWidget(QLabel("עמלות:"))
		form_layout.addWidget(self.commission_spin)
		_set_tall(self.commission_spin)
		form_layout.addWidget(QLabel("החלקה:"))
		form_layout.addWidget(self.slippage_spin)
		_set_tall(self.slippage_spin)
		form_layout.addStretch()

		scroll.setWidget(form_container)
		settings_panel_layout.addWidget(scroll)
		# hide the left settings card to free up UI space — controls are available in the header
		try:
			self.settings_panel.hide()
		except Exception:
			pass

		# Buttons at bottom in a horizontal bar so they remain visible and clear
		btn_bar = QHBoxLayout()
		btn_bar.setSpacing(8)
		btn_bar.addWidget(self.run_backtest_btn)
		btn_bar.addWidget(self.cfg_data_btn)
		btn_bar.addWidget(self.settings_btn)
		btn_bar.addStretch()
		btn_bar.addWidget(self.cancel_btn)
		# keep the stop button tall and available in the header (we add it to the header later)
		_set_tall(self.stop_btn)
		# make buttons easy to click
		_set_tall(self.run_backtest_btn)
		_set_tall(self.cfg_data_btn)
		_set_tall(self.settings_btn)
		_set_tall(self.cancel_btn)
		settings_panel_layout.addLayout(btn_bar)

		# Results panel (define before using it)
		results_panel = QFrame()
		results_panel.setObjectName("card")
		results_layout = QVBoxLayout(results_panel)
		results_header = QHBoxLayout()
		results_title = QLabel("תוצאות בק-טסט")
		results_title.setObjectName("section_title")
		# move important actions to the top header so the settings card can be removed
		# Settings and Run Backtest buttons were created above; add them here so they're
		# always visible while expanding the results area.
		results_header.addWidget(results_title)
		results_header.addStretch()
		# add Settings and Run buttons to the header
		try:
			results_header.addWidget(self.settings_btn)
		except Exception:
			pass
		try:
			results_header.addWidget(self.run_backtest_btn)
		except Exception:
			pass
		# stop button (visible) so the user can cancel a running job
		try:
			results_header.addWidget(self.stop_btn)
		except Exception:
			pass
		self.download_btn = QPushButton("הורד CSV")
		self.download_btn.setObjectName("secondary_button")
		self.download_btn.clicked.connect(self.download_results)
		results_header.addWidget(self.download_btn)
		self.progress_bar = QProgressBar()
		self.progress_bar.setVisible(False)
		self.results_table = QTableWidget()
		self.setup_results_table()
		results_layout.addLayout(results_header)
		results_layout.addWidget(self.progress_bar)
		results_layout.addWidget(self.results_table)
		# Trades detail area
		from PySide6.QtWidgets import QTableWidget
		self.trades_table = QTableWidget()
		self.trades_table.setColumnCount(10)
		self.trades_table.setHorizontalHeaderLabels(['Entry Date','Exit Date','Hold Days','Entry','Exit','Size','Profit','Profit %','Return %','Cum PnL'])
		self.trades_table.setObjectName('trades_table')
		self.trades_table.setVisible(True)
		results_layout.addWidget(self.trades_table)
		# export trades button
		from PySide6.QtWidgets import QPushButton
		self.export_trades_btn = QPushButton('ייצוא עסקאות')
		self.export_trades_btn.setObjectName('secondary_button')
		self.export_trades_btn.clicked.connect(self.export_trades)
		results_layout.addWidget(self.export_trades_btn)
		# Strategy comparison section (collapsed style stacked after trades)
		from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QDoubleSpinBox
		self.strategy_comp_frame = QFrame()
		self.strategy_comp_frame.setObjectName('card')
		comp_layout = QVBoxLayout(self.strategy_comp_frame)
		comp_header_layout = QHBoxLayout()
		comp_title = QLabel('השוואת אסטרטגיות')
		comp_title.setObjectName('section_subtitle')
		comp_header_layout.addWidget(comp_title)
		comp_header_layout.addStretch()
		self.refresh_comp_btn = QPushButton('רענן השוואה')
		self.refresh_comp_btn.clicked.connect(self._recompute_strategy_comparison)
		comp_header_layout.addWidget(self.refresh_comp_btn)
		self.export_comp_btn = QPushButton('ייצוא השוואה')
		self.export_comp_btn.clicked.connect(self.export_strategy_comparison)
		comp_header_layout.addWidget(self.export_comp_btn)
		self.comp_chart_btn = QPushButton('תרשים Sharpe')
		self.comp_chart_btn.clicked.connect(self.show_strategy_sharpe_chart)
		comp_header_layout.addWidget(self.comp_chart_btn)
		comp_layout.addLayout(comp_header_layout)
		from PySide6.QtWidgets import QTableWidget
		# threshold spin for Sharpe pass filter
		th_layout = QHBoxLayout()
		th_label = QLabel('סף Sharpe:')
		self.comp_sharpe_thresh = QDoubleSpinBox()
		self.comp_sharpe_thresh.setDecimals(2)
		self.comp_sharpe_thresh.setRange(-5.0, 20.0)
		self.comp_sharpe_thresh.setValue(0.5)
		self.comp_sharpe_thresh.valueChanged.connect(self._recompute_strategy_comparison)
		th_layout.addWidget(th_label)
		th_layout.addWidget(self.comp_sharpe_thresh)
		th_layout.addStretch()
		comp_layout.addLayout(th_layout)
		self.strategy_table = QTableWidget()
		self.strategy_table.setColumnCount(10)
		self.strategy_table.setHorizontalHeaderLabels(['Rank','Strategy','Avg Sharpe','Avg CAGR%','Median MaxDD%','Avg WinRate%','Total Trades','Symbols','Pass Rate%','Pass Count'])
		comp_layout.addWidget(self.strategy_table)
		results_layout.addWidget(self.strategy_comp_frame)
		# Do not add the left settings panel to the main layout; the controls were moved
		# into the results header to free up space for results.
		main_layout.addWidget(results_panel, 1)

	def setup_results_table(self):
		headers = ["Symbol", "Strategy", "Final Value", "Sharpe", "Max DD%", "Win Rate%", "Trades", "CAGR%", "Show Chart", "Passed Strategies", "Error"]
		self.results_table.setColumnCount(len(headers))
		self.results_table.setHorizontalHeaderLabels(headers)

	def run_backtest(self):
		# decide whether to include dates based on last saved settings from the dialog
		start_date = ''
		end_date = ''
		try:
			if getattr(self, '_last_settings', {}).get('start_date_enabled', False):
				start_date = self.start_date_edit.date().toString('yyyy-MM-dd')
			else:
				start_date = ''
		except Exception:
			start_date = ''
		try:
			if getattr(self, '_last_settings', {}).get('end_date_enabled', False):
				end_date = self.end_date_edit.date().toString('yyyy-MM-dd')
			else:
				end_date = ''
		except Exception:
			end_date = ''
		params = {
			'start_cash': self.start_cash_spin.value(),
			'commission': self.commission_spin.value(),
			'slippage': self.slippage_spin.value(),
			'universe_limit': int(self.universe_limit_spin.value()),
			'symbols': self.symbols_edit.text(),
			'min_trades': int(self.min_trades_spin.value()),
			'start_date': start_date,
			'end_date': end_date,
			'use_adj': bool(self.use_adj_check.isChecked()),
			'min_volume': float(self.min_volume_spin.value()),
			'min_close': float(self.min_close_spin.value())
		}
		# include selected strategies list if available
		try:
			if getattr(self, '_last_strategy_list', None):
				params['strategies'] = list(self._last_strategy_list)
		except Exception:
			pass
		# include last strategy params from Configure Strategy dialog (may be empty)
		try:
			params['strategy_params'] = getattr(self, '_last_strategy_params', {}) or {}
		except Exception:
			params['strategy_params'] = {}
		self.run_backtest_requested.emit(params)

	def start_backtest_worker(self, params, data_map):
		# guard: don't start if already running
		if self.worker_thread and getattr(self.worker_thread, 'isRunning', lambda: False)():
			return
		# lazy import to avoid import-time Qt dependency issues
		try:
			from ui.main_content.worker_thread import WorkerThread
		except Exception:
			from .worker_thread import WorkerThread

		self.worker_thread = WorkerThread('backtest', params, data_map)
		self.worker_thread.progress_updated.connect(self.update_progress)
		self.worker_thread.status_updated.connect(self.update_status)
		self.worker_thread.results_ready.connect(self.update_results)
		self.worker_thread.error_occurred.connect(self.show_error)
		self.worker_thread.finished_work.connect(self._on_worker_finished)

		self.show_progress(True)
		self.worker_thread.start()

	def cancel_backtest(self):
		if self.worker_thread:
			try:
				self.worker_thread.cancel()
				self.worker_thread.wait(2000)
			except Exception:
				pass
			self.show_progress(False)
			self.worker_thread = None
		else:
			self.show_progress(False)

	def _on_worker_finished(self):
		try:
			wt = self.worker_thread
			if wt is not None:
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
			self.show_progress(False)

	def show_progress(self, show=True):
		self.progress_bar.setVisible(show)
		self.run_backtest_btn.setEnabled(not show)
		self.cancel_btn.setVisible(show)
		# the Stop button is visible in the header; enable it only while a run is active
		try:
			self.stop_btn.setEnabled(bool(show))
		except Exception:
			pass
		if show:
			self.progress_bar.setValue(0)

	def update_progress(self, value):
		self.progress_bar.setValue(value)

	def update_status(self, status):
		# If this tab has a status label, set it; otherwise ignore
		try:
			self.status_label.setText(status)
		except Exception:
			# no-op if status widget not available
			return

	def update_results(self, results):
		self.show_progress(False)
		rows = results or []
		# store full results for later selection-based trade table population
		self._last_results_full = rows
		self.results_table.setRowCount(len(rows))
		from PySide6.QtWidgets import QTableWidgetItem, QPushButton
		for r, res in enumerate(rows):
			# safe extraction helpers
			sym = str(res.get('symbol', ''))
			strat = str(res.get('strategy', ''))
			fv = res.get('final_value', '')
			sh = res.get('sharpe', '')
			mx = res.get('max_dd', '')
			wr = res.get('win_rate', '')
			tr = res.get('trades', '')
			cagr = res.get('cagr', '')
			passed = res.get('passed_strategies', '')
			err = res.get('error', '')
			# populate cells
			self.results_table.setItem(r, 0, QTableWidgetItem(sym))
			self.results_table.setItem(r, 1, QTableWidgetItem(strat))
			self.results_table.setItem(r, 2, QTableWidgetItem(str(fv)))
			self.results_table.setItem(r, 3, QTableWidgetItem(str(sh)))
			self.results_table.setItem(r, 4, QTableWidgetItem(str(mx)))
			self.results_table.setItem(r, 5, QTableWidgetItem(str(wr)))
			self.results_table.setItem(r, 6, QTableWidgetItem(str(tr)))
			self.results_table.setItem(r, 7, QTableWidgetItem(str(cagr)))
			# show chart button
			# Chart button (full backtest figure)
			btn = QPushButton('Chart')
			btn.clicked.connect(lambda _, x=res: self.show_chart(x))
			self.results_table.setCellWidget(r, 8, btn)
			# If equity series present, add context menu or secondary quick equity dialog
			try:
				if res.get('equity_series'):
					btn_eq = QPushButton('Equity')
					btn_eq.setToolTip('הצג עקומת Equity ו-Drawdown')
					btn_eq.clicked.connect(lambda _, x=res: self.show_equity_curve(x))
					# insert after existing cell if space (reuse passed strategies column if empty)
					# For simplicity append as replacing "Passed Strategies" if empty
					if not str(res.get('passed_strategies')):
						self.results_table.setCellWidget(r, 9, btn_eq)
					else:
						# fallback: add below via spanning – skipped for simplicity
						pass
			except Exception:
				pass
			self.results_table.setItem(r, 9, QTableWidgetItem(str(passed)))
			self.results_table.setItem(r, 10, QTableWidgetItem(str(err)))
		# resize to contents for readability
		try:
			from PySide6.QtWidgets import QHeaderView
			self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		except Exception:
			pass
		# Recompute strategy comparison automatically after new results
		try:
			self._recompute_strategy_comparison()
		except Exception:
			pass
		# connect row selection to show trades
		try:
			self.results_table.itemSelectionChanged.connect(self._on_result_selection)
		except Exception:
			pass

	def show_trades(self, result):
		trades = result.get('trade_details')
		if not trades:
			QMessageBox.information(self, "עסקאות", "אין נתוני עסקאות זמינים לאסטרטגיה זו.")
			return

		from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QLabel

		symbol = result.get('symbol', '')
		strategy = result.get('strategy', '')

		dlg = QDialog(self)
		dlg.setWindowTitle(f"פירוט עסקאות - {symbol} / {strategy}")
		layout = QVBoxLayout(dlg)
		layout.addWidget(QLabel(f"<b>{symbol} - {strategy}</b>"))

		def safe_str(x):
			try:
				if x is None:
					return ''
				if isinstance(x, (list, tuple)):
					return ', '.join(safe_str(i) for i in x)
				if isinstance(x, dict):
					return ', '.join(f"{kk}: {vv}" for kk, vv in x.items())
				return str(x)
			except Exception:
				return repr(x)

		if isinstance(trades, list):
			headers = ['Entry Date', 'Entry Price', 'Exit Date', 'Exit Price', 'Profit', 'Size']
			table = QTableWidget()
			table.setColumnCount(len(headers))
			table.setHorizontalHeaderLabels(headers)
			table.setRowCount(len(trades))
			for r, t in enumerate(trades):
				entry_date = safe_str(t.get('entry_date') if isinstance(t, dict) else None)
				entry_price = safe_str(t.get('entry_price') if isinstance(t, dict) else None)
				exit_date = safe_str(t.get('exit_date') if isinstance(t, dict) else None)
				exit_price = safe_str(t.get('exit_price') if isinstance(t, dict) else None)
				profit = safe_str(t.get('profit') if isinstance(t, dict) else None)
				size = safe_str(t.get('size') if isinstance(t, dict) else None)
				vals = [entry_date, entry_price, exit_date, exit_price, profit, size]
				for c, v in enumerate(vals):
					item = QTableWidgetItem(v)
					table.setItem(r, c, item)
			table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
			layout.addWidget(table)
		elif isinstance(trades, dict):
			items = list(trades.items())
			table = QTableWidget()
			table.setColumnCount(2)
			table.setHorizontalHeaderLabels(['Metric', 'Value'])
			table.setRowCount(len(items))
			for r, (k, v) in enumerate(items):
				table.setItem(r, 0, QTableWidgetItem(str(k)))
				table.setItem(r, 1, QTableWidgetItem(safe_str(v)))
			table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
			layout.addWidget(table)
		else:
			table = QTableWidget()
			table.setColumnCount(1)
			table.setHorizontalHeaderLabels(['Value'])
			table.setRowCount(1)
			table.setItem(0, 0, QTableWidgetItem(safe_str(trades)))
			table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
			layout.addWidget(table)

		btn_layout = QHBoxLayout()
		btn_layout.addStretch()
		close_btn = QPushButton("סגור")
		close_btn.clicked.connect(dlg.accept)
		btn_layout.addWidget(close_btn)
		layout.addLayout(btn_layout)

		dlg.resize(900, 480)
		dlg.exec()

	def apply_shared_params(self, params: dict):
		"""Apply a shared params dict (from MainContent.current_params or settings dialog) to the Backtest tab widgets."""
		if not isinstance(params, dict):
			return
		try:
			# simple copy of logic from open_settings_dialog apply
			if 'symbols' in params:
				self.symbols_edit.setText(params.get('symbols',''))
		except Exception:
			pass
		try:
			self.universe_limit_spin.setValue(int(params.get('universe_limit',0) or 0))
		except Exception:
			pass
		try:
			self.min_trades_spin.setValue(int(params.get('min_trades',0) or 0))
		except Exception:
			pass
		try:
			from PySide6.QtCore import QDate
			if params.get('start_date'):
				self.start_date_edit.setDate(QDate.fromString(params.get('start_date'),'yyyy-MM-dd'))
			if params.get('end_date'):
				self.end_date_edit.setDate(QDate.fromString(params.get('end_date'),'yyyy-MM-dd'))
		except Exception:
			pass
		try:
			self.use_adj_check.setChecked(bool(params.get('use_adj', True)))
		except Exception:
			pass
		try:
			self.min_volume_spin.setValue(float(params.get('min_volume',0) or 0))
		except Exception:
			pass
		try:
			self.min_close_spin.setValue(float(params.get('min_close',0) or 0))
		except Exception:
			pass
		try:
			self.start_cash_spin.setValue(float(params.get('start_cash',10000)))
		except Exception:
			pass
		try:
			self.commission_spin.setValue(float(params.get('commission',0.0005)))
		except Exception:
			pass
		try:
			self.slippage_spin.setValue(float(params.get('slippage',0.0005)))
		except Exception:
			pass
		# store last settings so run_backtest respects date-enabled flags
		try:
			self._last_settings = {
				'start_date_enabled': bool(params.get('start_date_enabled', False)),
				'end_date_enabled': bool(params.get('end_date_enabled', False))
			}
		except Exception:
			pass

	def show_chart(self, result):
		try:
			import backend
			import matplotlib.pyplot as plt
			from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
			from PySide6.QtWidgets import QDialog, QVBoxLayout
		except Exception as e:
			QMessageBox.critical(self, "שגיאה", f"לא ניתן לייבא backend/matplotlib: {e}")
			return
		symbol = result.get('symbol')
		strategy = result.get('strategy')
		# try to obtain DataFrame from parent main content
		main_content = self.parentWidget().parentWidget() if hasattr(self, 'parentWidget') else None
		df = None
		if main_content and hasattr(main_content, 'data_map'):
			df = main_content.data_map.get(symbol)
		if df is None:
			QMessageBox.warning(self, "שגיאה", f"לא נמצאו נתונים עבור {symbol}")
			return
		figs = result.get('figs') if result.get('figs') else None
		if not figs:
			try:
				figs, _ = backend.run_backtest(
					df,
					strategy_name=strategy,
					params={},
					start_cash=self.start_cash_spin.value(),
					commission=self.commission_spin.value(),
					slippage_perc=self.slippage_spin.value(),
					plot=True
				)
			except Exception as e:
				QMessageBox.critical(self, "שגיאה", f"שגיאה ביצירת גרף: {e}")
				return
		if not figs:
			QMessageBox.warning(self, "שגיאה", "לא נוצר גרף")
			return
		fig = figs[0]
		trades = result.get('trade_details')
		# overlay trades on the figure if available
		try:
			if isinstance(trades, list) and trades:
				import pandas as _pd
				import matplotlib.lines as mlines
				ax = fig.axes[0] if getattr(fig, 'axes', None) and len(fig.axes) > 0 else fig.add_subplot(111)
				entry_handle = None
				exit_handle = None
				line_handle = None
				for t in trades:
					ed_raw = t.get('entry_date')
					xd_raw = t.get('exit_date')
					entry_dt = None
					exit_dt = None
					try:
						entry_dt = _pd.to_datetime(ed_raw) if ed_raw is not None else None
					except Exception:
						entry_dt = None
					try:
						exit_dt = _pd.to_datetime(xd_raw) if xd_raw is not None else None
					except Exception:
						exit_dt = None
					entry_price = t.get('entry_price')
					exit_price = t.get('exit_price')
					profit = t.get('profit')
					try:
						prof_val = float(profit) if profit is not None else None
					except Exception:
						prof_val = None
					col = 'gray' if prof_val is None else ('green' if prof_val >= 0 else 'red')
					# draw connecting line
					if entry_dt is not None and exit_dt is not None and entry_price is not None and exit_price is not None:
						try:
							ax.plot([entry_dt, exit_dt], [entry_price, exit_price], color=col, linewidth=2.2, alpha=0.9, zorder=4)
							if line_handle is None:
								line_handle = mlines.Line2D([], [], color='green', linewidth=2.2, label='Trade (green=win, red=loss)')
						except Exception:
							pass
					# entry marker
					msize = 90
					if entry_dt is not None and entry_price is not None:
						try:
							h = ax.scatter([entry_dt], [entry_price], marker='^', color='limegreen', edgecolors='black', linewidths=0.7, s=msize, zorder=6)
							if entry_handle is None:
								entry_handle = mlines.Line2D([], [], marker='^', color='limegreen', markeredgecolor='black', linestyle='None', markersize=8, label='Entry')
							try:
								txt = f"{float(entry_price):.2f}"
							except Exception:
								txt = str(entry_price)
							try:
								ax.annotate(txt, (entry_dt, entry_price), textcoords='offset points', xytext=(0,9), ha='center', color='darkgreen', fontsize=8)
							except Exception:
								pass
						except Exception:
							pass
					# exit marker
					if exit_dt is not None and exit_price is not None:
						try:
							h2 = ax.scatter([exit_dt], [exit_price], marker='v', color='orangered', edgecolors='black', linewidths=0.7, s=msize, zorder=6)
							if exit_handle is None:
								exit_handle = mlines.Line2D([], [], marker='v', color='orangered', markeredgecolor='black', linestyle='None', markersize=8, label='Exit')
							try:
								txt = f"{float(exit_price):.2f}"
							except Exception:
								txt = str(exit_price)
							try:
								label = (f"{txt}\n({float(profit):+.2f})" if profit is not None else txt)
							except Exception:
								label = txt
							try:
								ax.annotate(label, (exit_dt, exit_price), textcoords='offset points', xytext=(0,-14), ha='center', color='darkred', fontsize=8)
							except Exception:
								pass
						except Exception:
							pass
				# legend
				handles = [h for h in (entry_handle, exit_handle, line_handle) if h is not None]
				if handles:
					try:
						ax.legend(handles=handles, loc='upper left', fontsize=8)
					except Exception:
						pass
				try:
					fig.tight_layout()
				except Exception:
					pass
		except Exception:
			# never fail the UI for plotting overlays
			pass

		dialog = QDialog(self)
		dialog.setWindowTitle(f"גרף {symbol} - {strategy}")
		layout = QVBoxLayout(dialog)
		canvas = FigureCanvas(fig)
		layout.addWidget(canvas)
		dialog.resize(900, 600)
		dialog.exec()

	def show_equity_curve(self, result):
		"""Open a lightweight dialog showing equity curve + drawdown from result (without re-running backtest)."""
		try:
			from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
			import pandas as _pd
			import matplotlib
			try:
				matplotlib.use('Agg')
			except Exception:
				pass
			import matplotlib.pyplot as plt
			from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
		except Exception as e:
			QMessageBox.critical(self, 'שגיאה', f'שגיאה בטעינת ספריות גרף: {e}')
			return
		eq_series = result.get('equity_series') or []
		dd_series = result.get('drawdown_series') or []
		if not eq_series:
			QMessageBox.information(self, 'מידע', 'אין נתוני Equity זמינים')
			return
		# build data
		try:
			dts = [ _pd.to_datetime(t) for t,_ in eq_series if t ]
			vals = [ v for t,v in eq_series if t ]
			dd_vals = []
			if dd_series and len(dd_series) == len(eq_series):
				dd_vals = [ d for t,d in dd_series if t ]
		except Exception:
			QMessageBox.warning(self, 'שגיאה', 'כשל בעיבוד נתוני Equity')
			return
		fig, (ax_eq, ax_dd) = plt.subplots(2, 1, sharex=True, figsize=(8,5), gridspec_kw={'height_ratios':[3,1]})
		ax_eq.plot(dts, vals, color='tab:orange', linewidth=1.2, label='Equity')
		ax_eq.set_ylabel('Equity')
		ax_eq.legend(loc='upper left')
		if dd_vals:
			ax_dd.fill_between(dts, [-x for x in dd_vals], 0, color='tab:red', alpha=0.35, step='pre')
			ax_dd.set_ylabel('DD%')
		else:
			ax_dd.set_visible(False)
		try:
			fig.tight_layout()
		except Exception:
			pass
		dlg = QDialog(self)
		dlg.setWindowTitle('Equity / Drawdown')
		lay = QVBoxLayout(dlg)
		canvas = FigureCanvas(fig)
		lay.addWidget(canvas)
		dlg.resize(780, 520)
		dlg.exec()

	def _on_result_selection(self):
		"""Populate trades table for the currently selected result row (if any)."""
		try:
			selected = self.results_table.selectedItems()
			if not selected:
				return
			row = selected[0].row()
			# reconstruct result dict from table + stored rows (keep last results cached)
			# Simplest: keep last full results list on instance when update_results called
			res_list = getattr(self, '_last_results_full', None)
			if not res_list or row >= len(res_list):
				return
			res = res_list[row]
			trades = res.get('trade_details') or []
			if not isinstance(trades, list):
				# not a list - clear
				self.trades_table.setRowCount(0); return
			# build table
			self.trades_table.setRowCount(len(trades))
			cum_pnl = 0.0
			from PySide6.QtWidgets import QTableWidgetItem
			for i, t in enumerate(trades):
				if not isinstance(t, dict):
					continue
				ed = t.get('entry_date') or ''
				xd = t.get('exit_date') or ''
				hd = t.get('hold_days')
				entry = t.get('entry_price')
				exitp = t.get('exit_price')
				size = t.get('size')
				profit = t.get('profit')
				profit_pct = t.get('profit_pct')
				ret_pct = t.get('pct_return')
				try:
					if profit is not None:
						cum_pnl += float(profit)
				except Exception:
					pass
				vals = [ed, xd, hd, entry, exitp, size, profit, profit_pct, ret_pct, cum_pnl]
				for c, v in enumerate(vals):
					it = QTableWidgetItem('' if v is None else f"{v:.2f}" if isinstance(v,(int,float)) else str(v))
					self.trades_table.setItem(i, c, it)
					# color wins/losses on profit column
					if c == 6 and isinstance(profit,(int,float)):
						try:
							col = '#1b6e1b' if profit >= 0 else '#a83232'
							it.setForeground(col)
						except Exception:
							pass
		except Exception:
			return

	def export_trades(self):
		"""Export currently displayed trades table to CSV."""
		from PySide6.QtWidgets import QFileDialog, QMessageBox, QTableWidgetItem
		if self.trades_table.rowCount() == 0:
			QMessageBox.information(self,'מידע','אין עסקאות לייצא')
			return
		file_path,_ = QFileDialog.getSaveFileName(self,'ייצוא עסקאות','trades.csv','CSV Files (*.csv)')
		if not file_path:
			return
		try:
			with open(file_path,'w',encoding='utf-8') as f:
				headers = [self.trades_table.horizontalHeaderItem(i).text() for i in range(self.trades_table.columnCount())]
				f.write(','.join(headers)+'\n')
				for r in range(self.trades_table.rowCount()):
					row_vals = []
					for c in range(self.trades_table.columnCount()):
						it = self.trades_table.item(r,c)
						row_vals.append(it.text() if it else '')
					f.write(','.join(row_vals)+'\n')
			from PySide6.QtWidgets import QMessageBox as _QB
			_QB.information(self,'הצלחה',f'נשמר: {file_path}')
		except Exception as e:
			QMessageBox.critical(self,'שגיאה',f'כשל בכתיבת קובץ: {e}')

	def _recompute_strategy_comparison(self):
		"""Aggregate per-strategy metrics across all rows and populate strategy_table (with ranking)."""
		rows = getattr(self, '_last_results_full', []) or []
		thresh = 0.5
		try:
			thresh = float(self.comp_sharpe_thresh.value())
		except Exception:
			pass
		agg = {}
		for r in rows:
			try:
				strat = r.get('strategy')
				if not strat:
					continue
				if isinstance(r.get('final_value'), str) and r.get('final_value','').upper() == 'ERROR':
					continue
				sh = r.get('sharpe'); cagr = r.get('cagr'); dd = r.get('max_dd'); wr = r.get('win_rate'); tr = r.get('trades')
				if strat not in agg:
					agg[strat] = {'sh':[], 'cagr':[], 'dd':[], 'wr':[], 'trades':0, 'symbols':set(), 'passes':0, 'total_rows':0}
				bucket = agg[strat]
				def _num(x):
					return float(x) if isinstance(x,(int,float)) else (float(x) if isinstance(x,str) and x.replace('.','',1).replace('-','',1).isdigit() else None)
				val_sh = _num(sh); val_cagr = _num(cagr); val_dd = _num(dd); val_wr = _num(wr); val_tr = _num(tr)
				if val_sh is not None: bucket['sh'].append(val_sh)
				if val_cagr is not None: bucket['cagr'].append(val_cagr)
				if val_dd is not None: bucket['dd'].append(val_dd)
				if val_wr is not None: bucket['wr'].append(val_wr)
				if val_tr is not None: bucket['trades'] += int(val_tr)
				bucket['symbols'].add(r.get('symbol'))
				bucket['total_rows'] += 1
				if val_sh is not None and val_sh >= thresh:
					bucket['passes'] += 1
			except Exception:
				continue
		# sort by avg sharpe desc
		order = []
		for k,v in agg.items():
			avg_sh = sum(v['sh'])/len(v['sh']) if v['sh'] else -1e9
			order.append((k, avg_sh))
		order.sort(key=lambda x: -x[1])
		self.strategy_table.setRowCount(len(order))
		from PySide6.QtWidgets import QTableWidgetItem, QHeaderView
		for rank,(k,_) in enumerate(order, start=1):
			v = agg[k]
			def _avg(lst): return sum(lst)/len(lst) if lst else 0.0
			def _median(lst):
				if not lst: return 0.0
				s = sorted(lst); n=len(s)
				return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
			avg_sh = _avg(v['sh']); avg_cagr = _avg(v['cagr']); med_dd = _median(v['dd']); avg_wr = _avg(v['wr'])
			pass_rate = 100.0 * v['passes']/max(1,v['total_rows'])
			row_vals = [rank, k, avg_sh, avg_cagr, med_dd, avg_wr, v['trades'], len(v['symbols']), pass_rate, v['passes']]
			for c,val in enumerate(row_vals):
				fmt = f"{val:.4f}" if isinstance(val,(int,float)) and c not in (0,1) else str(val)
				self.strategy_table.setItem(rank-1,c,QTableWidgetItem(fmt))
		# color best Sharpe + CAGR
		try:
			rows_n = self.strategy_table.rowCount()
			if rows_n>0:
				sharpes = [(i,float(self.strategy_table.item(i,2).text())) for i in range(rows_n)]
				cagrs = [(i,float(self.strategy_table.item(i,3).text())) for i in range(rows_n)]
				best_sh = max(sharpes,key=lambda x:x[1])[1] if sharpes else None
				best_cagr = max(cagrs,key=lambda x:x[1])[1] if cagrs else None
				for i,val in sharpes:
					if best_sh is not None and val==best_sh:
						self.strategy_table.item(i,2).setForeground('#1b6e1b')
				for i,val in cagrs:
					if best_cagr is not None and val==best_cagr:
						self.strategy_table.item(i,3).setForeground('#1b4e8a')
			self.strategy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		except Exception:
			pass

	def export_strategy_comparison(self):
		from PySide6.QtWidgets import QFileDialog, QMessageBox
		if self.strategy_table.rowCount()==0:
			QMessageBox.information(self,'מידע','אין נתונים להשוואה')
			return
		fp,_ = QFileDialog.getSaveFileName(self,'ייצוא השוואת אסטרטגיות','strategy_comparison.csv','CSV Files (*.csv)')
		if not fp:
			return
		try:
			with open(fp,'w',encoding='utf-8') as f:
				headers=[self.strategy_table.horizontalHeaderItem(c).text() for c in range(self.strategy_table.columnCount())]
				f.write(','.join(headers)+'\n')
				for r in range(self.strategy_table.rowCount()):
					vals=[]
					for c in range(self.strategy_table.columnCount()):
						it=self.strategy_table.item(r,c)
						vals.append(it.text() if it else '')
					f.write(','.join(vals)+'\n')
			from PySide6.QtWidgets import QMessageBox as QB
			QB.information(self,'הצלחה',f'נשמר: {fp}')
		except Exception as e:
			QMessageBox.critical(self,'שגיאה',f'כשל שמירה: {e}')

	def show_strategy_sharpe_chart(self):
		"""Display bar chart of average Sharpe per strategy."""
		try:
			from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
			import matplotlib
			try:
				matplotlib.use('Agg')
			except Exception:
				pass
			import matplotlib.pyplot as plt
			from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
		except Exception as e:
			return
		rows_n = self.strategy_table.rowCount()
		if rows_n == 0:
			return
		strategies=[]; sharpes=[]
		for r in range(rows_n):
			# strategy name now at column 1, sharpe at column 2
			strategies.append(self.strategy_table.item(r,1).text())
			try:
				sharpes.append(float(self.strategy_table.item(r,2).text()))
			except Exception:
				sharpes.append(0.0)
		fig, ax = plt.subplots(figsize=(max(6,len(strategies)*0.6),4))
		ax.bar(strategies, sharpes, color='#1b4e8a', alpha=0.85)
		ax.set_ylabel('Avg Sharpe')
		ax.set_title('השוואת Sharpe לפי אסטרטגיה')
		for i,v in enumerate(sharpes):
			ax.text(i, v, f"{v:.2f}", ha='center', va='bottom', fontsize=8)
		fig.autofmt_xdate(rotation=25)
		try:
			fig.tight_layout()
		except Exception:
			pass
		dlg = QDialog(self)
		dlg.setWindowTitle('תרשים Sharpe')
		lay = QVBoxLayout(dlg)
		canvas = FigureCanvas(fig)
		lay.addWidget(canvas)
		dlg.resize(720, 420)
		dlg.exec()

	def open_data_config(self):
		dlg = DataConfigDialog(self)
		if dlg.exec():
			path = dlg.path_edit.text().strip()
			if path:
				main = self.parentWidget().parentWidget()
				if main and hasattr(main, 'on_load_data'):
					main.on_load_data({'path': path})

	def open_strategy_config(self):
		dlg = StrategyConfigDialog(self)
		if dlg.exec():
			# store parsed params dict if provided
			try:
				self._last_strategy_params = getattr(dlg, 'parsed_params', None) or {}
			except Exception:
				self._last_strategy_params = {}

	def open_settings_dialog(self):
		dlg = BacktestSettingsDialog(self)
		# preload with current values
		vals = {
			'symbols': self.symbols_edit.text(),
			'universe_limit': int(self.universe_limit_spin.value()),
			'min_trades': int(self.min_trades_spin.value()),
			# include explicit enabled flags if we have them saved; otherwise infer enabled if widget has a non-default value
			'start_date': self.start_date_edit.date().toString('yyyy-MM-dd') if getattr(self, '_last_settings', {}).get('start_date_enabled', False) else '',
			'end_date': self.end_date_edit.date().toString('yyyy-MM-dd') if getattr(self, '_last_settings', {}).get('end_date_enabled', False) else '',
			'start_date_enabled': getattr(self, '_last_settings', {}).get('start_date_enabled', False),
			'end_date_enabled': getattr(self, '_last_settings', {}).get('end_date_enabled', False),
			'use_adj': bool(self.use_adj_check.isChecked()),
			'min_volume': float(self.min_volume_spin.value()),
			'min_close': float(self.min_close_spin.value()),
			'start_cash': float(self.start_cash_spin.value()),
			'commission': float(self.commission_spin.value()),
			'slippage': float(self.slippage_spin.value()),
			'strategies': getattr(self, '_last_strategy_list', [])
		}
		dlg.set_values(vals)
		if dlg.exec():
			out = dlg.get_values()
			# apply back to widgets
			try:
				self.symbols_edit.setText(out.get('symbols',''))
			except Exception:
				pass
			try:
				self.universe_limit_spin.setValue(int(out.get('universe_limit',0) or 0))
			except Exception:
				pass
			try:
				self.min_trades_spin.setValue(int(out.get('min_trades',0) or 0))
			except Exception:
				pass
			try:
				from PySide6.QtCore import QDate
				if out.get('start_date'):
					self.start_date_edit.setDate(QDate.fromString(out.get('start_date'),'yyyy-MM-dd'))
				if out.get('end_date'):
					self.end_date_edit.setDate(QDate.fromString(out.get('end_date'),'yyyy-MM-dd'))
			except Exception:
				pass
			try:
				self.use_adj_check.setChecked(bool(out.get('use_adj', True)))
			except Exception:
				pass
			try:
				self.min_volume_spin.setValue(float(out.get('min_volume',0) or 0))
			except Exception:
				pass
			try:
				self.min_close_spin.setValue(float(out.get('min_close',0) or 0))
			except Exception:
				pass
			try:
				self.start_cash_spin.setValue(float(out.get('start_cash',10000)))
			except Exception:
				pass
			try:
				self.commission_spin.setValue(float(out.get('commission',0.0005)))
			except Exception:
				pass
			try:
				self.slippage_spin.setValue(float(out.get('slippage',0.0005)))
			except Exception:
				pass
			# store selected strategies
			# Also store settings into the main_content.shared params if possible
			try:
				main = getattr(self, 'parent', None)()
			except Exception:
				main = None
			try:
				# if this widget is hosted inside MainContent, update its current_params
				if main and hasattr(main, 'current_params'):
					main.current_params = out
			except Exception:
				pass
			try:
				self._last_strategy_list = out.get('strategies', [])
			except Exception:
				self._last_strategy_list = []
			# store per-strategy params so run_backtest can include them
			try:
				self._last_strategy_params = out.get('strategy_params', {}) or {}
			except Exception:
				self._last_strategy_params = {}
			# persist last settings (including explicit date-enable flags) so open_settings_dialog can prefill next time
			try:
				self._last_settings = {
					'start_date_enabled': bool(out.get('start_date_enabled', False)),
					'end_date_enabled': bool(out.get('end_date_enabled', False)),
				}
			except Exception:
				self._last_settings = {}

	def show_error(self, error):
		self.show_progress(False)
		QMessageBox.critical(self, "שגיאה", f"שגיאה בבק-טסט: {error}")

	def download_results(self):
		if self.results_table.rowCount() == 0:
			QMessageBox.information(self, "מידע", "אין תוצאות להורדה")
			return
		file_path, _ = QFileDialog.getSaveFileName(self, "שמור קובץ", "backtest_results.csv", "CSV Files (*.csv)")
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
				params = dlg.params_edit.toPlainText().strip()
				try:
					self._last_strategy_params = params
				except Exception:
					pass
# BacktestTab UI and logic

