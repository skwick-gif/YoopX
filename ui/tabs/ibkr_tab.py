from PySide6.QtWidgets import (QWidget,QVBoxLayout,QGroupBox,QGridLayout,QLabel,QLineEdit,QSpinBox,QComboBox,
                               QDoubleSpinBox,QHBoxLayout,QPushButton,QTableWidget,QTableWidgetItem,QMessageBox,
                               QToolButton,QStyle)
from PySide6.QtCore import Qt

class IBKRTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        conn_group = QGroupBox('הגדרות חיבור IBKR'); conn_layout = QGridLayout(conn_group)
        self.host_edit = QLineEdit('127.0.0.1')
        self.port_spin = QSpinBox(); self.port_spin.setRange(1,65535); self.port_spin.setValue(7497)
        self.client_id_spin = QSpinBox(); self.client_id_spin.setRange(0,9999); self.client_id_spin.setValue(111)
        conn_layout.addWidget(QLabel('Host:'),0,0); conn_layout.addWidget(self.host_edit,0,1)
        conn_layout.addWidget(QLabel('Port:'),1,0); conn_layout.addWidget(self.port_spin,1,1)
        conn_layout.addWidget(QLabel('Client ID:'),2,0); conn_layout.addWidget(self.client_id_spin,2,1)
        trading_group = QGroupBox('הגדרות מסחר'); trading_layout = QVBoxLayout(trading_group)
        self.symbols_mode_combo = QComboBox(); self.symbols_mode_combo.addItems(['Pass from last Scan','Manual']); self.symbols_mode_combo.currentTextChanged.connect(self.on_symbols_mode_changed)
        self.manual_symbols_edit = QLineEdit('SPY,AAPL,MSFT'); self.manual_symbols_edit.setEnabled(False)
        self.sizing_mode_combo = QComboBox(); self.sizing_mode_combo.addItems(['Fixed $ per symbol','ATR risk %'])
        self.alloc_spin = QDoubleSpinBox(); self.alloc_spin.setRange(100,1000000); self.alloc_spin.setValue(2000); self.alloc_spin.setSuffix(' $')
        for lbl,w in [('Symbols:',self.symbols_mode_combo),('Manual symbols (CSV):',self.manual_symbols_edit),('Sizing:',self.sizing_mode_combo),('$ per symbol:',self.alloc_spin)]:
            trading_layout.addWidget(QLabel(lbl)); trading_layout.addWidget(w)
        buttons_layout = QHBoxLayout()
        self.preview_btn = QPushButton('Preview Orders'); self.preview_btn.setObjectName('secondary_button'); self.preview_btn.clicked.connect(self.preview_orders)
        self.send_orders_btn = QPushButton('Send Orders (Paper)'); self.send_orders_btn.setObjectName('primary_button'); self.send_orders_btn.clicked.connect(self.send_orders)
        buttons_layout.addWidget(self.preview_btn); buttons_layout.addWidget(self.send_orders_btn)
        self.orders_table = QTableWidget(); self._setup_orders_table()
        help_btn = QToolButton()
        try:
            help_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        except Exception:
            help_btn.setText('?')
        help_btn.setToolTip('עזרה - IBKR')
        from ui.shared.help_viewer import show_markdown_dialog
        help_btn.clicked.connect(lambda: show_markdown_dialog(self,'docs/ibkr_tab.md','IBKR Help'))
        layout.addWidget(conn_group); layout.addWidget(trading_group); layout.addLayout(buttons_layout); layout.addWidget(help_btn); layout.addWidget(self.orders_table,1)

    def _setup_orders_table(self):
        headers=['Symbol','Side','Qty','Last Price','Notional']; self.orders_table.setColumnCount(len(headers)); self.orders_table.setHorizontalHeaderLabels(headers)

    def on_symbols_mode_changed(self, mode): self.manual_symbols_edit.setEnabled(mode=='Manual')

    def preview_orders(self):
        try:
            main_content = self.parentWidget().parentWidget() if hasattr(self,'parentWidget') else None
            data_map = getattr(main_content,'data_map',{}) if main_content is not None else {}
            mode = self.symbols_mode_combo.currentText(); symbols=[]
            if mode=='Manual':
                txt=self.manual_symbols_edit.text() or ''
                symbols=[s.strip().upper() for s in txt.split(',') if s.strip()]
            else:
                symbols=[]
                try:
                    scan_tab=getattr(main_content,'scan_tab',None)
                    if scan_tab and getattr(scan_tab,'_last_scan_results',None):
                        for r in scan_tab._last_scan_results:
                            if r.get('pass')=='Pass': symbols.append(r.get('symbol'))
                except Exception: pass
            symbols=list(dict.fromkeys(symbols))
            self.orders_table.setRowCount(len(symbols))
            alloc=self.alloc_spin.value(); sizing_mode=self.sizing_mode_combo.currentText()
            for row,sym in enumerate(symbols):
                price=None
                try:
                    df=data_map.get(sym)
                    if df is not None:
                        for c in df.columns[::-1]:
                            if 'close' in c.lower(): price=float(df[c].dropna().iloc[-1]); break
                except Exception: price=None
                qty=0
                if price and price>0:
                    if sizing_mode.startswith('Fixed'):
                        qty=int(alloc//price) if price else 0
                    else:
                        qty=int((alloc/price))
                for col,val in enumerate([sym,'BUY',qty,f"{price:.2f}" if price else '', f"{qty*price:.2f}" if price else '']):
                    from PySide6.QtWidgets import QTableWidgetItem
                    self.orders_table.setItem(row,col,QTableWidgetItem(str(val)))
        except Exception as e:
            QMessageBox.critical(self,'שגיאה',f'Preview error: {e}')

    def send_orders(self):
        if self.orders_table.rowCount()==0:
            QMessageBox.information(self,'מידע','אין הזמנות'); return
        QMessageBox.information(self,'מידע','(Mock) הזמנות נשלחו לחשבון Paper')
    # Help handled by shared utility
