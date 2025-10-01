from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit, QSpinBox, QComboBox, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog, QLineEdit, QListWidget, QListWidgetItem, QAbstractItemView, QSizePolicy, QGridLayout)
from PySide6.QtCore import Qt, Signal, QDate
from ui.main_content.dialogs.data_config_dialog import DataConfigDialog
from ui.main_content.dialogs.strategy_config_dialog import StrategyConfigDialog

import json


class AutoDiscoveryTab(QWidget):
    run_auto_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.worker_thread = None

    def setup_ui(self):
        layout = QVBoxLayout(self)
        settings_layout = QHBoxLayout()

        # Left panel (symbols and strategies)
        left_settings = QWidget()
        left_layout = QVBoxLayout(left_settings)

        # Row: strategy buttons (2x5) then manual symbols input to the right
        top_row = QHBoxLayout(); top_row.setSpacing(8)
        self.strat_buttons_container = QWidget()
        self._strat_buttons_layout = QGridLayout(self.strat_buttons_container)
        self._strat_buttons_layout.setContentsMargins(0,0,0,0)
        self._strat_buttons_layout.setHorizontalSpacing(4)
        self._strat_buttons_layout.setVerticalSpacing(4)
        self.strat_buttons = []
        self.manual_symbols_input = QLineEdit(); self.manual_symbols_input.setPlaceholderText('Symbols (comma)')
        self.manual_symbols_input.setFixedWidth(170)
        top_row.addWidget(self.strat_buttons_container, 3)
        top_row.addWidget(self.manual_symbols_input, 0, Qt.AlignTop)
        left_layout.addLayout(top_row)

        # Internal symbol storage (user-entered manual symbols are used at run time)
        self._available_symbols = []

        # compact row: bar-level filters + min trades + apply
        compact_filt_row = QHBoxLayout()
        self.min_price_spin = QSpinBox()
        # use safe 32-bit ranges to avoid PySide overflow on some platforms
        self.min_price_spin.setRange(0, 2_000_000_000)
        self.min_price_spin.setValue(0)
        self.min_vol_spin = QSpinBox()
        self.min_vol_spin.setRange(0, 2_000_000_000)
        self.min_vol_spin.setValue(0)

        self.min_trades_spin = QSpinBox()
        self.min_trades_spin.setRange(0, 10000)
        self.min_trades_spin.setValue(5)

        self.apply_bar_filters_chk = QPushButton("Apply Bar Filters")
        self.apply_bar_filters_chk.setCheckable(True)

        compact_filt_row.addWidget(QLabel("Min Close:"))
        compact_filt_row.addWidget(self.min_price_spin)
        compact_filt_row.addWidget(QLabel("Min Volume:"))
        compact_filt_row.addWidget(self.min_vol_spin)
        compact_filt_row.addSpacing(8)
        compact_filt_row.addWidget(QLabel("Min trades:"))
        compact_filt_row.addWidget(self.min_trades_spin)
        compact_filt_row.addSpacing(8)
        compact_filt_row.addWidget(self.apply_bar_filters_chk)

        left_layout.addLayout(compact_filt_row)

        # Right panel (controls)
        right_settings = QGroupBox("הפעלה ותצוגה")
        right_layout = QVBoxLayout(right_settings)
        right_layout.setContentsMargins(6,6,6,6)
        right_layout.setSpacing(4)
        right_settings.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.run_btn = QPushButton("הרץ Auto-Discovery")
        self.run_btn.setObjectName("primary_button")
        self.run_btn.clicked.connect(self.run_auto)
        # Objective selection (scoring metric) – default Sharpe
        obj_row = QHBoxLayout()
        obj_row.addWidget(QLabel('Objective:'))
        self.objective_combo = QComboBox()
        self.objective_combo.addItems(['Sharpe','CAGR','WinRate','Return/DD'])
        self.objective_combo.setCurrentIndex(0)
        obj_row.addWidget(self.objective_combo, 1)
        obj_row.addStretch()

        self.cfg_data_btn = QPushButton('Configure Data')
        self.cfg_data_btn.setObjectName('secondary_button')
        self.cfg_data_btn.clicked.connect(self.open_data_config)
        self.cfg_strategy_btn = QPushButton('Configure Strategy')
        self.cfg_strategy_btn.setObjectName('secondary_button')
        self.cfg_strategy_btn.clicked.connect(self.open_strategy_config)
        right_layout.addWidget(self.run_btn)
        right_layout.addLayout(obj_row)
        # Compact two-row button grid
        row1 = QHBoxLayout(); row1.setSpacing(4)
        self.export_btn = QPushButton('Export'); self.export_btn.setObjectName('secondary_button'); self.export_btn.clicked.connect(self.export_results)
        self.show_log_btn = QPushButton('Log'); self.show_log_btn.setObjectName('secondary_button'); self.show_log_btn.clicked.connect(self.show_log)
        self.cfg_grid_btn = QPushButton('Grid'); self.cfg_grid_btn.setObjectName('secondary_button'); self.cfg_grid_btn.clicked.connect(self._open_grid_editor)
        row1.addWidget(self.export_btn); row1.addWidget(self.show_log_btn); row1.addWidget(self.cfg_grid_btn)
        row2 = QHBoxLayout(); row2.setSpacing(4)
        row2.addWidget(self.cfg_data_btn); row2.addWidget(self.cfg_strategy_btn)
        right_layout.addLayout(row1)
        right_layout.addLayout(row2)
        right_layout.addStretch()

        settings_layout.addWidget(left_settings)
        settings_layout.addWidget(right_settings)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel('')
        self.results_table = QTableWidget()
        self.setup_results_table()

        layout.addLayout(settings_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.results_table, 1)

    def setup_results_table(self):
        # Added Score column (depends on chosen objective metric)
        headers = ["Symbol", "Strategy", "Params", "CAGR", "Sharpe", "WinRate", "MaxDD", "Trades", "Score"]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)

    def run_auto(self):
        params = {
            'grid_json': getattr(self, '_grid_json', '') or '',
            'min_trades': self.min_trades_spin.value(),
            'apply_bar_filters': self.apply_bar_filters_chk.isChecked(),
            'min_price_bar': self.min_price_spin.value(),
            'min_vol_bar': self.min_vol_spin.value(),
            'objective': self.objective_combo.currentText()
        }
        # include selected symbols: first prefer manual input, otherwise fallback to available symbols
        manual = (self.manual_symbols_input.text() or '').strip()
        if manual:
            syms = [s.strip() for s in manual.split(',') if s.strip()]
            if syms:
                params['symbols'] = syms
        else:
            if getattr(self, '_available_symbols', None):
                params['symbols'] = list(self._available_symbols)
        # collect strategies from toggle buttons if any
        try:
            selected_strats = [btn.text() for btn in self.strat_buttons if btn.isChecked()]
            if selected_strats:
                params['strategies'] = selected_strats
        except Exception:
            pass

        self.run_auto_requested.emit(params)

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

    def set_symbols(self, symbols):
        """Populate the symbols list widget (list of strings)."""
        try:
            self._available_symbols = sorted(list(symbols))
        except Exception:
            pass

    def _open_grid_editor(self):
        # open a simple dialog to edit grid JSON (small and modal)
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle('Edit Grid JSON')
        v = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setPlainText(getattr(self, '_grid_json', '') or '')
        v.addWidget(te)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(bb)
        def on_accept():
            try:
                txt = te.toPlainText().strip()
                # basic validation: must be empty or valid JSON
                if txt:
                    import json as _j
                    _j.loads(txt)
                self._grid_json = txt
            except Exception as e:
                QMessageBox.critical(self, 'Invalid JSON', str(e))
                return
            dlg.accept()
        bb.accepted.connect(on_accept)
        bb.rejected.connect(dlg.reject)
        dlg.exec()

    def set_strategies(self, strategies):
        """Populate the strategies list widget (list of strings)."""
        """Populate the strategy toggle buttons (list of strings).
        Also append two placeholder buttons for future strategies.
        """
        try:
            # clear previous buttons
            for b in getattr(self, 'strat_buttons', [])[:]:
                try:
                    b.setParent(None)
                except Exception:
                    pass
            self.strat_buttons = []
            # create buttons for given strategies
            # place buttons in a 2x5 grid
            max_cols = 5
            r = 0
            c = 0
            for idx, s in enumerate(strategies):
                btn = QPushButton(s)
                btn.setCheckable(True)
                def _on_toggle(checked, b=btn):
                    try:
                        b.setProperty('checked', bool(checked))
                        b.style().unpolish(b)
                        b.style().polish(b)
                    except Exception:
                        pass
                btn.toggled.connect(_on_toggle)
                self._strat_buttons_layout.addWidget(btn, r, c)
                self.strat_buttons.append(btn)
                c += 1
                if c >= max_cols:
                    c = 0
                    r += 1
                if r >= 2:
                    # limit to 2 rows
                    break
            # fill remaining slots up to 10 with placeholders
            total_slots = 2 * max_cols
            existing = len(self.strat_buttons)
            for i in range(existing, total_slots):
                ph = QPushButton(f"+ Strat {i-existing+1}")
                ph.setEnabled(False)
                rr = i // max_cols
                cc = i % max_cols
                self._strat_buttons_layout.addWidget(ph, rr, cc)
        except Exception:
            pass

    def show_progress(self, show=True):
        self.progress_bar.setVisible(show)
        self.run_btn.setEnabled(not show)
        if show:
            self.progress_bar.setValue(0)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_results(self, rows):
        # rows: list of dicts with Symbol, Strategy, Params (json), CAGR, Sharpe, WinRate, MaxDD, Trades
        self.show_progress(False)
        self.results_table.setRowCount(len(rows))
        cols = ["Symbol","Strategy","Params","CAGR","Sharpe","WinRate","MaxDD","Trades","Score"]
        for r, row in enumerate(rows):
            vals = [row.get(k, '') for k in cols]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                self.results_table.setItem(r, c, item)
        # store last results for export
        self._last_results = rows or []

    def export_results(self):
        rows = getattr(self, '_last_results', None)
        if not rows:
            QMessageBox.information(self, 'No results', 'אין תוצאות לייצוא')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save results CSV', '', 'CSV Files (*.csv)')
        if not path:
            return
        import csv
        keys = ['Symbol','Strategy','Params','CAGR','Sharpe','WinRate','MaxDD','Trades','Score']
        try:
            with open(path, 'w', newline='', encoding='utf-8') as cf:
                writer = csv.DictWriter(cf, fieldnames=keys)
                writer.writeheader()
                for r in rows:
                    writer.writerow({k: r.get(k,'') for k in keys})
            QMessageBox.information(self, 'Saved', f'Saved results to {path}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def show_log(self):
        # open a simple file dialog to show a log if exists
        import os
        log_path = os.path.join(os.getcwd(), 'auto_discovery.log')
        if not os.path.isfile(log_path):
            QMessageBox.information(self, 'No log', 'No auto_discovery.log found in project root')
            return
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                txt = f.read()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))
            return
        dlg = QMessageBox(self)
        dlg.setWindowTitle('Auto-Discovery Log')
        dlg.setText('Log (first 10k chars):')
        dlg.setDetailedText(txt[:10000])
        dlg.exec()

    def set_status(self, text: str):
        try:
            self.status_label.setText(text)
        except Exception:
            pass
