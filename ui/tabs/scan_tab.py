from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QLineEdit, QPushButton, QGroupBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QCheckBox, QTextBrowser, QSizePolicy, QDialog, QDialogButtonBox, QToolButton, QStyle
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QColor
import json, os
from ui.worker_thread import WorkerThread
from ui.shared.settings_manager import load_settings, save_settings


class ScanTab(QWidget):
    run_scan_requested = Signal(dict)
    train_ml_requested = Signal(dict)
    calibrate_requested = Signal(dict)
    settings_changed = Signal(dict)

    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self._last_scan_results = []
        self._last_enhanced_results = []  # Store enhanced scan results for score detail panel
        self._last_backtest_results = self._last_scan_results
        self._settings = load_settings()
        self._build_ui()
        self._apply_persisted()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        # Toolbar minimal: Run / Stop / Settings + Quick filters + status
        from PySide6.QtWidgets import QLineEdit as _QLineEdit, QDoubleSpinBox as _QDoubleSpinBox, QLabel as _QLabel
        toolbar = QHBoxLayout(); toolbar.setSpacing(8)
        self.run_scan_btn = QPushButton('הרץ SCAN'); self.run_scan_btn.setObjectName('primary_button'); self.run_scan_btn.clicked.connect(self.run_scan)
        self.stop_btn = QPushButton('עצור'); self.stop_btn.setObjectName('secondary_button'); self.stop_btn.clicked.connect(self.cancel_scan); self.stop_btn.setVisible(False)
        
        # Enhanced scan toggle
        self.enhanced_mode_btn = QPushButton('Enhanced ON'); self.enhanced_mode_btn.setObjectName('toggle_button'); 
        self.enhanced_mode_btn.setCheckable(True); self.enhanced_mode_btn.setChecked(True)
        self.enhanced_mode_btn.clicked.connect(self._toggle_enhanced_mode)
        
        # Rigorous scan toggle - for premium quality filtering
        self.rigorous_mode_btn = QPushButton('🎯 RIGOROUS'); self.rigorous_mode_btn.setObjectName('premium_button')
        self.rigorous_mode_btn.setCheckable(True); self.rigorous_mode_btn.setChecked(False)
        self.rigorous_mode_btn.setVisible(False)  # Hidden until working
        self.rigorous_mode_btn.setToolTip('סריקה נוקשה - רק מניות באיכות יוצאת מן הכלל')
        self.rigorous_mode_btn.clicked.connect(self._toggle_rigorous_mode)
        
        # Rigorous profile selector (dropdown)
        self.rigorous_profile_combo = QComboBox()
        self.rigorous_profile_combo.addItems(['Conservative', 'Growth', 'Elite'])
        self.rigorous_profile_combo.setCurrentText('Conservative')
        self.rigorous_profile_combo.setToolTip('פרופיל סינון: Conservative (שמרני), Growth (צמיחה), Elite (עלית)')
        self.rigorous_profile_combo.setVisible(False)  # Hidden until working
        
        self.settings_btn = QPushButton('הגדרות'); self.settings_btn.setObjectName('secondary_button'); self.settings_btn.clicked.connect(self._open_settings_dialog)
        self.quick_symbols_edit = _QLineEdit(); self.quick_symbols_edit.setPlaceholderText('Symbols CSV'); self.quick_symbols_edit.editingFinished.connect(self._apply_quick_filters)
        self.quick_min_prob = _QDoubleSpinBox(); self.quick_min_prob.setRange(0.0,1.0); self.quick_min_prob.setDecimals(2); self.quick_min_prob.setSingleStep(0.01); self.quick_min_prob.setPrefix('P>='); self.quick_min_prob.editingFinished.connect(self._apply_quick_filters)
        self.status_label = QLabel(''); self.status_label.setObjectName('status_info')
        for w in (self.run_scan_btn,self.stop_btn,self.enhanced_mode_btn,self.rigorous_mode_btn,self.rigorous_profile_combo,self.settings_btn): toolbar.addWidget(w)
        toolbar.addWidget(_QLabel('|'))
        toolbar.addWidget(self.quick_symbols_edit); toolbar.addWidget(self.quick_min_prob)
        toolbar.addStretch(); toolbar.addWidget(self.status_label)
        # Help icon (small unobtrusive) opening docs/ui_behaviors.md
        self.help_btn = QToolButton()
        try:
            self.help_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        except Exception:
            self.help_btn.setText('?')
        self.help_btn.setToolTip('עזרה: הסבר על הכפתורים וההתנהגות')
        self.help_btn.setAutoRaise(True)
        from ui.shared.help_viewer import show_markdown_dialog
        self.help_btn.clicked.connect(lambda: show_markdown_dialog(self, 'docs/ui_behaviors.md', 'עזרה'))
        toolbar.addWidget(self.help_btn)
        main_layout.addLayout(toolbar)

        # Results panel only (settings moved to dialog)
        results_panel = QFrame(); results_panel.setObjectName('card')
        results_layout = QVBoxLayout(results_panel)
        header_layout = QHBoxLayout(); title = QLabel('תוצאות סריקה'); title.setObjectName('section_title')
        self.download_btn = QPushButton('הורד CSV'); self.download_btn.setObjectName('secondary_button'); self.download_btn.clicked.connect(self.download_results)
        header_layout.addWidget(title); header_layout.addStretch(); header_layout.addWidget(self.download_btn)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        self.results_table = QTableWidget(); self._setup_table()
        results_layout.addLayout(header_layout); results_layout.addWidget(self.progress_bar)
        # Summary bar
        self.summary_frame = QFrame(); self.summary_frame.setObjectName('summary_bar')
        from PySide6.QtWidgets import QHBoxLayout as _QHB
        _sf_l = _QHB(self.summary_frame); _sf_l.setContentsMargins(6,2,6,2); _sf_l.setSpacing(12)
        self.summary_label = QLabel('Summary: --'); self.summary_label.setObjectName('summary_text')
        _sf_l.addWidget(self.summary_label); _sf_l.addStretch(1)
        results_layout.addWidget(self.summary_frame)
        # Side score detail panel
        self.score_side_panel = QFrame(); self.score_side_panel.setObjectName('score_side_panel')
        sp_lay = QVBoxLayout(self.score_side_panel); sp_lay.setContentsMargins(6,6,6,6); sp_lay.setSpacing(4)
        sp_title = QLabel('Score Detail'); sp_title.setObjectName('section_subtitle'); sp_lay.addWidget(sp_title)
        from PySide6.QtWidgets import QTextBrowser as _QTB
        self.score_detail_browser = _QTB(); self.score_detail_browser.setPlaceholderText('בחר שורה להצגת פירוק')
        # Collapse toggle button (feature 7) added AFTER creating browser
        self.side_toggle_btn = QPushButton('Hide ▶')
        self.side_toggle_btn.setObjectName('secondary_button')
        self.side_toggle_btn.setMaximumWidth(90)
        def _toggle_side():
            vis = self.score_detail_browser.isVisible()
            self.score_detail_browser.setVisible(not vis)
            if vis:
                self.side_toggle_btn.setText('Show ◀')
            else:
                self.side_toggle_btn.setText('Hide ▶')
            try:
                self._settings['side_panel_visible'] = (not vis)
                save_settings(self._settings)
            except Exception:
                pass
        try:
            self.side_toggle_btn.clicked.connect(_toggle_side)
        except Exception:
            pass
        sp_lay.addWidget(self.side_toggle_btn)
        sp_lay.addWidget(self.score_detail_browser,1)
        table_wrap = QHBoxLayout(); table_wrap.setContentsMargins(0,0,0,0); table_wrap.setSpacing(6)
        table_wrap.addWidget(self.results_table,4); table_wrap.addWidget(self.score_side_panel,2)
        results_layout.addLayout(table_wrap)
        main_layout.addWidget(results_panel,1)

        # Build the hidden settings dialog widgets now so run_scan works even before user opens dialog
        self._init_settings_dialog()

    def _init_settings_dialog(self):
        if hasattr(self, '_settings_dialog') and self._settings_dialog:
            return
        self._settings_dialog = QDialog(self)
        self._settings_dialog.setWindowTitle('הגדרות סריקה')
        self._settings_dialog.setModal(False)
        layout_root = QVBoxLayout(self._settings_dialog)
        layout_root.setSpacing(8)
        layout_root.setContentsMargins(10, 10, 10, 10)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)
        layout_root.addLayout(grid)

        # Basic
        # Strategy multi-select buttons instead of dropdown
        self._strategy_names = ["Donchian Breakout","SMA Cross","EMA Cross","MACD Trend","RSI(2) @ Bollinger"]
        from PySide6.QtWidgets import QHBoxLayout
        self.strategy_btn_row = QWidget()
        s_layout = QHBoxLayout(self.strategy_btn_row); s_layout.setContentsMargins(0,0,0,0); s_layout.setSpacing(4)
        self.strategy_buttons = {}
        for name in self._strategy_names:
            btn = QPushButton(name.split()[0])  # short label (can adjust later if ambiguity)
            btn.setCheckable(True)
            btn.setObjectName('chip_button')
            btn.setToolTip(name)
            btn.toggled.connect(lambda checked, full=name: self._on_strategy_toggled(full, checked))
            s_layout.addWidget(btn)
            self.strategy_buttons[name] = btn
        s_layout.addStretch(1)
        # default: first selected
        try:
            self.strategy_buttons[self._strategy_names[0]].setChecked(True)
        except Exception:
            pass
        # StyleSheet for chip buttons (checked state coloring)
        try:
            self.strategy_btn_row.setStyleSheet(
                "QPushButton#chip_button {"
                "background:#3a3d41; border:1px solid #555; border-radius:11px; padding:4px 10px; color:#d0d0d0; font-size:12px;"
                "}"
                "QPushButton#chip_button:hover { border-color:#888; }"
                "QPushButton#chip_button:checked { background:#2563eb; border:1px solid #1d4ed8; color:#ffffff; font-weight:600; }"
                "QPushButton#chip_button:checked:hover { border-color:#1e40af; }"
            )
        except Exception:
            pass
        # Removed: free-text patterns edit, manual symbols input, universe limit spin (always full universe)
        self.patterns_edit = None
        self.symbols_edit = None
        self.universe_limit_spin = None
        self.lookback_spin = QSpinBox(); self.lookback_spin.setRange(5,200); self.lookback_spin.setValue(30)
        self.rr_target_combo = QComboBox(); self.rr_target_combo.addItems(["2xATR","Boll mid","Donchian high"])
        self.min_rr_spin = QDoubleSpinBox(); self.min_rr_spin.setRange(0.0,10.0); self.min_rr_spin.setSingleStep(0.1)
        basic_box = QGroupBox('בסיס')
        b_l = QVBoxLayout(basic_box); b_l.setSpacing(4); b_l.setContentsMargins(6,6,6,6)
        # Add placeholder extra strategy buttons (future expansion)
        self._extra_strategy_names = ["BreakoutX","MeanRevY","VolSpikeZ","GapPlay","RangeFade"]
        self.extra_strategy_row = QWidget(); from PySide6.QtWidgets import QHBoxLayout as _QHB
        es_lay = _QHB(self.extra_strategy_row); es_lay.setContentsMargins(0,0,0,0); es_lay.setSpacing(4)
        self.extra_strategy_buttons = {}
        for nm in self._extra_strategy_names:
            b = QPushButton(nm); b.setCheckable(True); b.setObjectName('chip_button'); b.setToolTip('(עתידי) '+nm)
            b.setEnabled(False)  # disabled until implemented
            b.toggled.connect(lambda c, full=nm: self._on_strategy_toggled(full, c))
            es_lay.addWidget(b); self.extra_strategy_buttons[nm] = b
        es_lay.addStretch(1)

        # Candlestick pattern buttons (multi-select)
        self._pattern_names = ["ENGULFING","DOJI","HAMMER","HARAMI","MORNINGSTAR","SHOOTINGSTAR","PIERCING"]
        self.pattern_btn_row = QWidget(); p_lay = _QHB(self.pattern_btn_row); p_lay.setContentsMargins(0,0,0,0); p_lay.setSpacing(4)
        self.pattern_buttons = {}
        for pat in self._pattern_names:
            pb = QPushButton(pat); pb.setCheckable(True); pb.setObjectName('chip_button'); pb.setToolTip(pat)
            p_lay.addWidget(pb); self.pattern_buttons[pat] = pb
        p_lay.addStretch(1)
        # Style reuse (chip_button) already applied earlier to parent row; apply to new rows too
        try:
            # Extra (future) strategies keep regular size
            self.extra_strategy_row.setStyleSheet(
                "QPushButton#chip_button {background:#3a3d41; border:1px solid #555; border-radius:11px; padding:4px 10px; color:#d0d0d0; font-size:12px;}"
                "QPushButton#chip_button:hover { border-color:#888; }"
                "QPushButton#chip_button:checked { background:#9333ea; border:1px solid #7e22ce; color:#ffffff; font-weight:600;}"
                "QPushButton#chip_button:checked:hover { border-color:#6b21a8; }"
            )
            # Candlestick pattern buttons slightly smaller so full text fits better
            self.pattern_btn_row.setStyleSheet(
                "QPushButton#chip_button {background:#3a3d41; border:1px solid #555; border-radius:11px; padding:3px 8px; color:#d0d0d0; font-size:11px;}"
                "QPushButton#chip_button:hover { border-color:#888; }"
                "QPushButton#chip_button:checked { background:#9333ea; border:1px solid #7e22ce; color:#ffffff; font-weight:600;}"
                "QPushButton#chip_button:checked:hover { border-color:#6b21a8; }"
            )
        except Exception:
            pass

        for lbl, w in [
            ('אסטרטגיות:', self.strategy_btn_row), ('אסטרטגיות (עתידי):', self.extra_strategy_row), ('דפוסי נרות:', self.pattern_btn_row), ('Lookback:', self.lookback_spin), ('RR Target:', self.rr_target_combo), ('Min R:R:', self.min_rr_spin)
        ]:
            b_l.addWidget(QLabel(lbl)); b_l.addWidget(w)
        # Strategy params dialog button
        self.strategy_params_btn = QPushButton('פרמטרים...')
        self.strategy_params_btn.setObjectName('secondary_button')
        self.strategy_params_btn.clicked.connect(self._open_strategy_params_dialog)
        b_l.addWidget(self.strategy_params_btn)
        # Reset to preset button (feature 5)
        self.reset_preset_btn = QPushButton('איפוס לברירת מחדל')
        self.reset_preset_btn.setObjectName('secondary_button')
        self.reset_preset_btn.setToolTip('Reset weights / formula / horizons to preset')
        self.reset_preset_btn.clicked.connect(self._reset_to_preset)
        b_l.addWidget(self.reset_preset_btn)

        # Advanced / Model
        self.fast_spin = QSpinBox(); self.fast_spin.setRange(2,400); self.fast_spin.setValue(10)
        self.slow_spin = QSpinBox(); self.slow_spin.setRange(3,800); self.slow_spin.setValue(20)
        self.upper_spin = QSpinBox(); self.upper_spin.setRange(5,400); self.upper_spin.setValue(20)
        self.lower_spin = QSpinBox(); self.lower_spin.setRange(2,400); self.lower_spin.setValue(10)
        self.bb_p_spin = QSpinBox(); self.bb_p_spin.setRange(5,400); self.bb_p_spin.setValue(20)
        self.bb_k_spin = QDoubleSpinBox(); self.bb_k_spin.setRange(0.5,10.0); self.bb_k_spin.setSingleStep(0.1); self.bb_k_spin.setValue(2.0)
        self.ema_trend_spin = QSpinBox(); self.ema_trend_spin.setRange(20,1000); self.ema_trend_spin.setValue(200)
        self.rsi_p_spin = QSpinBox(); self.rsi_p_spin.setRange(1,50); self.rsi_p_spin.setValue(2)
        self.rsi_buy_spin = QSpinBox(); self.rsi_buy_spin.setRange(1,100); self.rsi_buy_spin.setValue(10)
        self.model_combo = QComboBox(); self.model_combo.addItems(['rf','xgb','lgbm','ensemble'])
        self.ml_thresh_spin = QDoubleSpinBox(); self.ml_thresh_spin.setRange(0.0,1.0); self.ml_thresh_spin.setDecimals(2); self.ml_thresh_spin.setSingleStep(0.01); self.ml_thresh_spin.setValue(0.0)
        adv_box = QGroupBox('מתקדם + מודל')
        adv_grid = QGridLayout(adv_box); adv_grid.setHorizontalSpacing(6); adv_grid.setVerticalSpacing(4); adv_grid.setContentsMargins(6,6,6,6)
        for r, (lbl, w) in enumerate([
            ('Fast', self.fast_spin), ('Slow', self.slow_spin), ('Donch Upper', self.upper_spin), ('Donch Lower', self.lower_spin), ('EMA Trend', self.ema_trend_spin), ('BB Period', self.bb_p_spin), ('BB k', self.bb_k_spin), ('RSI Period', self.rsi_p_spin), ('RSI Buy<=', self.rsi_buy_spin), ('Model', self.model_combo), ('Min ML Prob', self.ml_thresh_spin)
        ]):
            adv_grid.addWidget(QLabel(lbl+':'), r, 0); adv_grid.addWidget(w, r, 1)
        self.adv_box = adv_box

        # Filters
        self.min_price_spin = QDoubleSpinBox(); self.min_price_spin.setRange(0.0,100000.0); self.min_price_spin.setDecimals(2)
        self.max_price_spin = QDoubleSpinBox(); self.max_price_spin.setRange(0.0,100000.0); self.max_price_spin.setDecimals(2)
        self.min_atr_spin = QDoubleSpinBox(); self.min_atr_spin.setRange(0.0,10000.0); self.min_atr_spin.setDecimals(4)
        self.max_atr_spin = QDoubleSpinBox(); self.max_atr_spin.setRange(0.0,10000.0); self.max_atr_spin.setDecimals(4)
        self.max_age_spin = QSpinBox(); self.max_age_spin.setRange(0,1000); self.max_age_spin.setValue(0)
        filters_box = QGroupBox('סינונים')
        fil_grid = QGridLayout(filters_box); fil_grid.setHorizontalSpacing(6); fil_grid.setVerticalSpacing(4); fil_grid.setContentsMargins(6,6,6,6)
        for r, (lbl, w) in enumerate([
            ('Min Price', self.min_price_spin), ('Max Price', self.max_price_spin), ('Min ATR', self.min_atr_spin), ('Max ATR', self.max_atr_spin), ('Max Age', self.max_age_spin)
        ]):
            fil_grid.addWidget(QLabel(lbl+':'), r, 0); fil_grid.addWidget(w, r, 1)
        self.extra_box = filters_box

        # Scoring / Horizons
        self.score_formula_combo = QComboBox(); self.score_formula_combo.addItems(['weighted','geometric'])
        self.w_prob_spin = QDoubleSpinBox(); self.w_prob_spin.setRange(0.0,2.0); self.w_prob_spin.setSingleStep(0.01); self.w_prob_spin.setValue(0.55)
        self.w_rr_spin = QDoubleSpinBox(); self.w_rr_spin.setRange(0.0,2.0); self.w_rr_spin.setSingleStep(0.01); self.w_rr_spin.setValue(0.25)
        self.w_fresh_spin = QDoubleSpinBox(); self.w_fresh_spin.setRange(0.0,2.0); self.w_fresh_spin.setSingleStep(0.01); self.w_fresh_spin.setValue(0.15)
        self.w_pattern_spin = QDoubleSpinBox(); self.w_pattern_spin.setRange(0.0,2.0); self.w_pattern_spin.setSingleStep(0.01); self.w_pattern_spin.setValue(0.05)
        self.horizons_edit = QLineEdit(); self.horizons_edit.setPlaceholderText('5,10,20')
        self.horizon_select = QComboBox(); self.horizon_select.setPlaceholderText('Use Horizon (optional)')
        # Historical training cutoff - days back from today
        self.training_days_back_spin = QSpinBox()
        self.training_days_back_spin.setRange(30, 365)  # 30 to 365 trading days back
        self.training_days_back_spin.setValue(60)  # default 60 trading days back
        self.training_days_back_spin.setSuffix(' trading days')
        self.training_days_back_spin.setToolTip('היסטורי: כמה ימי מסחר אחורה לכלול בנתוני האימון (לא כולל סופי שבוע)')
        self.auto_rescan_chk = QCheckBox('Auto-rescan after train'); self.auto_rescan_chk.setChecked(True)
        try:
            self.auto_rescan_chk.setStyleSheet(
                'QCheckBox { padding:1px; }'
                'QCheckBox::indicator { width:16px; height:16px; border:1px solid #888; background:#fff; }'
                'QCheckBox::indicator:checked { background:#16a34a; border:2px solid #0d7a35; }'
                'QCheckBox::indicator:unchecked { background:#fff; }'
            )
        except Exception:
            pass
        scoring_box = QGroupBox('Scoring / Horizons')
        sc_grid = QGridLayout(scoring_box); sc_grid.setHorizontalSpacing(6); sc_grid.setVerticalSpacing(4); sc_grid.setContentsMargins(6,6,6,6)
        for r, (lbl, w) in enumerate([
            ('Formula', self.score_formula_combo), ('W Prob', self.w_prob_spin), ('W R:R', self.w_rr_spin), ('W Fresh', self.w_fresh_spin), ('W Pattern', self.w_pattern_spin), ('Train Horizons', self.horizons_edit), ('Use Horizon', self.horizon_select), ('Training Cutoff', self.training_days_back_spin)
        ]):
            sc_grid.addWidget(QLabel(lbl+':'), r, 0); sc_grid.addWidget(w, r, 1)
        sc_grid.addWidget(self.auto_rescan_chk, r+1, 0, 1, 2)

        # Actions
        actions_box = QGroupBox('Actions')
        act_l = QHBoxLayout(actions_box); act_l.setSpacing(6); actions_box.setContentsMargins(6,6,6,6)
        self.train_btn = QPushButton('Train ML'); self.train_btn.setObjectName('secondary_button'); self.train_btn.clicked.connect(self.train_ml)
        self.calib_btn = QPushButton('Calibrate'); self.calib_btn.setObjectName('secondary_button'); self.calib_btn.clicked.connect(self.calibrate_ml)
        self.thresh_btn = QPushButton('Suggest Thresh'); self.thresh_btn.setObjectName('secondary_button')
        self.optimize_weights_btn = QPushButton('Optimize Weights'); self.optimize_weights_btn.setObjectName('secondary_button')
        self.explain_btn = QPushButton('Explain Row'); self.explain_btn.setObjectName('secondary_button')
        self.score_decomp_btn = QPushButton('Score Decomp'); self.score_decomp_btn.setObjectName('secondary_button')
        # Export breakdown CSV (feature 8)
        self.export_breakdown_btn = QPushButton('Export Breakdown')
        self.export_breakdown_btn.setObjectName('secondary_button')
        self.export_breakdown_btn.setToolTip('Export score component breakdown for top N rows to CSV')
        self.export_breakdown_btn.clicked.connect(self._export_breakdown_csv)
        for b in (self.train_btn, self.calib_btn, self.thresh_btn, self.optimize_weights_btn, self.explain_btn, self.score_decomp_btn, self.export_breakdown_btn):
            act_l.addWidget(b)
        act_l.addStretch(1)

        # Layout 4 columns
        grid.addWidget(basic_box, 0, 0)
        grid.addWidget(adv_box, 0, 1)
        grid.addWidget(filters_box, 0, 2)
        grid.addWidget(scoring_box, 0, 3)
        for i in range(4):
            grid.setColumnStretch(i, 1)

        # Dialog size smaller
        try:
            target_w = 1350
            target_h = 600
            screen_geo = self.screen().availableGeometry() if hasattr(self, 'screen') and self.screen() else None
            if screen_geo:
                target_w = min(target_w, int(screen_geo.width()*0.9))
                target_h = min(target_h, int(screen_geo.height()*0.85))
            self._settings_dialog.resize(target_w, target_h)
            self._settings_dialog.setMinimumWidth(int(target_w*0.9))
        except Exception:
            pass

        layout_root.addWidget(actions_box)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self._settings_dialog.close); bb.accepted.connect(self._settings_dialog.close)
        layout_root.addWidget(bb)

        # Connect actions
        for btn, handler in [
            (self.thresh_btn, self.suggest_threshold),
            (self.optimize_weights_btn, self.optimize_weights),
            (self.explain_btn, self.explain_selected),
            (self.score_decomp_btn, self.show_score_decomposition)
        ]:
            try: btn.clicked.connect(handler)
            except Exception: pass

        # Persist triggers
        for w in (self.model_combo, self.score_formula_combo, self.horizon_select):
            w.currentTextChanged.connect(lambda _=None: self._persist())
        for sp in (self.ml_thresh_spin, self.w_prob_spin, self.w_rr_spin, self.w_fresh_spin, self.w_pattern_spin):
            sp.valueChanged.connect(lambda _=None: self._persist())
        self.auto_rescan_chk.stateChanged.connect(lambda _=None: self._persist())
        self.horizons_edit.textChanged.connect(lambda _=None: self._persist())
        self._update_action_buttons()

    def _open_settings_dialog(self):
        try:
            if not hasattr(self,'_settings_dialog') or not self._settings_dialog:
                self._init_settings_dialog()
            self._settings_dialog.show(); self._settings_dialog.raise_(); self._settings_dialog.activateWindow()
        except Exception:
            pass

    def _persist_settings_dialog_geometry(self):
        try:
            if hasattr(self,'_settings_dialog') and self._settings_dialog is not None:
                geo = self._settings_dialog.saveGeometry()
                import base64
                self._settings['scan_settings_geometry'] = base64.b64encode(bytes(geo)).decode('utf-8')
                save_settings(self._settings)
        except Exception:
            pass

    def _apply_quick_filters(self):
        """Update in-memory settings for symbols / min prob from quick strip without modifying persistent dialog fields."""
        try:
            # Symbols field removed; only probability quick filter applies
            qprob = float(self.quick_min_prob.value())
            if qprob > 0:
                self.ml_thresh_spin.setValue(qprob)
            self._persist()
        except Exception:
            pass

    def _toggle_advanced(self):
        try:
            vis = self.adv_box.isVisible()
            new_state = not vis
            self.adv_box.setVisible(new_state)
            self.extra_box.setVisible(new_state)
            self.adv_toggle_btn.setText('Advanced ▲' if new_state else 'Advanced ▼')
            # persist state
            self._settings['adv_visible'] = new_state
            save_settings(self._settings)
        except Exception:
            pass

    def _setup_table(self):
        # Enhanced headers - focused on key insights only
        if hasattr(self, 'enhanced_mode_btn') and self.enhanced_mode_btn.isChecked():
            headers = ["Symbol","Signal","Age","Price","R:R","Patterns","Enhanced Score","Grade","Recommendation","Sector","Risk"]
        else:
            # Classic headers
            headers = ["Symbol","Strategy","Pass","Signal","Age","Price","ATR","R:R","Target","ExpTarget","ExpMove%","ExpRR","Patterns","ML Prob","Score","Drift"]
        
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSortingEnabled(True)
        self._apply_header_tooltips()

    def _apply_header_tooltips(self):
        try:
            # Enhanced tooltips
            enhanced_tips = {
                'Enhanced Score': 'ציון משוכלל הכולל: ניתוח טכני (40%) + פונדמנטלי (35%) + סקטור (15%) + איכות עסקית (10%)',
                'Grade': 'דירוג כללי A+ עד F מבוסס על הציון המשוכלל',
                'Recommendation': 'המלצת פעולה חכמה: STRONG BUY, BUY, HOLD, NEUTRAL, AVOID',
                'Sector': 'סקטור כלכלי - משפיע על ציון הסקטור',
                'Risk': 'רמת סיכון מחושבת: LOW, MEDIUM, HIGH (מבוסס על כל הפרמטרים)',
                'Signal': 'אות טכני משופר',
                'R:R': 'יחס סיכון תשואה',
                'Patterns': 'פטרנים טכניים שזוהו'
            }
            
            # Classic tooltips
            classic_tips = {
                'ML Prob': 'Model probability. Background: red = lowest, green = highest within current scan.',
                'Score': 'Composite score (weights/ formula). Background same gradient relative to current scan.' ,
                'ExpTarget': 'Projected target price (placeholder).',
                'ExpMove%': 'Expected move from current price to target (placeholder %).',
                'ExpRR': 'Expected risk/reward (placeholder).'
            }
            
            # Use appropriate tooltips based on mode
            is_enhanced = hasattr(self, 'enhanced_mode_btn') and self.enhanced_mode_btn.isChecked()
            tips = enhanced_tips if is_enhanced else classic_tips
            
            for c in range(self.results_table.columnCount()):
                item = self.results_table.horizontalHeaderItem(c)
                if item and item.text() in tips:
                    item.setToolTip(tips[item.text()])
                    
            # Table level tooltip as legend
            if is_enhanced:
                self.results_table.setToolTip('סריקה משופרת: ציונים מבוססים על ניתוח טכני, פונדמנטלי, סקטוריאלי ואיכות עסקית')
            else:
                self.results_table.setToolTip('Color legend: ML Prob & Score cells use a red→green gradient scaled to min/max of current scan results.')
        except Exception:
            pass

    def _toggle_enhanced_mode(self):
        """Toggle between enhanced and classic scanning mode"""
        is_enhanced = self.enhanced_mode_btn.isChecked()
        if is_enhanced:
            self.enhanced_mode_btn.setText('Enhanced ON')
            self.enhanced_mode_btn.setToolTip('סריקה משופרת עם ניתוח פונדמנטלי וניקוד מורכב')
        else:
            self.enhanced_mode_btn.setText('Classic ON')  
            self.enhanced_mode_btn.setToolTip('סריקה קלאסית - רק ניתוח טכני')
            
        # If enhanced is turned off, also turn off rigorous mode
        if not is_enhanced and self.rigorous_mode_btn.isChecked():
            self.rigorous_mode_btn.setChecked(False)
            self._toggle_rigorous_mode()
        
        self.rigorous_mode_btn.setVisible(False)  # Hidden until working
        
        # Save preference
        try:
            self._settings['use_enhanced_scan'] = is_enhanced
            save_settings(self._settings)
        except Exception:
            pass

    def _toggle_rigorous_mode(self):
        """Toggle rigorous premium filtering mode"""
        is_rigorous = self.rigorous_mode_btn.isChecked()
        
        if is_rigorous:
            # Rigorous mode requires enhanced mode
            if not self.enhanced_mode_btn.isChecked():
                self.enhanced_mode_btn.setChecked(True)
                self._toggle_enhanced_mode()
                
            self.rigorous_mode_btn.setText('🎯 RIGOROUS ON')
            self.rigorous_mode_btn.setToolTip('מצב נוקשה פעיל - רק מניות באיכות יוצאת מן הכלל יעברו')
            self.rigorous_profile_combo.setVisible(True)
            
            # Update status
            profile = self.rigorous_profile_combo.currentText().lower()
            self.status_label.setText(f'🎯 Rigorous {profile.title()} mode active')
            
        else:
            self.rigorous_mode_btn.setText('🎯 RIGOROUS')
            self.rigorous_mode_btn.setToolTip('סריקה נוקשה - רק מניות באיכות יוצאת מן הכלל')
            self.rigorous_profile_combo.setVisible(False)
            
            # Clear status if it was showing rigorous mode
            if 'Rigorous' in self.status_label.text():
                self.status_label.setText('')
        
        # Save preference  
        try:
            self._settings['use_rigorous_scan'] = is_rigorous
            self._settings['rigorous_profile'] = self.rigorous_profile_combo.currentText().lower()
            save_settings(self._settings)
        except Exception:
            pass

    def run_scan(self):
        # Collect chosen strategies (at least one always)
        chosen = [name for name, btn in self.strategy_buttons.items() if btn.isChecked()]
        if not chosen:  # safety: select default
            chosen = [self._strategy_names[0]]
        # Collect patterns from buttons (override free text legacy)
        chosen_patterns = [p for p, btn in getattr(self,'pattern_buttons',{}).items() if btn.isChecked()]
        # Build per-strategy param map
        strat_param_map = {}
        for strat, vals in getattr(self,'_strategy_params', {}).items():
            try:
                strat_param_map[strat] = dict(vals)
            except Exception:
                pass
        
        # Base parameters
        params = {
            'scan_strategies': chosen,
            'patterns': ','.join(chosen_patterns),
            'lookback': self.lookback_spin.value(),
            'rr_target': self.rr_target_combo.currentText(),
            'min_rr': self.min_rr_spin.value(),
            'symbols': '',  # manual symbols input removed
            'universe_limit': 0,  # always full universe
            'ml_model': self.model_combo.currentText(),
            'ml_min_prob': self.ml_thresh_spin.value(),
            'score_formula': self.score_formula_combo.currentText(),
            'w_prob': self.w_prob_spin.value(),
            'w_rr': self.w_rr_spin.value(),
            'w_fresh': self.w_fresh_spin.value(),
            'w_pattern': self.w_pattern_spin.value(),
            'horizons': self.horizons_edit.text(),
            'use_horizon': self.horizon_select.currentText() if self.horizon_select.currentText() else '',
            # new numeric filter params (0 meaning ignore for max_age; 0 for others treated as given but we will handle None server side if not >0)
            'min_price': self.min_price_spin.value() if self.min_price_spin.value() > 0 else None,
            'max_price': self.max_price_spin.value() if self.max_price_spin.value() > 0 else None,
            'min_atr': self.min_atr_spin.value() if self.min_atr_spin.value() > 0 else None,
            'max_atr': self.max_atr_spin.value() if self.max_atr_spin.value() > 0 else None,
            'max_age': int(self.max_age_spin.value()) if self.max_age_spin.value() > 0 else None,
            'strategy_param_map': strat_param_map,
        }
        
        # Enhanced scan parameters
        if hasattr(self, 'enhanced_mode_btn') and self.enhanced_mode_btn.isChecked():
            params['use_enhanced_scan'] = True
            # Add enhanced filtering options if available
            quick_symbols = self.quick_symbols_edit.text().strip()
            if quick_symbols:
                params['symbols'] = quick_symbols
            
            min_prob = self.quick_min_prob.value()
            if min_prob > 0:
                params['min_composite_score'] = min_prob * 100  # Convert to 0-100 scale
                
            # Add enhanced parameters
            params.update({
                'max_results': 50,  # Limit results for performance
                'include_fundamentals': True,
                'include_sector_analysis': True,
                'include_business_quality': True
            })
            
            # Rigorous scan parameters - premium quality filtering
            if hasattr(self, 'rigorous_mode_btn') and self.rigorous_mode_btn.isChecked():
                params['use_rigorous_scan'] = True
                params['rigorous_profile'] = self.rigorous_profile_combo.currentText().lower()
                # Stricter limits for rigorous mode
                params.update({
                    'max_results': 20,  # Even more selective
                    'require_all_data': True,  # Only stocks with complete data
                    'premium_quality_only': True
                })
                self.status_label.setText(f'🎯 Running rigorous {params["rigorous_profile"]} scan...')
            else:
                params['use_rigorous_scan'] = False
                
        else:
            params['use_enhanced_scan'] = False
            params['use_rigorous_scan'] = False
            
        # attempt to include active snapshot pointer if available in registry
        try:
            import os
            ap = os.path.join('ml','registry','ACTIVE.txt')
            if os.path.exists(ap):
                with open(ap,'r',encoding='utf-8') as f:
                    params['active_snapshot'] = f.read().strip()
        except Exception:
            pass
            
        params.update({'fast': self.fast_spin.value(), 'slow': self.slow_spin.value(), 'upper': self.upper_spin.value(), 'lower': self.lower_spin.value(), 'ema_trend': self.ema_trend_spin.value(), 'bb_p': self.bb_p_spin.value(), 'bb_k': self.bb_k_spin.value(), 'rsi_p': self.rsi_p_spin.value(), 'rsi_buy': self.rsi_buy_spin.value()})
        
        self.run_scan_requested.emit(params)
        self.settings_changed.emit(params)
        self._settings.update({'ml_model': params['ml_model'], 'ml_min_prob': params['ml_min_prob']})
        self._persist()
        # scanning started; disable actions that depend on results
        self._update_action_buttons()

    def _on_strategy_toggled(self, full_name: str, checked: bool):
        # Optional future logic: shift-click range, right-click presets, etc.
        try:
            self._persist()
        except Exception:
            pass

    # ---------------- Strategy Params Dialog -----------------
    def _ensure_strategy_params(self):
        if hasattr(self, '_strategy_params'):
            return
        defaults = {
            'Donchian Breakout': {'upper':20,'lower':10},
            'SMA Cross': {'fast':10,'slow':20},
            'EMA Cross': {'fast':10,'slow':20},
            'MACD Trend': {'fast':12,'slow':26,'signal':9,'ema_trend':200},
            'RSI(2) @ Bollinger': {'rsi_p':2,'rsi_buy':10,'bb_p':20,'bb_k':2.0},
        }
        cfg_path = os.path.join('config','strategy_params.json')
        loaded = None
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path,'r',encoding='utf-8') as f:
                    loaded = json.load(f)
        except Exception:
            loaded = None
        if isinstance(loaded, dict) and loaded:
            merged = defaults.copy()
            for k,v in loaded.items():
                if isinstance(v, dict):
                    merged[k] = v
            self._strategy_params = merged
        else:
            self._strategy_params = defaults

    def _save_strategy_params(self):
        try:
            os.makedirs('config', exist_ok=True)
            cfg_path = os.path.join('config','strategy_params.json')
            with open(cfg_path,'w',encoding='utf-8') as f:
                json.dump(self._strategy_params, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _open_strategy_params_dialog(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, QSpinBox, QDoubleSpinBox, QPushButton
        self._ensure_strategy_params()
        dlg = QDialog(self); dlg.setWindowTitle('פרמטרי אסטרטגיות'); dlg.resize(520, 340)
        v = QVBoxLayout(dlg)
        tabs = QTabWidget(); v.addWidget(tabs,1)
        editors = {}
        spec = {
            'Donchian Breakout': [('upper',5,400,20), ('lower',2,400,10)],
            'SMA Cross': [('fast',2,400,10), ('slow',3,800,20)],
            'EMA Cross': [('fast',2,400,10), ('slow',3,800,20)],
            'MACD Trend': [('fast',2,400,12), ('slow',3,800,26), ('signal',1,100,9), ('ema_trend',20,1000,200)],
            'RSI(2) @ Bollinger': [('rsi_p',1,50,2), ('rsi_buy',1,100,10), ('bb_p',5,400,20), ('bb_k',1,10,2.0,'double')],
        }
        for strat in self._strategy_params.keys():
            page = QWidget(); p_l = QVBoxLayout(page); p_l.setContentsMargins(8,8,8,8); p_l.setSpacing(6)
            eds = {}
            for ent in spec.get(strat, []):
                name = ent[0]
                if len(ent)==5 and ent[4]=='double':
                    w = QDoubleSpinBox(); w.setRange(ent[1], ent[2]); w.setValue(self._strategy_params[strat].get(name, ent[3])); w.setSingleStep(0.1)
                else:
                    w = QSpinBox(); w.setRange(ent[1], ent[2]); w.setValue(self._strategy_params[strat].get(name, ent[3]))
                p_l.addWidget(QLabel(name)); p_l.addWidget(w)
                eds[name] = w
            p_l.addStretch(1)
            editors[strat] = eds
            tabs.addTab(page, strat)
        # Buttons
        btn_row = QHBoxLayout(); save_btn = QPushButton('שמור'); close_btn = QPushButton('סגור'); btn_row.addStretch(1); btn_row.addWidget(save_btn); btn_row.addWidget(close_btn); v.addLayout(btn_row)
        def _save():
            for strat, eds in editors.items():
                for k, w in eds.items():
                    try:
                        val = float(w.value()) if hasattr(w,'value') else None
                        # store int if integral
                        if isinstance(val,(int,float)) and abs(val - int(val)) < 1e-9:
                            val = int(val)
                        self._strategy_params[strat][k] = val
                    except Exception:
                        pass
            self._save_strategy_params()
            dlg.accept()
        save_btn.clicked.connect(_save); close_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def train_ml(self):
        params = {
            'ml_model': self.model_combo.currentText(),
            'auto_rescan': self.auto_rescan_chk.isChecked(),
            'horizons': self.horizons_edit.text(),
            'training_days_back': self.training_days_back_spin.value(),
        }
        self.train_ml_requested.emit(params)
        self._settings.update({'ml_model': params['ml_model'], 'auto_rescan': params['auto_rescan']})
        self._persist()

    def calibrate_ml(self):
        params = {
            'ml_model': self.model_combo.currentText(),
        }
        self.calibrate_requested.emit(params)
        self._settings.update({'ml_model': params['ml_model']})
        self._persist()

    def _apply_persisted(self):
        try:
            s = self._settings
            # If first run (no horizons / no weights saved) attempt to load default preset
            if not s.get('initialized_preset'):
                preset_path = os.path.join('config','scan_preset_default.json')
                try:
                    if os.path.exists(preset_path):
                        with open(preset_path,'r',encoding='utf-8') as pf:
                            preset = json.load(pf)
                        if isinstance(preset, dict):
                            # merge only missing keys so user custom stays when reloading
                            for k,v in preset.items():
                                if k not in s:
                                    s[k] = v
                            s['initialized_preset'] = True
                            save_settings(s)
                except Exception:
                    pass
            if s.get('ml_model') in ['rf','xgb','lgbm']:
                idx = self.model_combo.findText(s['ml_model'])
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
            if isinstance(s.get('ml_min_prob'), (int,float)):
                self.ml_thresh_spin.setValue(float(s['ml_min_prob']))
            self.auto_rescan_chk.setChecked(bool(s.get('auto_rescan', True)))
            # scoring
            if s.get('score_formula') in ['weighted','geometric']:
                idx = self.score_formula_combo.findText(s['score_formula'])
                if idx >= 0:
                    self.score_formula_combo.setCurrentIndex(idx)
            for key, widget in [('w_prob',self.w_prob_spin),('w_rr',self.w_rr_spin),('w_fresh',self.w_fresh_spin),('w_pattern',self.w_pattern_spin)]:
                try:
                    if isinstance(s.get(key),(int,float)):
                        widget.setValue(float(s.get(key)))
                except Exception:
                    pass
            if isinstance(s.get('horizons'), str):
                self.horizons_edit.setText(s.get('horizons'))
                parts = [p.strip() for p in s.get('horizons','').split(',') if p.strip()]
                if parts:
                    self.horizon_select.clear(); self.horizon_select.addItems(parts)
            if isinstance(s.get('use_horizon'), str) and s.get('use_horizon'):
                if self.horizon_select.findText(s['use_horizon']) < 0:
                    self.horizon_select.addItem(s['use_horizon'])
            
            # Enhanced scan mode
            if hasattr(self, 'enhanced_mode_btn'):
                use_enhanced = s.get('use_enhanced_scan', True)  # Default to enhanced
                self.enhanced_mode_btn.setChecked(use_enhanced)
                if use_enhanced:
                    self.enhanced_mode_btn.setText('Enhanced ON')
                else:
                    self.enhanced_mode_btn.setText('Classic ON')
                idx2 = self.horizon_select.findText(s['use_horizon'])
                if idx2 >= 0:
                    self.horizon_select.setCurrentIndex(idx2)
            # advanced visibility
            try:
                adv_vis = bool(s.get('adv_visible', True))
                self.adv_box.setVisible(adv_vis)
                self.extra_box.setVisible(adv_vis)
                if hasattr(self, 'adv_toggle_btn'):
                    self.adv_toggle_btn.setText('Advanced ▲' if adv_vis else 'Advanced ▼')
            except Exception:
                pass
            # numeric filters
            for key, widget in [
                ('min_price', self.min_price_spin), ('max_price', self.max_price_spin),
                ('min_atr', self.min_atr_spin), ('max_atr', self.max_atr_spin)
            ]:
                try:
                    if isinstance(s.get(key),(int,float)) and float(s.get(key))>0:
                        widget.setValue(float(s.get(key)))
                except Exception:
                    pass
            try:
                if isinstance(s.get('max_age'), (int,float)) and int(s.get('max_age'))>0:
                    self.max_age_spin.setValue(int(s.get('max_age')))
            except Exception:
                pass
            # restore strategy & pattern selections
            try:
                if isinstance(s.get('selected_strategies'), list):
                    for strat, btn in self.strategy_buttons.items():
                        btn.setChecked(strat in s['selected_strategies'])
                if isinstance(s.get('selected_patterns'), list):
                    for pat, btn in getattr(self,'pattern_buttons',{}).items():
                        btn.setChecked(pat in s['selected_patterns'])
            except Exception:
                pass
        except Exception:
            pass
        QTimer.singleShot(150, getattr(self,'_update_weight_diff', lambda: None))
        # restore side panel visibility
        try:
            if not self._settings.get('side_panel_visible', True):
                self.score_detail_browser.setVisible(False)
                if hasattr(self,'side_toggle_btn'):
                    self.side_toggle_btn.setText('Show ◀')
        except Exception:
            pass

    def _persist(self):
        try:
            sel_strats = [k for k,b in self.strategy_buttons.items() if b.isChecked()]
            sel_patts = [k for k,b in getattr(self,'pattern_buttons',{}).items() if b.isChecked()]
            self._settings.update({
                'ml_model': self.model_combo.currentText(),
                'ml_min_prob': float(self.ml_thresh_spin.value()),
                'auto_rescan': bool(self.auto_rescan_chk.isChecked()),
                'score_formula': self.score_formula_combo.currentText(),
                'w_prob': float(self.w_prob_spin.value()),
                'w_rr': float(self.w_rr_spin.value()),
                'w_fresh': float(self.w_fresh_spin.value()),
                'w_pattern': float(self.w_pattern_spin.value()),
                'horizons': self.horizons_edit.text(),
                'use_horizon': self.horizon_select.currentText() if self.horizon_select.currentText() else '',
                'min_price': float(self.min_price_spin.value()) if self.min_price_spin.value()>0 else None,
                'max_price': float(self.max_price_spin.value()) if self.max_price_spin.value()>0 else None,
                'min_atr': float(self.min_atr_spin.value()) if self.min_atr_spin.value()>0 else None,
                'max_atr': float(self.max_atr_spin.value()) if self.max_atr_spin.value()>0 else None,
                'max_age': int(self.max_age_spin.value()) if self.max_age_spin.value()>0 else None,
                'selected_strategies': sel_strats,
                'selected_patterns': sel_patts,
            })
            save_settings(self._settings)
        except Exception:
            pass
        try:
            self._update_weight_diff()
        except Exception:
            pass

    # --- Feature 5: Reset to preset ---
    def _reset_to_preset(self):
        try:
            preset_path = os.path.join('config','scan_preset_default.json')
            if not os.path.exists(preset_path):
                QMessageBox.information(self,'Info','Preset file missing')
                return
            with open(preset_path,'r',encoding='utf-8') as f:
                preset = json.load(f)
            if not isinstance(preset, dict):
                QMessageBox.information(self,'Info','Invalid preset')
                return
            # apply limited keys
            if preset.get('score_formula') in ['weighted','geometric']:
                idx = self.score_formula_combo.findText(preset['score_formula'])
                if idx>=0: self.score_formula_combo.setCurrentIndex(idx)
            for k,spin in [('w_prob',self.w_prob_spin),('w_rr',self.w_rr_spin),('w_fresh',self.w_fresh_spin),('w_pattern',self.w_pattern_spin)]:
                if k in preset and isinstance(preset[k], (int,float)):
                    spin.setValue(float(preset[k]))
            if 'horizons' in preset and isinstance(preset['horizons'], str):
                self.horizons_edit.setText(preset['horizons'])
                parts = [p.strip() for p in preset['horizons'].split(',') if p.strip()]
                self.horizon_select.clear();
                if parts: self.horizon_select.addItems(parts)
            if 'use_horizon' in preset and isinstance(preset['use_horizon'], str) and preset['use_horizon']:
                idx2 = self.horizon_select.findText(preset['use_horizon'])
                if idx2>=0: self.horizon_select.setCurrentIndex(idx2)
            self._persist()
            QMessageBox.information(self,'בוצע','הוגדרו מחדש ערכי ברירת המחדל מהpreset')
        except Exception as e:
            QMessageBox.critical(self,'שגיאה',f'כשל באיפוס: {e}')

    # --- Feature 6: Multi-preset management (save/load named) ---
    def _preset_dir(self):
        d = os.path.join('config','presets'); os.makedirs(d, exist_ok=True); return d

    def save_current_as_preset(self, name: str):
        try:
            if not name:
                return
            path = os.path.join(self._preset_dir(), f'{name}.json')
            data = {
                'score_formula': self.score_formula_combo.currentText(),
                'w_prob': self.w_prob_spin.value(),
                'w_rr': self.w_rr_spin.value(),
                'w_fresh': self.w_fresh_spin.value(),
                'w_pattern': self.w_pattern_spin.value(),
                'horizons': self.horizons_edit.text(),
                'use_horizon': self.horizon_select.currentText(),
                'selected_strategies': [k for k,b in self.strategy_buttons.items() if b.isChecked()],
                'selected_patterns': [k for k,b in getattr(self,'pattern_buttons',{}).items() if b.isChecked()],
            }
            with open(path,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
            QMessageBox.information(self,'Preset','Preset saved')
        except Exception as e:
            QMessageBox.critical(self,'Error',f'Failed save preset: {e}')

    def load_preset(self, name: str):
        try:
            if not name: return
            path = os.path.join(self._preset_dir(), f'{name}.json')
            if not os.path.exists(path):
                QMessageBox.information(self,'Info','Preset not found'); return
            with open(path,'r',encoding='utf-8') as f: data = json.load(f)
            if not isinstance(data, dict): return
            if data.get('score_formula') in ['weighted','geometric']:
                idx = self.score_formula_combo.findText(data['score_formula'])
                if idx>=0: self.score_formula_combo.setCurrentIndex(idx)
            for k,spin in [('w_prob',self.w_prob_spin),('w_rr',self.w_rr_spin),('w_fresh',self.w_fresh_spin),('w_pattern',self.w_pattern_spin)]:
                if k in data and isinstance(data[k], (int,float)): spin.setValue(float(data[k]))
            if isinstance(data.get('horizons'), str):
                self.horizons_edit.setText(data['horizons'])
                parts=[p.strip() for p in data['horizons'].split(',') if p.strip()]
                self.horizon_select.clear();
                if parts: self.horizon_select.addItems(parts)
            if isinstance(data.get('use_horizon'), str) and data['use_horizon']:
                idx2 = self.horizon_select.findText(data['use_horizon'])
                if idx2>=0: self.horizon_select.setCurrentIndex(idx2)
            # restore selections
            if isinstance(data.get('selected_strategies'), list):
                for strat, btn in self.strategy_buttons.items():
                    btn.setChecked(strat in data['selected_strategies'])
            if isinstance(data.get('selected_patterns'), list):
                for pat, btn in getattr(self,'pattern_buttons',{}).items():
                    btn.setChecked(pat in data['selected_patterns'])
            self._persist()
            QMessageBox.information(self,'Preset','Preset loaded')
        except Exception as e:
            QMessageBox.critical(self,'Error',f'Failed load preset: {e}')

    def manage_presets_dialog(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QHBoxLayout, QPushButton, QLineEdit
        dlg = QDialog(self); dlg.setWindowTitle('ניהול פריסטים'); dlg.resize(380,360)
        v = QVBoxLayout(dlg)
        lst = QListWidget(); v.addWidget(lst,1)
        # load existing
        try:
            for fn in sorted(os.listdir(self._preset_dir())):
                if fn.lower().endswith('.json'):
                    lst.addItem(fn[:-5])
        except Exception:
            pass
        name_edit = QLineEdit(); name_edit.setPlaceholderText('שם חדש / קיים')
        v.addWidget(name_edit)
        btn_row = QHBoxLayout();
        save_btn = QPushButton('שמור כחדש'); load_btn = QPushButton('טען'); del_btn = QPushButton('מחק'); close_btn = QPushButton('סגור')
        for b in (save_btn, load_btn, del_btn, close_btn): btn_row.addWidget(b)
        v.addLayout(btn_row)
        def _refresh():
            lst.clear();
            try:
                for fn in sorted(os.listdir(self._preset_dir())):
                    if fn.lower().endswith('.json'):
                        lst.addItem(fn[:-5])
            except Exception: pass
        def _do_save():
            nm = name_edit.text().strip()
            if not nm: return
            self.save_current_as_preset(nm); _refresh()
        def _do_load():
            nm = lst.currentItem().text() if lst.currentItem() else name_edit.text().strip()
            if not nm: return
            self.load_preset(nm)
        def _do_del():
            nm = lst.currentItem().text() if lst.currentItem() else name_edit.text().strip()
            if not nm: return
            path = os.path.join(self._preset_dir(), f'{nm}.json')
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
            _refresh()
        save_btn.clicked.connect(_do_save); load_btn.clicked.connect(_do_load); del_btn.clicked.connect(_do_del); close_btn.clicked.connect(dlg.reject)
        lst.itemDoubleClicked.connect(lambda _: _do_load())
        dlg.exec()

    # --- Feature 8: Export breakdown CSV ---
    def _export_breakdown_csv(self):
        try:
            if not self._last_scan_results:
                QMessageBox.information(self,'Info','Run a scan first'); return
            from PySide6.QtWidgets import QInputDialog
            n, ok = QInputDialog.getInt(self,'Top N','Export top N rows by Score', min=1, max=max(1,len(self._last_scan_results)), value=min(50,len(self._last_scan_results)))
            if not ok: return
            # sort copy by score desc
            rows = sorted([r for r in self._last_scan_results if isinstance(r.get('score'), (int,float))], key=lambda r: r.get('score'), reverse=True)[:n]
            if not rows: QMessageBox.information(self,'Info','No rows with score'); return
            file_path, _ = QFileDialog.getSaveFileName(self,'שמור פירוק','score_breakdown.csv','CSV Files (*.csv)')
            if not file_path: return
            import csv
            with open(file_path,'w',newline='',encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['symbol','strategy','score','ml_prob','rr','age','patterns','prob_comp','rr_norm','freshness','pattern_comp','weight_prob','weight_rr','weight_fresh','weight_pattern','contrib_prob','contrib_rr','contrib_fresh','contrib_pattern','formula'])
                W_PROB = float(self.w_prob_spin.value()); W_RR = float(self.w_rr_spin.value()); W_FRESH = float(self.w_fresh_spin.value()); W_PATTERN = float(self.w_pattern_spin.value())
                w_sum = W_PROB + W_RR + W_FRESH + W_PATTERN
                if w_sum>0:
                    nW_PROB, nW_RR, nW_FRESH, nW_PATTERN = [W_PROB/w_sum, W_RR/w_sum, W_FRESH/w_sum, W_PATTERN/w_sum]
                else:
                    nW_PROB=nW_RR=nW_FRESH=nW_PATTERN=0
                formula = self.score_formula_combo.currentText().lower()
                for rec in rows:
                    ml_prob = rec.get('ml_prob'); rr = rec.get('rr'); age = rec.get('age'); patterns = rec.get('patterns','')
                    prob_comp = float(ml_prob) if isinstance(ml_prob,(int,float)) else 0.5
                    rr_norm = min(float(rr)/3.0,1.0) if isinstance(rr,(int,float)) else 0.0
                    freshness = 0.0 if not isinstance(age,(int,float)) or age >=10 else max(0.0,1.0-(float(age)/10.0))
                    patt_ct = len([p for p in patterns.split(',') if p]) if isinstance(patterns,str) and patterns else 0
                    pattern_comp = min(patt_ct/3.0,1.0)
                    if formula == 'geometric':
                        contrib_prob=contrib_rr=contrib_fresh=contrib_pattern=None
                    else:
                        contrib_prob = nW_PROB*prob_comp; contrib_rr = nW_RR*rr_norm; contrib_fresh = nW_FRESH*freshness; contrib_pattern = nW_PATTERN*pattern_comp
                    w.writerow([
                        rec.get('symbol'), rec.get('strategy'), rec.get('score'), ml_prob, rr, age, patterns,
                        prob_comp, rr_norm, freshness, pattern_comp,
                        nW_PROB, nW_RR, nW_FRESH, nW_PATTERN,
                        contrib_prob, contrib_rr, contrib_fresh, contrib_pattern, formula
                    ])
            QMessageBox.information(self,'הצלחה',f'נשמר {file_path}')
        except Exception as e:
            QMessageBox.critical(self,'Error', f'Export failed: {e}')

    def start_scan_worker(self, params, data_map):
        if self.worker_thread and self.worker_thread.isRunning():
            return
            
        # Use enhanced worker thread if enhanced mode is enabled
        use_enhanced = params.get('use_enhanced_scan', False)
        
        try:
            if use_enhanced:
                from ui.enhanced_worker_thread import create_worker_thread
                self.worker_thread = create_worker_thread('scan', params, data_map, use_enhanced=True)
                
                # Connect enhanced signals if available
                if hasattr(self.worker_thread, 'enhanced_results_ready'):
                    self.worker_thread.enhanced_results_ready.connect(self.update_enhanced_results)
            else:
                # Use legacy worker thread
                self.worker_thread = WorkerThread('scan', params, data_map)
        except Exception as e:
            print(f"Failed to create enhanced worker, falling back to legacy: {e}")
            self.worker_thread = WorkerThread('scan', params, data_map)
        
        # Connect common signals
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.status_updated.connect(self.update_status)
        self.worker_thread.results_ready.connect(self.update_results)
        self.worker_thread.error_occurred.connect(self.show_error)
        
        try:
            self.worker_thread.finished_work.connect(lambda: (getattr(self.worker_thread,'quit',lambda:None)(), getattr(self.worker_thread,'wait',lambda *_:None)(2000)))
        except Exception:
            pass
        self.show_progress(True)
        self.worker_thread.start()
        try:
            self.worker_thread.finished.connect(lambda: self._on_worker_finished())
        except Exception:
            pass

    def cancel_scan(self):
        if self.worker_thread:
            self.worker_thread.cancel()
            try:
                self.worker_thread.quit()
                self.worker_thread.wait(2000)
            except Exception:
                pass
            self.show_progress(False)

    def show_progress(self, show=True):
        # עדכון מצב כפתורים ובר התקדמות
        try:
            self.progress_bar.setVisible(show)
        except Exception:
            pass
        try:
            self.run_scan_btn.setEnabled(not show)
        except Exception:
            pass
        try:
            self.stop_btn.setVisible(show)
        except Exception:
            pass
        if show:
            try: self.progress_bar.setValue(0)
            except Exception: pass

    def update_progress(self, v): self.progress_bar.setValue(v)
    def update_status(self, s): self.status_label.setText(s)

    def update_results(self, results):
        try:
            self._last_scan_results = results or []
            self._last_backtest_results = self._last_scan_results
        except Exception:
            pass
        self._update_action_buttons()
        # Log dump
        try:
            import pathlib
            outdir = pathlib.Path('logs'); outdir.mkdir(exist_ok=True)
            jsonl_path = outdir / 'backtest_ui_results.jsonl'; text_path = outdir / 'backtest_ui_results.txt'
            def sanitize(v):
                try:
                    import numpy as _np, pandas as _pd
                    if isinstance(v, (_np.generic,)): return float(v)
                    if isinstance(v, (_pd.Timestamp,)): return str(v)
                except Exception: pass
                if v is None or isinstance(v,(str,int,float,bool,list,dict)): return v
                try: return str(v)
                except Exception: return repr(v)
            with open(jsonl_path,'w',encoding='utf-8') as jfh, open(text_path,'w',encoding='utf-8') as tfh:
                for r in results:
                    try:
                        s = {k: sanitize(v) for k,v in r.items()}; jfh.write(json.dumps(s,ensure_ascii=False)+'\n'); tfh.write(repr(s)+'\n')
                    except Exception as e:
                        tfh.write('FAILED: '+repr(r)+'\n'); tfh.write('ERR: '+str(e)+'\n')
        except Exception:
            pass
        self.show_progress(False)
        
        # Update table with results
        self._populate_results_table(results)

    def update_enhanced_results(self, enhanced_data):
        """Handle enhanced scan results with comprehensive data"""
        try:
            if not enhanced_data:
                return
                
            # Extract results
            top_picks = enhanced_data.get('top_picks', [])
            summary = enhanced_data.get('summary', {})
            
            # Store for export
            self._last_scan_results = []
            for result in top_picks:
                # Convert to legacy format for compatibility
                legacy_result = {
                    'symbol': result.symbol,
                    'signal': result.technical_signal,
                    'age': result.technical_age,
                    'price': result.price_at_signal,
                    'rr': result.rr_ratio if result.rr_ratio else 'N/A',
                    'patterns': ','.join(result.patterns) if result.patterns else '',
                    'composite_score': result.composite_score,
                    'grade': result.grade,
                    'recommendation': result.recommendation,
                    'sector': result.sector,
                    'financial_strength': result.financial_strength,
                    'risk_level': result.risk_level,
                    'pe_ratio': result.pe_ratio,
                    'roe': result.roe,
                    'employee_count': result.employee_count,
                    'tech_score': result.technical_score,
                    'fund_score': result.fundamental_score
                }
                self._last_scan_results.append(legacy_result)
            
            self._last_backtest_results = self._last_scan_results
            
            # Update summary
            if summary:
                total = summary.get('total_scanned', 0)
                successful = summary.get('successful', 0)
                avg_score = summary.get('average_score', 0)
                top_score = summary.get('top_score', 0)
                
                summary_text = f"סרוק: {total} | הצליח: {successful} | ציון ממוצע: {avg_score:.1f} | ציון מקסימלי: {top_score:.1f}"
                self.summary_label.setText(f"Summary: {summary_text}")
            
            # Update table with enhanced results  
            self._populate_enhanced_results_table(top_picks)
            
            self._update_action_buttons()
            self.show_progress(False)
            
        except Exception as e:
            print(f"Error updating enhanced results: {e}")
            self.show_error(f"Failed to update enhanced results: {str(e)}")

    def _populate_results_table(self, results):
        """Populate table with standard scan results"""
        if not results:
            return
            
        self.status_label.setText(f"נמצאו {len(results)} תוצאות")
        self.results_table.setRowCount(len(results))
        
        # Standard population logic (existing)
        # ... (this would contain the existing table population code)
        
    def _populate_enhanced_results_table(self, enhanced_results):
        """Populate table with enhanced scan results - focused on key insights"""
        if not enhanced_results:
            return
            
        self.results_table.setRowCount(len(enhanced_results))
        
        for row, result in enumerate(enhanced_results):
            try:
                # Enhanced table columns: Symbol, Signal, Age, Price, R:R, Patterns, Enhanced Score, Grade, Recommendation, Sector, Risk
                col = 0
                
                # Basic technical info
                # Symbol
                self.results_table.setItem(row, col, QTableWidgetItem(result.symbol or "")); col += 1
                
                # Signal  
                self.results_table.setItem(row, col, QTableWidgetItem(result.technical_signal or "")); col += 1
                
                # Age
                age_text = str(result.technical_age) if result.technical_age is not None else ""
                self.results_table.setItem(row, col, QTableWidgetItem(age_text)); col += 1
                
                # Price - וודא שזה מחיר ולא סיגנל!
                price_text = f"${result.price_at_signal:.2f}" if result.price_at_signal and result.price_at_signal > 0 else ""
                self.results_table.setItem(row, col, QTableWidgetItem(price_text)); col += 1
                
                # Risk:Reward Ratio
                rr_text = f"{result.rr_ratio:.2f}" if result.rr_ratio and result.rr_ratio > 0 else ""
                self.results_table.setItem(row, col, QTableWidgetItem(rr_text)); col += 1
                
                # Patterns
                patterns_text = ','.join(result.patterns) if result.patterns else ""
                self.results_table.setItem(row, col, QTableWidgetItem(patterns_text)); col += 1
                
                # *** THE MAIN STAR: Enhanced Score *** 
                enhanced_score_item = QTableWidgetItem(f"{result.composite_score:.1f}")
                enhanced_score_item.setToolTip(f"טכני: {result.technical_score:.1f} | פונדמנטלי: {result.fundamental_score:.1f} | סקטור: {result.sector_score} | איכות: {result.business_quality_score:.1f}")
                
                # Strong color coding for the enhanced score
                if result.composite_score >= 85:
                    enhanced_score_item.setBackground(QColor(34, 139, 34))   # Forest Green
                    enhanced_score_item.setForeground(QColor(255, 255, 255))  # White text
                elif result.composite_score >= 75:
                    enhanced_score_item.setBackground(QColor(144, 238, 144))  # Light Green
                elif result.composite_score >= 65:
                    enhanced_score_item.setBackground(QColor(255, 255, 224))  # Light Yellow
                elif result.composite_score >= 50:
                    enhanced_score_item.setBackground(QColor(255, 228, 196))  # Light Orange
                else:
                    enhanced_score_item.setBackground(QColor(255, 182, 193))  # Light Pink
                    
                self.results_table.setItem(row, col, enhanced_score_item); col += 1
                
                # Grade with color - ווידוי שיש ערך
                grade_text = result.grade if result.grade else "N/A"
                grade_item = QTableWidgetItem(grade_text)
                if grade_text.startswith('A'):
                    grade_item.setBackground(QColor(144, 238, 144))  # Light green
                elif grade_text.startswith('B'):
                    grade_item.setBackground(QColor(255, 255, 224))  # Light yellow
                elif grade_text.startswith('C'):
                    grade_item.setBackground(QColor(255, 228, 196))  # Light orange
                elif grade_text.startswith('D') or grade_text.startswith('F'):
                    grade_item.setBackground(QColor(255, 182, 193))  # Light pink
                self.results_table.setItem(row, col, grade_item); col += 1
                
                # Recommendation with strong color coding - ווידוי שיש ערך
                rec_text = result.recommendation if result.recommendation else "N/A"
                rec_item = QTableWidgetItem(rec_text)
                if rec_text == 'STRONG BUY':
                    rec_item.setBackground(QColor(34, 139, 34))   # Dark Green
                    rec_item.setForeground(QColor(255, 255, 255))  # White text
                elif rec_text == 'BUY':
                    rec_item.setBackground(QColor(144, 238, 144))  # Light Green
                elif rec_text == 'HOLD':
                    rec_item.setBackground(QColor(255, 255, 224))  # Light Yellow
                elif rec_text == 'NEUTRAL':
                    rec_item.setBackground(QColor(255, 228, 196))  # Light Orange
                elif rec_text == 'AVOID':
                    rec_item.setBackground(QColor(255, 69, 0))     # Red Orange
                    rec_item.setForeground(QColor(255, 255, 255))  # White text
                self.results_table.setItem(row, col, rec_item); col += 1
                
                # Sector info
                sector_text = result.sector if result.sector else "N/A"
                self.results_table.setItem(row, col, QTableWidgetItem(sector_text)); col += 1
                
                # Risk with color
                risk_text = result.risk_level if result.risk_level else "MEDIUM"
                risk_item = QTableWidgetItem(risk_text)
                if risk_text == 'LOW':
                    risk_item.setBackground(QColor(144, 238, 144))  # Green
                elif risk_text == 'MEDIUM':
                    risk_item.setBackground(QColor(255, 255, 224))  # Yellow
                elif risk_text == 'HIGH':
                    risk_item.setBackground(QColor(255, 182, 193))  # Pink
                self.results_table.setItem(row, col, risk_item); col += 1
                
            except Exception as e:
                print(f"Error populating row {row}: {e}")
                
        self.status_label.setText(f"נמצאו {len(enhanced_results)} תוצאות משופרות - ממוינות לפי ציון משוכלל")
        
        # Store enhanced results for score detail panel
        self._last_enhanced_results = enhanced_results
        
        # Enable sorting and auto-sort by Enhanced Score (column 6) descending
        try:
            self.results_table.setSortingEnabled(True)
            enhanced_score_col = 6  # Enhanced Score is column 6 (0-indexed)
            from PySide6.QtCore import Qt as _Qt
            self.results_table.sortItems(enhanced_score_col, _Qt.SortOrder.DescendingOrder)
        except Exception:
            pass
            
        # Hook selection event for score detail panel (if not already hooked)
        try:
            if not hasattr(self,'_selection_hooked'):
                self.results_table.itemSelectionChanged.connect(self._update_score_detail_side)
                self._selection_hooked=True
        except Exception:
            pass
            
        # Show the score detail panel and update it
        try:
            self.score_detail_browser.setVisible(True)
            self._update_score_detail_side()
        except Exception:
            pass
    def _populate_results_table(self, results):
        """Populate table with standard scan results"""
        if not results:
            self.results_table.setRowCount(0)
            self.status_label.setText("אין תוצאות")
            return
            
        print(f"Populating standard results table with {len(results)} results")
        # This is the classic/legacy populate function
        # Enhanced mode uses _populate_enhanced_results_table instead
        
        self.results_table.setRowCount(len(results))
        
        # Clear enhanced results when showing classic results
        self._last_enhanced_results = []
        
        # Simple population for standard mode - detailed implementation not shown for brevity
        for row, result in enumerate(results):
            try:
                col = 0
                # Basic population logic for standard results
                for key in ['symbol','strategy','pass','signal','age','price','patterns','ml_prob','score']:
                    value = str(result.get(key, ''))
                    item = QTableWidgetItem(value)
                    self.results_table.setItem(row, col, item)
                    col += 1
            except Exception as e:
                print(f"Error populating standard row {row}: {e}")
                
        self.status_label.setText(f"נמצאו {len(results)} תוצאות")
        
        # Hook selection event for score detail panel (if not already hooked)
        try:
            if not hasattr(self,'_selection_hooked'):
                self.results_table.itemSelectionChanged.connect(self._update_score_detail_side)
                self._selection_hooked=True
        except Exception:
            pass
            
        # Show the score detail panel and update it
        try:
            self.score_detail_browser.setVisible(True)
            self._update_score_detail_side()
        except Exception:
            pass

    def show_error(self, error):
        self.show_progress(False)
        QMessageBox.critical(self,'שגיאה',f'שגיאה בסריקה: {error}')

    def _on_worker_finished(self):
        try: QTimer.singleShot(50, lambda: None)
        except Exception: pass
        try: self.show_progress(False)
        except Exception: pass
        self.worker_thread = None

    def download_results(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.information(self,'מידע','אין תוצאות להורדה'); return
        file_path, _ = QFileDialog.getSaveFileName(self,'שמור קובץ','scan_results.csv','CSV Files (*.csv)')
        if file_path:
            with open(file_path,'w',encoding='utf-8') as f:
                headers = [self.results_table.horizontalHeaderItem(c).text() for c in range(self.results_table.columnCount())]
                f.write(','.join(headers)+'\n')
                for r in range(self.results_table.rowCount()):
                    row_data = []
                    for c in range(self.results_table.columnCount()):
                        it = self.results_table.item(r,c); row_data.append(it.text() if it else '')
                    f.write(','.join(row_data)+'\n')
            QMessageBox.information(self,'הצלחה',f'הקובץ נשמר: {file_path}')

    def suggest_threshold(self):
        try:
            from ml.train_model import load_model, DEFAULT_MODEL_PATH, XGB_MODEL_PATH, LGBM_MODEL_PATH, suggest_probability_threshold
            sel = self.model_combo.currentText().lower()
            path = DEFAULT_MODEL_PATH
            if sel == 'xgb': path = XGB_MODEL_PATH
            elif sel == 'lgbm': path = LGBM_MODEL_PATH
            m = load_model(path)
            if m is None:
                QMessageBox.information(self,'Info','Model not found')
                return
            # single horizon only for now
            val_probs = m.get('val_probs') if isinstance(m,dict) else None
            val_labels = m.get('val_labels') if isinstance(m,dict) else None
            if not val_probs or not val_labels:
                QMessageBox.information(self,'Info','No validation probabilities stored')
                return
            best = suggest_probability_threshold(val_probs, val_labels, metric='f1')
            if not best:
                QMessageBox.information(self,'Info','No suggestion available')
                return
            self.ml_thresh_spin.setValue(best['threshold'])
            QMessageBox.information(self,'Suggested', f"Threshold {best['threshold']} (F1={best.get('f1')}, P={best.get('precision')}, R={best.get('recall')})")
        except Exception as e:
            QMessageBox.critical(self,'Error',f'Failed: {e}')

    def optimize_weights(self):
        try:
            from ml.train_model import optimize_scoring_weights
            best = optimize_scoring_weights(self._last_scan_results, metric='corr')
            if not best:
                QMessageBox.information(self,'Info','No optimization result')
                return
            self.w_prob_spin.setValue(best['w_prob'])
            self.w_rr_spin.setValue(best['w_rr'])
            self.w_fresh_spin.setValue(best['w_fresh'])
            self.w_pattern_spin.setValue(best['w_pattern'])
            QMessageBox.information(self,'Weights Applied', f"Applied weights with score={best.get('score')}")
        except Exception as e:
            QMessageBox.critical(self,'Error',f'Failed: {e}')

    def explain_selected(self):
        try:
            row = self.results_table.currentRow()
            if row < 0:
                QMessageBox.information(self,'Info','Select a row first')
                return
            if not self._last_scan_results:
                QMessageBox.information(self,'Info','Run a scan first')
                return
            rec = self._last_scan_results[row] if row < len(self._last_scan_results) else None
            if not rec:
                QMessageBox.information(self,'Info','No record found')
                return
            features_dict = rec.get('_features') or {}
            if not features_dict:
                QMessageBox.information(self,'Info','No captured feature vector for this row (run a fresh scan after training)')
                return
            # load selected model (single or multi) to get importance + stats
            from ml.train_model import load_model, DEFAULT_MODEL_PATH, XGB_MODEL_PATH, LGBM_MODEL_PATH
            sel = self.model_combo.currentText().lower()
            path = DEFAULT_MODEL_PATH
            if sel == 'xgb': path = XGB_MODEL_PATH
            elif sel == 'lgbm': path = LGBM_MODEL_PATH
            model_obj = load_model(path)
            if model_obj is None:
                QMessageBox.information(self,'Info','Model not loaded')
                return
            # if multi-horizon container, choose first horizon model for feature importance
            if isinstance(model_obj, dict) and model_obj.get('multi') and 'models' in model_obj:
                try:
                    first_key = sorted(model_obj['models'].keys(), key=lambda k: int(k))[0]
                    model_for_imp = model_obj['models'][first_key]
                except Exception:
                    model_for_imp = None
            else:
                model_for_imp = model_obj
            import pandas as pd
            ser = pd.Series(features_dict)
            from ml.explain import compute_contributions, summarize_contributions
            stats = model_obj.get('feature_stats') if isinstance(model_obj, dict) else None
            contributions = compute_contributions(model_for_imp if model_for_imp else model_obj, ser, stats, top_k=15)
            if not contributions:
                QMessageBox.information(self,'Info','No contributions computed')
                return
            summary = summarize_contributions(contributions)
            lines = []
            lines.append(f"Symbol: {rec.get('symbol')}")
            lines.append(f"ML Prob: {rec.get('ml_prob')}")
            lines.append(f"Score: {rec.get('score')}")
            lines.append("Top feature contributions (z * importance):")
            for c in contributions:
                lines.append(f"  {c['feature']}: val={round(c['value'],4)} z={round(c['z'],3)} imp={round(c['importance'],3)} contrib={round(c['contribution'],4)}")
            lines.append(f"Totals: +{round(summary['total_positive'],4)}  -{round(summary['total_negative'],4)}  net={round(summary['net'],4)}")
            QMessageBox.information(self,'Explain', '\n'.join(lines))
        except Exception as e:
            QMessageBox.critical(self,'Error', f'Explain failed: {e}')

    def show_score_decomposition(self):
        try:
            row = self.results_table.currentRow()
            if row < 0:
                QMessageBox.information(self,'Info','Select a row first'); return
            if not self._last_scan_results:
                QMessageBox.information(self,'Info','Run a scan first'); return
            rec = self._last_scan_results[row] if row < len(self._last_scan_results) else None
            if not rec:
                QMessageBox.information(self,'Info','No record'); return
            # reconstruct components (approx): we have final score; recompute components with current formula
            ml_prob = rec.get('ml_prob'); rr = rec.get('rr'); age = rec.get('age'); patterns = rec.get('patterns','')
            try:
                prob_comp = float(ml_prob) if isinstance(ml_prob,(int,float)) else 0.5
            except Exception:
                prob_comp = 0.5
            try:
                rr_norm = min(float(rr)/3.0,1.0) if isinstance(rr,(int,float)) else 0.0
            except Exception:
                rr_norm = 0.0
            try:
                freshness = 0.0 if not isinstance(age,(int,float)) or age >=10 else max(0.0,1.0-(float(age)/10.0))
            except Exception:
                freshness = 0.0
            pattern_ct = 0
            if isinstance(patterns,str) and patterns:
                pattern_ct = len([p for p in patterns.split(',') if p])
            pattern_comp = min(pattern_ct/3.0, 1.0)
            W_PROB = float(self.w_prob_spin.value()); W_RR = float(self.w_rr_spin.value()); W_FRESH = float(self.w_fresh_spin.value()); W_PATTERN = float(self.w_pattern_spin.value())
            formula = self.score_formula_combo.currentText().lower()
            # normalized weights
            w_sum = W_PROB + W_RR + W_FRESH + W_PATTERN
            if w_sum > 0:
                nW_PROB, nW_RR, nW_FRESH, nW_PATTERN = [W_PROB/w_sum, W_RR/w_sum, W_FRESH/w_sum, W_PATTERN/w_sum]
            else:
                nW_PROB, nW_RR, nW_FRESH, nW_PATTERN = (0,0,0,0)
            if formula == 'geometric':
                import math
                score_calc = (max(prob_comp,1e-6)**nW_PROB)*(max(rr_norm,1e-6)**nW_RR)*(max(freshness,1e-6)**nW_FRESH)*(max(pattern_comp,1e-6)**nW_PATTERN)
                contribs = [prob_comp, rr_norm, freshness, pattern_comp]
            else:
                score_calc = nW_PROB*prob_comp + nW_RR*rr_norm + nW_FRESH*freshness + nW_PATTERN*pattern_comp
                contribs = [nW_PROB*prob_comp, nW_RR*rr_norm, nW_FRESH*freshness, nW_PATTERN*pattern_comp]
            # build dialog
            dlg = QDialog(self)
            dlg.setWindowTitle('Score Decomposition')
            v = QVBoxLayout(dlg)
            tb = QTextBrowser()
            lines = []
            lines.append(f"Symbol: {rec.get('symbol')}")
            lines.append(f"Formula: {formula}")
            lines.append(f"Stored Score: {rec.get('score')}")
            lines.append(f"Recalc Score: {round(score_calc,4)}")
            lines.append("Components:")
            lines.append(f"  prob={round(prob_comp,4)} rr_norm={round(rr_norm,4)} freshness={round(freshness,4)} pattern={round(pattern_comp,4)}")
            lines.append("Weights (raw / normalized):")
            lines.append(f"  prob={W_PROB:.3f}/{nW_PROB:.3f} rr={W_RR:.3f}/{nW_RR:.3f} fresh={W_FRESH:.3f}/{nW_FRESH:.3f} pattern={W_PATTERN:.3f}/{nW_PATTERN:.3f}")
            if formula == 'weighted':
                lines.append("Weighted contributions:")
                labels = ['prob','rr','fresh','pattern']
                for lbl,val in zip(labels, contribs):
                    lines.append(f"  {lbl}: {round(val,4)}")
            tb.setText('\n'.join(lines))
            v.addWidget(tb)
            bb = QDialogButtonBox(QDialogButtonBox.Close)
            bb.rejected.connect(dlg.reject); bb.accepted.connect(dlg.accept)
            v.addWidget(bb)
            dlg.resize(420,380)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self,'Error',f'Score decomposition failed: {e}')

    def _update_score_detail_side(self):
        try:
            row = self.results_table.currentRow()
            
            # Check if we're in Enhanced mode and have enhanced results
            if hasattr(self, '_last_enhanced_results') and self._last_enhanced_results:
                if row < 0 or row >= len(self._last_enhanced_results):
                    self.score_detail_browser.setText('')
                    return
                enhanced_result = self._last_enhanced_results[row]
                self.score_detail_browser.setText(self._compose_enhanced_score_detail(enhanced_result))
                return
            
            # Fall back to classic results
            if row < 0 or row >= len(self._last_scan_results):
                self.score_detail_browser.setText('')
                return
            rec = self._last_scan_results[row]
            self.score_detail_browser.setText(self._compose_score_detail(rec))
        except Exception:
            pass

    def _compose_enhanced_score_detail(self, result):
        """Create detailed score breakdown for enhanced results"""
        try:
            lines = [
                f"📊 {result.symbol} - Enhanced Score Breakdown",
                "=" * 40,
                "",
                f"🎯 Final Enhanced Score: {result.composite_score:.1f}/100",
                f"🏆 Grade: {result.grade}",
                f"📋 Recommendation: {result.recommendation}",
                "",
                "📈 Component Breakdown:",
                "-" * 25,
                f"• Technical Analysis (40%): {result.technical_score:.1f}",
                f"• Fundamental Analysis (35%): {result.fundamental_score:.1f}", 
                f"• Sector Performance (15%): {result.sector_score}",
                f"• Business Quality (10%): {result.business_quality_score:.1f}",
                "",
                "🔢 Weighted Calculation:",
                f"({result.technical_score:.1f} × 0.40) + ({result.fundamental_score:.1f} × 0.35) + ({result.sector_score} × 0.15) + ({result.business_quality_score:.1f} × 0.10)",
                f"= {result.technical_score * 0.4:.1f} + {result.fundamental_score * 0.35:.1f} + {result.sector_score * 0.15:.1f} + {result.business_quality_score * 0.1:.1f}",
                f"= {result.composite_score:.1f}",
                "",
                "💼 Business Context:",
                "-" * 18,
                f"• Sector: {result.sector or 'N/A'}",
                f"• Risk Level: {result.risk_level or 'N/A'}",
                "",
                "📊 Technical Details:",
                "-" * 18,
                f"• Signal: {result.technical_signal or 'N/A'}",
                f"• Signal Age: {result.technical_age} days" if result.technical_age is not None else "• Signal Age: N/A",
                f"• Price at Signal: ${result.price_at_signal:.2f}" if result.price_at_signal else "• Price at Signal: N/A",
                f"• Risk:Reward Ratio: {result.risk_reward:.2f}" if result.risk_reward else "• Risk:Reward Ratio: N/A",
                f"• Patterns: {result.patterns or 'None'}",
                "",
                "🎯 Investment Thesis:",
                "-" * 18,
            ]
            
            # Add investment thesis based on score
            if result.composite_score >= 85:
                lines.extend([
                    "🟢 STRONG INVESTMENT CANDIDATE",
                    "• Excellent scores across all dimensions", 
                    "• High probability of success",
                    "• Consider for immediate action"
                ])
            elif result.composite_score >= 75:
                lines.extend([
                    "🟡 GOOD INVESTMENT OPPORTUNITY", 
                    "• Strong fundamentals with solid technical setup",
                    "• Above-average probability of success",
                    "• Suitable for portfolio consideration"
                ])
            elif result.composite_score >= 65:
                lines.extend([
                    "🟠 MODERATE OPPORTUNITY",
                    "• Mixed signals - some strengths, some concerns", 
                    "• Requires additional analysis",
                    "• Proceed with caution"
                ])
            else:
                lines.extend([
                    "🔴 HIGH RISK / LOW CONFIDENCE",
                    "• Multiple concerns across analysis dimensions",
                    "• Low probability of success", 
                    "• Consider avoiding or wait for better setup"
                ])
                
            return '\n'.join(lines)
        except Exception as e:
            return f'Error creating enhanced score detail: {e}'

    def _compose_score_detail(self, rec):
        """Create detailed score breakdown for classic results"""
        try:
            ml_prob = rec.get('ml_prob'); rr = rec.get('rr'); age = rec.get('age'); patterns = rec.get('patterns','')
            prob_comp = float(ml_prob) if isinstance(ml_prob,(int,float)) else 0.5
            rr_norm = min(float(rr)/3.0,1.0) if isinstance(rr,(int,float)) else 0.0
            freshness = 0.0 if not isinstance(age,(int,float)) or age >=10 else max(0.0,1.0-(float(age)/10.0))
            pattern_ct = len([p for p in patterns.split(',') if p]) if isinstance(patterns,str) and patterns else 0
            pattern_comp = min(pattern_ct/3.0,1.0)
            W_PROB = float(self.w_prob_spin.value()); W_RR = float(self.w_rr_spin.value()); W_FRESH = float(self.w_fresh_spin.value()); W_PATTERN = float(self.w_pattern_spin.value())
            w_sum = W_PROB + W_RR + W_FRESH + W_PATTERN
            if w_sum>0:
                nW_PROB, nW_RR, nW_FRESH, nW_PATTERN = [W_PROB/w_sum, W_RR/w_sum, W_FRESH/w_sum, W_PATTERN/w_sum]
            else:
                nW_PROB=nW_RR=nW_FRESH=nW_PATTERN=0
            formula = self.score_formula_combo.currentText().lower()
            if formula == 'geometric':
                import math
                score_calc = (max(prob_comp,1e-6)**nW_PROB)*(max(rr_norm,1e-6)**nW_RR)*(max(freshness,1e-6)**nW_FRESH)*(max(pattern_comp,1e-6)**nW_PATTERN)
                contrib_lines = []
            else:
                contrib_prob = nW_PROB*prob_comp; contrib_rr=nW_RR*rr_norm; contrib_fresh=nW_FRESH*freshness; contrib_pattern=nW_PATTERN*pattern_comp
                score_calc = contrib_prob+contrib_rr+contrib_fresh+contrib_pattern
                contrib_lines = [
                    f"prob {prob_comp:.3f} * {nW_PROB:.2f} = {contrib_prob:.3f}",
                    f"rr {rr_norm:.3f} * {nW_RR:.2f} = {contrib_rr:.3f}",
                    f"fresh {freshness:.3f} * {nW_FRESH:.2f} = {contrib_fresh:.3f}",
                    f"pattern {pattern_comp:.3f} * {nW_PATTERN:.2f} = {contrib_pattern:.3f}",
                ]
            lines = [
                f"Symbol: {rec.get('symbol')}  Strategy: {rec.get('strategy')}",
                f"Stored Score: {rec.get('score')}",
                f"Recalc: {score_calc:.4f} ({formula})",
                f"ML Prob={prob_comp:.3f}  RR_norm={rr_norm:.3f}  Fresh={freshness:.3f}  Patt={pattern_comp:.3f} (cnt={pattern_ct})",
                f"Weights raw prob={W_PROB} rr={W_RR} fresh={W_FRESH} patt={W_PATTERN}",
            ]
            if contrib_lines:
                lines.append('Contributions:'); lines.extend(contrib_lines)
            lines.append(f"Patterns: {patterns or '-'}")
            return '\n'.join(lines)
        except Exception:
            return 'Error computing detail'

    def cleanup(self):
        """Stop worker thread safely (called on application close)."""
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                try: self.worker_thread.cancel()
                except Exception: pass
                try: self.worker_thread.quit()
                except Exception: pass
                try: self.worker_thread.wait(2000)
                except Exception: pass
        except Exception:
            pass

    def _update_action_buttons(self):
        """Enable/disable action buttons based on available context (results, etc.)."""
        try:
            has_results = bool(self._last_scan_results)
            # Buttons needing results
            for b in (self.optimize_weights_btn, self.explain_btn, self.score_decomp_btn):
                b.setEnabled(has_results)
                if not has_results:
                    b.setToolTip('Run a scan first')
                else:
                    b.setToolTip('')
            # Suggest threshold & train/calibrate independent (always enabled)
            for b in (self.train_btn, self.calib_btn, self.thresh_btn):
                b.setEnabled(True)
        except Exception:
            pass

    # (help dialog now provided by ui.shared.help_viewer)
