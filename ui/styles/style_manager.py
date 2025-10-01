# Centralized style management for QuantDesk UI
from PySide6.QtCore import Qt

class StyleManager:
    """Centralized style management for QuantDesk UI"""
    COLORS = {
        'primary': '#667eea',
        'primary_hover': '#764ba2',
        'secondary': '#f7fafc',
        'background': '#f8fafc',
        'card_bg': '#ffffff',
        'border': '#e2e8f0',
        'border_light': '#f1f5f9',
        'text_primary': '#2d3748',
        'text_secondary': '#4a5568',
        'text_muted': '#718096',
        'success': '#48bb78',
        'warning': '#ed8936',
        'error': '#f56565',
        'info': '#38b2ac',
        # Added subtle accent + shadow tones for modern tab styling
        'accent': '#3b82f6',           # brighter blue accent
        'accent_hover': '#2563eb',
        'accent_bg': '#eef6ff',        # light background for selected pill
        'shadow': 'rgba(0,0,0,0.12)',
        'shadow_strong': 'rgba(0,0,0,0.24)'
    }
    @classmethod
    def get_main_window_style(cls):
        return f"""
        QMainWindow {{
            /* Use the same neutral background as main content to avoid a visible seam */
            background-color: {cls.COLORS['background']};
        }}
        """
    @classmethod
    def get_sidebar_style(cls):
        return f"""
        /* Sidebar container */
        QWidget {{
            background-color: {cls.COLORS['card_bg']};
            border-right: 1px solid {cls.COLORS['border']};
        }}
        /* Sidebar header */
        QWidget[objectName="sidebar_header"] {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 {cls.COLORS['primary']}, 
                                      stop: 1 {cls.COLORS['primary_hover']});
            color: white;
            border: none;
        }}
        /* Logo */
        QLabel[objectName="logo"] {{
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-bottom: 4px;
        }}
        /* Subtitle */
        QLabel[objectName="subtitle"] {{
            font-size: 14px;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 300;
        }}
        /* Group boxes (sections) */
        QGroupBox {{
            font-size: 16px;
            font-weight: 600;
            color: {cls.COLORS['text_secondary']};
            border: none;
            border-bottom: 1px solid {cls.COLORS['border_light']};
            padding: 20px;
            margin: 0px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 0px;
            padding: 0px 0px 16px 0px;
        }}
        /* Form controls */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
            padding: 10px 12px;
            border: 1.5px solid {cls.COLORS['border']};
            border-radius: 8px;
            font-size: 14px;
            background-color: {cls.COLORS['card_bg']};
            selection-background-color: {cls.COLORS['primary']};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, 
        QComboBox:focus, QTextEdit:focus {{
            border-color: {cls.COLORS['primary']};
        }}
        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, 
        QComboBox:hover, QTextEdit:hover {{
            border-color: #cbd5e0;
        }}
        /* Labels */
        QLabel {{
            color: {cls.COLORS['text_secondary']};
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 6px;
        }}
        /* Checkboxes and Radio buttons */
        QCheckBox, QRadioButton {{
            color: {cls.COLORS['text_secondary']};
            font-size: 14px;
            spacing: 8px;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {cls.COLORS['primary']};
            border: 2px solid {cls.COLORS['primary']};
            border-radius: 3px;
        }}
        QCheckBox::indicator:unchecked {{
            background-color: white;
            border: 2px solid {cls.COLORS['border']};
            border-radius: 3px;
        }}
        /* Buttons */
        QPushButton {{
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            min-height: 20px;
        }}
        QPushButton[objectName="primary_button"] {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 {cls.COLORS['primary']}, 
                                      stop: 1 {cls.COLORS['primary_hover']});
            color: white;
        }}
        QPushButton[objectName="primary_button"]:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 {cls.COLORS['primary_hover']}, 
                                      stop: 1 {cls.COLORS['primary']});
        }}
        QPushButton[objectName="primary_button"]:pressed {{
            background: {cls.COLORS['primary_hover']};
        }}
        QPushButton[objectName="secondary_button"] {{
            background-color: {cls.COLORS['secondary']};
            color: {cls.COLORS['text_secondary']};
            border: 1px solid {cls.COLORS['border']};
        }}
        QPushButton[objectName="secondary_button"]:hover {{
            background-color: #edf2f7;
        }}
        /* Toggle button */
        QPushButton[objectName="toggle_button"] {{
            background-color: {cls.COLORS['info']};
            color: white;
            border: 1px solid {cls.COLORS['info']};
        }}
        QPushButton[objectName="toggle_button"]:checked {{
            background-color: {cls.COLORS['success']};
            border-color: {cls.COLORS['success']};
        }}
        QPushButton[objectName="toggle_button"]:hover {{
            background-color: #2d8aba;
        }}
        /* Premium button - for rigorous scanning */
        QPushButton[objectName="premium_button"] {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 #ff6b6b, stop: 0.5 #ff8e8e, stop: 1 #ffa8a8);
            color: white;
            border: 2px solid #ff5757;
            font-weight: 600;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        QPushButton[objectName="premium_button"]:checked {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 #ff4757, stop: 0.5 #ff3838, stop: 1 #ff2f2f);
            border-color: #ff3838;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
        }}
        QPushButton[objectName="premium_button"]:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 #ff4757, stop: 0.5 #ff6b6b, stop: 1 #ff8e8e);
            transform: translateY(-1px);
        }}
        QPushButton[objectName="premium_button"]:pressed {{
            background: #ff3838;
            transform: translateY(0px);
        }}
        /* Scroll area */
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {cls.COLORS['border_light']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {cls.COLORS['border']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {cls.COLORS['text_muted']};
        }}
        """
    @classmethod
    def get_main_content_style(cls):
        return f"""
        /* Main content container */
        QWidget {{
            background-color: {cls.COLORS['background']};
        }}
        /* Tab widget */
        QTabWidget::pane {{
            border: none;
            background-color: {cls.COLORS['background']};
        }}
        QTabWidget::tab-bar {{
            alignment: left;
            margin: 0px;
            padding: 0px;
        }}
        /* --- Modern Tab Styling: pill shaped with accent indicator --- */
        QTabBar::tab {{
            padding: 6px 14px; /* reduced for more tabs per row */
            margin: 4px 4px 0 0; /* tighter spacing */
            border: 1px solid {cls.COLORS['border']};
            border-radius: 12px;
            background-color: {cls.COLORS['card_bg']};
            color: {cls.COLORS['text_secondary']};
            font-weight: 600;
            min-width: 90px;
            /* transition: all 120ms ease; */ /* Qt doesn't support transitions - removed to prevent warnings */
        }}
        QTabBar::tab:hover {{
            background-color: {cls.COLORS['secondary']};
            color: {cls.COLORS['text_primary']};
            border-color: {cls.COLORS['border']};
        }}
        QTabBar::tab:selected {{
            background-color: {cls.COLORS['accent_bg']};
            color: {cls.COLORS['accent']};
            border: 1px solid {cls.COLORS['accent']};
            font-weight: 700;
        }}
        /* Focus/keyboard navigation outline */
        QTabBar::tab:focus {{
            outline: none;
            border: 1px solid {cls.COLORS['primary_hover']};
        }}
        /* Bottom accent bar under the whole tab bar for visual separation */
        QTabWidget::pane::top {{
            border-top: 0px;
            margin-top: -4px;
        }}
        QTabWidget::pane {{
            border: none;
        }}
        /* Optional subtle shadow mimic (Qt lacks real box-shadow, emulate via border colors if needed) */
        /* Could enhance further with a wrapper QFrame if 3D depth required */
        /* Cards/Frames */
        QFrame[objectName="card"] {{
            background-color: {cls.COLORS['card_bg']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 12px;
            padding: 24px;
            margin: 8px;
        }}
        /* Section titles */
        QLabel[objectName="section_title"] {{
            font-size: 18px;
            font-weight: 600;
            color: {cls.COLORS['text_primary']};
            margin-bottom: 20px;
        }}
        /* Status labels */
        QLineEdit[objectName="status_info"] {{
            background-color: #e6fffa;
            color: #234e52;
            border: 1px solid #b2f5ea;
            border-radius: 4px;
            padding: 6px 12px;
            margin: 0px;
            font-size: 12px;
            text-align: left;
            selection-background-color: {cls.COLORS['primary']};
            selection-color: white;
        }}
        QLabel[objectName="status_info"] {{
            background-color: #e6fffa;
            color: #234e52;
            border: 1px solid #b2f5ea;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 16px 0px;
        }}
        /* Metric cards */
        QFrame[objectName="metric_card"] {{
            background-color: {cls.COLORS['card_bg']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 10px;
            padding: 20px;
            min-width: 120px;
            max-width: 200px;
        }}
        QLabel[objectName="metric_value"] {{
            font-size: 24px;
            font-weight: 700;
            color: {cls.COLORS['text_primary']};
        }}
        QLabel[objectName="metric_label"] {{
            font-size: 14px;
            color: {cls.COLORS['text_muted']};
            margin-top: 4px;
        }}
        /* Tables */
        QTableWidget {{
            background-color: {cls.COLORS['card_bg']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 8px;
            gridline-color: {cls.COLORS['border_light']};
            selection-background-color: {cls.COLORS['primary']};
            selection-color: white;
        }}
        QTableWidget::item {{
            padding: 12px 16px;
            border-bottom: 1px solid {cls.COLORS['border_light']};
        }}
        QTableWidget::item:hover {{
            background-color: {cls.COLORS['secondary']};
        }}
        QHeaderView::section {{
            background-color: {cls.COLORS['secondary']};
            color: {cls.COLORS['text_secondary']};
            padding: 12px 16px;
            border: none;
            border-bottom: 1px solid {cls.COLORS['border']};
            font-weight: 600;
        }}
        /* Progress bar */
        QProgressBar {{
            border: none;
            border-radius: 3px;
            background-color: {cls.COLORS['border']};
            height: 6px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                      stop: 0 {cls.COLORS['primary']}, 
                                      stop: 1 {cls.COLORS['primary_hover']});
            border-radius: 3px;
        }}
        /* Bottom unified bar */
        QFrame[objectName="bottom_bar"] {{
            background-color: {cls.COLORS['card_bg']};
            border-top: 1px solid {cls.COLORS['border']};
        }}
        QPushButton[objectName="toolbar_button"] {{
            background-color: {cls.COLORS['secondary']};
            color: {cls.COLORS['text_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 500;
            text-align: center;
            min-width: 90px;
            max-width: 140px;
            height: 28px;
        }}
        QPushButton[objectName="toolbar_button"]:hover {{
            background-color: #edf2f7;
        }}
        QPushButton[objectName="toolbar_button"]:pressed {{
            background-color: #e2e8f0;
        }}
        /* Stop button (danger style) */
        QPushButton[objectName="stop_button"] {{
            background-color: {cls.COLORS['error']};
            color: white;
            border: 1px solid #e53e3e;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
            text-align: center;
            min-width: 60px;
            max-width: 80px;
            height: 28px;
        }}
        QPushButton[objectName="stop_button"]:hover {{
            background-color: #e53e3e;
        }}
        QPushButton[objectName="stop_button"]:pressed {{
            background-color: #c53030;
        }}
        /* Cache refresh button (small circular) */
        QPushButton[objectName="cache_refresh_button"] {{
            background-color: {cls.COLORS['secondary']};
            color: {cls.COLORS['text_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 14px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton[objectName="cache_refresh_button"]:hover {{
            background-color: #edf2f7;
        }}
        QPushButton[objectName="cache_refresh_button"]:pressed {{
            background-color: #e2e8f0;
        }}
        /* Cache info box */
        QLabel[objectName="cache_info_box"] {{
            background-color: {cls.COLORS['accent_bg']};
            color: {cls.COLORS['text_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 500;
        }}
        /* Group boxes in main content */
        QGroupBox {{
            font-size: 16px;
            font-weight: 600;
            color: {cls.COLORS['text_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: 8px;
            padding-top: 15px;
            margin-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0px 8px 0px 8px;
            background-color: {cls.COLORS['background']};
        }}
        /* Checked toggle buttons - used for strategy selection */
        QPushButton[checked="true"] {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 {cls.COLORS['primary']}, 
                                      stop: 1 {cls.COLORS['primary_hover']});
            color: white;
            border: 1px solid {cls.COLORS['primary']};
        }}
        QPushButton[checked="true"]:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                      stop: 0 {cls.COLORS['primary_hover']}, 
                                      stop: 1 {cls.COLORS['primary']});
        }}
        """
    @classmethod
    def apply_main_window_style(cls, widget):
        widget.setStyleSheet(cls.get_main_window_style())
    @classmethod
    def apply_sidebar_style(cls, widget):
        widget.setStyleSheet(cls.get_sidebar_style())
        if hasattr(widget, 'header'):
            widget.header.setObjectName("sidebar_header")
    @classmethod
    def apply_main_content_style(cls, widget):
        widget.setStyleSheet(cls.get_main_content_style())
