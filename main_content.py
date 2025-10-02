"""Slim orchestration facade for the application main content.

All heavy UI logic has been moved to dedicated modules under ui/tabs/ and
background processing lives in ui/worker_thread.py. This file now:
  * Creates the tab widget and adds modular tabs
  * Manages data loading threads (catalog & daily update)
  * Forwards scan/backtest/optimize/auto-discovery requests to tabs
  * Exposes a stable MainContent API for existing code
"""

import os, json, threading, datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QPushButton,
                               QProgressBar, QFileDialog, QMessageBox, QLineEdit, QSizePolicy)
from PySide6.QtCore import Signal, QThread, QTimer, Qt
from PySide6.QtGui import QGuiApplication

from styles import StyleManager
# Always use the new ScanTab implementation; guard against accidental legacy import
from ui.tabs.scan_tab import ScanTab as NewScanTab
from ui.tabs.backtest_tab import BacktestTab
from ui.tabs.optimize_tab import OptimizeTab
from ui.tabs.ibkr_tab import IBKRTab
from ui.tabs.model_dashboard_tab import ModelDashboardTab
from ui.tabs.run_repo_tab import RunRepoTab
from ui.tabs.watchlist_tab import WatchListTab

class MainContent(QWidget):
    tab_changed = Signal(int)
    training_progress = Signal(dict)  # emits progress events from training thread
    
    def __init__(self):
        super().__init__()
        self.data_map = {}
        self.current_params = {}
        self._active_model_snapshot_dir = None
        self._drift_history = []  # store recent drift values (mean across symbols) for trigger logic
        self._pending_retrain_flag = False
        self._last_auto_retrain_ts = None
        self._automation_cfg = self._load_automation_cfg()
        self.setup_ui()
        self.apply_styles()
        try:
            self.training_progress.connect(self._handle_training_progress)
        except Exception:
            pass
        # --- Unified bottom bar (buttons + status + progress) ---
        from PySide6.QtWidgets import QHBoxLayout, QFrame, QSizePolicy
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottom_bar")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(8, 6, 8, 6)
        bottom_layout.setSpacing(6)
        bottom_frame.setFixedHeight(40)  # Smaller frame for compact buttons
        self.bottom_layout = bottom_layout  # keep reference for dynamic insertions

        # Action buttons (compact modern look)
        def _mk_btn(text, slot):
            b = QPushButton(text)
            b.setObjectName('toolbar_button')  # custom style
            b.clicked.connect(slot)
            b.setMinimumWidth(95)   # Increased width for progress display
            b.setFixedHeight(28)    # Match the refresh button height
            b.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            return b

        self.daily_update_btn = _mk_btn("Daily Update", self._on_daily_update_clicked)
        self.daily_update_btn.setToolTip("Download new data, convert to Parquet, and update catalog")
        
        self.verify_data_btn = _mk_btn("Verify Data", self._on_verify_data_clicked)
        self.verify_data_btn.setToolTip("Verify data integrity and completeness")
        
        self.force_rebuild_btn = _mk_btn("Force Rebuild", self._on_force_rebuild_clicked)
        self.force_rebuild_btn.setToolTip("Emergency: Force complete rebuild of all data (for troubleshooting)")

        # Simplified button layout - removed redundant Build/Refresh and Normalize
        for btn in [self.daily_update_btn, self.verify_data_btn, self.force_rebuild_btn]:
            bottom_layout.addWidget(btn, 0, Qt.AlignVCenter)

        # Stretch spacer before status + progress
        from PySide6.QtWidgets import QWidget as _W
        spacer = _W(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bottom_layout.addWidget(spacer)
        self._bottom_spacer = spacer

        # Status label (single line) & progress bar (slim)
        # Use QLineEdit (read-only) instead of QLabel so selection & copy works reliably across platforms
        from PySide6.QtWidgets import QHBoxLayout, QWidget as _W
        status_container = _W()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0,0,0,0)
        status_layout.setSpacing(4)
        self.status_label = QLineEdit("טוען נתונים... אנא המתן")
        self.status_label.setReadOnly(True)
        self.status_label.setObjectName("status_info")
        # Allow it to expand as much as possible (remove narrow clipping)
        self.status_label.setMinimumWidth(300)  # Reduced minimum to allow more flexibility
        try:
            from PySide6.QtWidgets import QSizePolicy as _SP
            self.status_label.setSizePolicy(_SP.Expanding, _SP.Preferred)
        except Exception:
            pass
        try:
            # Changed to left align for better text display, especially for progress messages
            self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        except Exception:
            pass
        try:
            self.status_label.setFrame(True)
            self.status_label.setFocusPolicy(Qt.ClickFocus)
            self.status_label.setCursorPosition(0)
            self.status_label.setToolTip('סטטוס (סמן והעתק או כפתור Copy)')
            self.status_label.setContextMenuPolicy(Qt.ActionsContextMenu)
            copy_act = self.status_label.addAction('Copy', QLineEdit.TrailingPosition)
            def _copy_status_ctx():
                try: QGuiApplication.clipboard().setText(self.status_label.text())
                except Exception: pass
            copy_act.triggered.connect(_copy_status_ctx)
        except Exception:
            pass
        status_layout.addWidget(self.status_label, 1)
        # Removed explicit Copy button (field is selectable; right-click or Ctrl+C works)
        bottom_layout.addWidget(status_container, 5)
        try:
            # Increase stretch so status gets priority; reduce others later
            bottom_layout.setStretch(bottom_layout.indexOf(status_container), 5)
        except Exception:
            pass

        # Cache stats label (styled as info box)
        self.cache_label = QLabel("Cache: 0 files / 0 rows / 0 symbols")
        self.cache_label.setObjectName('cache_info_box')
        self.cache_label.setMinimumWidth(180)
        self.cache_label.setFixedHeight(28)  # Match button height
        self.cache_label.setAlignment(Qt.AlignCenter)
        self.cache_label.setToolTip("Current cache statistics - click refresh to update")
        bottom_layout.addWidget(self.cache_label, 0)
        # Refresh cache stats button (small)
        self.cache_refresh_btn = QPushButton('↻')
        self.cache_refresh_btn.setFixedSize(28, 28)  # Keep square button same size
        self.cache_refresh_btn.setObjectName('cache_refresh_button')  # Different style
        self.cache_refresh_btn.setToolTip("Refresh cache statistics")
        self.cache_refresh_btn.clicked.connect(self.update_cache_stats)
        bottom_layout.addWidget(self.cache_refresh_btn, 0, Qt.AlignVCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setMaximumWidth(160)
        self.progress_bar.setMinimumHeight(10)
        bottom_layout.addWidget(self.progress_bar, 0)
        try:
            bottom_layout.setStretch(bottom_layout.indexOf(self.progress_bar), 0)
        except Exception:
            pass
        # Add auto elide tooltip logic so if text is clipped user can hover to see full
        try:
            from PySide6.QtGui import QFontMetrics
            def _refresh_status_tooltip():
                try:
                    fm = QFontMetrics(self.status_label.font())
                    full = self.status_label.text()
                    # Compute elided version for current width (minus small padding)
                    avail = max(10, self.status_label.width() - 12)
                    elided = fm.elidedText(full, Qt.TextElideMode.ElideMiddle, avail)
                    if elided != full:
                        self.status_label.setToolTip(full)
                    else:
                        # Keep existing tooltip if we set one earlier for other reasons
                        if self.status_label.toolTip() == '' or 'סטטוס' in self.status_label.toolTip():
                            self.status_label.setToolTip(full)
                except Exception:
                    pass
            self.status_label.textChanged.connect(lambda _: _refresh_status_tooltip())
            from PySide6.QtCore import QTimer as _QT
            _QT.singleShot(1200, _refresh_status_tooltip)
        except Exception:
            pass

        self.layout().addWidget(bottom_frame)
        # Keep tabs enabled; removed previous '(Loading...)' suffix mechanism for cleaner UI
        self._data_loading = True
        default_folder = os.path.join(os.path.dirname(__file__), 'data backup')
        if os.path.isdir(default_folder):
            self.load_data_threaded(default_folder)
        # attempt to auto-load ACTIVE model pointer for lifecycle automation
        try:
            active_ptr = os.path.join('ml','registry','ACTIVE.txt')
            if os.path.exists(active_ptr):
                with open(active_ptr,'r',encoding='utf-8') as f:
                    self._active_model_snapshot_dir = f.read().strip() or None
        except Exception:
            self._active_model_snapshot_dir = None
        # if active snapshot present and scan tab model differs, adjust UI (best-effort)
        try:
            if self._active_model_snapshot_dir and hasattr(self,'scan_tab') and hasattr(self.scan_tab,'model_combo'):
                # infer model type from metadata.json inside snapshot
                md = os.path.join(self._active_model_snapshot_dir,'metadata.json')
                if os.path.exists(md):
                    with open(md,'r',encoding='utf-8') as mf:
                        meta = json.load(mf)
                    mtype = meta.get('model_type','')
                    base_name = 'rf'
                    if 'xgb' in mtype: base_name='xgb'
                    elif 'lgbm' in mtype: base_name='lgbm'
                    # only override if user hasn't persisted a preference yet
                    if self.scan_tab.model_combo.currentText().lower() != base_name:
                        idx = self.scan_tab.model_combo.findText(base_name)
                        if idx >= 0:
                            self.scan_tab.model_combo.setCurrentIndex(idx)
        except Exception:
            pass
        # Set up periodic evaluation timer (live performance monitoring)
        try:
            self._eval_timer = QTimer(self)
            self._eval_timer.setInterval(60_000)  # 60s
            self._eval_timer.timeout.connect(self._run_live_evaluation_cycle)
            self._eval_timer.start()
        except Exception:
            pass
        # Set up optional periodic auto-scan timer based on automation config
        try:
            if self._automation_cfg.get('auto_scan_interval_minutes'):
                m = int(self._automation_cfg.get('auto_scan_interval_minutes') or 0)
                if m > 0:
                    self._auto_scan_timer = QTimer(self)
                    self._auto_scan_timer.setInterval(m * 60_000)
                    self._auto_scan_timer.timeout.connect(self._maybe_run_auto_scan)
                    self._auto_scan_timer.start()
        except Exception:
            pass
        # Post-start automation actions (train / scan / ensemble optimize)
        # Add flag to prevent multiple automation runs
        self._automation_started = False
        QTimer.singleShot(1500, self._post_start_automation)
        # initial cache stats update
        try:
            QTimer.singleShot(1200, self.update_cache_stats)
        except Exception:
            pass

    def update_cache_stats(self):
        """Update cache stats label from cache_manager (best effort)."""
        try:
            from cache.cache_manager import stats as cache_stats
            s = cache_stats()
            self.cache_label.setText(f"Cache: {s.get('files',0)} files / {s.get('rows',0)} rows / {len(s.get('symbols') or [])} symbols")
        except Exception:
            try:
                self.cache_label.setText('Cache: n/a')
            except Exception:
                pass

    def closeEvent(self, event):
        """Ensure background threads are stopped before window closes."""
        print("[CLEANUP] Starting cleanup process...")
        
        # Stop all workers using the comprehensive method
        try:
            self.stop_all_workers(timeout=3000)
        except Exception as e:
            print(f"[CLEANUP] stop_all_workers failed: {e}")
        
        # Stop scan worker if running
        try:
            if hasattr(self,'scan_tab') and hasattr(self.scan_tab,'cleanup'):
                self.scan_tab.cleanup()
        except Exception as e:
            print(f"[CLEANUP] scan_tab cleanup failed: {e}")
        
        # Stop loader thread with improved error handling
        try:
            if hasattr(self,'loader_worker') and self.loader_worker:
                try:
                    self.loader_worker.cancel()
                except Exception as e:
                    print(f"[CLEANUP] loader_worker cancel failed: {e}")
                    
            if hasattr(self,'loader_thread') and self.loader_thread:
                try:
                    if self.loader_thread.isRunning():
                        self.loader_thread.quit()
                        if not self.loader_thread.wait(3000):
                            print("[CLEANUP] Loader thread did not quit gracefully, terminating...")
                            self.loader_thread.terminate()
                            self.loader_thread.wait(1000)
                except Exception as e:
                    print(f"[CLEANUP] loader_thread cleanup failed: {e}")
        except Exception as e:
            print(f"[CLEANUP] General loader cleanup failed: {e}")
        
        print("[CLEANUP] Cleanup completed")
        try:
            super().closeEvent(event)
        except Exception as e:
            print(f"[CLEANUP] Super closeEvent failed: {e}")
            event.accept()

    def load_data_threaded(self, folder):
        import pandas as pd
        from PySide6.QtCore import QThread, Signal, QObject
        class LoaderWorker(QObject):
            progress = Signal(int)
            status = Signal(str)
            finished = Signal(dict, int)
            def __init__(self, folder):
                super().__init__()
                self.folder = folder
                self._cancel = False
            
            def cancel(self):
                try:
                    self._cancel = True
                except Exception:
                    pass
            def run(self):
                print("[LoaderWorker] run() started", flush=True)
                # Try using catalog/parquet fast-path if available to speed up loads
                try:
                    from data.data_utils import get_catalog, load_tickers_on_demand, maybe_adjust_with_adj, load_json, load_csv
                except Exception:
                    print("[LoaderWorker] primary import failed, falling back to smaller import set", flush=True)
                    # fallback to older imports
                    from data.data_utils import load_json, load_csv, maybe_adjust_with_adj

                # If a catalog exists in folder/_catalog, prefer it
                data_map = {}
                loaded = 0
                try:
                    catalog = None
                    try:
                        catalog = get_catalog(self.folder)
                        print(f"[LoaderWorker] get_catalog returned: {'None' if catalog is None else ('rows=' + str(len(catalog)))}", flush=True)
                    except Exception as e:
                        print(f"[LoaderWorker] get_catalog raised: {e}", flush=True)
                        catalog = None
                    if catalog is not None and not catalog.empty:
                        # Incremental load: iterate catalog rows and read parquet per-ticker so we can emit progress
                        rows = list(catalog.to_dict(orient='records'))
                        total = len(rows) or 1
                        self.status.emit(f"טוען קטלוג Parquet ({total} מניות) ...")
                        try:
                            for i, r in enumerate(rows):
                                if getattr(self, '_cancel', False):
                                    print("[LoaderWorker] cancel requested during catalog load", flush=True)
                                    break
                                t = r.get('ticker') or r.get('symbol')
                                pq = r.get('parquet_path') or r.get('parquet') or None
                                if not t:
                                    continue
                                if pq and os.path.exists(pq):
                                    try:
                                        # attempt columns-limited read first for speed
                                        try:
                                            df = pd.read_parquet(pq)
                                        except Exception:
                                            df = pd.read_parquet(pq)
                                        try:
                                            df = maybe_adjust_with_adj(df.copy(), use_adj=True)
                                        except Exception:
                                            pass
                                        data_map[t] = df
                                        loaded += 1
                                    except Exception as e:
                                        print(f"[LoaderWorker] failed to read parquet for {t}: {e}", flush=True)
                                # emit progress and status per 10 items (or last one)
                                if (i % 10) == 0 or i == (total - 1):
                                    pct = int((i+1) / total * 100)
                                    try:
                                        self.progress.emit(pct)
                                        self.status.emit(f"טוען {i+1}/{total} ({t})")
                                    except Exception:
                                        pass
                        except Exception as e:
                            print(f"[LoaderWorker] incremental catalog load failed: {e}", flush=True)
                            # fallback to bulk loader if available
                            try:
                                tickers = list(catalog['ticker'].dropna().unique())
                                loaded_map = load_tickers_on_demand(tickers, catalog_df=catalog)
                                for sym, df in loaded_map.items():
                                    try:
                                        df = maybe_adjust_with_adj(df.copy(), use_adj=True)
                                    except Exception:
                                        pass
                                    data_map[sym] = df
                                    loaded += 1
                            except Exception:
                                data_map = {}
                                loaded = 0

                    if loaded == 0:
                        print("[LoaderWorker] parquet fast-path did not load anything, scanning folder files", flush=True)
                        # Fallback: scan files as before
                        files = [f for f in os.listdir(self.folder) if f.endswith(('.json','.csv','.parquet'))]
                        total = len(files) or 1
                        for i, fname in enumerate(files):
                            if getattr(self, '_cancel', False):
                                print("[LoaderWorker] cancel requested, breaking file scan", flush=True)
                                break
                            fpath = os.path.join(self.folder, fname)
                            symbol = os.path.splitext(fname)[0]
                            try:
                                if fname.endswith('.parquet'):
                                    df = pd.read_parquet(fpath)
                                elif fname.lower().endswith('.json'):
                                    df = load_json(fpath)
                                elif fname.lower().endswith('.csv'):
                                    df = load_csv(fpath)
                                else:
                                    df = None
                                if df is not None:
                                    try:
                                        df = maybe_adjust_with_adj(df.copy(), use_adj=True)
                                    except Exception:
                                        pass
                                    data_map[symbol] = df
                                    loaded += 1
                            except Exception as e:
                                print(f"[LoaderWorker] failed loading file {fname}: {e}", flush=True)
                            self.progress.emit(int((i+1)/total*100))
                            self.status.emit(f"טוען {i+1}/{total} ({fname})")

                except Exception:
                    # Last-resort: print traceback and continue
                    import traceback
                    print("[LoaderWorker] exception in run():", flush=True)
                    traceback.print_exc()
                    print("[LoaderWorker] continuing to emit finished with whatever collected", flush=True)

                print(f"[LoaderWorker] emitting finished: loaded={loaded}", flush=True)
                self.finished.emit(data_map, loaded)

        self.loader_thread = QThread()
        self.loader_worker = LoaderWorker(folder)
        self.loader_worker.moveToThread(self.loader_thread)
        self.loader_thread.started.connect(self.loader_worker.run)
        self.loader_worker.progress.connect(self.progress_bar.setValue)
        # Direct status updates (log removed)
        self.loader_worker.status.connect(self.status_label.setText)
        def on_finished(data_map, loaded):
            self.data_map = data_map
            try:
                self._last_data_folder = folder
            except Exception:
                pass
            self.status_label.setText(f"נטענו אוטומטית {loaded} קבצים מתיקיית הנתונים הראשית")
            self.progress_bar.setValue(100)
            self._data_loading = False
            # if automation wanted to auto-train but data wasn't ready earlier, trigger now
            try:
                if getattr(self,'_automation_cfg',{}).get('auto_train_on_start') and not self._active_model_snapshot_dir:
                    # ensure automation currently enabled (check toggle override if exists)
                    if not hasattr(self.model_dashboard_tab, '_automation_enabled_override') or self.model_dashboard_tab._automation_enabled_override:
                        self._automation_log('Deferred auto-train after data load')
                        mdl = self._automation_cfg.get('default_train_model') or 'rf'
                        horizons = self._automation_cfg.get('default_train_horizons') or ''
                        self.on_train_ml({'ml_model': mdl, 'horizons': horizons, 'auto_rescan': False})
            except Exception:
                pass
            # no loading suffix to clean up (suffix mechanism removed)
        self.loader_worker.finished.connect(on_finished)
        # ensure the thread is stopped when worker finishes
        def on_loader_finished():
            try:
                # Use QTimer to defer the quit call to avoid waiting on self
                QTimer.singleShot(0, self.loader_thread.quit)
            except Exception:
                pass
        
        self.loader_worker.finished.connect(on_loader_finished)

        # start the loader thread so the background load actually runs
        try:
            self.loader_thread.start()
        except Exception as e:
            try:
                self.status_label.setText(f"Failed to start data loader thread: {e}")
            except Exception:
                pass

    def _on_build_catalog_clicked(self):
        # Ask user for folder to build catalog for (default to last used)
        folder = QFileDialog.getExistingDirectory(self, "Select data folder for catalog", os.path.join(os.path.dirname(__file__), 'data backup'))
        if not folder:
            return
        # Prevent overlapping build / force rebuild operations that cause heavy IO + crashes
        if getattr(self, '_catalog_building', False):
            try:
                QMessageBox.information(self, 'Busy', 'Catalog build already running')
            except Exception:
                pass
            return
        self._catalog_building = True
        # Disable button while running
        self.build_catalog_btn.setEnabled(False)
        # Start background thread to run build_or_refresh_catalog
        def _run_build():
            try:
                from ForReferenceOnly.data_setup import build_or_refresh_catalog
            except Exception as e:
                try:
                    self.status_label.setText(f"Cannot import catalog builder: {e}")
                except Exception:
                    pass
                self.build_catalog_btn.setEnabled(True)
                self._catalog_building = False
                return
            from PySide6.QtCore import QTimer
            def _safe(call):
                try:
                    QTimer.singleShot(0, call)
                except Exception:
                    # fallback: call directly (may still risk thread warning but better than silent fail)
                    try:
                        call()
                    except Exception:
                        pass
            def prog(done, total):
                pct = int(done/total*100) if total else 0
                def _u():
                    try:
                        self.progress_bar.setValue(pct)
                        self.status_label.setText(f"Building catalog: {done}/{total}")
                    except Exception:
                        pass
                _safe(_u)

            import traceback
            try:
                print('[BUILD] Starting catalog build for folder:', folder, flush=True)
                catalog_df = build_or_refresh_catalog(folder, show_progress=True, progress_cb=prog)
                print('[BUILD] Catalog build finished. Entries:', len(catalog_df) if catalog_df is not None else 'None', flush=True)
                # stash catalog in app state
                def _after_success():
                    try:
                        self.catalog_df = catalog_df
                        self.status_label.setText(f"Catalog built: {len(catalog_df)} entries")
                    except Exception:
                        pass
                    # Auto-load data into memory map for ML if not already loaded
                    try:
                        self.load_data_threaded(folder)
                    except Exception as e2:
                        print('[BUILD] Failed to trigger load_data_threaded:', e2, flush=True)
                _safe(_after_success)
            except Exception as e:
                traceback.print_exc()
                def _fail():
                    try:
                        self.status_label.setText(f"Catalog build failed: {e}")
                    except Exception:
                        pass
                print('[BUILD] ERROR:', e, flush=True)
                _safe(_fail)
            finally:
                def _cleanup():
                    try:
                        self.build_catalog_btn.setEnabled(True)
                        self.progress_bar.setValue(100)
                    except Exception:
                        pass
                    self._catalog_building = False
                _safe(_cleanup)

        t = threading.Thread(target=_run_build, daemon=True)
        t.start()

    def _on_force_rebuild_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select data folder for force rebuild", os.path.join(os.path.dirname(__file__), 'data backup'))
        if not folder:
            return
        if getattr(self, '_catalog_building', False):
            try:
                QMessageBox.information(self, 'Busy', 'Catalog build already running')
            except Exception:
                pass
            return
        reply = QMessageBox.question(self, 'Confirm', f"Force rebuild catalog & parquet for folder?\n{folder}\nThis may take time.", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._catalog_building = True
        self.force_rebuild_btn.setEnabled(False)
        self.status_label.setText('Force rebuilding (deleting existing catalog + rebuilding)...')
        def _do_force():
            try:
                # delete existing catalog artifacts & optional parquet temp indexes (not data itself)
                cat_parq = os.path.join(folder,'_catalog.parquet')
                cat_json = os.path.join(folder,'_catalog.json')
                for p in (cat_parq, cat_json):
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass
                    # Invalidate full cache as part of force rebuild
                    try:
                        from cache.cache_manager import invalidate
                        invalidate()
                    except Exception:
                        pass
                from ForReferenceOnly.data_setup import build_or_refresh_catalog
                from PySide6.QtCore import QTimer
                def _safe(call):
                    try:
                        QTimer.singleShot(0, call)
                    except Exception:
                        try:
                            call()
                        except Exception:
                            pass
                def prog(done, total):
                    pct = int(done/total*100) if total else 0
                    def _u():
                        try:
                            self.progress_bar.setValue(pct)
                            self.status_label.setText(f"Force rebuild: {done}/{total}")
                        except Exception:
                            pass
                    _safe(_u)
                import traceback
                try:
                    print('[FORCE] Starting force rebuild for folder:', folder, flush=True)
                    catalog_df = build_or_refresh_catalog(folder, show_progress=True, progress_cb=prog)
                    print('[FORCE] Force rebuild finished. Entries:', len(catalog_df) if catalog_df is not None else 'None', flush=True)
                    def _after_success():
                        try:
                            self.status_label.setText('Force rebuild complete')
                        except Exception:
                            pass
                        # auto-load
                        try:
                            self.catalog_df = catalog_df
                            self.load_data_threaded(folder)
                        except Exception as e2:
                            print('[FORCE] Failed to trigger load_data_threaded:', e2, flush=True)
                    _safe(_after_success)
                except Exception as e:
                    traceback.print_exc()
                    def _fail():
                        try:
                            self.status_label.setText(f"Force rebuild failed: {e}")
                        except Exception:
                            pass
                    _safe(_fail)
                try:
                    self.update_cache_stats()
                except Exception:
                    pass
            except Exception as e:
                def _fail_outer():
                    try:
                        self.status_label.setText(f"Force rebuild failed: {e}")
                    except Exception:
                        pass
                _safe(_fail_outer)
            finally:
                def _cleanup():
                    try:
                        self.force_rebuild_btn.setEnabled(True)
                        self.progress_bar.setValue(100)
                    except Exception:
                        pass
                    self._catalog_building = False
                _safe(_cleanup)
        threading.Thread(target=_do_force, daemon=True).start()

    def _on_verify_data_clicked(self):
        # Use the new processed data directory by default
        from data.data_paths import get_data_paths
        default_folder = get_data_paths()['processed']
        
        folder = QFileDialog.getExistingDirectory(self, "Select data folder to verify", default_folder)
        if not folder:
            return
            
        self.verify_data_btn.setEnabled(False)
        self.status_label.setText('Verifying ML/Backtest/Optimize/Scanner compatibility...')
        
        def _verify():
            try:
                # Use enhanced verification for new data structure  
                if os.path.exists(os.path.join(folder, '_parquet')) and os.path.exists(os.path.join(folder, '_catalog')):
                    from data.enhanced_verification import verify_processed_data_structure
                    report = verify_processed_data_structure(folder)
                    
                    # Extract summary for display
                    summary = report['summary']
                    recommendations = report.get('recommendations', [])
                    
                    if summary['verified_tickers'] == summary['total_tickers'] and summary['total_tickers'] > 0:
                        status_msg = f"✅ All {summary['total_tickers']} tickers verified - Ready for ML/Backtest!"
                    else:
                        failed = summary['failed_tickers']
                        warnings = summary['warning_tickers']
                        status_msg = f"⚠️ Verified: {summary['verified_tickers']}/{summary['total_tickers']} ({failed} failed, {warnings} warnings)"
                    
                else:
                    # Fallback to old verification for legacy data
                    from data.data_verification import verify_data_consistency, write_verification_log  
                    report = verify_data_consistency(folder)
                    write_verification_log(report)
                    
                    ok_count = len(report.get('ok_tickers', []))
                    total_count = len(report.get('tickers', []))
                    status_msg = f"Legacy verification: {ok_count}/{total_count} tickers OK"
                
                self.status_label.setText(status_msg)
                
                # Save verification report
                from datetime import datetime
                report_filename = f"verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                report_path = os.path.join(folder, report_filename)
                with open(report_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(report, f, indent=2, default=str)
                
                try:
                    self.update_cache_stats()
                except Exception:
                    pass
                    
            except Exception as e:
                try:
                    self.status_label.setText(f"Verification failed: {e}")
                except Exception:
                    pass
            finally:
                try:
                    self.verify_data_btn.setEnabled(True)
                except Exception:
                    pass
        threading.Thread(target=_verify, daemon=True).start()

    def _on_normalize_json_clicked(self):
        """Convert raw JSON files (yahoo.daily) into a stable Parquet layer for ML.

        Creates/updates <folder>/_mlready/*.parquet and a summary file. Then optionally
        reloads those parquet files into data_map.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select raw JSON folder", os.path.join(os.path.dirname(__file__), 'data backup'))
        if not folder:
            return
        self.normalize_btn.setEnabled(False)
        self.status_label.setText('Normalizing JSON → Parquet ...')
        def _do_norm():
            try:
                from data.data_normalizer import normalize_price_json_folder
                summary = normalize_price_json_folder(folder)
                # After success, optionally load parquet layer directly
                out_dir = os.path.join(folder, '_mlready')
                loaded = 0
                if os.path.isdir(out_dir):
                    new_map = {}
                    import pandas as _pd
                    for f in os.listdir(out_dir):
                        if f.lower().endswith('.parquet'):
                            sym = os.path.splitext(f)[0]
                            try:
                                df = _pd.read_parquet(os.path.join(out_dir, f))
                                # Try set Date index if present
                                if 'Date' in df.columns:
                                    try:
                                        df['Date'] = _pd.to_datetime(df['Date'], errors='coerce', utc=True)
                                        df = df.dropna(subset=['Date']).set_index('Date')
                                    except Exception:
                                        pass
                                new_map[sym] = df
                                loaded += 1
                            except Exception:
                                continue
                    if loaded:
                        self.data_map = new_map
                self.status_label.setText(f"Normalize: wrote={summary.get('written')} skipped_existing={summary.get('skipped_existing')} small={summary.get('skipped_small')} err={len(summary.get('errors') or [])}")
            except Exception as e:
                try:
                    self.status_label.setText(f"Normalize failed: {e}")
                except Exception:
                    pass
            finally:
                try:
                    self.normalize_btn.setEnabled(True)
                except Exception:
                    pass
        threading.Thread(target=_do_norm, daemon=True).start()

    def clear_cache(self):
        """Explicit user-invoked full cache clear (optional future wiring)."""
        try:
            from cache.cache_manager import invalidate
            invalidate()
            self.status_label.setText('Cache cleared')
            self.update_cache_stats()
        except Exception as e:
            try:
                self.status_label.setText(f'Cache clear failed: {e}')
            except Exception:
                pass

    def _handle_training_progress(self, ev: dict):
        try:
            phase = ev.get('phase')
            # ensure monotonic progress bar (never decrease)
            if not hasattr(self, '_last_progress_pct'):
                self._last_progress_pct = 0
            def _set_progress(p):
                try:
                    if p > self._last_progress_pct:
                        self.progress_bar.setValue(p)
                        self._last_progress_pct = p
                except Exception:
                    pass
            if phase == 'collect_start':
                tot = ev.get('total')
                self.status_label.setText(f"מתחיל איסוף פיצ'רים ({tot} סימבולים)...")
                _set_progress(2)
            elif phase == 'collect':
                i = ev.get('i'); total = ev.get('total'); kept = ev.get('kept'); eta = ev.get('eta')
                pct = int((i/total)*50) if total else 0
                msg = f"איסוף פיצ'רים {i}/{total} (נשמרו {kept})"
                if eta:
                    try:
                        msg += f" ETA~{int(eta)}s"
                    except Exception:
                        pass
                self.status_label.setText(msg)
                _set_progress(pct)
            elif phase == 'collect_done':
                rows = ev.get('rows')
                self.status_label.setText(f"איסוף הושלם, {rows} שורות")
                _set_progress(55)
            elif phase == 'dataset_validation_start':
                ctx = ev.get('context'); rows = ev.get('rows')
                self.status_label.setText(f"בודק תקינות נתונים ({ctx}) rows={rows}")
                # stay within current progress band
            elif phase == 'dataset_validation_result':
                ctx = ev.get('context'); status = ev.get('status'); rows = ev.get('rows'); feats = ev.get('feature_count')
                pr = ev.get('positive_rate'); miss = ev.get('missing_ratio')
                base = f"ולידציית נתונים {ctx}: status={status} rows={rows} feats={feats}"
                if isinstance(pr,(int,float)):
                    base += f" pos={pr:.2%}"
                if isinstance(miss,(int,float)):
                    base += f" miss={miss:.2%}"
                self.status_label.setText(base)
            elif phase == 'train_start':
                rows = ev.get('rows')
                self.status_label.setText(f"מאמן מודל על {rows} שורות...")
                _set_progress(60)
            elif phase == 'rf_progress':
                done = ev.get('done'); total_trees = ev.get('total'); eta = ev.get('eta')
                msg = f"אימון RandomForest {done}/{total_trees} עצים"
                if eta:
                    try:
                        msg += f" ETA~{int(eta)}s"
                    except Exception:
                        pass
                self.status_label.setText(msg)
                # If inside historical horizon slice, scale progress within that slice (40..85 allocated to horizons)
                if hasattr(self, '_hist_current') and self._hist_current:
                    try:
                        idx = self._hist_current.get('idx',1); total_h = self._hist_current.get('total',1)
                        slice_span = 45 / max(total_h,1)  # total horizon span (40..85)
                        inner = (done/total_trees) if total_trees else 0
                        pct_start = 40 + (idx-1)*slice_span
                        pct_end = 40 + idx*slice_span
                        pct = int(pct_start + inner * (pct_end - pct_start))
                        _set_progress(min(pct,85))
                    except Exception:
                        base_pct = 60; span = 30
                        pct = base_pct + int((done/total_trees)*span) if total_trees else base_pct
                        _set_progress(pct)
                else:
                    base_pct = 60; span = 30
                    pct = base_pct + int((done/total_trees)*span) if total_trees else base_pct
                    _set_progress(pct)
            elif phase == 'xgb_train_start':
                self.status_label.setText('מאמן XGBoost (400 סבבים)...')
                self.progress_bar.setValue(60)
            elif phase == 'saved':
                self.progress_bar.setValue(90)
            elif phase == 'cv_progress':
                fold = ev.get('fold'); folds = ev.get('folds');
                # map folds (1..F) into 90..99
                try:
                    pct = 90 + int((fold / max(folds,1)) * 9)
                except Exception:
                    pct = 92
                self.status_label.setText(f"ולידציה צולבת (Fold {fold}/{folds})...")
                self.progress_bar.setValue(min(pct,99))
            elif phase == 'historical_start':
                tot = ev.get('total_horizons', 0)
                self.status_label.setText(f"מתחיל אימון היסטורי ({tot} אופקים)...")
                _set_progress(5)
            elif phase == 'filtered_symbols':
                syms = ev.get('symbols'); hz = ev.get('horizon')
                self.status_label.setText(f"סינון נתונים (אופק {hz}) - {syms} סמלים נשמרו")
                _set_progress(15)
            elif phase == 'building_labels':
                hz = ev.get('horizon'); syms = ev.get('symbols', '')
                self.status_label.setText(f"בונה labels (אופק {hz}) מתוך {syms} סמלים...")
                _set_progress(25)
            elif phase == 'build_labels_tick':
                i = ev.get('i',0); total = ev.get('total',1)
                # Map ticks into 10..25% (only if we haven't passed 25 yet)
                if self._last_progress_pct < 25:
                    try:
                        pct = 10 + int((i / max(total,1)) * 15)
                    except Exception:
                        pct = 12
                    self.status_label.setText(f"בונה labels... {i}/{total}")
                    _set_progress(min(pct,25))
            elif phase == 'build_labels_complete':
                rows = ev.get('total_rows'); pr = ev.get('positive_rate')
                try:
                    self.status_label.setText(f"labels מוכנים: {rows} שורות (חיובי={pr:.2%})")
                except Exception:
                    self.status_label.setText(f"labels מוכנים: {rows} שורות")
                _set_progress(40)
            elif phase == 'training_model':
                algo = ev.get('algorithm'); ds = ev.get('dataset_size'); hz = ev.get('horizon')
                self.status_label.setText(f"מאמן {algo} (אופק {hz}) על {ds} דגימות...")
                _set_progress(55)
            elif phase == 'historical_horizon_start':
                horizon = ev.get('horizon'); idx = ev.get('index',1); total = ev.get('total',1)
                try:
                    slice_span = 45 / max(total,1)
                    pct = 40 + int((idx-1)*slice_span)
                except Exception:
                    pct = 40
                self.status_label.setText(f"אימון היסטורי - התחלת אופק {horizon} ימים ({idx}/{total})")
                # Avoid premature jump to 40% if still in earlier label-building phases (<30%)
                try:
                    if self._last_progress_pct < 30:
                        pct = self._last_progress_pct  # defer bump; real bump will occur at build_labels_complete (40%)
                except Exception:
                    pass
                _set_progress(min(int(pct),85))
                try:
                    self._hist_current = {'idx': idx, 'total': total}
                except Exception:
                    pass
            elif phase == 'historical_horizon_done':
                horizon = ev.get('horizon'); idx = ev.get('index',1); total = ev.get('total',1)
                try:
                    slice_span = 45 / max(total,1)
                    pct = 40 + int(idx*slice_span)
                except Exception:
                    pct = 60
                self.status_label.setText(f"אימון היסטורי - הסתיים אופק {horizon} ({idx}/{total})")
                _set_progress(min(pct,85))
                try:
                    # clear current context after finishing horizon so next start resets
                    self._hist_current = None
                except Exception:
                    pass
            elif phase == 'multi_horizon_complete':
                hz = ev.get('horizon'); idx = ev.get('index',1); total = ev.get('total',1)
                samples = ev.get('samples'); auc = ev.get('auc')
                # allocate 60..85 for multi-horizon (non-historical) per horizon progression if not historical context
                if not (hasattr(self,'_hist_current') and self._hist_current):
                    try:
                        slice_span = 25 / max(total,1)  # 60..85 span
                        pct = 60 + int(idx * slice_span)
                    except Exception:
                        pct = 70
                    _set_progress(min(pct,85))
                txt = f"אופק {hz} הושלם ({idx}/{total})"
                if isinstance(samples,int):
                    txt += f" | samples={samples}"
                if isinstance(auc,(int,float)):
                    txt += f" | AUC={auc:.3f}"
                self.status_label.setText(txt)
            elif phase == 'historical_done':
                succ = ev.get('success', 0); tot = ev.get('total', 0)
                self.status_label.setText(f"אימון היסטורי הסתיים {succ}/{tot} הצליחו. יוצר Snapshot...")
                _set_progress(90)
            elif phase == 'done':
                self.progress_bar.setValue(100)
                # If meta summary not already placed by training completion, show concise snapshot hint
                try:
                    snap = ev.get('snapshot') or None
                    if snap:
                        base = self.status_label.text()
                        if 'ACTIVE' not in base and 'Snapshot' not in base:
                            self.status_label.setText(base + f" | Snapshot: {os.path.basename(snap)}")
                except Exception:
                    pass
            elif phase == 'snapshot_start':
                try:
                    self.status_label.setText('יוצר Snapshot למודל...')
                    if getattr(self,'model_dashboard_tab',None):
                        self.model_dashboard_tab.info_lbl.setText('Creating model snapshot...')
                except Exception:
                    pass
            elif phase == 'snapshot_done':
                try:
                    snap = ev.get('snapshot')
                    if snap:
                        name = os.path.basename(snap)
                        self.status_label.setText(f"Snapshot נוצר: {name}")
                        if getattr(self,'model_dashboard_tab',None):
                            self.model_dashboard_tab.info_lbl.setText(f'Snapshot ready: {name}')
                        # advance a bit if still below 95
                        _set_progress(95)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_daily_update_clicked(self):
        # Run daily update silently using the canonical data folder.
        # Use two-step merge (write CSV then merge) and enable APIs by default.
        default_folder = os.path.join(os.path.dirname(__file__), 'data backup')
        folder = default_folder if os.path.isdir(default_folder) else QFileDialog.getExistingDirectory(self, "Select data folder to update", default_folder)
        if not folder:
            return

        # disable button while running
        try:
            self.daily_update_btn.setEnabled(False)
        except Exception:
            pass

        # automatic settings: run as one-step background process (two-step merge + API fallback)
        merge_mode = 'two-step'
        use_apis = True

        try:
            # create thread and worker
            from PySide6.QtCore import QThread
            from data.daily_update_worker_new import DailyUpdateWorkerNew
        except Exception as e:
            self.status_label.setText(f"Daily update error importing worker: {e}")
            try:
                self.daily_update_btn.setEnabled(True)
            except Exception:
                pass
            return

        self._daily_thread = QThread()
        self._daily_worker = DailyUpdateWorkerNew()
        self._daily_worker.moveToThread(self._daily_thread)

        # wire signals with button text updates
        def _on_progress_update(p):
            try:
                self.progress_bar.setValue(p)
                # Update button text to show progress
                if 0 < p < 100:
                    self.daily_update_btn.setText(f"Daily Update ({p}%)")
                elif p == 100:
                    self.daily_update_btn.setText("Daily Update")
            except Exception:
                pass
        
        self._daily_worker.progress.connect(_on_progress_update)
        self._daily_worker.status.connect(lambda s: self.status_label.setText(s))
        
        def _on_ticker_done(ticker, success, meta):
            # brief toast/update could be implemented; append to logs area if present
            try:
                if success:
                    self.status_label.setText(f"✓ Updated {ticker}")
                else:
                    self.status_label.setText(f"⚠ No update for {ticker}")
            except Exception:
                pass
        self._daily_worker.ticker_done.connect(_on_ticker_done)

        def _on_finished(summary):
            try:
                self.status_label.setText(f"✅ Daily update complete: {summary.get('done',0)}/{summary.get('total',0)} processed, {summary.get('successes',0)} successful")
            except Exception:
                pass
            try:
                # Reset button text and enable
                self.daily_update_btn.setText("Daily Update")
                self.daily_update_btn.setEnabled(True)
            except Exception:
                pass
            # remove stop button if present
            try:
                if hasattr(self, '_stop_daily_btn') and self._stop_daily_btn is not None:
                    self._stop_daily_btn.setParent(None)
                    self._stop_daily_btn = None
            except Exception:
                pass
            # cleanup thread
            try:
                self._daily_thread.quit()
                self._daily_thread.wait(1000)
            except Exception:
                pass

        # Insert/replace a Stop button in bottom bar
        try:
            if hasattr(self, '_stop_daily_btn') and self._stop_daily_btn is not None:
                try:
                    self._stop_daily_btn.setParent(None)
                except Exception:
                    pass
            self._stop_daily_btn = QPushButton('🛑 Stop')
            self._stop_daily_btn.setObjectName('stop_button')  # Special red styling
            self._stop_daily_btn.setToolTip('עצור עדכון יומי פעיל')
            def _cancel_daily():
                try:
                    if hasattr(self, '_daily_worker') and hasattr(self._daily_worker, 'cancel'):
                        self._daily_worker.cancel()
                    self.status_label.setText('ביטול תהליך עדכון יומי...')
                except Exception:
                    pass
            self._stop_daily_btn.clicked.connect(_cancel_daily)
            # insert before spacer (so it sits with other action buttons)
            try:
                if hasattr(self, 'bottom_layout') and hasattr(self, '_bottom_spacer'):
                    idx = self.bottom_layout.indexOf(self._bottom_spacer)
                    if idx >= 0:
                        self.bottom_layout.insertWidget(idx, self._stop_daily_btn)
                    else:
                        self.bottom_layout.addWidget(self._stop_daily_btn)
                else:
                    self.layout().addWidget(self._stop_daily_btn)
            except Exception:
                self.layout().addWidget(self._stop_daily_btn)
        except Exception:
            pass

        def _on_error(msg):
            try:
                self.status_label.setText(f"❌ Daily update error: {msg}")
            except Exception:
                pass
            try:
                # Reset button text and enable
                self.daily_update_btn.setText("Daily Update")
                self.daily_update_btn.setEnabled(True)
            except Exception:
                pass
            try:
                self._daily_thread.quit()
            except Exception:
                pass

        self._daily_worker.progress.connect(lambda p: None)
        self._daily_worker.finished.connect(_on_finished)
        self._daily_worker.error.connect(_on_error)
        # start worker when thread starts
        self._daily_thread.started.connect(self._daily_worker.run)
        # ensure cleanup when thread finishes
        self._daily_worker.finished.connect(self._daily_thread.quit)

        # start the thread quietly (single call)
        try:
            self._daily_thread.start()
        except Exception as e:
            try:
                self.status_label.setText(f"Failed to start daily update thread: {e}")
            except Exception:
                pass
            try:
                self.daily_update_btn.setEnabled(True)
            except Exception:
                pass
    def load_parquet_folder(self, folder_path):
        """Load all Parquet files from a folder into self.data_map"""
        import pandas as pd
        loaded = 0
        for fname in os.listdir(folder_path):
            if fname.endswith('.parquet'):
                symbol = os.path.splitext(fname)[0]
                fpath = os.path.join(folder_path, fname)
                try:
                    df = pd.read_parquet(fpath)
                    self.data_map[symbol] = df
                    loaded += 1
                except Exception as e:
                    print(f"Error loading {fname}: {e}")
        return loaded
        
    def setup_ui(self):
        # Setup UI (status log removed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        # remove any default contents margins on the tab widget and its tab bar
        try:
            self.tab_widget.setContentsMargins(0, 0, 0, 0)
            tb = self.tab_widget.tabBar()
            tb.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        # connect to an internal handler so we can forward both index and tab text
        self.tab_widget.currentChanged.connect(self._on_tab_widget_changed)

        # Always use unified ScanTab from ui.tabs.scan_tab (legacy ui.main_content.scan_tab removed)
        self.scan_tab = NewScanTab()
        try:
            # update shared params when scan tab settings change
            self.scan_tab.settings_changed.connect(lambda vals: setattr(self, 'current_params', vals))
        except Exception:
            pass
        # Use unified BacktestTab from ui.tabs.backtest_tab (legacy duplicate removed)
        self.backtest_tab = BacktestTab()
        self.optimize_tab = OptimizeTab()
        # Walk-Forward tab
        try:
            from ui.tabs.walkforward_tab import WalkForwardTab
            self.walkforward_tab = WalkForwardTab()
        except Exception:
            self.walkforward_tab = None
        self.ibkr_tab = IBKRTab()
        self.model_dashboard_tab = ModelDashboardTab()
        try:
            from ui.main_content.auto_discovery_tab import AutoDiscoveryTab
        except Exception:
            from .auto_discovery_tab import AutoDiscoveryTab
        self.auto_discovery_tab = AutoDiscoveryTab()

        # Reordered tabs for logical workflow: Models -> WatchList -> Scan -> Optimize -> Backtest -> Walk-Forward -> IBKR -> Discover
        self.tab_widget.addTab(self.model_dashboard_tab, "🗂️ Models")
        self.watchlist_tab = WatchListTab()
        self.tab_widget.addTab(self.watchlist_tab, "👁️ WatchList")
        self.tab_widget.addTab(self.scan_tab, "🔍 Scan")
        self.tab_widget.addTab(self.optimize_tab, "🧪 Opt")
        self.tab_widget.addTab(self.backtest_tab, "📈 Backtest")
        if self.walkforward_tab:
            self.tab_widget.addTab(self.walkforward_tab, "🚶 WF")
        self.tab_widget.addTab(self.ibkr_tab, "🤖 IBKR")
        self.tab_widget.addTab(self.auto_discovery_tab, "⚡ Discover")
        # Run repository tab
        try:
            self.run_repo_tab = RunRepoTab()
            self.run_repo_tab.load_run_requested.connect(self.on_load_run_from_repo)
            self.tab_widget.addTab(self.run_repo_tab, "📁 Runs")
        except Exception:
            self.run_repo_tab = None

        layout.addWidget(self.tab_widget)
        # (status_log removed per user request)
        # Add ensemble optimize button onto model dashboard (lightweight integration)
        try:
            if hasattr(self.model_dashboard_tab, 'layout'):
                btn = QPushButton('Optimize Ensemble / Meta')
                btn.setObjectName('secondary_button')
                btn.clicked.connect(self.optimize_ensemble)
                self.model_dashboard_tab.layout().addWidget(btn)
                self._ensemble_btn = btn
        except Exception:
            pass
        
        # Connect signals
        self.scan_tab.run_scan_requested.connect(self.on_run_scan)
        try:
            self.scan_tab.train_ml_requested.connect(self.on_train_ml)
        except Exception:
            pass
        # training from Models tab (new controls)
        try:
            self.model_dashboard_tab.train_ml_requested.connect(self.on_train_ml)
        except Exception:
            pass
        # iterative training from Models tab
        try:
            self.model_dashboard_tab.iterative_training_requested.connect(self.on_iterative_training_requested)
        except Exception:
            pass
        try:
            self.scan_tab.calibrate_requested.connect(self.on_calibrate_ml)
        except Exception:
            pass
        # walk-forward signal
        try:
            if self.walkforward_tab:
                self.walkforward_tab.run_walkforward_requested.connect(self.on_run_walkforward)
        except Exception:
            pass
        self.backtest_tab.run_backtest_requested.connect(self.on_run_backtest)
        self.optimize_tab.run_optimize_requested.connect(self.on_run_optimize)
        try:
            self.optimize_tab.apply_params_requested.connect(self.on_apply_optimized_params)
        except Exception:
            pass
        # connect auto-discovery
        self.auto_discovery_tab.run_auto_requested.connect(self.on_run_auto_discovery)
        # populate auto-discovery selectors with current data/strategies if available
        try:
            # symbol list from loaded data
            syms = list(self.data_map.keys()) if getattr(self, 'data_map', None) else []
            if syms:
                self.auto_discovery_tab.set_symbols(syms)
        except Exception:
            pass
        try:
            # default strategy list (must mirror worker defaults)
            default_strats = ["SMA Cross","EMA Cross","MACD","RSI","Stochastic","Bollinger Breakout","Bollinger MeanRevert","Donchian Breakout"]
            self.auto_discovery_tab.set_strategies(default_strats)
        except Exception:
            pass

        # After adding tabs, wire watchlist -> scan quick symbols
        try:
            if hasattr(self, 'watchlist_tab') and hasattr(self, 'scan_tab'):
                def _on_watchlist_changed(syms):
                    try:
                        # Update quick symbols line edit and persist to dialog symbols field
                        csv_line = ','.join(syms[:500])  # safety cap
                        if hasattr(self.scan_tab, 'quick_symbols_edit'):
                            self.scan_tab.quick_symbols_edit.setText(csv_line)
                            self.scan_tab._apply_quick_filters()
                        # Also surface status to bottom bar
                        self.status_label.setText(f'WatchList → {len(syms)} symbols loaded')
                    except Exception:
                        pass
                self.watchlist_tab.watchlist_changed.connect(_on_watchlist_changed)
                # Fire once with current symbols
                try:
                    _on_watchlist_changed(self.watchlist_tab.get_symbols())
                except Exception:
                    pass
        except Exception:
            pass

    def on_run_auto_discovery(self, params):
        """Handle Auto-Discovery runs from the UI tab.
        This forwards work to a WorkerThread that implements the
        multi-strategy grid search. The worker is stored on the
        MainContent instance to ensure it isn't garbage-collected
        while running.
        """
        # merge sidebar params (self.current_params) with tab params to form combined params
        combined_params = {**getattr(self, 'current_params', {}), **(params or {})}
        try:
            from ui.main_content.worker_thread import WorkerThread
        except Exception:
            from .worker_thread import WorkerThread

        data_map = getattr(self, 'data_map', {})

        # create and attach worker (do not set parent) to avoid QObject parent-child
        # deletion while thread is still running which can trigger the QThread destroyed error
        self.auto_discovery_worker = WorkerThread('auto_discovery', combined_params, data_map)
        wt = self.auto_discovery_worker

        # wire basic signals to tab
        wt.progress_updated.connect(self.auto_discovery_tab.update_progress)
        wt.results_ready.connect(self.auto_discovery_tab.update_results)

        # show status updates in the Auto-Discovery tab (best-effort)
        try:
            wt.status_updated.connect(self.auto_discovery_tab.set_status)
        except Exception:
            try:
                wt.status_updated.connect(lambda s: None)
            except Exception:
                pass

        wt.error_occurred.connect(lambda e: QMessageBox.critical(self, 'שגיאה', str(e)))
        wt.finished_work.connect(lambda: self.auto_discovery_tab.show_progress(False))

        # clear stored reference and schedule deletion after finished
        try:
            wt.finished.connect(lambda: setattr(self, 'auto_discovery_worker', None))
            try:
                wt.finished.connect(wt.deleteLater)
            except Exception:
                pass
        except Exception:
            pass

        self.auto_discovery_tab.show_progress(True)
        wt.start()

    def _on_tab_widget_changed(self, index: int):
        """Forward the tab change with both index and tab text so other
        components (sidebar) can react based on the tab name.
        """
        try:
            try:
                tab_text = self.tab_widget.tabText(index)
            except Exception:
                tab_text = None
            # emit a signal with index and name; slot may accept one or two args
            try:
                self.tab_changed.emit(index)
            except Exception:
                pass
            # also attempt to call connected slots with both arguments if they accept it
            try:
                # direct call to connected Qt slots is handled by Qt; use emit with two args
                self.tab_changed.emit(index)
            except Exception:
                pass
            # For backward compatibility, call any Python slots directly if needed
            # (the main window already connected tab_changed to sidebar.on_tab_changed which now accepts (index, name))
            try:
                # Create a generic Qt signal dispatch: get connected slots and call them if they accept two args
                # This is best-effort and intentionally conservative.
                # Note: Qt handles signal delivery; the above emit(index) will notify.
                pass
            except Exception:
                pass
            # If Backtest tab activated, push shared params into it if available
            try:
                tab_text = self.tab_widget.tabText(index)
                if tab_text and 'Backtest' in tab_text:
                    try:
                        if hasattr(self, 'backtest_tab') and hasattr(self.backtest_tab, 'apply_shared_params'):
                            try:
                                params = getattr(self, 'current_params', None) or {}
                                if params:
                                    self.backtest_tab.apply_shared_params(params)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass
        
    def apply_styles(self):
        StyleManager.apply_main_content_style(self)

    def closeEvent(self, event):
        """Ensure background threads are cancelled and waited on when the main content is closed."""
        # iterate known attributes and try to stop any QThread-like objects
        for val in list(self.__dict__.values()):
            try:
                if hasattr(val, 'isRunning') and callable(getattr(val, 'isRunning')):
                    try:
                        if hasattr(val, 'cancel') and callable(getattr(val, 'cancel')):
                            val.cancel()
                    except Exception:
                        pass
                    try:
                        val.quit()
                    except Exception:
                        pass
                    try:
                        val.wait(2000)
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            event.accept()
        except Exception:
            pass

    def __del__(self):
        # Best-effort: ensure any running worker threads are requested to stop
        try:
            try:
                self.stop_all_workers(timeout=5000)
            except Exception:
                pass
        except Exception:
            pass

    def stop_all_workers(self, timeout=2000):
        """Best-effort stop all known worker threads attached to this MainContent.
        This method is safe to call multiple times and will attempt to cancel/quit
        and wait for threads to finish.
        """
        # Special handling for loader worker
        try:
            if hasattr(self, 'loader_worker') and self.loader_worker:
                self.loader_worker.cancel()
            if hasattr(self, 'loader_thread') and self.loader_thread:
                self.loader_thread.quit()
                self.loader_thread.wait(min(timeout, 3000))
        except Exception:
            pass
            
        for name, val in list(self.__dict__.items()):
            try:
                if hasattr(val, 'isRunning') and callable(getattr(val, 'isRunning')):
                    try:
                        if hasattr(val, 'cancel') and callable(getattr(val, 'cancel')):
                            try:
                                val.cancel()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        val.quit()
                    except Exception:
                        pass
                    try:
                        val.wait(timeout)
                    except Exception:
                        pass
                    # if still running after wait, attempt a forceful termination as last resort
                    try:
                        if hasattr(val, 'isRunning') and val.isRunning():
                            if hasattr(val, 'terminate') and callable(getattr(val, 'terminate')):
                                try:
                                    val.terminate()
                                except Exception:
                                    pass
                                try:
                                    val.wait(1000)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass
        
    def on_load_data(self, params):
        """Handle data loading from sidebar"""
        try:
            source_type = params.get('source_type', 'folder')
            path = params.get('path', '')
            use_adj = params.get('use_adj', True)
            start_date = params.get('start_date', '')
            
            if not path:
                QMessageBox.warning(self, "אזהרה", "נא לבחור נתיב קבצים")
                return
                
            self.data_map = {}
            
            if source_type == 'folder':
                # use data utilities to robustly parse CSV/JSON files
                try:
                    from data.data_utils import load_csv, load_json, maybe_adjust_with_adj
                except Exception:
                    load_csv = load_json = maybe_adjust_with_adj = None
                self.data_map = {}
                loaded = 0
                for fname in os.listdir(path):
                    fpath = os.path.join(path, fname)
                    symbol = os.path.splitext(fname)[0]
                    try:
                        if fname.endswith('.parquet'):
                            import pandas as _pd
                            df = _pd.read_parquet(fpath)
                        elif fname.endswith('.json') and load_json:
                            df = load_json(fpath)
                        elif fname.endswith('.csv') and load_csv:
                            df = load_csv(fpath)
                        else:
                            # fallback: try to read with pandas
                            import pandas as _pd
                            try:
                                df = _pd.read_csv(fpath)
                            except Exception:
                                df = None
                        if df is not None:
                            # optionally adjust with adj close
                            if maybe_adjust_with_adj is not None:
                                df = maybe_adjust_with_adj(df, use_adj)
                            self.data_map[symbol] = df
                            loaded += 1
                    except Exception:
                        continue
                if hasattr(self, 'status_label'):
                    self.status_label.setText(f"נטענו {loaded} קבצים מהתיקייה שנבחרה")
                QMessageBox.information(self, "הצלחה", f"נטענו {loaded} קבצים מהתיקייה")
                # populate auto-discovery symbols and strategies after loading
                try:
                    syms = list(self.data_map.keys()) if getattr(self, 'data_map', None) else []
                    if hasattr(self, 'auto_discovery_tab') and syms:
                        self.auto_discovery_tab.set_symbols(syms)
                except Exception:
                    pass
            else:
                QMessageBox.information(self, "מידע", "טעינת קבצים בודדים עדיין לא מיושמת")
                
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת נתונים: {str(e)}")
            
    def load_from_folder(self, folder_path, use_adj, start_date):
        """Load data from folder"""
        import pandas as pd
        loaded = 0
        if not os.path.isdir(folder_path):
            QMessageBox.warning(self, "אזהרה", "התיקייה לא קיימת")
            return
        for fname in os.listdir(folder_path):
            fpath = os.path.join(folder_path, fname)
            symbol = os.path.splitext(fname)[0]
            try:
                if fname.endswith('.parquet'):
                    df = pd.read_parquet(fpath)
                    self.data_map[symbol] = df
                    loaded += 1
                elif fname.endswith('.json'):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        raw = json.load(f)
                        # Try to extract price.yahoo.daily, fallback to price.daily or whole file
                        daily_list = None
                        if 'price' in raw:
                            if 'yahoo' in raw['price'] and 'daily' in raw['price']['yahoo']:
                                daily_list = raw['price']['yahoo']['daily']
                            elif 'daily' in raw['price']:
                                daily_list = raw['price']['daily']
                        if daily_list is not None:
                            df = pd.DataFrame(daily_list)
                            self.data_map[symbol] = df
                        else:
                            # Fallback: store the whole JSON as a single-row DataFrame
                            self.data_map[symbol] = pd.DataFrame([raw])
                        loaded += 1
                elif fname.endswith('.csv'):
                    df = pd.read_csv(fpath)
                    self.data_map[symbol] = df
                    loaded += 1
            except Exception as e:
                print(f"Error loading {fname}: {e}")
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"נטענו {loaded} קבצים מהתיקייה שנבחרה")
        QMessageBox.information(self, "הצלחה", f"נטענו {loaded} קבצים מהתיקייה")
        
    def on_parameters_changed(self, params):
        """Handle parameter changes from sidebar"""
        # Always keep latest sidebar parameters (including strategies)
        self.current_params = params
        
    def on_run_scan(self, scan_params):
        """Handle scan request"""
        # If no data loaded yet attempt a quick load from default folder's _parquet (fast path)
        if not self.data_map:
            try:
                default_folder = os.path.join(os.path.dirname(__file__), 'data backup')
                pq_dir = os.path.join(default_folder, '_parquet')
                if os.path.isdir(pq_dir):
                    import pandas as _pd
                    loaded = 0
                    for fname in os.listdir(pq_dir):
                        if fname.lower().endswith('.parquet'):
                            sym = os.path.splitext(fname)[0]
                            fpath = os.path.join(pq_dir, fname)
                            try:
                                df = _pd.read_parquet(fpath)
                                if 'Close' not in df.columns:
                                    for cand in df.columns:
                                        if 'close' in str(cand).lower():
                                            df['Close'] = df[cand]; break
                                self.data_map[sym] = df; loaded += 1
                            except Exception:
                                pass
                    if hasattr(self, 'status_label'):
                        self.status_label.setText(f"Loaded {loaded} parquet symbols for quick scan")
            except Exception:
                pass
        if not self.data_map:
            QMessageBox.warning(self, "אין נתונים", "לא נטענו נתונים לסריקה עדיין")
            return
        combined_params = {**self.current_params, **scan_params}
        try:
            if self._active_model_snapshot_dir:
                pass
        except Exception:
            pass
        # Wrap status update hook to parse drift average lines from worker
        try:
            orig_slot = self.scan_tab.update_status
            def wrapped_status(msg:str):
                try:
                    if isinstance(msg,str) and msg.startswith('DriftAvg='):
                        val = float(msg.split('=',1)[1])
                        self._drift_history.append(val)
                        if len(self._drift_history) > 30:
                            self._drift_history = self._drift_history[-30:]
                        # --- Configurable drift thresholds ---
                        cfg = getattr(self,'_automation_cfg',{}) or {}
                        high_thr = float(cfg.get('drift_high_threshold') or 1.25)
                        sustain_n = int(cfg.get('drift_sustain_count') or 5)
                        notify_mode = (cfg.get('drift_notify_mode') or 'inline').lower()  # inline|popup|silent
                        recent = self._drift_history[-sustain_n:]
                        if len(recent) >= sustain_n and all(d > high_thr for d in recent):
                            if not self._pending_retrain_flag:
                                self._pending_retrain_flag = True
                                alert_text = f"Drift גבוה (>{high_thr}) רציף {sustain_n} פעמים – מומלץ אימון מחדש"
                                try:
                                    if notify_mode != 'silent':
                                        if notify_mode == 'popup':
                                            QMessageBox.information(self,'Drift Alert', alert_text)
                                        # always update inline as well (unless silent)
                                        base = self.status_label.text()
                                        if alert_text not in base:
                                            self.status_label.setText((base + ' | ' + alert_text) if base else alert_text)
                                except Exception:
                                    pass
                    else:
                        orig_slot(msg)
                except Exception:
                    try:
                        orig_slot(msg)
                    except Exception:
                        pass
            self.scan_tab.update_status = wrapped_status
        except Exception:
            pass
        self.scan_tab.start_scan_worker(combined_params, self.data_map)
        # After worker created, connect its status directly to status_label
        try:
            if hasattr(self.scan_tab, 'worker_thread') and self.scan_tab.worker_thread:
                self.scan_tab.worker_thread.status_updated.connect(self.status_label.setText)
        except Exception:
            pass

    # status_log helpers removed

    def on_run_walkforward(self, wf_params):
        """Handle walk-forward request from WalkForwardTab."""
        if not getattr(self, 'walkforward_tab', None):
            return
        if not self.data_map:
            try:
                QMessageBox.warning(self,'אין נתונים','טען נתונים לפני הרצת Walk-Forward')
            except Exception:
                pass
            return
        params = dict(wf_params)
        try:
            if isinstance(self.current_params, dict) and self.current_params.get('strategies') and 'strategies' not in params:
                params['strategies'] = self.current_params.get('strategies')
        except Exception:
            pass
        # propagate financial settings from backtest tab if present
        try:
            if hasattr(self,'backtest_tab'):
                params.setdefault('commission', self.backtest_tab.commission_spin.value())
                params.setdefault('slippage', self.backtest_tab.slippage_spin.value())
                params.setdefault('start_cash', self.backtest_tab.start_cash_spin.value())
        except Exception:
            pass
        self.walkforward_tab.start_walkforward_worker(params, self.data_map)

    def _run_live_evaluation_cycle(self):
        """Periodic task: backfill realized outcomes and compute live metrics; update status label concisely."""
        try:
            from ml.evaluation import backfill_realized_outcomes, compute_live_metrics, summarize_recent
            pred_log = os.path.join('logs','predictions.jsonl')
            # backfill if data exists
            if self.data_map and os.path.exists(pred_log):
                updated = backfill_realized_outcomes(pred_log, self.data_map)
            else:
                updated = 0
            metrics = compute_live_metrics(pred_log)
            recent = summarize_recent(pred_log, last_n=200)
            parts = []
            if metrics:
                parts.append(f"Live F1={metrics.get('f1')}")
                if metrics.get('auc') is not None:
                    parts.append(f"AUC={metrics.get('auc')}")
                # --- Adaptive thresholding: adjust global threshold slightly if precision drifts low ---
                try:
                    if self._active_model_snapshot_dir:
                        thr_path = os.path.join(self._active_model_snapshot_dir, 'thresholds.json')
                        if os.path.exists(thr_path):
                            with open(thr_path,'r',encoding='utf-8') as f:
                                thr_data = json.load(f)
                            # simple rule: if precision < 0.4 and have >200 preds, raise threshold by +0.02 (cap 0.9)
                            if metrics.get('precision') is not None and metrics.get('count',0) >= 200:
                                prec = metrics['precision']
                                changed = False
                                if prec < 0.4:
                                    g = thr_data.get('global',0.5)
                                    new_g = min(g + 0.02, 0.9)
                                    if abs(new_g - g) >= 0.005:
                                        thr_data['global'] = new_g
                                        thr_data.setdefault('history', []).append({'ts': datetime.datetime.utcnow().isoformat()+'Z','type':'adaptive_inc','prev': g,'new': new_g,'reason': f'precision {prec}'})
                                        changed = True
                                elif prec > 0.65:
                                    g = thr_data.get('global',0.5)
                                    new_g = max(g - 0.02, 0.3)
                                    if abs(new_g - g) >= 0.005:
                                        thr_data['global'] = new_g
                                        thr_data.setdefault('history', []).append({'ts': datetime.datetime.utcnow().isoformat()+'Z','type':'adaptive_dec','prev': g,'new': new_g,'reason': f'precision {prec}'})
                                        changed = True
                                if changed:
                                    try:
                                        with open(thr_path,'w',encoding='utf-8') as f:
                                            json.dump(thr_data, f, ensure_ascii=False, indent=2)
                                        parts.append(f"ThrAdj={thr_data.get('global')}")
                                    except Exception:
                                        pass
                except Exception:
                    pass
            if updated:
                parts.append(f"Backfilled={updated}")
            if recent:
                parts.append(f"Recent>=0.5={recent.get('pct_ge_0_5')}")
            if parts:
                # non-intrusive append to existing status
                base = self.status_label.text() if hasattr(self,'status_label') else ''
                tail = ' | '.join(parts)
                # avoid uncontrolled growth
                if len(base) > 120:
                    base = base[-120:]
                try:
                    self.status_label.setText(tail)
                except Exception:
                    pass
            # Drift-triggered retrain automation
            try:
                if self._automation_cfg.get('auto_retrain_on_drift') and self._pending_retrain_flag:
                    # cooldown check
                    cooldown_h = float(self._automation_cfg.get('retrain_cooldown_hours') or 6)
                    allow = False
                    if self._last_auto_retrain_ts is None:
                        allow = True
                    else:
                        dt_hours = (datetime.datetime.utcnow() - self._last_auto_retrain_ts).total_seconds() / 3600.0
                        if dt_hours >= cooldown_h:
                            allow = True
                    if allow:
                        self._pending_retrain_flag = False
                        self._last_auto_retrain_ts = datetime.datetime.utcnow()
                        self.status_label.setText('Auto-retrain (drift) starting...')
                        # reuse default model/horizons config
                        mdl = self._automation_cfg.get('default_train_model') or 'rf'
                        horizons = self._automation_cfg.get('default_train_horizons') or ''
                        self.on_train_ml({'ml_model': mdl, 'horizons': horizons, 'auto_rescan': True})
            except Exception:
                pass
        except Exception:
            pass

    def optimize_ensemble(self, auto_mode: bool=False):
        """Aggregate validation sets of rf/xgb/lgbm models if available; compute optimal linear weights & stacking meta-model; persist results."""
        try:
            base_files = [('rf','ml/base_meta_rf.json'),('xgb','ml/base_meta_xgb.json'),('lgbm','ml/base_meta_lgbm.json')]
            metas = []
            for name, path in base_files:
                if not os.path.exists(path):
                    continue
                try:
                    with open(path,'r',encoding='utf-8') as f:
                        data = json.load(f)
                    # derive auc if present
                    auc = None
                    val = data.get('validation')
                    if isinstance(val, dict):
                        auc = val.get('auc') or val.get('auc_mean') or data.get('cv_mean_auc')
                    metas.append({'name': name, 'val_probs': data.get('val_probs'), 'val_labels': data.get('val_labels'), 'auc': auc})
                except Exception:
                    continue
            if len(metas) < 2:
                if not auto_mode:
                    QMessageBox.information(self,'Info','Need at least two base models with validation data to optimize ensemble')
                else:
                    self._automation_log('Auto ensemble optimize skipped (need >=2 models)')
                return
            from ml.ensemble import optimize_linear_weights, train_meta_model, persist_ensemble_artifacts
            weight_res = optimize_linear_weights(metas, step=0.1)
            meta_res = train_meta_model(metas)
            weights_named = None
            if weight_res.get('weights'):
                try:
                    # Map weights to model order rf,xgb,lgbm present in metas list insertion order
                    ordered_names = [m['name'] for m in metas]
                    w_list = weight_res['weights']
                    weights_named = {ordered_names[i]: w_list[i] for i in range(len(ordered_names))}
                except Exception:
                    pass
            persist_ensemble_artifacts('ml', weights_named, meta_res.get('auc'))
            msg = 'Ensemble optimization completed.'
            if weight_res.get('auc'):
                msg += f" Linear AUC={round(weight_res['auc'],4)}"
            if meta_res.get('auc'):
                msg += f" | Meta AUC={round(meta_res.get('auc'),4)}"
            if auto_mode:
                self._automation_log(msg)
            else:
                QMessageBox.information(self,'Done', msg)
        except Exception as e:
            if auto_mode:
                self._automation_log(f'Ensemble optimization failed: {e}')
            else:
                QMessageBox.critical(self,'Error', f'Ensemble optimization failed: {e}')
        
    def on_run_backtest(self, backtest_params):
        """Handle backtest request"""
        # Merge sidebar params (including selected strategies) with backtest params
        combined_params = {**self.current_params, **backtest_params}
        self.backtest_tab.start_backtest_worker(combined_params, self.data_map)
        
    def on_run_optimize(self, optimize_params):
        """Handle optimize request"""
        combined_params = {**self.current_params, **optimize_params}
        self.optimize_tab.start_optimize_worker(combined_params, self.data_map)

    def on_apply_optimized_params(self, params: dict):
        """Apply best optimization params to the global current_params (light merge)."""
        try:
            if not isinstance(params, dict):
                return
            # Merge keeping existing unrelated keys
            self.current_params.update(params)
            # Provide brief UI feedback
            try:
                self.status_label.setText('הוחלו פרמטרים מיטביים מאופטימיזציה')
            except Exception:
                pass
            # Optionally propagate to scan/backtest tabs if they expose a method (best effort)
            try:
                if hasattr(self.backtest_tab, 'set_strategy_params'):
                    self.backtest_tab.set_strategy_params(params)
            except Exception:
                pass
        except Exception:
            pass

    def on_load_run_from_repo(self, run_id: str):
        """Load run metadata + results (best-effort) and show brief info message."""
        try:
            from run_repo.run_repository import load_run
            meta, results = load_run(run_id)
            if not meta:
                QMessageBox.information(self,'Run','לא נמצאה ריצה')
                return
            # store last loaded run for possible comparison
            self._last_loaded_run = {'meta': meta, 'results': results}
            self.status_label.setText(f"נטענה ריצה {run_id} ({meta.get('type')})")
            # Optionally route results to an appropriate tab (only if user currently there)
            t = meta.get('type')
            if t == 'optimize' and results and hasattr(self.optimize_tab,'update_results'):
                self.optimize_tab.update_results(results)
            elif t == 'backtest' and results and hasattr(self.backtest_tab,'update_results'):
                self.backtest_tab.update_results(results)
            elif t == 'walkforward' and results and getattr(self,'walkforward_tab',None):
                try:
                    self.walkforward_tab.update_results(results)
                except Exception:
                    pass
        except Exception as e:
            try:
                QMessageBox.critical(self,'Run','שגיאה בטעינת ריצה: '+str(e))
            except Exception:
                pass

    def on_train_ml(self, params):
        """Train ML model (rf or xgb) in a background thread; show brief status on completion."""
        # Prevent concurrent trainings (can corrupt outputs)
        if getattr(self, '_training_in_progress', False):
            try:
                print('[TRAIN] Ignored new training request - training already in progress', flush=True)
            except Exception:
                pass
            return
        if not self.data_map:
            QMessageBox.warning(self, 'אין נתונים', 'אין נתונים לאימון')
            return
        # --- Pre-train diagnostics to understand why frames appear empty ---
        try:
            non_empty = 0; have_close = 0; sample_dump = []
            for i,(sym,df) in enumerate(self.data_map.items()):
                if i < 8:
                    try:
                        shape = getattr(df,'shape',()) if df is not None else ()
                        cols = list(df.columns)[:12] if hasattr(df,'columns') else 'n/a'
                        sample_dump.append({'sym': sym, 'type': type(df).__name__, 'shape': shape, 'cols': cols})
                    except Exception:
                        pass
                if hasattr(df,'empty') and not df.empty:
                    non_empty += 1
                    if 'Close' in df.columns:
                        have_close += 1
            print(f"[PRETRAIN] data_map summary: symbols={len(self.data_map)} non_empty={non_empty} have_Close={have_close}")
            print(f"[PRETRAIN] sample entries: {sample_dump}", flush=True)
            # Salvage attempt: if (a) all empty OR (b) we have zero symbols with a Close column
            # After fixing load_json to expand yahoo.daily, reloading a subset may repair dataset without full app restart.
            if (non_empty == 0 or have_close == 0) and getattr(self, '_last_data_folder', None):
                import os
                from data.data_utils import load_json
                folder = self._last_data_folder
                tried = 0; fixed = 0
                # If have_close==0, do a full reload of every JSON to guarantee expansion after loader fix
                symbols = list(self.data_map.keys()) if have_close == 0 else list(self.data_map.keys())[:50]
                for sym in symbols:
                    path_json = os.path.join(folder, sym + '.json')
                    if os.path.exists(path_json):
                        try:
                            df2 = load_json(path_json)
                            if df2 is not None and not df2.empty and 'Close' in df2.columns:
                                self.data_map[sym] = df2
                                fixed += 1
                        except Exception:
                            pass
                    tried += 1
                print(f"[PRETRAIN] salvage reload attempt (reason={'no_data' if non_empty==0 else 'no_close'}) symbols={len(symbols)} tried={tried} fixed={fixed}", flush=True)
        except Exception as e:
            print('[PRETRAIN] diagnostics failed:', e, flush=True)
        model_choice = (params.get('ml_model') if isinstance(params, dict) else 'rf') or 'rf'
        self.status_label.setText(f"Training ML model: {model_choice} ...")
        self.train_btn_disabled = True
        try:
            self.scan_tab.train_btn.setEnabled(False)
        except Exception:
            pass
        try:
            print('[TRAIN] Starting training. model=', model_choice, 'horizons_raw=', params.get('horizons'), 'data_map_symbols=', len(self.data_map), flush=True)
        except Exception:
            pass

        # parse horizons if provided (comma separated) e.g. '5,10,20'
        horizons_raw = ''
        horizons_list = None
        try:
            horizons_raw = (params.get('horizons') or '').strip()
            if horizons_raw:
                parts = [p.strip() for p in horizons_raw.split(',') if p.strip()]
                hl = []
                for p in parts:
                    try:
                        v = int(p)
                        if v > 0:
                            hl.append(v)
                    except Exception:
                        pass
                if hl:
                    horizons_list = sorted(list(set(hl)))
        except Exception:
            horizons_list = None
        # Fallback: if user left multi-horizons blank but there is a single active horizon selector in UI we can try to use it
        try:
            if (not horizons_list) and hasattr(self.scan_tab, 'horizon_select') and self.scan_tab.horizon_select.count() > 0:
                cur_h = self.scan_tab.horizon_select.currentText().strip()
                if cur_h.isdigit():
                    horizons_list = [int(cur_h)]
        except Exception:
            pass
        
        # Historical training cutoff - using trading days, not calendar days
        training_days_back = params.get('training_days_back')
        historical_cutoff_date = None
        if training_days_back and isinstance(training_days_back, int) and training_days_back > 0:
            from datetime import datetime, timedelta
            import pandas as pd
            
            # Calculate cutoff using actual trading days from available data
            # Find the most recent date in the data and go back N trading days from there
            try:
                latest_date = None
                for symbol, df in self.data_map.items():
                    if df is not None and not df.empty:
                        if isinstance(df.index, pd.DatetimeIndex):
                            df_latest = df.index.max()
                        elif 'Date' in df.columns:
                            df_latest = pd.to_datetime(df['Date']).max()
                        else:
                            continue
                        
                        if latest_date is None or df_latest > latest_date:
                            latest_date = df_latest
                
                if latest_date:
                    # Create a date range of business days going back from latest_date
                    # Use pandas business day frequency to skip weekends
                    end_date = pd.Timestamp(latest_date)
                    # Generate business days going backwards
                    business_days = pd.bdate_range(end=end_date, periods=training_days_back + 1, freq='B')
                    cutoff_dt = business_days[0]  # First date (oldest)
                    historical_cutoff_date = cutoff_dt.strftime('%Y-%m-%d')
                    print(f'[TRAIN] Historical training mode: {training_days_back} TRADING days back from {end_date.strftime("%Y-%m-%d")} = cutoff_date {historical_cutoff_date}', flush=True)
                else:
                    # Fallback to calendar days if no data dates found
                    cutoff_dt = datetime.now() - timedelta(days=training_days_back * 1.4)  # Rough conversion
                    historical_cutoff_date = cutoff_dt.strftime('%Y-%m-%d')
                    print(f'[TRAIN] Historical training mode (fallback): cutoff_date = {historical_cutoff_date}', flush=True)
                    
            except Exception as e:
                # Fallback to calendar days if calculation fails
                cutoff_dt = datetime.now() - timedelta(days=training_days_back * 1.4)
                historical_cutoff_date = cutoff_dt.strftime('%Y-%m-%d')
                print(f'[TRAIN] Historical training mode (error fallback): cutoff_date = {historical_cutoff_date}, error = {e}', flush=True)

        def _run_training():
            meta = None
            err = None
            try:
                def _progress(ev: dict):
                    # emit signal to marshal safely to GUI thread
                    try:
                        self.training_progress.emit(ev)
                    except Exception:
                        pass
                
                if historical_cutoff_date and horizons_list:
                    # Historical multi-horizon training
                    from ml.train_model import train_multi_horizon_model, filter_data_until_date
                    print(f'[TRAIN] Historical multi-horizon training: cutoff={historical_cutoff_date}, horizons={horizons_list}', flush=True)
                    # Emit start phase
                    _progress({'phase': 'historical_start', 'total_horizons': len(horizons_list)})
                    
                    # Filter data to cutoff date
                    filtered_data = filter_data_until_date(self.data_map, historical_cutoff_date)
                    if not filtered_data:
                        raise ValueError(f'No data available for cutoff date {historical_cutoff_date}')
                    
                    print(f'[TRAIN] Filtered data: {len(filtered_data)} symbols for historical training', flush=True)
                    
                    # Train models for each horizon
                    trained_models = {}
                    total_combinations = len(horizons_list)
                    
                    for i, horizon in enumerate(horizons_list):
                        try:
                            print(f'[TRAIN] Training {model_choice} for horizon {horizon}d ({i+1}/{total_combinations})', flush=True)
                            _progress({'phase': 'historical_horizon_start', 'horizon': horizon, 'index': i+1, 'total': total_combinations})
                            
                            model_path = train_multi_horizon_model(
                                cutoff_date=historical_cutoff_date,
                                horizon_days=horizon,
                                algorithm=model_choice,
                                data_map=filtered_data,
                                progress_cb=_progress
                            )
                            
                            if model_path:
                                trained_models[horizon] = model_path
                                print(f'[TRAIN] ✅ Horizon {horizon}d model saved: {model_path}', flush=True)
                            else:
                                print(f'[TRAIN] ❌ Horizon {horizon}d training failed', flush=True)
                            _progress({'phase': 'historical_horizon_done', 'horizon': horizon, 'index': i+1, 'total': total_combinations})
                                
                        except Exception as e:
                            print(f'[TRAIN] ❌ Error training horizon {horizon}d: {e}', flush=True)
                            continue
                    
                    # Create meta result
                    meta = {
                        'type': 'historical_multi_horizon',
                        'cutoff_date': historical_cutoff_date,
                        'trained_models': trained_models,
                        'model_type': model_choice,
                        'horizons': horizons_list,
                        'success_count': len(trained_models),
                        'total_requested': len(horizons_list)
                    }
                    _progress({'phase': 'historical_done', 'success': len(trained_models), 'total': len(horizons_list)})
                    
                else:
                    # Regular training
                    from ml.train_model import train_model
                    print('[TRAIN] Regular training with horizons_list=', horizons_list, flush=True)
                    meta = train_model(self.data_map, model=model_choice, multi_horizons=horizons_list, progress_cb=_progress)
                try:
                    print('[TRAIN] train_model returned meta keys=', list(meta.keys()) if isinstance(meta, dict) else type(meta), flush=True)
                except Exception:
                    pass
            except Exception as e:
                err = str(e)
                try:
                    import traceback; traceback.print_exc()
                    print('[TRAIN] ERROR during train_model:', err, flush=True)
                except Exception:
                    pass
            def _finish():
                # mark done
                try:
                    self._training_in_progress = False
                except Exception:
                    pass
                try:
                    print('[TRAIN] _finish invoked. err=', err, 'meta keys=', list(meta.keys()) if isinstance(meta, dict) else type(meta), flush=True)
                except Exception:
                    pass
                try:
                    if err:
                        def _gui_err():
                            try:
                                QMessageBox.critical(self, 'שגיאה', f'אימון נכשל: {err}')
                                self.status_label.setText('אימון נכשל')
                            except Exception:
                                pass
                        QTimer.singleShot(0, _gui_err)
                    else:
                        # write report file
                        try:
                            os.makedirs('logs', exist_ok=True)
                            with open('logs/ml_last_report.json','w',encoding='utf-8') as f:
                                json.dump(meta, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                        # --- Model Registry Snapshot ---
                        try:
                            try:
                                self.training_progress.emit({'phase':'snapshot_start'})
                            except Exception:
                                pass
                            ts = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                            registry_root = os.path.join('ml','registry')
                            os.makedirs(registry_root, exist_ok=True)
                            snap_dir = os.path.join(registry_root, ts)
                            os.makedirs(snap_dir, exist_ok=True)
                            artifact_src = meta.get('path')
                            if artifact_src and os.path.exists(artifact_src):
                                import shutil
                                try:
                                    shutil.copy2(artifact_src, os.path.join(snap_dir, os.path.basename(artifact_src)))
                                except Exception as ce:
                                    print('[TRAIN] snapshot copy failed:', ce, flush=True)
                            else:
                                print('[TRAIN] WARN: artifact_src missing or does not exist ->', artifact_src, flush=True)
                            # thresholds placeholder (global + per-horizon) for automation; we can fill after optimization later
                            # --- Threshold optimization (global & per-horizon) ---
                            thresholds_obj = {
                                'created_at': datetime.datetime.utcnow().isoformat()+'Z',
                                'global': None,
                                'per_horizon': {},
                                'optimized_metric': 'f1',
                                'history': []
                            }
                            try:
                                from ml.train_model import suggest_probability_threshold
                                # single model path
                                if meta.get('val_probs') and meta.get('val_labels'):
                                    best = suggest_probability_threshold(meta.get('val_probs'), meta.get('val_labels'), metric='f1')
                                    if best:
                                        thresholds_obj['global'] = best.get('threshold')
                                        thresholds_obj['history'].append({'ts': thresholds_obj['created_at'], 'type':'initial_global', 'metric':'f1', 'threshold': best.get('threshold'), 'f1': best.get('f1')})
                                # multi horizon container
                                if meta.get('horizon_models'):
                                    for hm in meta.get('horizon_models'):
                                        vp = hm.get('val_probs'); vl = hm.get('val_labels'); hz = hm.get('horizon')
                                        if vp and vl and hz is not None:
                                            best_h = suggest_probability_threshold(vp, vl, metric='f1')
                                            if best_h:
                                                thresholds_obj['per_horizon'][str(hz)] = best_h.get('threshold')
                                                thresholds_obj['history'].append({'ts': thresholds_obj['created_at'], 'type':'initial_horizon', 'horizon': hz, 'threshold': best_h.get('threshold'), 'f1': best_h.get('f1')})
                                # Fallback: if no per-horizon but global missing try simple 0.5
                                if thresholds_obj['global'] is None:
                                    thresholds_obj['global'] = 0.5
                            except Exception:
                                pass
                            try:
                                with open(os.path.join(snap_dir,'thresholds.json'),'w',encoding='utf-8') as tf:
                                    json.dump(thresholds_obj, tf, ensure_ascii=False, indent=2)
                            except Exception:
                                pass
                            # metadata including class balance
                            snapshot_meta = {
                                'timestamp': ts,
                                'model_type': meta.get('model_type'),
                                'path': artifact_src,
                                'samples': meta.get('samples'),
                                'symbols': meta.get('symbols'),
                                'top_features': meta.get('top_features'),
                                'validation': meta.get('validation'),
                                'cv_mean_auc': meta.get('cv_mean_auc'),
                                'feature_stats': meta.get('feature_stats'),
                                'horizons': meta.get('horizons'),
                                'class_balance': meta.get('class_balance'),
                                'thresholds_file': 'thresholds.json'
                            }
                            try:
                                with open(os.path.join(snap_dir,'metadata.json'),'w',encoding='utf-8') as sf:
                                    json.dump(snapshot_meta, sf, ensure_ascii=False, indent=2)
                            except Exception as me:
                                print('[TRAIN] failed writing metadata.json:', me, flush=True)
                            # Write/update base meta for ensemble optimization
                            try:
                                base_meta_path = os.path.join('ml', f'base_meta_{model_choice}.json')
                                base_meta_obj = {
                                    'model_type': meta.get('model_type'),
                                    'timestamp': ts,
                                    'validation': meta.get('validation'),
                                    'cv_mean_auc': meta.get('cv_mean_auc'),
                                    'val_probs': meta.get('val_probs'),
                                    'val_labels': meta.get('val_labels'),
                                    'horizon_models': meta.get('horizon_models'),
                                    'horizons': meta.get('horizons')
                                }
                                with open(base_meta_path,'w',encoding='utf-8') as bmf:
                                    json.dump(base_meta_obj, bmf, ensure_ascii=False, indent=2)
                            except Exception:
                                pass
                            # update / create registry index
                            index_path = os.path.join(registry_root,'index.json')
                            index_data = []
                            if os.path.exists(index_path):
                                try:
                                    with open(index_path,'r',encoding='utf-8') as inf:
                                        index_data = json.load(inf) or []
                                except Exception:
                                    index_data = []
                            entry = {k: snapshot_meta.get(k) for k in ('timestamp','model_type','samples','symbols','cv_mean_auc')}
                            entry['snapshot_dir'] = snap_dir
                            index_data.append(entry)
                            try:
                                index_data = sorted(index_data, key=lambda r: r.get('timestamp',''), reverse=True)
                            except Exception:
                                pass
                            try:
                                with open(index_path,'w',encoding='utf-8') as outf:
                                    json.dump(index_data, outf, ensure_ascii=False, indent=2)
                            except Exception as ie:
                                print('[TRAIN] failed writing index.json:', ie, flush=True)
                            # Auto promote: set as ACTIVE (could add criteria later)
                            try:
                                with open(os.path.join(registry_root,'ACTIVE.txt'),'w',encoding='utf-8') as af:
                                    af.write(snap_dir)
                                self._active_model_snapshot_dir = snap_dir
                                print('[TRAIN] ACTIVE pointer updated ->', snap_dir, flush=True)
                            except Exception as ae:
                                print('[TRAIN] failed writing ACTIVE.txt:', ae, flush=True)
                            try:
                                self.training_progress.emit({'phase':'snapshot_done','snapshot': snap_dir})
                            except Exception:
                                pass
                            # Ensure final 'done' phase emitted for progress=100
                            try:
                                self.training_progress.emit({'phase':'done','snapshot': snap_dir})
                            except Exception:
                                pass
                        except Exception:
                            pass
                        samples = meta.get('samples') if meta else '?'
                        symbols = meta.get('symbols') if meta else '?'
                        top_feats = ', '.join(meta.get('top_features', [])[:7]) if meta else ''
                        def _gui_update_status():
                            try:
                                self.status_label.setText(f"אימון הסתיים ({model_choice}) דגימות={samples}")
                            except Exception:
                                pass
                        QTimer.singleShot(0, _gui_update_status)
                        # extract quick metrics (precision/recall for class '1')
                        quick_metrics = ''
                        try:
                            rep = meta.get('report', {})
                            cls1 = rep.get('1', {})
                            p = cls1.get('precision'); r = cls1.get('recall'); f1 = cls1.get('f1-score')
                            if all(isinstance(v, (int,float)) for v in (p,r,f1)):
                                quick_metrics = f"P={p:.2f} R={r:.2f} F1={f1:.2f}"
                        except Exception:
                            pass
                        msg = f"אימון הסתיים. מודל: {model_choice}\nSamples: {samples}\nSymbols: {symbols}"
                        # validation metrics
                        try:
                            val = meta.get('validation') if meta else None
                            if val:
                                auc = val.get('auc'); brier = val.get('brier'); ll = val.get('log_loss')
                                if isinstance(auc,(int,float)):
                                    msg += f"\nVal AUC: {auc:.3f}"
                                if isinstance(brier,(int,float)):
                                    msg += f" | Brier: {brier:.4f}"
                                if isinstance(ll,(int,float)):
                                    msg += f" | LogLoss: {ll:.3f}"
                                if val.get('calibrated'):
                                    msg += "\n(Probabilities calibrated)"
                        except Exception:
                            pass
                        if quick_metrics:
                            msg += f"\nMetrics: {quick_metrics}"
                        if top_feats:
                            msg += f"\nTop Features: {top_feats}"
                        try:
                            cv_mean = meta.get('cv_mean_auc')
                            if isinstance(cv_mean,(int,float)):
                                msg += f"\nCV mean AUC: {cv_mean:.3f}"
                        except Exception:
                            pass
                        # Replace popup dialog with inline status + dashboard info label (user requested no popup)
                        def _inline_notify(msg_text: str):
                            try:
                                # Append concise metrics to the main status label (single line)
                                compact = msg_text.replace('\n',' | ')
                                if len(compact) > 240:
                                    compact = compact[:237] + '...'
                                cur = self.status_label.text()
                                # Avoid duplicating prior text
                                if 'אימון הסתיים' not in cur:
                                    self.status_label.setText(compact)
                                # Update dashboard info label if available
                                try:
                                    if getattr(self,'model_dashboard_tab',None):
                                        self.model_dashboard_tab.info_lbl.setText(compact)
                                        # Trigger metrics panel refresh (if method present)
                                        if hasattr(self.model_dashboard_tab,'load_active_metrics'):
                                            QTimer.singleShot(0, self.model_dashboard_tab.load_active_metrics)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        QTimer.singleShot(0, lambda m=msg: _inline_notify(m))
                        # Auto-rescan if we have previous scan params to refresh probabilities
                        try:
                            auto_rescan = params.get('auto_rescan', True)
                            if auto_rescan:
                                last_params = getattr(self, 'current_params', {}) or {}
                                # inject horizons into last_params for scan use
                                if horizons_raw and 'horizons' not in last_params:
                                    last_params['horizons'] = horizons_raw
                                # populate horizon selector UI if multi-horizon model
                                try:
                                    if meta and isinstance(meta.get('horizons'), (list, tuple)) and hasattr(self.scan_tab, 'horizon_select'):
                                        self.scan_tab.horizon_select.clear()
                                        for h in meta.get('horizons'):
                                            self.scan_tab.horizon_select.addItem(str(h))
                                except Exception:
                                    pass
                                if hasattr(self.scan_tab, 'model_combo') and self.scan_tab.model_combo.currentText().lower() == model_choice.lower():
                                    self.status_label.setText('מרענן סריקה עם המודל החדש...')
                                    self.scan_tab.start_scan_worker(last_params, self.data_map)
                        except Exception:
                            pass
                finally:
                    try:
                        def _reenable():
                            try:
                                self.scan_tab.train_btn.setEnabled(True)
                            except Exception:
                                pass
                        QTimer.singleShot(0, _reenable)
                    except Exception:
                        pass
                # Chain multi-model training if in Train All mode
                try:
                    if getattr(self, '_train_all_mode', False):
                        # store last meta for potential summary (optional)
                        if not hasattr(self, '_train_all_results'):
                            self._train_all_results = []
                        self._train_all_results.append({'model': model_choice, 'err': err, 'meta_ok': bool(meta)})
                        QTimer.singleShot(250, self._advance_train_all)
                except Exception:
                    pass
            # marshal back to GUI thread; also call directly to avoid silent scheduling misses
            executed = False
            try:
                _finish()
                executed = True
            except Exception as e:
                try:
                    print('[TRAIN] direct _finish call failed, scheduling via QTimer:', e, flush=True)
                except Exception:
                    pass
            if not executed:
                try:
                    QTimer.singleShot(0, _finish)
                except Exception as e2:
                    try:
                        print('[TRAIN] QTimer.singleShot failed, attempting raw call again:', e2, flush=True)
                    except Exception:
                        pass
                    try:
                        _finish()
                    except Exception as e3:
                        try:
                            print('[TRAIN] _finish ultimate fallback failed:', e3, flush=True)
                        except Exception:
                            pass

        # mark training started
        try:
            self._training_in_progress = True
        except Exception:
            pass
        t = threading.Thread(target=_run_training, daemon=True)
        t.start()

    # -------------- Train All (rf -> xgb -> lgbm) orchestration --------------
    def start_train_all(self, params):
        # Deprecated legacy multi-model orchestration retained for backward compatibility.
        try:
            QMessageBox.information(self,'Info','Train All הוסר. השתמש ב-Iterative Train מהלשונית.')
        except Exception:
            pass

    def on_iterative_training_requested(self, params: dict):
        """Handle iterative training requests from model dashboard tab."""
        if getattr(self, '_iterative_in_progress', False):
            try:
                QMessageBox.information(self,'Busy','Iterative training already running')
            except Exception:
                pass
            return
        self._iterative_in_progress = True
        horizons_text = params.get('horizons','5')
        try:
            horizons = [int(x.strip()) for x in horizons_text.split(',') if x.strip()]
        except Exception:
            horizons = [5]
        # Map UI 'validation_days' to initial lookback window for training (training slice)
        initial_lookback_days = int(params.get('validation_days', 30))
        target_accuracy = float(params.get('target_accuracy', 0.6))
        improvement_threshold = float(params.get('improvement_threshold', 0.005))
        max_iterations = int(params.get('max_iterations', 5))
        # פרמטרים חדשים: threshold להגדרת הצלחה ו-blend alpha לדיוק המשולב
        try:
            label_threshold = float(params.get('label_threshold', 0.02))
        except Exception:
            label_threshold = 0.02
        try:
            blend_alpha = float(params.get('blend_alpha', 0.40))
        except Exception:
            blend_alpha = 0.40
        # Build config object for trainer
        cfg = {
            'initial_lookback_days': initial_lookback_days,
            'horizons': horizons,
            'target_accuracy': target_accuracy,
            'min_accuracy_improvement': improvement_threshold,
            'max_iterations': max_iterations,
            'label_threshold': label_threshold,
            'blend_alpha': blend_alpha
        }
        self.status_label.setText(
            f"Iterative training running (hz={horizons}, thr={label_threshold}, α={blend_alpha})..."
        )
        threading.Thread(target=self._run_iterative_training_worker, args=(cfg,), daemon=True).start()

    def _run_iterative_training_worker(self, cfg: dict):
        from ml.iterative_training_system import IterativeHistoricalTrainer, IterativeTrainingConfig
        try:
            trainer = IterativeHistoricalTrainer(self.data_map)
            config = IterativeTrainingConfig(
                initial_lookback_days=cfg['initial_lookback_days'],
                horizons=cfg['horizons'],
                max_iterations=cfg['max_iterations'],
                min_accuracy_improvement=cfg['min_accuracy_improvement'],
                target_accuracy=cfg['target_accuracy'],
                label_threshold=cfg.get('label_threshold', 0.02),
                blend_alpha=cfg.get('blend_alpha', 0.40)
            )
            results = trainer.run_iterative_training(config)
            # Build concise accuracy summary per horizon from last iteration
            if results:
                last = results[-1]
                hz_parts = [f"{h}D={last.accuracy_by_horizon.get(h,0):.3f}" for h in cfg['horizons']]
                self.status_label.setText("Iterative done: " + ', '.join(hz_parts))
            else:
                self.status_label.setText('Iterative finished: no results')
        except Exception as e:
            self.status_label.setText(f'Iterative failed: {e}')
        finally:
            self._iterative_in_progress = False

    def _advance_train_all(self):
        try:
            if not getattr(self, '_train_all_mode', False):
                return
            if self._train_all_queue:
                nxt = self._train_all_queue.pop(0)
                remaining = len(self._train_all_queue)
                training_days_back = getattr(self, '_train_all_training_days_back', None)
                
                if training_days_back:
                    self.status_label.setText(f'Train All היסטורי - {nxt} ({remaining} נותרו)')
                else:
                    self.status_label.setText(f'Train All continuing with {nxt} ({remaining} remaining)')
                    
                train_params = {'ml_model': nxt, 'horizons': getattr(self,'_train_all_horizons',''), 'auto_rescan': False}
                if training_days_back:
                    train_params['training_days_back'] = training_days_back
                self.on_train_ml(train_params)
            else:
                # done -> run ensemble optimization automatically
                self.status_label.setText('Train All complete. Optimizing ensemble...')
                try:
                    self.optimize_ensemble(auto_mode=True)
                except Exception:
                    pass
                # final optional rescan using last requested model (ensemble if created)
                if self._train_all_autorescan:
                    try:
                        params = getattr(self,'current_params',{}) or {}
                        params['horizons'] = getattr(self,'_train_all_horizons','')
                        # prefer ensemble if created
                        if os.path.exists('ensemble.json'):
                            params['ml_model'] = 'ensemble'
                            if hasattr(self.scan_tab,'model_combo'):
                                idx = self.scan_tab.model_combo.findText('ensemble')
                                if idx >= 0:
                                    self.scan_tab.model_combo.setCurrentIndex(idx)
                        self.status_label.setText('Auto-rescan after Train All...')
                        if hasattr(self.scan_tab,'start_scan_worker'):
                            self.scan_tab.start_scan_worker(params, self.data_map)
                    except Exception:
                        pass
                # cleanup state
                self._train_all_mode = False
        except Exception:
            try:
                self._train_all_mode = False
            except Exception:
                pass


    def on_calibrate_ml(self, params):
        if not self.data_map:
            QMessageBox.warning(self,'אין נתונים','אין נתונים לקליברציה')
            return
        model_choice = (params.get('ml_model') if isinstance(params, dict) else 'rf') or 'rf'
        self.status_label.setText(f"Calibrating model: {model_choice} ...")
        try:
            self.scan_tab.calib_btn.setEnabled(False)
        except Exception:
            pass
        def _run_calib():
            meta = None; err=None
            try:
                from ml.train_model import calibrate_model
                meta = calibrate_model(self.data_map, model=model_choice)
            except Exception as e:
                err=str(e)
            def _finish():
                try:
                    if err:
                        QMessageBox.critical(self,'שגיאה',f'קליברציה נכשלה: {err}')
                        self.status_label.setText('קליברציה נכשלה')
                    else:
                        self.status_label.setText('קליברציה הסתיימה')
                        try:
                            QMessageBox.information(self,'הצלחה',f"קליברציה הסתיימה. AUC={meta.get('auc'):.3f}" if isinstance(meta.get('auc'),(int,float)) else 'קליברציה הסתיימה')
                        except Exception:
                            pass
                        # Refresh scan (probabilities only) if model matches
                        try:
                            last_params = getattr(self,'current_params',{}) or {}
                            if hasattr(self.scan_tab,'model_combo') and self.scan_tab.model_combo.currentText().lower()==model_choice.lower():
                                self.status_label.setText('מרענן סריקה (קליברציה)...')
                                self.scan_tab.start_scan_worker(last_params, self.data_map)
                        except Exception:
                            pass
                finally:
                    try:
                        self.scan_tab.calib_btn.setEnabled(True)
                    except Exception:
                        pass
            try:
                QTimer.singleShot(0,_finish)
            except Exception:
                _finish()
        threading.Thread(target=_run_calib, daemon=True).start()

    # ---------------- Automation Helpers -----------------
    def _load_automation_cfg(self):
        try:
            path = os.path.join('config','automation.json')
            if os.path.exists(path):
                with open(path,'r',encoding='utf-8') as f:
                    user_cfg = json.load(f) or {}
            else:
                user_cfg = {}
            # merge defaults
            defaults = {
                'auto_retrain_on_drift': True,
                'drift_high_threshold': 1.25,
                'drift_sustain_count': 5,
                'drift_notify_mode': 'inline',  # inline|popup|silent
                'retrain_cooldown_hours': 6,
            }
            for k,v in defaults.items():
                user_cfg.setdefault(k,v)
            return user_cfg
        except Exception:
            pass
        return {}

    def _post_start_automation(self):
        """Run after UI settles: auto-train / auto-ensemble / auto-scan depending on config and current state."""
        # Prevent multiple runs
        if getattr(self, '_automation_started', False):
            self._automation_log('Post-start automation already executed, skipping')
            return
        self._automation_started = True
        
        try:
            cfg = self._automation_cfg
            # respect runtime toggle (if user turned OFF automation in UI between init and now)
            try:
                if hasattr(self.model_dashboard_tab,'_automation_enabled_override') and self.model_dashboard_tab._automation_enabled_override is False:
                    self._automation_log('Automation disabled by user toggle; skipping post-start actions')
                    return
            except Exception:
                pass
            # Auto-train if no ACTIVE snapshot present
            if cfg.get('auto_train_on_start'):
                if not self._active_model_snapshot_dir:
                    # delay if data still loading; handled in loader on_finished
                    if not self._data_loading:
                        mdl = cfg.get('default_train_model') or 'rf'
                        horizons = cfg.get('default_train_horizons') or ''
                        self.status_label.setText('Auto-training (startup)...')
                        self._automation_log(f'Auto-train start model={mdl} horizons={horizons}')
                        self.on_train_ml({'ml_model': mdl, 'horizons': horizons, 'auto_rescan': False})
                    else:
                        self._automation_log('Deferring auto-train until data load finishes')
            # Auto ensemble optimize (after a tiny delay to ensure base meta files exist if just trained)
            if cfg.get('auto_optimize_ensemble'):
                def _auto_ens():
                    try:
                        # check toggle still ON
                        if hasattr(self.model_dashboard_tab,'_automation_enabled_override') and self.model_dashboard_tab._automation_enabled_override is False:
                            self._automation_log('Skip auto ensemble optimize (toggle OFF)')
                            return
                        self._automation_log('Auto ensemble optimize start (silent)')
                        self.optimize_ensemble(auto_mode=True)
                    except Exception:
                        pass
                QTimer.singleShot(8000, _auto_ens)
            # Auto-scan startup
            if cfg.get('auto_scan_on_start'):
                QTimer.singleShot(4000, self._maybe_run_auto_scan)
        except Exception:
            pass

    def _maybe_run_auto_scan(self):
        """Execute a scan automatically using configured strategy and current ACTIVE model if data is loaded."""
        try:
            # respect toggle
            if hasattr(self.model_dashboard_tab,'_automation_enabled_override') and self.model_dashboard_tab._automation_enabled_override is False:
                return
            if not self.data_map:
                return
            # build params from scan_tab defaults + automation overrides
            strategy = self._automation_cfg.get('default_scan_strategy') or 'Donchian Breakout'
            params = {
                'scan_strategy': strategy,
                'patterns': '',
                'lookback': getattr(self.scan_tab, 'lookback_spin', None).value() if hasattr(getattr(self,'scan_tab',None),'lookback_spin') else 30,
                'rr_target': '2xATR',
                'min_rr': 0.0,
                'symbols': '',
                'universe_limit': 0,
                'ml_model': 'ensemble' if os.path.exists('ensemble.json') else (self._automation_cfg.get('default_train_model') or 'rf'),
                'ml_min_prob': 0.0,
                'score_formula': 'weighted',
                'w_prob': 0.55,
                'w_rr': 0.25,
                'w_fresh': 0.15,
                'w_pattern': 0.05,
                'horizons': '',
                'use_horizon': ''
            }
            try:
                if hasattr(self.scan_tab,'start_scan_worker'):
                    self.scan_tab.start_scan_worker(params, self.data_map)
                    self.status_label.setText('Auto-scan executed')
                    self._automation_log(f'Auto-scan executed strategy={strategy}')
            except Exception:
                pass
        except Exception:
            pass

    def _automation_log(self, msg: str):
        try:
            os.makedirs('logs', exist_ok=True)
            with open(os.path.join('logs','automation.log'),'a',encoding='utf-8') as f:
                f.write(datetime.datetime.utcnow().isoformat()+ 'Z ' + msg + '\n')
        except Exception:
            pass
        
    def get_data_summary(self):
        """Get summary of loaded data"""
        return {
            'total_symbols': len(self.data_map),
            'symbols': list(self.data_map.keys())
        }