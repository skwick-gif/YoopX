from __future__ import annotations

import os, json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QMessageBox, QFileDialog, QLabel, QToolButton
)
from PySide6.QtCore import Qt, Signal


WATCHLIST_PATH = os.path.join('config', 'watchlist.json')


class WatchListTab(QWidget):
    """Lightweight watchlist manager.
    Features (initial scope):
      * Load/save list of symbols from config/watchlist.json
      * Add multiple symbols (comma/space separated)
      * Remove selected
      * Optional import from text/CSV file (first column) for convenience
    Future (not implemented yet): send subset to Scan tab as universe filter.
    """

    watchlist_changed = Signal(list)  # emits full symbol list after change

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # Header / actions row
        header = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText('הוסף סימבולים (מופרדים בפסיק / רווח)...')
        add_btn = QPushButton('Add')
        add_btn.setObjectName('secondary_button')
        add_btn.clicked.connect(self.add_symbols_from_input)
        rem_btn = QPushButton('Remove Selected')
        rem_btn.setObjectName('secondary_button')
        rem_btn.clicked.connect(self.remove_selected)
        import_btn = QToolButton(); import_btn.setText('📂'); import_btn.setToolTip('ייבוא קובץ רשימת סימבולים')
        import_btn.clicked.connect(self.import_file)
        save_btn = QToolButton(); save_btn.setText('💾'); save_btn.setToolTip('שמירה ידנית (נשמר גם אוטומטית)')
        save_btn.clicked.connect(self.save)
        header.addWidget(self.input_edit, 1)
        header.addWidget(add_btn)
        header.addWidget(rem_btn)
        header.addWidget(import_btn)
        header.addWidget(save_btn)
        lay.addLayout(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(['Symbol'])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        lay.addWidget(self.table, 1)

        # Footer status
        self.status_lbl = QLabel('')
        lay.addWidget(self.status_lbl)

        # Load existing watchlist
        self._symbols = []
        self.load()
        self._refresh_table()

    # -------- Persistence --------
    def load(self):
        try:
            if os.path.exists(WATCHLIST_PATH):
                with open(WATCHLIST_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f) or []
                if isinstance(data, list):
                    self._symbols = [s.strip().upper() for s in data if s and isinstance(s, str)]
        except Exception as e:
            self.status_lbl.setText(f'Load error: {e}')

    def save(self):
        try:
            os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
            with open(WATCHLIST_PATH, 'w', encoding='utf-8') as f:
                json.dump(self._symbols, f, ensure_ascii=False, indent=2)
            self.status_lbl.setText(f'נשמר ({len(self._symbols)} סימבולים)')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to save: {e}')

    # -------- Actions --------
    def add_symbols_from_input(self):
        txt = (self.input_edit.text() or '').strip()
        if not txt:
            return
        parts = [p.strip().upper() for chunk in txt.replace(',', ' ').split() for p in [chunk] if p]
        new_syms = []
        for s in parts:
            if s and s not in self._symbols:
                self._symbols.append(s)
                new_syms.append(s)
        if new_syms:
            self._symbols.sort()
            self._refresh_table()
            self.save()
            self.watchlist_changed.emit(self._symbols)
        self.input_edit.clear()

    def remove_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            try:
                sym = self.table.item(r, 0).text()
                if sym in self._symbols:
                    self._symbols.remove(sym)
            except Exception:
                pass
        self._refresh_table()
        self.save()
        self.watchlist_changed.emit(self._symbols)

    def import_file(self):
        dlg = QFileDialog.getOpenFileName(self, 'בחר קובץ רשימת סימבולים', '', 'Text / CSV (*.txt *.csv);;All Files (*)')
        path = dlg[0]
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # split by newline / comma / space
            raw = [tok.strip().upper() for tok in content.replace(',', ' ').split() if tok.strip()]
            added = 0
            for s in raw:
                if s not in self._symbols:
                    self._symbols.append(s); added += 1
            if added:
                self._symbols.sort()
                self._refresh_table(); self.save(); self.watchlist_changed.emit(self._symbols)
            self.status_lbl.setText(f'ייבוא הסתיים – נוספו {added} סימבולים חדשים')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Import failed: {e}')

    # -------- Helpers --------
    def _refresh_table(self):
        self.table.setRowCount(len(self._symbols))
        for i, sym in enumerate(self._symbols):
            self.table.setItem(i, 0, QTableWidgetItem(sym))
        self.status_lbl.setText(f'{len(self._symbols)} symbols in watchlist')

    def get_symbols(self):
        return list(self._symbols)
