from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QMessageBox, QTextBrowser, QHBoxLayout, QGroupBox, QGridLayout,
    QComboBox, QLineEdit, QCheckBox, QToolButton, QStyle, QMenu, QSpinBox, QDoubleSpinBox, QFormLayout
)
from PySide6.QtCore import Signal, Qt, QEvent, QTimer
from ui.styles.style_manager import StyleManager
import os, json

class ModelDashboardTab(QWidget):
    """Simple dashboard listing model registry snapshots and allowing selection of active model.
    Active selection persists via a small pointer file ml/registry/ACTIVE.txt.
    """
    # Signal emitted when user requests a model training from this tab
    train_ml_requested = Signal(dict)
    # Removed legacy Train All; adding iterative training support
    iterative_training_requested = Signal(dict)  # params for iterative historical training
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        # Compact header with overflow menu instead of multiple buttons
        header_row = QHBoxLayout()
        self.info_lbl = QLabel('')
        self.info_lbl.setObjectName('status_info')
        header_row.addWidget(self.info_lbl, 1)
        # Overflow menu button (⋮)
        self.overflow_btn = QToolButton()
        self.overflow_btn.setText('⋮')
        self.overflow_btn.setToolTip('More actions')
        menu = QMenu(self)
        act_refresh = menu.addAction('Manual Refresh')
        act_refresh.triggered.connect(self.load_index)
        act_set_active = menu.addAction('Set Active (Manual)')
        act_set_active.triggered.connect(self.set_active)
        act_open = menu.addAction('Open Active Dir')
        act_open.triggered.connect(self.open_active)
        menu.addSeparator()
        act_drift = menu.addAction('Compute Drift Now')
        act_drift.triggered.connect(lambda: self._compute_global_drift())
        act_store = menu.addAction('Refresh Feature Store')
        act_store.triggered.connect(lambda: self._refresh_feature_store())
        # Debug helper to inspect widget states
        act_debug = menu.addAction('Debug Widget States')
        def _debug_states():
            try:
                print('[DEBUG] Train button enabled:', getattr(self, 'train_btn', None).isEnabled() if getattr(self,'train_btn',None) else 'n/a', flush=True)
                print('[DEBUG] Auto-rescan enabled:', getattr(self, 'auto_rescan_chk', None).isEnabled() if getattr(self,'auto_rescan_chk',None) else 'n/a', flush=True)
                if getattr(self,'auto_rescan_chk',None):
                    print('[DEBUG] Auto-rescan checkable:', self.auto_rescan_chk.isCheckable(), 'checked:', self.auto_rescan_chk.isChecked(), flush=True)
                print('[DEBUG] Table geometry:', self.table.geometry() if hasattr(self,'table') else 'n/a', flush=True)
            except Exception as e:
                print('[DEBUG] Error during debug states:', e, flush=True)
        act_debug.triggered.connect(_debug_states)
        self.overflow_btn.setMenu(menu)
        self.overflow_btn.setPopupMode(QToolButton.InstantPopup)
        header_row.addWidget(self.overflow_btn, 0)
        # Help icon (info pop)
        help_btn = QToolButton()
        try:
            help_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        except Exception:
            help_btn.setText('?')
        help_btn.setToolTip('עזרה - Model Dashboard')
        from ui.shared.help_viewer import show_markdown_dialog
        help_btn.clicked.connect(lambda: show_markdown_dialog(self,'docs/model_dashboard_tab.md','Model Dashboard Help'))
        header_row.addWidget(help_btn, 0)
        # Inline usage toggle (ℹ) to expand/collapse quick guide without opening external help
        self.toggle_usage_btn = QToolButton()
        self.toggle_usage_btn.setText('ℹ')
        self.toggle_usage_btn.setToolTip('הצג / הסתר מדריך מהיר')
        self.toggle_usage_btn.setCheckable(True)
        self.toggle_usage_btn.setAutoRaise(True)
        self.toggle_usage_btn.toggled.connect(lambda _: self._toggle_usage())
        header_row.addWidget(self.toggle_usage_btn, 0)
        lay.addLayout(header_row)
        # Snapshot table (will be placed next to Train panel instead of top full width)
        self.table = QTableWidget(); self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Timestamp','Model','Samples','CV AUC','Dir','Horizons'])
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_menu)
        self.table.setMinimumHeight(220)
        # --- Train panel (left) + Snapshots table (right) ---
        train_snap_row = QHBoxLayout()
        # Train panel
        train_box = QGroupBox('Train / Update')
        from PySide6.QtWidgets import QButtonGroup
        train_vbox = QVBoxLayout(train_box); train_vbox.setContentsMargins(8,8,8,8); train_vbox.setSpacing(6)
        models_row = QHBoxLayout(); models_row.setSpacing(8)
        self.model_btn_group = QButtonGroup(self); self.model_btn_group.setExclusive(True)
        def _mk_model_btn(text):
            b = QPushButton(text.upper()); b.setCheckable(True); b.setObjectName('toggle_button'); b.setMinimumWidth(60); return b
        self.btn_rf = _mk_model_btn('rf'); self.btn_xgb = _mk_model_btn('xgb'); self.btn_lgbm = _mk_model_btn('lgbm')
        self.btn_rf.setChecked(True)
        for i,btn in enumerate([self.btn_rf, self.btn_xgb, self.btn_lgbm]):
            self.model_btn_group.addButton(btn, i); models_row.addWidget(btn)
        models_row.addStretch(1); train_vbox.addLayout(models_row)
        row2 = QHBoxLayout(); row2.setSpacing(10)
        self.horizons_edit = QLineEdit(); self.horizons_edit.setPlaceholderText('horizons e.g. 5,10,20'); self.horizons_edit.setFixedWidth(110)
        row2.addWidget(QLabel('Horizons:')); row2.addWidget(self.horizons_edit)
        self.training_days_back_spin = QSpinBox(); self.training_days_back_spin.setRange(30, 365); self.training_days_back_spin.setValue(60); self.training_days_back_spin.setSuffix(' tdays'); self.training_days_back_spin.setFixedWidth(90)
        row2.addWidget(QLabel('Train Range:')); row2.addWidget(self.training_days_back_spin)
        self.auto_rescan_chk = QCheckBox('Auto-rescan'); self.auto_rescan_chk.setChecked(True); row2.addWidget(self.auto_rescan_chk); row2.addStretch(1)
        train_vbox.addLayout(row2)
        row3 = QHBoxLayout(); row3.setSpacing(10)
        self.train_btn = QPushButton('Train'); self.train_btn.setObjectName('secondary_button')
        self.iterative_btn = QPushButton('Iterative Train'); self.iterative_btn.setObjectName('secondary_button'); self.iterative_btn.setToolTip('אימון היסטורי איטרטיבי עם כמה cutoff וולידציות מתקדמות')
        self.iterative_results_btn = QPushButton('Iter Results'); self.iterative_results_btn.setObjectName('secondary_button'); self.iterative_results_btn.setToolTip('הצג / רענן תוצאות איטרטיביות אחרונות')
        self.iterative_adv_toggle = QToolButton(); self.iterative_adv_toggle.setText('⋯'); self.iterative_adv_toggle.setCheckable(True); self.iterative_adv_toggle.setToolTip('הצג / הסתר הגדרות איטרטיביות מתקדמות')
        for w in (self.train_btn, self.iterative_btn, self.iterative_results_btn, self.iterative_adv_toggle): row3.addWidget(w)
        row3.addStretch(1); train_vbox.addLayout(row3)
        self.iterative_cfg_box = QWidget(); self.iterative_cfg_box.setVisible(False)
        cfg_form = QFormLayout(self.iterative_cfg_box); cfg_form.setContentsMargins(4,4,4,4); cfg_form.setSpacing(4); train_vbox.addWidget(self.iterative_cfg_box)
    # (Removed old flat train_hbox structure; replaced with structured rows above)
        # fields
        self.iter_start_cutoff_edit = QLineEdit(); self.iter_start_cutoff_edit.setPlaceholderText('YYYY-MM-DD (start cutoff)')
        self.iter_min_cutoff_edit = QLineEdit(); self.iter_min_cutoff_edit.setPlaceholderText('YYYY-MM-DD (min cutoff)')
        self.iter_validation_days_spin = QSpinBox(); self.iter_validation_days_spin.setRange(10,180); self.iter_validation_days_spin.setValue(80)
        self.iter_target_acc_spin = QDoubleSpinBox(); self.iter_target_acc_spin.setRange(0.1,0.999); self.iter_target_acc_spin.setSingleStep(0.01); self.iter_target_acc_spin.setValue(0.6)
        self.iter_improve_thr_spin = QDoubleSpinBox(); self.iter_improve_thr_spin.setRange(0.000,0.05); self.iter_improve_thr_spin.setDecimals(4); self.iter_improve_thr_spin.setSingleStep(0.001); self.iter_improve_thr_spin.setValue(0.005)
        self.iter_max_iter_spin = QSpinBox(); self.iter_max_iter_spin.setRange(1,15); self.iter_max_iter_spin.setValue(5)
        self.iter_threshold_spin = QDoubleSpinBox(); self.iter_threshold_spin.setRange(0.001,0.2); self.iter_threshold_spin.setSingleStep(0.001); self.iter_threshold_spin.setValue(0.02)
        self.iter_weight_alpha_spin = QDoubleSpinBox(); self.iter_weight_alpha_spin.setRange(0.0,1.0); self.iter_weight_alpha_spin.setSingleStep(0.05); self.iter_weight_alpha_spin.setValue(0.5)
        # add rows
        cfg_form.addRow('Start Cutoff:', self.iter_start_cutoff_edit)
        cfg_form.addRow('Min Cutoff:', self.iter_min_cutoff_edit)
        cfg_form.addRow('Validation Days:', self.iter_validation_days_spin)
        cfg_form.addRow('Target Acc:', self.iter_target_acc_spin)
        cfg_form.addRow('Improve Δ:', self.iter_improve_thr_spin)
        cfg_form.addRow('Max Iter:', self.iter_max_iter_spin)
        cfg_form.addRow('Label Thr (ret):', self.iter_threshold_spin)
        cfg_form.addRow('Blend α:', self.iter_weight_alpha_spin)
        # horizons for iterative
        self.iter_horizons_edit = QLineEdit(); self.iter_horizons_edit.setPlaceholderText('Iter horizons e.g. 1,5,10'); cfg_form.addRow('Iter Horizons:', self.iter_horizons_edit)
        # Connections
        self.iterative_adv_toggle.toggled.connect(lambda v: self.iterative_cfg_box.setVisible(v))
        self.train_btn.clicked.connect(self._emit_train_request)
        self.iterative_btn.clicked.connect(self._emit_iterative_train)
        self.iterative_results_btn.clicked.connect(self._toggle_iter_results_box)
        # Style toggle buttons via stylesheet tweak (if style manager not already handling)
        try:
            self.setStyleSheet(self.styleSheet() + '\nQPushButton#toggle_button:checked { background:#2563eb; color:white; font-weight:bold; }\nQPushButton#toggle_button { background:#2d2d2d; color:#ddd; }')
        except Exception:
            pass
        # Add train panel and snapshot table to shared row
        train_snap_row.addWidget(train_box, 1)
        train_snap_row.addWidget(self.table, 2)
        lay.addLayout(train_snap_row)
        # Inline active model metrics (auto-refreshed after training)
        self.metrics_box = QGroupBox('Active Model Metrics')
        mb_lay = QGridLayout(self.metrics_box); mb_lay.setContentsMargins(8,6,8,6); mb_lay.setSpacing(6)
        self.lbl_active_model = QLabel('Model: --')
        self.lbl_active_auc = QLabel('AUC: --')
        self.lbl_active_cv = QLabel('CV AUC: --')
        self.lbl_active_samples = QLabel('Samples: --')
        self.lbl_active_thr = QLabel('Threshold: --')
        self.edit_thresholds_btn = QPushButton('Edit Thresholds'); self.edit_thresholds_btn.setObjectName('secondary_button')
        self.lbl_active_hz = QLabel('Horizons: --')
        self.lbl_active_drift = QLabel('Avg Drift (last scan): --')
        labels = [
            ('Model', self.lbl_active_model),
            ('Val AUC', self.lbl_active_auc),
            ('CV AUC', self.lbl_active_cv),
            ('Samples', self.lbl_active_samples),
            ('Threshold', self.lbl_active_thr),
            ('Horizons', self.lbl_active_hz),
            ('Drift', self.lbl_active_drift)
        ]
        for row,(t,lbl) in enumerate(labels):
            mb_lay.addWidget(QLabel(t+':'), row, 0)
            mb_lay.addWidget(lbl, row, 1)
        mb_lay.addWidget(self.edit_thresholds_btn, 0, 2, 2, 1)
        self.edit_thresholds_btn.clicked.connect(self._open_threshold_editor)
        # Build feature store / drift panel now (to place beside metrics)
        fs_box = self._build_feature_store_section()
        bottom_row = QHBoxLayout(); bottom_row.setSpacing(12)
        bottom_row.addWidget(self.metrics_box, 1)
        bottom_row.addWidget(fs_box, 1)
        lay.addLayout(bottom_row)
        # Iterative results viewer (collapsed by default)
        self.iter_results_box = QGroupBox('Iterative Results (Latest)')
        self.iter_results_box.setVisible(False)
        from PySide6.QtWidgets import QVBoxLayout as _QVBL2, QHBoxLayout as _QHBL2, QComboBox as _QCB2, QPushButton as _QPB2
        ir_layout = _QVBL2(self.iter_results_box); ir_layout.setContentsMargins(8,6,8,8); ir_layout.setSpacing(6)
        top_row = _QHBL2(); top_row.setSpacing(8)
        self.iter_results_refresh_btn = _QPB2('Refresh')
        self.iter_results_refresh_btn.setObjectName('secondary_button')
        self.iter_results_hz_filter = _QCB2(); self.iter_results_hz_filter.addItem('All')
        self.iter_results_status = QLabel('')
        top_row.addWidget(self.iter_results_refresh_btn)
        top_row.addWidget(QLabel('Horizon:'))
        top_row.addWidget(self.iter_results_hz_filter)
        top_row.addWidget(self.iter_results_status, 1)
        ir_layout.addLayout(top_row)
        self.iter_results_table = QTableWidget(); self.iter_results_table.setColumnCount(9)
        self.iter_results_table.setHorizontalHeaderLabels(['Date','Symbol','Horizon','PredProb','PredCls','ActualCls','ActRet','Correct','TargetDate'])
        self.iter_results_table.setMinimumHeight(160)
        ir_layout.addWidget(self.iter_results_table, 1)
        lay.addWidget(self.iter_results_box)
        self.iter_results_refresh_btn.clicked.connect(self._load_latest_iter_results)
        self.iter_results_hz_filter.currentIndexChanged.connect(self._apply_iter_results_filter)
        self._iter_results_rows = []  # cached raw rows
        # Safety: ensure interactive controls remain enabled
        try:
            self.auto_rescan_chk.setEnabled(True)
            self.train_btn.setEnabled(True)
            self.auto_rescan_chk.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        except Exception:
            pass
        # --- Deep debug instrumentation (temporary) ---
        try:
            # Remove debug highlight styling; keep event filters only if needed
            self.auto_rescan_chk.installEventFilter(self)
            self.train_btn.installEventFilter(self)
            train_box.installEventFilter(self)
            # Improved visibility for checkbox (explicit border + fill)
            self.auto_rescan_chk.setStyleSheet(
                'QCheckBox { padding:1px; }'
                'QCheckBox::indicator { width:16px; height:16px; border:1px solid #888; background:#fff; }'
                'QCheckBox::indicator:checked { background:#16a34a; border:2px solid #0d7a35; }'
                'QCheckBox::indicator:unchecked { background:#fff; }'
            )
        except Exception:
            pass
        try:
            QTimer.singleShot(800, self._dump_widget_states)
        except Exception:
            pass

        # Usage guide now minimal icon-driven (still keep internal browser hidden until needed)
        self.usage_browser = QTextBrowser()
        self.usage_browser.setVisible(False)
        self.usage_browser.setOpenExternalLinks(True)
        self.usage_browser.setStyleSheet('background:#1e1e1e; color:#ffffff; font-size:12px;')
        lay.addWidget(self.usage_browser)
        # Simple automation flags (future expansion)
        self._automation_enabled_override = True
        self._populate_usage_text()
        self.load_index()
        # Initial metrics load (if active exists)
        try:
            QTimer.singleShot(200, self.load_active_metrics)
        except Exception:
            pass
    # Initial refresh done inside _build_feature_store_section

    def _build_feature_store_section(self):
        box = QGroupBox('Feature Store & Drift')
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
        outer = QVBoxLayout(box); outer.setContentsMargins(8,8,8,8); outer.setSpacing(6)
        top_row = QHBoxLayout(); top_row.setSpacing(10)
        self.fs_refresh_btn = QPushButton('Refresh'); self.fs_refresh_btn.setObjectName('secondary_button')
        self.drift_refresh_btn = QPushButton('Drift'); self.drift_refresh_btn.setObjectName('secondary_button')
        self.drift_label = QLabel('Drift: --')
        top_row.addWidget(self.fs_refresh_btn)
        top_row.addWidget(self.drift_refresh_btn)
        top_row.addWidget(self.drift_label)
        top_row.addStretch(1)
        outer.addLayout(top_row)
        self.fs_table = QTableWidget(); self.fs_table.setColumnCount(3); self.fs_table.setHorizontalHeaderLabels(['Symbol','Age(s)','Feature Count'])
        self.fs_table.setMinimumHeight(140)
        outer.addWidget(self.fs_table)
        # Connections
        self.fs_refresh_btn.clicked.connect(self._refresh_feature_store)
        self.drift_refresh_btn.clicked.connect(self._compute_global_drift)
        # Initial refresh
        self._refresh_feature_store()
        return box

    def _refresh_feature_store(self):
        try:
            from ml.feature_store import snapshot_catalog
            rows = snapshot_catalog()
            self.fs_table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                for c,k in enumerate(['symbol','age_sec','feature_count']):
                    val = r.get(k,'')
                    if k == 'age_sec':
                        try:
                            val = int(val)
                        except Exception:
                            pass
                    self.fs_table.setItem(i,c,QTableWidgetItem(str(val)))
        except Exception:
            pass

    def _compute_global_drift(self):
        # simplistic: sample up to first 25 entries and average drift vs active model feature_stats if present
        try:
            active_meta = None
            import os, json
            act_ptr = os.path.join('ml','registry','ACTIVE.txt')
            if os.path.exists(act_ptr):
                with open(act_ptr,'r',encoding='utf-8') as f:
                    adir = f.read().strip()
                md = os.path.join(adir,'metadata.json')
                if os.path.exists(md):
                    with open(md,'r',encoding='utf-8') as mf:
                        active_meta = json.load(mf)
            feature_stats = None
            if active_meta:
                feature_stats = active_meta.get('feature_stats') or None
            if not feature_stats:
                self.drift_label.setText('Drift: n/a (no stats)')
                return
            from ml.feature_store import snapshot_catalog, get_features, compute_drift
            catalog = snapshot_catalog()
            if not catalog:
                self.drift_label.setText('Drift: empty store')
                return
            sample = catalog[:25]
            drifts = []
            for row in sample:
                sym = row.get('symbol')
                rec = get_features(sym)
                feats = None
                try:
                    feats = (rec or {}).get('features')
                except Exception:
                    feats = None
                d = compute_drift(feats, feature_stats)
                if d is not None:
                    drifts.append(d)
            if drifts:
                avg = sum(drifts)/len(drifts)
                self.drift_label.setText(f'Drift: {avg:.3f} (n={len(drifts)})')
            else:
                self.drift_label.setText('Drift: no overlap')
        except Exception:
            self.drift_label.setText('Drift: error')
        # Also update drift line in metrics panel if present
        try:
            if hasattr(self,'lbl_active_drift'):
                self.lbl_active_drift.setText(self.drift_label.text().replace('Drift:','').strip())
        except Exception:
            pass

    # ------------------ Active Metrics Loader ------------------
    def load_active_metrics(self):
        try:
            import os, json
            act_ptr = os.path.join('ml','registry','ACTIVE.txt')
            if not os.path.exists(act_ptr):
                return
            with open(act_ptr,'r',encoding='utf-8') as f:
                adir = f.read().strip()
            meta_path = os.path.join(adir,'metadata.json')
            thr_path = os.path.join(adir,'thresholds.json')
            meta = {}
            thr = {}
            if os.path.exists(meta_path):
                with open(meta_path,'r',encoding='utf-8') as mf: meta = json.load(mf) or {}
            if os.path.exists(thr_path):
                with open(thr_path,'r',encoding='utf-8') as tf: thr = json.load(tf) or {}
            self.lbl_active_model.setText(str(meta.get('model_type','--')))
            val_auc = meta.get('validation',{}).get('auc') if isinstance(meta.get('validation'),dict) else None
            self.lbl_active_auc.setText(f"{val_auc:.3f}" if isinstance(val_auc,(int,float)) else '--')
            cv_auc = meta.get('cv_mean_auc')
            self.lbl_active_cv.setText(f"{cv_auc:.3f}" if isinstance(cv_auc,(int,float)) else '--')
            self.lbl_active_samples.setText(str(meta.get('samples','--')))
            glob_thr = thr.get('global')
            self.lbl_active_thr.setText(f"{glob_thr:.3f}" if isinstance(glob_thr,(int,float)) else '--')
            hz = meta.get('horizons')
            self.lbl_active_hz.setText(','.join(str(h) for h in hz) if isinstance(hz,(list,tuple)) else '--')
        except Exception:
            pass

    # ------------------ Usage Guide Helpers ------------------
    def _toggle_usage(self):
        self.usage_browser.setVisible(not self.usage_browser.isVisible())

    def _populate_usage_text(self):
        # Short operational guide requested by user; keep concise & update-friendly
        guide = []
        guide.append('<h3 style="color:#fff;">ML Workflow – Quick Guide</h3>')
        guide.append('<ol style="margin-left:14px;">')
        guide.append('<li><b>Train</b>: Use the form above (or Scan tab). Enter horizons (e.g. 5,10,20). Snapshot + thresholds auto-saved & promoted.</li>')
        guide.append('<li><b>Optimize Ensemble</b>: After having ≥2 base models (rf/xgb/lgbm), click "Optimize Ensemble / Meta" on this tab (button placed in Models section). Weighted ensemble + stacking meta AUC saved to <code>ensemble.json</code>.</li>')
        guide.append('<li><b>Run Scan</b>: In Scan tab pick horizon (if multi), model (rf/xgb/lgbm/ensemble) and press SCAN. Rows below active threshold (per-horizon → global → manual) are filtered.</li>')
        guide.append('<li><b>Explain</b>: Select a result row -> Explain Row for top feature contributions. Use Score Decomposition for score components (prob, R:R, freshness, pattern).</li>')
        guide.append('<li><b>Adjust Scoring</b>: Tweak weights / formula (weighted vs geometric). Re-run SCAN to see ordering impact.</li>')
        guide.append('<li><b>Monitoring</b>: Background loop logs predictions (<code>logs/predictions.jsonl</code>), backfills outcomes and shows live F1/AUC in status bar. Drift spikes trigger retrain suggestion.</li>')
        guide.append('<li><b>Thresholds</b>: Auto-optimized (F1) at training; adaptively nudged by live precision. Edit manually by setting Min ML Prob or adjusting JSON in snapshot.</li>')
        guide.append('<li><b>Snapshots</b>: Listed above. Select and press Set Active to switch. ACTIVE pointer drives scan inference.</li>')
        guide.append('<li><b>Retrain</b>: When drift high or performance drops (F1/AUC down) – retrain. New snapshot auto-promotes if criteria (currently always) met.</li>')
        guide.append('</ol>')
        guide.append('<p style="font-size:11px;color:#bbb;">Artifacts: <code>ml/registry/&lt;timestamp&gt;</code> (models + thresholds), <code>ensemble.json</code>, <code>thresholds.json</code>, <code>logs/predictions.jsonl</code>. You can hide this panel after reading.</p>')
        self.usage_browser.setHtml('\n'.join(guide))

    # ------------------ Internal Actions ------------------
    def _emit_train_request(self):
        # Determine selected model from toggle buttons
        if self.btn_rf.isChecked():
            model = 'rf'
        elif self.btn_xgb.isChecked():
            model = 'xgb'
        elif self.btn_lgbm.isChecked():
            model = 'lgbm'
        else:
            model = 'rf'
        params = {
            'ml_model': model,
            'horizons': self.horizons_edit.text(),
            'training_days_back': self.training_days_back_spin.value(),
            'auto_rescan': bool(self.auto_rescan_chk.isChecked())
        }
        try:
            print('[DEBUG] _emit_train_request called with', params, flush=True)
            self.train_ml_requested.emit(params)
            self.info_lbl.setText(f"Training requested: {params['ml_model']} horizons={params['horizons'] or 'single'}")
        except Exception:
            pass

    def _emit_iterative_train(self):
        """Emit iterative training request with collected params"""
        params = {
            'start_cutoff': self.iter_start_cutoff_edit.text().strip() or None,
            'min_cutoff': self.iter_min_cutoff_edit.text().strip() or None,
            'validation_days': self.iter_validation_days_spin.value(),
            'target_accuracy': self.iter_target_acc_spin.value(),
            'improvement_threshold': self.iter_improve_thr_spin.value(),
            'max_iterations': self.iter_max_iter_spin.value(),
            'label_threshold': self.iter_threshold_spin.value(),  # תגית הצלחה
            'blend_alpha': self.iter_weight_alpha_spin.value(),   # משקל דיוק משוקלל
            'horizons': self.iter_horizons_edit.text().strip() or '5'
        }
        try:
            print('[DEBUG] iterative_training_request', params, flush=True)
            self.info_lbl.setText('Iterative training started...')
            self.iterative_training_requested.emit(params)
        except Exception:
            pass

    # ------------------ Iterative Results Viewer ------------------
    def _toggle_iter_results_box(self):
        try:
            vis = not self.iter_results_box.isVisible()
            self.iter_results_box.setVisible(vis)
            if vis:
                self._load_latest_iter_results()
        except Exception as e:
            print('[ITER_RES] toggle error', e, flush=True)

    def _latest_iteration_basepath(self):
        try:
            d = os.path.join('ml','iterative_results')
            if not os.path.isdir(d):
                return None
            files = [f for f in os.listdir(d) if f.startswith('iteration_') and f.endswith('.json') and '_predictions' not in f and '_actual_results' not in f]
            if not files:
                return None
            # sort by iteration number then date (filenames include iteration_XX_YYYYMMDD)
            def _key(fn):
                try:
                    parts = fn.split('_')
                    it = int(parts[1])
                    date_part = parts[2].split('.')[0]
                    return (it, date_part)
                except Exception:
                    return (0, fn)
            files.sort(key=_key, reverse=True)
            latest = files[0]
            return os.path.join(d, latest[:-5])  # strip .json
        except Exception:
            return None

    def _load_latest_iter_results(self):
        base = self._latest_iteration_basepath()
        if not base:
            self.iter_results_status.setText('No iteration files')
            self.iter_results_table.setRowCount(0)
            return
        actual_path = base + '_actual_results.json'
        summary_path = base + '.json'
        if not os.path.exists(actual_path):
            self.iter_results_status.setText('No actual_results file for latest iteration')
            self.iter_results_table.setRowCount(0)
            return
        try:
            with open(actual_path,'r',encoding='utf-8') as f:
                data = json.load(f) or []
        except Exception as e:
            self.iter_results_status.setText(f'Load error: {e}')
            return
        self._iter_results_rows = data
        # Load summary for accuracy stats, if present
        acc_label = ''
        try:
            if os.path.exists(summary_path):
                with open(summary_path,'r',encoding='utf-8') as sf:
                    summary = json.load(sf) or {}
                accs = summary.get('accuracy_by_horizon') or {}
                avg_acc = summary.get('avg_accuracy')
                parts = []
                for h, a in accs.items():
                    try:
                        parts.append(f"{h}D {a:.3f}")
                    except Exception:
                        pass
                if avg_acc is not None:
                    parts.append(f"AVG {avg_acc:.3f}")
                if parts:
                    acc_label = ' | '.join(parts)
        except Exception:
            pass
        # populate horizon filter
        try:
            horizons = sorted({r.get('horizon') for r in data if 'horizon' in r})
            self.iter_results_hz_filter.blockSignals(True)
            self.iter_results_hz_filter.clear(); self.iter_results_hz_filter.addItem('All')
            for h in horizons:
                self.iter_results_hz_filter.addItem(str(h))
            self.iter_results_hz_filter.blockSignals(False)
        except Exception:
            pass
        self._apply_iter_results_filter()
        base_name = os.path.basename(base)
        if acc_label:
            self.iter_results_status.setText(f"{base_name}: {len(data)} rows | {acc_label}")
        else:
            self.iter_results_status.setText(f"{base_name}: {len(data)} rows")

    def _apply_iter_results_filter(self):
        try:
            self.iter_results_table.setRowCount(0)
            if not self._iter_results_rows:
                return
            sel = self.iter_results_hz_filter.currentText() if self.iter_results_hz_filter.count() else 'All'
            rows = self._iter_results_rows
            if sel and sel != 'All':
                try:
                    hv = int(sel)
                    rows = [r for r in rows if r.get('horizon') == hv]
                except Exception:
                    pass
            self.iter_results_table.setRowCount(len(rows))
            for i,r in enumerate(rows):
                vals = [
                    r.get('date',''), r.get('symbol',''), r.get('horizon',''),
                    f"{r.get('prediction_proba',0):.3f}", r.get('prediction_class',''), r.get('actual_class',''),
                    f"{r.get('actual_return',0):.3f}", '✓' if r.get('prediction_correct') else '✗', r.get('target_date','')
                ]
                for c,v in enumerate(vals):
                    self.iter_results_table.setItem(i,c,QTableWidgetItem(str(v)))
        except Exception as e:
            self.iter_results_status.setText(f'Filter err: {e}')

    # ------------------ Threshold Editor ------------------
    def _open_threshold_editor(self):
        try:
            import os, json
            act_ptr = os.path.join('ml','registry','ACTIVE.txt')
            if not os.path.exists(act_ptr):
                QMessageBox.information(self,'Info','No active snapshot')
                return
            with open(act_ptr,'r',encoding='utf-8') as f:
                adir = f.read().strip()
            thr_path = os.path.join(adir,'thresholds.json')
            if not os.path.exists(thr_path):
                QMessageBox.information(self,'Info','No thresholds.json found')
                return
            with open(thr_path,'r',encoding='utf-8') as tf:
                data = json.load(tf) or {}
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
            dlg = QDialog(self); dlg.setWindowTitle('עריכת Thresholds'); dlg.resize(500,600)
            v = QVBoxLayout(dlg); txt = QTextEdit();
            import json as _json
            txt.setText(_json.dumps(data, ensure_ascii=False, indent=2))
            hint = QLabel('עדכן ערכים בזהירות. שמירה תעדכן thresholds.json ותטען מחדש ל-Active Metrics.')
            v.addWidget(hint); v.addWidget(txt,1)
            btn_row = QHBoxLayout(); save_btn = QPushButton('שמור'); cancel_btn = QPushButton('סגור')
            btn_row.addWidget(save_btn); btn_row.addWidget(cancel_btn); btn_row.addStretch(1); v.addLayout(btn_row)
            def _save():
                try:
                    new_obj = json.loads(txt.toPlainText())
                    with open(thr_path,'w',encoding='utf-8') as wf:
                        json.dump(new_obj, wf, ensure_ascii=False, indent=2)
                    self.lbl_active_thr.setText(str(new_obj.get('global','--')) if isinstance(new_obj.get('global'),(int,float)) else '--')
                    QMessageBox.information(self,'נשמר','Thresholds עודכנו')
                    dlg.close()
                except Exception as e:
                    QMessageBox.critical(self,'שגיאה', str(e))
            save_btn.clicked.connect(_save); cancel_btn.clicked.connect(dlg.close)
            dlg.exec()
        except Exception as e:
            try: QMessageBox.critical(self,'Error', str(e))
            except Exception: pass

    # Debug helper
    def _dump_widget_states(self):
        try:
            print('[DUMP] train_btn enabled=', self.train_btn.isEnabled(), 'visible=', self.train_btn.isVisible(), 'geom=', self.train_btn.geometry(), flush=True)
            print('[DUMP] auto_rescan enabled=', self.auto_rescan_chk.isEnabled(), 'checkable=', self.auto_rescan_chk.isCheckable(), 'checked=', self.auto_rescan_chk.isChecked(), 'geom=', self.auto_rescan_chk.geometry(), flush=True)
            print('[DUMP] table geom=', self.table.geometry(), 'parent size=', self.size(), flush=True)
            # Hit-test: map center point of checkbox to global for potential overlay suspicion not possible here but we log anyway
        except Exception as e:
            print('[DUMP] error:', e, flush=True)

    def eventFilter(self, obj, event):
        try:
            if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick):
                print(f"[EVT] {obj.__class__.__name__} mouse {event.type().name} at", getattr(event, 'position', lambda: None)(), flush=True)
            if obj is self.auto_rescan_chk and event.type() == QEvent.Type.MouseButtonPress:
                print('[EVT] Click on auto_rescan_chk - enabled?', self.auto_rescan_chk.isEnabled(), 'checkable?', self.auto_rescan_chk.isCheckable(), flush=True)
            if obj is self.auto_rescan_chk and event.type() == QEvent.Type.MouseButtonRelease:
                # Log state after release
                prev = getattr(self, '_last_auto_state', self.auto_rescan_chk.isChecked())
                cur = self.auto_rescan_chk.isChecked()
                print(f'[EVT] auto_rescan_chk release state prev={prev} now={cur}', flush=True)
                if prev == cur:
                    # Force toggle manually as fallback
                    self.auto_rescan_chk.setChecked(not cur)
                    print(f'[EVT] auto_rescan_chk manually toggled to {self.auto_rescan_chk.isChecked()}', flush=True)
                self._last_auto_state = self.auto_rescan_chk.isChecked()
            if obj is self.train_btn and event.type() == QEvent.Type.MouseButtonPress:
                print('[EVT] Click on train_btn - enabled?', self.train_btn.isEnabled(), flush=True)
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _toggle_automation(self):
        # Placeholder kept for compatibility (now always ON unless changed programmatically)
        self._automation_enabled_override = True

    def load_index(self):
        idx_path = os.path.join('ml','registry','index.json')
        self.table.setRowCount(0)
        if not os.path.exists(idx_path):
            self.info_lbl.setText('No registry index found')
            return
        try:
            with open(idx_path,'r',encoding='utf-8') as f:
                data = json.load(f) or []
        except Exception as e:
            self.info_lbl.setText(f'Failed to load index: {e}')
            return
        self.table.setRowCount(len(data))
        active_ptr = None
        try:
            with open(os.path.join('ml','registry','ACTIVE.txt'),'r',encoding='utf-8') as af:
                active_ptr = af.read().strip()
        except Exception:
            active_ptr = None
        for r,row in enumerate(data):
            ts = row.get('timestamp','')
            # find metadata for horizons
            meta_horizons = ''
            try:
                md = os.path.join(row.get('snapshot_dir',''),'metadata.json')
                if os.path.exists(md):
                    with open(md,'r',encoding='utf-8') as mf:
                        mdat = json.load(mf)
                    hz = mdat.get('horizons')
                    if isinstance(hz,(list,tuple)):
                        meta_horizons = ','.join(str(x) for x in hz)
            except Exception:
                pass
            values = [ts, row.get('model_type',''), str(row.get('samples','')), f"{row.get('cv_mean_auc','')}", row.get('snapshot_dir',''), meta_horizons]
            for c,val in enumerate(values):
                self.table.setItem(r,c,QTableWidgetItem(str(val)))
            try:
                p = row.get('snapshot_dir','')
                if active_ptr and p == active_ptr:
                    accent_bg = StyleManager.COLORS.get('accent_bg', '#eef6ff')
                    accent_fg = StyleManager.COLORS.get('accent', '#3b82f6')
                    for c in range(self.table.columnCount()):
                        it = self.table.item(r,c)
                        if it:
                            it.setBackground(Qt.GlobalColor.transparent)
                            # Use HTML-like coloring via foreground since per-cell stylesheet is limited
                            from PySide6.QtGui import QBrush, QColor
                            it.setBackground(QColor(accent_bg))
                            it.setForeground(QBrush(QColor(accent_fg)))
                            f = it.font(); f.setBold(True); it.setFont(f)
            except Exception:
                pass
        self.info_lbl.setText(f'{self.table.rowCount()} snapshots loaded')

    def _show_table_menu(self, pos):
        row = self.table.indexAt(pos).row()
        if row < 0:
            return
        menu = QMenu(self)
        a_set = menu.addAction('Set Active')
        a_open = menu.addAction('Open Dir')
        a_copy = menu.addAction('Copy Path')
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == a_set:
            self.table.selectRow(row)
            self.set_active()
        elif chosen == a_open:
            self.table.selectRow(row)
            self.open_active()
        elif chosen == a_copy:
            try:
                path = self.table.item(row,4).text()
                from PySide6.QtGui import QGuiApplication
                QGuiApplication.clipboard().setText(path)
                self.info_lbl.setText('Copied path')
            except Exception:
                pass

    def set_active(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self,'Info','Select a snapshot row first')
            return
        snapshot_dir = self.table.item(row,4).text() if self.table.item(row,4) else ''
        if not snapshot_dir or not os.path.isdir(snapshot_dir):
            QMessageBox.warning(self,'Warning','Snapshot directory invalid')
            return
        # Write ACTIVE.txt with path to metadata.json (or model artifact if present)
        try:
            active_path = os.path.join('ml','registry','ACTIVE.txt')
            with open(active_path,'w',encoding='utf-8') as f:
                f.write(snapshot_dir)
            self.info_lbl.setText(f'Active set: {snapshot_dir}')
        except Exception as e:
            QMessageBox.critical(self,'Error',f'Failed to set active: {e}')

    def open_active(self):
        try:
            ap = os.path.join('ml','registry','ACTIVE.txt')
            if not os.path.exists(ap):
                QMessageBox.information(self,'Info','No active model set')
                return
            with open(ap,'r',encoding='utf-8') as f:
                d = f.read().strip()
            if not os.path.isdir(d):
                QMessageBox.warning(self,'Warning','Active directory missing')
                return
            # On Windows, open in explorer
            import subprocess, sys
            if sys.platform.startswith('win'):
                subprocess.Popen(['explorer', d])
            else:
                subprocess.Popen(['xdg-open', d])
        except Exception as e:
            QMessageBox.critical(self,'Error',f'Failed to open: {e}')
