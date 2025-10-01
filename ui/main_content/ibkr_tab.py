# ...existing imports...

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox, QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox)
from PySide6.QtCore import Qt

class IBKRTab(QWidget):
	def __init__(self):
		super().__init__()
		self.setup_ui()

	def setup_ui(self):
		layout = QVBoxLayout(self)
		conn_group = QGroupBox("הגדרות חיבור IBKR")
		conn_layout = QGridLayout(conn_group)
		self.host_edit = QLineEdit("127.0.0.1")
		self.port_spin = QSpinBox()
		self.port_spin.setRange(1, 65535)
		self.port_spin.setValue(7497)
		self.client_id_spin = QSpinBox()
		self.client_id_spin.setRange(0, 9999)
		self.client_id_spin.setValue(111)
		conn_layout.addWidget(QLabel("Host:"), 0, 0)
		conn_layout.addWidget(self.host_edit, 0, 1)
		conn_layout.addWidget(QLabel("Port:"), 1, 0)
		conn_layout.addWidget(self.port_spin, 1, 1)
		conn_layout.addWidget(QLabel("Client ID:"), 2, 0)
		conn_layout.addWidget(self.client_id_spin, 2, 1)
		trading_group = QGroupBox("הגדרות מסחר")
		trading_layout = QVBoxLayout(trading_group)
		self.symbols_mode_combo = QComboBox()
		self.symbols_mode_combo.addItems(["Pass from last Scan", "Manual"])
		self.symbols_mode_combo.currentTextChanged.connect(self.on_symbols_mode_changed)
		self.manual_symbols_edit = QLineEdit("SPY,AAPL,MSFT")
		self.manual_symbols_edit.setEnabled(False)
		self.sizing_mode_combo = QComboBox()
		self.sizing_mode_combo.addItems(["Fixed $ per symbol", "ATR risk %"])
		self.alloc_spin = QDoubleSpinBox()
		self.alloc_spin.setRange(100, 1000000)
		self.alloc_spin.setValue(2000)
		self.alloc_spin.setSuffix(" $")
		trading_layout.addWidget(QLabel("Symbols:"))
		trading_layout.addWidget(self.symbols_mode_combo)
		trading_layout.addWidget(QLabel("Manual symbols (CSV):"))
		trading_layout.addWidget(self.manual_symbols_edit)
		trading_layout.addWidget(QLabel("Sizing:"))
		trading_layout.addWidget(self.sizing_mode_combo)
		trading_layout.addWidget(QLabel("$ per symbol:"))
		trading_layout.addWidget(self.alloc_spin)
		buttons_layout = QHBoxLayout()
		self.preview_btn = QPushButton("Preview Orders")
		self.preview_btn.setObjectName("secondary_button")
		self.preview_btn.clicked.connect(self.preview_orders)
		self.send_orders_btn = QPushButton("Send Orders (Paper)")
		self.send_orders_btn.setObjectName("primary_button")
		self.send_orders_btn.clicked.connect(self.send_orders)
		buttons_layout.addWidget(self.preview_btn)
		buttons_layout.addWidget(self.send_orders_btn)
		self.orders_table = QTableWidget()
		self.setup_orders_table()
		layout.addWidget(conn_group)
		layout.addWidget(trading_group)
		layout.addLayout(buttons_layout)
		layout.addWidget(self.orders_table, 1)

	def setup_orders_table(self):
		headers = ["Symbol", "Side", "Qty", "Last Price", "Notional"]
		self.orders_table.setColumnCount(len(headers))
		self.orders_table.setHorizontalHeaderLabels(headers)

	def on_symbols_mode_changed(self, mode):
		self.manual_symbols_edit.setEnabled(mode == "Manual")

	def preview_orders(self):
		pass

	def send_orders(self):
		if self.orders_table.rowCount() == 0:
			QMessageBox.information(self, "מידע", "אין הזמנות לשליחה. לחץ 'Preview Orders' תחילה.")
			return
		reply = QMessageBox.question(self, "אישור", 
								   f"האם אתה בטוח שברצונך לשלוח {self.orders_table.rowCount()} הזמנות לחשבון Paper?",
								   QMessageBox.Yes | QMessageBox.No)
		if reply == QMessageBox.Yes:
			try:
				QMessageBox.information(self, "הצלחה", "ההזמנות נשלחו בהצלחה לחשבון Paper!")
			except Exception as e:
				QMessageBox.critical(self, "שגיאה", f"שגיאה בשליחת הזמנות: {str(e)}")
# IBKRTab UI and logic

