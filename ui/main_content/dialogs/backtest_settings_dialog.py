from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
                                QDateEdit, QCheckBox, QPushButton, QListWidget, QListWidgetItem, QSizePolicy, QComboBox, QWidget, QFormLayout, QPlainTextEdit)
from PySide6.QtCore import Qt
import backend
from inspect import isclass
from typing import Dict


class BacktestSettingsDialog(QDialog):
    """Dialog that exposes the full backtest settings (filters + strategy selection).

    This dialog is intentionally simple: it mirrors the controls shown in the Backtest tab
    and exposes a multi-select strategy list populated from backend.STRAT_MAP keys.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backtest Settings")
        self.resize(640, 520)

        self.layout = QVBoxLayout(self)

        # basic filters
        self.symbols_edit = QLineEdit()
        self.universe_limit_spin = QSpinBox()
        self.universe_limit_spin.setRange(0, 10000)
        self.min_trades_spin = QSpinBox()
        self.min_trades_spin.setRange(0, 10000)
        from PySide6.QtCore import QDate
        # start/end date controls plus explicit enabled checkboxes so we can represent "unset"
        self.start_date_enabled = QCheckBox('Enable start date')
        self.end_date_enabled = QCheckBox('Enable end date')
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat('yyyy-MM-dd')
        # sensible defaults: disabled (interpreted as unset) and today for the editor
        self.start_date_enabled.setChecked(False)
        self.end_date_enabled.setChecked(False)
        self.start_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDate(QDate.currentDate())
        self.use_adj_check = QCheckBox('Use adjusted close (if available)')
        self.min_volume_spin = QDoubleSpinBox()
        self.min_volume_spin.setRange(0, 1e12)
        self.min_close_spin = QDoubleSpinBox()
        self.min_close_spin.setRange(0, 1e9)

        # financial params
        self.start_cash_spin = QDoubleSpinBox()
        self.start_cash_spin.setRange(1000, 1e9)
        self.start_cash_spin.setSuffix(' $')
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0, 0.01)
        self.commission_spin.setDecimals(6)
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 0.02)
        self.slippage_spin.setDecimals(6)

        # Strategies list (multi-select)
        self.strat_list = QListWidget()
        self.strat_list.setSelectionMode(QListWidget.MultiSelection)
        # populate from backend STRAT_MAP
        try:
            keys = list(getattr(backend, 'STRAT_MAP', {}).keys())
        except Exception:
            keys = []
        for k in keys:
            item = QListWidgetItem(k)
            item.setCheckState(Qt.Unchecked)
            # make item checkable/enabled so changes emit itemChanged
            try:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            except Exception:
                pass
            self.strat_list.addItem(item)

        # Strategy params editor (select or check strategies to edit their params)
        self.layout.addWidget(QLabel('Edit strategy parameters (visual):'))
        strat_row = QHBoxLayout()
        self.strat_selector = QComboBox()
        for k in keys:
            self.strat_selector.addItem(k)
        strat_row.addWidget(QLabel('Strategy:'))
        strat_row.addWidget(self.strat_selector)
        self.layout.addLayout(strat_row)

        # when the user clicks an item in the checklist, show it in the selector so they can edit params
        try:
            # map clicks in the checklist to the selector index so the param editor updates
            def _on_item_clicked(it):
                try:
                    txt = it.text()
                    idx = self.strat_selector.findText(txt)
                    if idx >= 0:
                        self.strat_selector.setCurrentIndex(idx)
                except Exception:
                    pass
            self.strat_list.itemClicked.connect(_on_item_clicked)
        except Exception:
            pass
        # if we have strategy keys, auto-select the first one in the selector so params appear by default
        try:
            if len(keys) > 0:
                self.strat_selector.setCurrentIndex(0)
        except Exception:
            pass

        # dynamic param area (will host param editors for checked/selected strategies)
        self.param_widget = QWidget()
        self.param_form = QFormLayout(self.param_widget)
        self.param_widget.setMinimumHeight(120)
        self.layout.addWidget(self.param_widget)

        # hold param values per strategy
        self._params_by_strategy = {}

        # connect
        self.strat_selector.currentTextChanged.connect(self._on_strategy_changed)
        try:
            self.strat_list.itemChanged.connect(self._on_strat_list_changed)
        except Exception:
            pass

        # assemble layout
        def add_row(label_text, widget):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(180)
            row.addWidget(lbl)
            row.addWidget(widget)
            self.layout.addLayout(row)

        add_row('Symbols (comma-separated):', self.symbols_edit)
        add_row('Universe limit (0 = none):', self.universe_limit_spin)
        add_row('Min trades (0 = none):', self.min_trades_spin)
        # show enable checkbox + editor so we can return '' when not enabled
        add_row('', self.start_date_enabled)
        add_row('Start date:', self.start_date_edit)
        add_row('', self.end_date_enabled)
        add_row('End date:', self.end_date_edit)
        add_row('', self.use_adj_check)
        add_row('Min avg volume:', self.min_volume_spin)
        add_row('Min close price:', self.min_close_spin)
        add_row('Start cash:', self.start_cash_spin)
        add_row('Commission:', self.commission_spin)
        add_row('Slippage:', self.slippage_spin)

        self.layout.addWidget(QLabel('Strategies (choose one or more):'))
        self.layout.addWidget(self.strat_list)

        # buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.ok_btn = QPushButton('OK')
        self.cancel_btn = QPushButton('Cancel')
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.ok_btn)
        self.layout.addLayout(btn_row)

    def set_values(self, values: dict):
        # populate controls from a values dict if provided
        if not isinstance(values, dict):
            return
        try:
            self.symbols_edit.setText(values.get('symbols', ''))
        except Exception:
            pass
        try:
            self.universe_limit_spin.setValue(int(values.get('universe_limit', 0) or 0))
        except Exception:
            pass
        try:
            self.min_trades_spin.setValue(int(values.get('min_trades', 0) or 0))
        except Exception:
            pass
        try:
            sd = values.get('start_date')
            if sd:
                from PySide6.QtCore import QDate
                self.start_date_enabled.setChecked(True)
                self.start_date_edit.setDate(QDate.fromString(sd, 'yyyy-MM-dd'))
            else:
                # leave disabled to represent unset
                self.start_date_enabled.setChecked(False)
        except Exception:
            pass
        try:
            ed = values.get('end_date')
            if ed:
                from PySide6.QtCore import QDate
                self.end_date_enabled.setChecked(True)
                self.end_date_edit.setDate(QDate.fromString(ed, 'yyyy-MM-dd'))
            else:
                self.end_date_enabled.setChecked(False)
        except Exception:
            pass
        try:
            self.use_adj_check.setChecked(bool(values.get('use_adj', True)))
        except Exception:
            pass
        try:
            self.min_volume_spin.setValue(float(values.get('min_volume', 0) or 0))
        except Exception:
            pass
        try:
            self.min_close_spin.setValue(float(values.get('min_close', 0) or 0))
        except Exception:
            pass
        try:
            self.start_cash_spin.setValue(float(values.get('start_cash', 10000)))
        except Exception:
            pass
        try:
            self.commission_spin.setValue(float(values.get('commission', 0.0005)))
        except Exception:
            pass
        try:
            self.slippage_spin.setValue(float(values.get('slippage', 0.0005)))
        except Exception:
            pass
        # strategies selection
        try:
            sel = values.get('strategies') or []
            sel_set = set(sel)
            for i in range(self.strat_list.count()):
                it = self.strat_list.item(i)
                if it.text() in sel_set:
                    it.setCheckState(Qt.Checked)
                else:
                    it.setCheckState(Qt.Unchecked)
        except Exception:
            pass

        # strategy params per-strategy (optional)
        try:
            sp = values.get('strategy_params') or {}
            if isinstance(sp, dict):
                for name, pvals in sp.items():
                    if isinstance(pvals, dict):
                        self._params_by_strategy[name] = pvals.copy()
        except Exception:
            pass

        # if input dict carries explicit flags about dates, honor them
        try:
            if isinstance(values.get('start_date_enabled'), bool):
                self.start_date_enabled.setChecked(bool(values.get('start_date_enabled')))
        except Exception:
            pass
        try:
            if isinstance(values.get('end_date_enabled'), bool):
                self.end_date_enabled.setChecked(bool(values.get('end_date_enabled')))
        except Exception:
            pass

    def get_values(self) -> dict:
        out = {}
        out['symbols'] = self.symbols_edit.text().strip()
        out['universe_limit'] = int(self.universe_limit_spin.value())
        out['min_trades'] = int(self.min_trades_spin.value())
        # only return dates if the user enabled them; otherwise return empty string
        try:
            if getattr(self, 'start_date_enabled', None) and self.start_date_enabled.isChecked():
                out['start_date'] = self.start_date_edit.date().toString('yyyy-MM-dd')
            else:
                out['start_date'] = ''
        except Exception:
            out['start_date'] = ''
        try:
            if getattr(self, 'end_date_enabled', None) and self.end_date_enabled.isChecked():
                out['end_date'] = self.end_date_edit.date().toString('yyyy-MM-dd')
            else:
                out['end_date'] = ''
        except Exception:
            out['end_date'] = ''
        # include explicit enabled flags so callers can know whether the date was intentionally set
        try:
            out['start_date_enabled'] = bool(getattr(self, 'start_date_enabled', None) and self.start_date_enabled.isChecked())
        except Exception:
            out['start_date_enabled'] = False
        try:
            out['end_date_enabled'] = bool(getattr(self, 'end_date_enabled', None) and self.end_date_enabled.isChecked())
        except Exception:
            out['end_date_enabled'] = False
        out['use_adj'] = bool(self.use_adj_check.isChecked())
        out['min_volume'] = float(self.min_volume_spin.value())
        out['min_close'] = float(self.min_close_spin.value())
        out['start_cash'] = float(self.start_cash_spin.value())
        out['commission'] = float(self.commission_spin.value())
        out['slippage'] = float(self.slippage_spin.value())
        # strategies
        sel = []
        for i in range(self.strat_list.count()):
            it = self.strat_list.item(i)
            if it.checkState() == Qt.Checked:
                sel.append(it.text())
        out['strategies'] = sel
        # include any per-strategy params the user edited
        out['strategy_params'] = self._params_by_strategy.copy()
        return out

    def _on_strategy_changed(self, name: str):
        # when selector changes, build editor focused on that strategy (and sync with checklist)
        # We'll reuse the checklist handler to build editors for all checked strategies.
        self._on_strat_list_changed()

    def _on_strat_list_changed(self, item=None):
        """Build param editors for every checked strategy in the list.
        If called with item (from itemChanged), it's optional; we always rebuild from current checked set.
        """
        # clear existing rows
        while self.param_form.rowCount() > 0:
            self.param_form.removeRow(0)
        # collect checked strategies
        checked = []
        try:
            for i in range(self.strat_list.count()):
                it = self.strat_list.item(i)
                if it.checkState() == Qt.Checked:
                    checked.append(it.text())
        except Exception:
            checked = []
        # if none checked but combo has a selection, use that
        try:
            if not checked and self.strat_selector.currentText():
                checked = [self.strat_selector.currentText()]
        except Exception:
            pass

        for name in checked:
            try:
                # header for this strategy
                self.param_form.addRow(QLabel(f"--- {name} ---"))
                strat_cls = getattr(backend, 'STRAT_MAP', {}).get(name)
            except Exception:
                strat_cls = None
            if strat_cls is None:
                # fallback to freeform editor
                note = QLabel("No static params found for this strategy. Enter custom params as key=value, one per line:")
                editor = QPlainTextEdit()
                editor.setPlaceholderText('e.g. period=20\nthreshold=0.01')
                prev = self._params_by_strategy.get(name, {})
                if prev:
                    try:
                        lines = [f"{k}={v}" for k, v in prev.items()]
                        editor.setPlainText('\n'.join(lines))
                    except Exception:
                        pass

                def _on_custom_changed(n=name, e=editor):
                    text = e.toPlainText()
                    parsed = {}
                    for raw in text.splitlines():
                        line = raw.strip()
                        if not line or '=' not in line:
                            continue
                        k, v = line.split('=', 1)
                        k = k.strip(); v = v.strip()
                        if v.lower() in ('true', 'false'):
                            parsed_val = v.lower() == 'true'
                        else:
                            try:
                                if '.' in v:
                                    parsed_val = float(v)
                                else:
                                    parsed_val = int(v)
                            except Exception:
                                parsed_val = v
                        parsed[k] = parsed_val
                    if parsed:
                        self._params_by_strategy[n] = parsed
                    else:
                        if n in self._params_by_strategy:
                            try:
                                del self._params_by_strategy[n]
                            except Exception:
                                pass

                editor.textChanged.connect(_on_custom_changed)
                self.param_form.addRow(note)
                self.param_form.addRow(editor)
                continue

            # attempt to read params tuple
            raw = strat_cls.__dict__.get('params', None)
            if raw is None:
                raw = getattr(strat_cls, 'params', None)
            params = None
            if isinstance(raw, (list, tuple)):
                params = raw
            else:
                try:
                    params = list(raw)
                except Exception:
                    params = None

            if not params:
                continue

            for p in params:
                try:
                    key = p[0]
                    default = p[1] if len(p) > 1 else ''
                except Exception:
                    continue
                # create appropriate widget
                w = None
                if isinstance(default, int):
                    w = QSpinBox()
                    w.setRange(-999999999, 999999999)
                    try: w.setValue(int(default))
                    except Exception: pass
                elif isinstance(default, float):
                    w = QDoubleSpinBox()
                    w.setRange(-1e9, 1e9)
                    w.setDecimals(6)
                    try: w.setValue(float(default))
                    except Exception: pass
                elif isinstance(default, bool):
                    w = QCheckBox()
                    try: w.setChecked(bool(default))
                    except Exception: pass
                else:
                    w = QLineEdit()
                    try: w.setText(str(default))
                    except Exception: pass

                # load previously edited value if present
                prev = self._params_by_strategy.get(name, {}).get(key, None)
                if prev is not None:
                    try:
                        if isinstance(w, QSpinBox): w.setValue(int(prev))
                        elif isinstance(w, QDoubleSpinBox): w.setValue(float(prev))
                        elif isinstance(w, QCheckBox): w.setChecked(bool(prev))
                        elif isinstance(w, QLineEdit): w.setText(str(prev))
                    except Exception:
                        pass

                def _make_slot(nm=name, k=key, widget=w):
                    def slot():
                        try:
                            if isinstance(widget, QSpinBox): val = int(widget.value())
                            elif isinstance(widget, QDoubleSpinBox): val = float(widget.value())
                            elif isinstance(widget, QCheckBox): val = bool(widget.isChecked())
                            else: val = widget.text()
                            self._params_by_strategy.setdefault(nm, {})[k] = val
                        except Exception:
                            pass
                    return slot

                if isinstance(w, QSpinBox) or isinstance(w, QDoubleSpinBox):
                    w.valueChanged.connect(_make_slot())
                elif isinstance(w, QCheckBox):
                    w.stateChanged.connect(_make_slot())
                else:
                    w.textChanged.connect(_make_slot())

                self.param_form.addRow(QLabel(key), w)
