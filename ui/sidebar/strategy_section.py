# StrategySection for sidebar UI
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QCheckBox, QSpinBox, QWidget
from PySide6.QtCore import Signal
import backend

class StrategySection(QGroupBox):
    parameters_changed = Signal(dict)
    def __init__(self):
        super().__init__("📈 אסטרטגיה")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Prefer canonical strategy list from backend.STRAT_MAP so the
        # app has a single source of truth for available strategies.
        try:
            keys = list(getattr(backend, 'STRAT_MAP', {}).keys())
            if not keys:
                raise Exception('empty')
        except Exception:
            # fallback to the original hard-coded list when STRAT_MAP is missing
            keys = [
                "SMA Cross",
                "EMA Cross",
                "Donchian Breakout",
                "MACD Trend",
                "RSI(2) @ Bollinger"
            ]
        self.strategy_names = keys
        self.strategy_checkboxes = []
        strategy_layout = QVBoxLayout()
        for name in self.strategy_names:
            cb = QCheckBox(name)
            cb.setChecked(False)
            cb.stateChanged.connect(self.on_strategy_checked)
            self.strategy_checkboxes.append(cb)
            strategy_layout.addWidget(cb)
        layout.addWidget(QLabel("אסטרטגיות לבחירה:"))
        layout.addLayout(strategy_layout)
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        layout.addWidget(self.params_widget)
        self.strategy_checkboxes[0].setChecked(True)
        self.update_parameters_ui(self.strategy_names[0])
        self.setLayout(layout)
    def on_strategy_checked(self, state):
        checked = [cb.text() for cb in self.strategy_checkboxes if cb.isChecked()]
        if checked:
            self.update_parameters_ui(checked[0])
        else:
            self.update_parameters_ui(self.strategy_names[0])
        self.parameters_changed.emit({'strategies': checked})
    def update_parameters_ui(self, strategy):
        for i in reversed(range(self.params_layout.count())):
            self.params_layout.itemAt(i).widget().setParent(None)
        if strategy in ["SMA Cross", "EMA Cross"]:
            self.fast_spin = QSpinBox()
            self.fast_spin.setRange(2, 400)
            self.fast_spin.setValue(10)
            self.slow_spin = QSpinBox()
            self.slow_spin.setRange(2, 600)
            self.slow_spin.setValue(20)
            self.params_layout.addWidget(QLabel("Fast Period:"))
            self.params_layout.addWidget(self.fast_spin)
            self.params_layout.addWidget(QLabel("Slow Period:"))
            self.params_layout.addWidget(self.slow_spin)
        elif strategy == "Donchian Breakout":
            self.upper_spin = QSpinBox()
            self.upper_spin.setRange(5, 250)
            self.upper_spin.setValue(20)
            self.lower_spin = QSpinBox()
            self.lower_spin.setRange(5, 250)
            self.lower_spin.setValue(10)
            self.params_layout.addWidget(QLabel("Upper (N):"))
            self.params_layout.addWidget(self.upper_spin)
            self.params_layout.addWidget(QLabel("Lower (N):"))
            self.params_layout.addWidget(self.lower_spin)
