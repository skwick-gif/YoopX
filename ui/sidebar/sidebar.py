# Sidebar main class for sidebar UI
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from styles import StyleManager
from ui.sidebar.sidebar_header import SidebarHeader
from ui.sidebar.data_source_section import DataSourceSection
from ui.sidebar.universe_filter_section import UniverseFilterSection
from ui.sidebar.strategy_section import StrategySection
from ui.sidebar.risk_management_section import RiskManagementSection
from ui.sidebar.preset_section import PresetSection

class Sidebar(QWidget):
    load_data_requested = Signal(dict)
    parameters_changed = Signal(dict)
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.apply_styles()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # allow the sidebar to expand vertically to fill the window
        try:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        except Exception:
            pass
        self.header = SidebarHeader()
        layout.addWidget(self.header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        try:
            scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        except Exception:
            pass
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.data_source = DataSourceSection()
        self.universe_filter = UniverseFilterSection()
        self.strategy = StrategySection()
        self.risk_management = RiskManagementSection()
        self.presets = PresetSection()
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        try:
            content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        except Exception:
            pass
        # zero margins so the content aligns exactly under the header
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.data_source)
        content_layout.addWidget(self.universe_filter)
        content_layout.addWidget(self.strategy)
        content_layout.addWidget(self.risk_management)
        content_layout.addWidget(self.presets)
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)
        self.data_source.load_data_requested.connect(self.load_data_requested)
        self.strategy.parameters_changed.connect(self.parameters_changed)
    def apply_styles(self):
        StyleManager.apply_sidebar_style(self)
    def on_tab_changed(self, tab_index, tab_name=None):
        """Hide the sidebar for certain full-screen tabs (IBKR and Auto-Discovery).

        The MainContent tab order is currently: 0=Scan, 1=Backtest, 2=Optimize,
        3=IBKR, 4=Auto-Discovery. We hide the sidebar for tabs 3 and 4 so the
        main content can occupy the full window. This does not remove the
        sidebar from the layout and it remains available for other tabs.
        """
        try:
            # Prefer to decide based on tab name if provided (more robust than index)
            hide_names = {"🤖 IBKR Paper", "⚡ Auto-Discovery", "IBKR Paper", "Auto-Discovery"}
            should_hide = False
            if tab_name:
                try:
                    if tab_name in hide_names:
                        should_hide = True
                except Exception:
                    pass
            else:
                # fallback to index-based check for compatibility
                if tab_index in (3, 4):
                    should_hide = True

            if should_hide:
                self._collapse()
            else:
                self._expand()
        except Exception:
            # best-effort: don't raise from a UI signal handler
            try:
                self.show()
            except Exception:
                pass

    def _collapse(self, duration: int = 220):
        """Animate the sidebar width down to zero so the main content uses full width."""
        try:
            if not hasattr(self, '_last_width'):
                self._last_width = self.width() or 320
            # animate maximumWidth to 0
            # ensure widget is visible while animating
            try:
                self.show()
            except Exception:
                pass
            anim = QPropertyAnimation(self, b"maximumWidth", self)
            anim.setDuration(duration)
            anim.setEasingCurve(QEasingCurve.InOutCubic)
            anim.setStartValue(self.width() or self._last_width)
            anim.setEndValue(0)
            # keep a reference while animating
            self._last_animation = anim
            # after collapse finishes, hide widget to remove it from accessibility / focus
            try:
                anim.finished.connect(lambda: (self.hide(), setattr(self, '_collapsed', True)))
            except Exception:
                pass
            anim.start()
        except Exception:
            try:
                self.hide()
            except Exception:
                pass

    def _expand(self, duration: int = 220):
        """Restore the sidebar to its previous width (or default) with animation."""
        try:
            target = getattr(self, '_last_width', 320) or 320
            # ensure widget visible before expanding
            try:
                self.show()
            except Exception:
                pass
            anim = QPropertyAnimation(self, b"maximumWidth", self)
            anim.setDuration(duration)
            anim.setEasingCurve(QEasingCurve.InOutCubic)
            anim.setStartValue(self.width() or 0)
            anim.setEndValue(target)
            self._last_animation = anim
            try:
                anim.finished.connect(lambda: setattr(self, '_collapsed', False))
            except Exception:
                pass
            anim.start()
        except Exception:
            try:
                self.show()
            except Exception:
                pass
