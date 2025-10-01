from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGroupBox,QLabel,QTextEdit,QSpinBox,QComboBox,
                               QPushButton,QProgressBar,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,
                               QCheckBox,QDialog,QGridLayout,QToolButton,QStyle)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from ui.worker_thread import WorkerThread
import json

class OptimizeTab(QWidget):
    run_optimize_requested = Signal(dict)
    apply_params_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.worker_thread=None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        settings_layout = QHBoxLayout()
        help_btn = QToolButton()
        try:
            help_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        except Exception:
            help_btn.setText('?')
        help_btn.setToolTip('עזרה - Optimize')
        from ui.shared.help_viewer import show_markdown_dialog
        help_btn.clicked.connect(lambda: show_markdown_dialog(self,'docs/optimize_tab.md','Optimize Help'))
        left = QGroupBox('הגדרות אופטימיזציה'); left_l = QVBoxLayout(left)
        self.ranges_edit = QTextEdit(); self.ranges_edit.setMaximumHeight(160); self.ranges_edit.setPlainText('{\n  "fast": [8, 20, 4],\n  "slow": [20, 40, 4]\n}')
        self.universe_limit_spin = QSpinBox(); self.universe_limit_spin.setRange(0,10000); self.universe_limit_spin.setValue(50)
        self.folds_spin = QSpinBox(); self.folds_spin.setRange(1,10); self.folds_spin.setValue(3)
        self.patience_spin = QSpinBox(); self.patience_spin.setRange(0,500); self.patience_spin.setValue(0)
        self.stream_chk = QCheckBox('Stream Updates'); self.stream_chk.setChecked(True)
        for lbl,w in [
            ('Parameter Ranges (JSON):',self.ranges_edit),
            ('Universe limit:',self.universe_limit_spin),
            ('Folds:',self.folds_spin),
            ('Patience (0=off):', self.patience_spin),
        ]:
            left_l.addWidget(QLabel(lbl)); left_l.addWidget(w)
        left_l.addWidget(self.stream_chk)
        right = QGroupBox('יעד אופטימיזציה'); right_l = QVBoxLayout(right)
        self.objective_combo = QComboBox(); self.objective_combo.addItems(['Sharpe','CAGR','Return/DD','WinRate','Trades'])
        self.max_results_spin = QSpinBox(); self.max_results_spin.setRange(1,200); self.max_results_spin.setValue(50)
        self.run_optimize_btn = QPushButton('הרץ OPTIMIZE'); self.run_optimize_btn.setObjectName('primary_button'); self.run_optimize_btn.clicked.connect(self.run_optimize)
        self.cancel_btn = QPushButton('ביטול'); self.cancel_btn.setObjectName('secondary_button'); self.cancel_btn.clicked.connect(self.cancel_optimize); self.cancel_btn.setVisible(False)
        # Action buttons (apply + heatmap)
        self.apply_best_btn = QPushButton('החל עליון'); self.apply_best_btn.setObjectName('secondary_button'); self.apply_best_btn.clicked.connect(self.apply_best); self.apply_best_btn.setEnabled(False)
        self.heatmap_btn = QPushButton('Heatmap'); self.heatmap_btn.setObjectName('secondary_button'); self.heatmap_btn.clicked.connect(self.show_heatmap_dialog); self.heatmap_btn.setEnabled(False)
        self.full_heatmap_btn = QPushButton('FullHeatmap'); self.full_heatmap_btn.setObjectName('secondary_button'); self.full_heatmap_btn.clicked.connect(lambda: self.show_heatmap_dialog(full=True)); self.full_heatmap_btn.setEnabled(False)
        self.drill_btn = QPushButton('Drill Param'); self.drill_btn.setObjectName('secondary_button'); self.drill_btn.clicked.connect(self.show_param_drill_dialog); self.drill_btn.setEnabled(False)
        self.export_sens_btn = QPushButton('Export Sens'); self.export_sens_btn.setObjectName('secondary_button'); self.export_sens_btn.clicked.connect(self.export_sensitivity); self.export_sens_btn.setEnabled(False)
        # Heatmap axis selectors
        axis_box = QHBoxLayout()
        self.axis_x_combo = QComboBox(); self.axis_y_combo = QComboBox()
        self.axis_x_combo.setEnabled(False); self.axis_y_combo.setEnabled(False)
        axis_box.addWidget(QLabel('X:')); axis_box.addWidget(self.axis_x_combo); axis_box.addWidget(QLabel('Y:')); axis_box.addWidget(self.axis_y_combo)
        for lbl,w in [('Objective:',self.objective_combo),('Show top:',self.max_results_spin)]:
            right_l.addWidget(QLabel(lbl)); right_l.addWidget(w)
        right_l.addWidget(self.run_optimize_btn); right_l.addWidget(self.cancel_btn); right_l.addStretch()
        right_l.addWidget(self.apply_best_btn)
        right_l.addWidget(self.heatmap_btn)
        right_l.addWidget(self.full_heatmap_btn)
        right_l.addWidget(self.drill_btn)
        right_l.addWidget(self.export_sens_btn)
        right_l.addLayout(axis_box)
        settings_layout.addWidget(left); settings_layout.addWidget(right); settings_layout.addWidget(help_btn)
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        self.results_table = QTableWidget(); self._setup_results_table()
        # Summary box
        self.summary_box = QTextEdit(); self.summary_box.setReadOnly(True); self.summary_box.setMaximumHeight(90)
        dl_layout = QHBoxLayout(); dl_layout.addStretch(); self.download_btn = QPushButton('הורד CSV'); self.download_btn.setObjectName('secondary_button'); self.download_btn.clicked.connect(self.download_results); dl_layout.addWidget(self.download_btn)
        layout.addLayout(settings_layout); layout.addWidget(self.progress_bar); layout.addWidget(self.results_table,1); layout.addLayout(dl_layout)
        layout.addWidget(QLabel('Summary (Top Distribution):'))
        layout.addWidget(self.summary_box)
        self._last_results = []

    def _setup_results_table(self):
        headers=["Rank","Params","Score","Sharpe","SharpeStd","PosSharpe%","CAGR%","MaxDD%","WinRate%","Trades","Universe","Folds"]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.horizontalHeader().setStretchLastSection(True)

    def run_optimize(self):
        params={'ranges_json': self.ranges_edit.toPlainText(),
                'universe_limit': self.universe_limit_spin.value(),
                'folds': self.folds_spin.value(),
                'objective': self.objective_combo.currentText(),
                'max_results': self.max_results_spin.value(),
                'patience': self.patience_spin.value(),
                'stream': self.stream_chk.isChecked()}
        self.run_optimize_requested.emit(params)

    def start_optimize_worker(self, params, data_map):
        if self.worker_thread and self.worker_thread.isRunning(): return
        self.worker_thread = WorkerThread('optimize', params, data_map)
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.status_updated.connect(lambda s: None)
        self.worker_thread.results_ready.connect(self.update_results)
        try:
            self.worker_thread.full_results_ready.connect(self.on_full_results)
        except Exception:
            pass
        # Streamed intermediate results (if enabled)
        try:
            self.worker_thread.intermediate_results.connect(self.update_results)
        except Exception:
            pass
        self.worker_thread.error_occurred.connect(self.show_error)
        self.show_progress(True); self.worker_thread.start()

    def cancel_optimize(self):
        if self.worker_thread:
            self.worker_thread.cancel(); self.show_progress(False)

    def show_progress(self, show=True):
        self.progress_bar.setVisible(show); self.run_optimize_btn.setEnabled(not show); self.cancel_btn.setVisible(show)
        if show: self.progress_bar.setValue(0)

    def update_progress(self, v): self.progress_bar.setValue(v)

    # Help now handled by shared utility

    def update_results(self, results):
        if not isinstance(results, list):
            return
        self._last_results = results
        # Enable post-run actions if we have finalized list
        if results:
            self.apply_best_btn.setEnabled(True)
            self.heatmap_btn.setEnabled(True)
            self.drill_btn.setEnabled(True)
            self.export_sens_btn.setEnabled(True)
            # derive parameter keys for heatmap combos
            try:
                first = results[0].get('params') or {}
                if isinstance(first, dict):
                    names = list(first.keys())
                    self.axis_x_combo.clear(); self.axis_y_combo.clear()
                    for n in names:
                        self.axis_x_combo.addItem(n)
                        self.axis_y_combo.addItem(n)
                    if len(names) >= 2:
                        self.axis_x_combo.setCurrentIndex(0)
                        self.axis_y_combo.setCurrentIndex(1)
                    self.axis_x_combo.setEnabled(True); self.axis_y_combo.setEnabled(True)
            except Exception:
                pass
        # If this is a streaming update keep progress bar visible until final (heuristic: progress <100 keeps visible handled externally)
        if self.progress_bar.isVisible() and self.progress_bar.value() >= 100:
            self.show_progress(False)
        # Render table
        self.results_table.setRowCount(len(results))
        keys=['rank','params','score','sharpe','sharpe_std','pos_sharpe_pct','cagr','max_dd','win_rate','trades','universe','folds']
        for row,result in enumerate(results):
            for col,key in enumerate(keys):
                val=result.get(key,'')
                if key=='params':
                    text=str(val)[:60]+"..." if len(str(val))>60 else str(val)
                elif isinstance(val,(int,float)) and key not in ['rank','trades','universe','folds']:
                    text=f"{val:.3f}"
                else:
                    text=str(val)
                item=QTableWidgetItem(text)
                if key=='rank' and isinstance(val,int) and val<=3:
                    item.setBackground(QColor(255,248,220))
                elif key=='score' and isinstance(val,(int,float)) and val>1.0:
                    item.setBackground(QColor(198,246,213))
                self.results_table.setItem(row,col,item)
        self._update_summary_box()
        # (trimmed) may not be full universe; do not overwrite stored full dataset if already captured
        # Save run after final (heuristic: progress bar hidden OR rank present on first row)
        try:
            if results and results[0].get('rank'):
                from run_repo.run_repository import save_run
                # Attempt parse ranges json
                try:
                    ranges = json.loads(self.ranges_edit.toPlainText())
                except Exception:
                    ranges = {}
                save_run('optimize', {'ranges': ranges, 'objective': self.objective_combo.currentText()}, results[:self.max_results_spin.value()])
        except Exception:
            pass

    def on_full_results(self, all_results):
        # keeper for deeper sensitivity
        if isinstance(all_results, list) and all_results:
            self._full_results = all_results
            # enable full heatmap once we have entire set
            self.full_heatmap_btn.setEnabled(True)
            self._compute_param_importance()

    def _compute_param_importance(self):
        # Simple variance-based + correlation heuristic importance.
        try:
            import math
            if not hasattr(self, '_full_results') or not self._full_results:
                return
            rows = self._full_results
            # build column-wise lists
            param_keys = []
            for r in rows:
                p = r.get('params') or {}
                if isinstance(p, dict):
                    for k in p.keys():
                        if k not in param_keys:
                            param_keys.append(k)
            score_list = [float(r.get('score') or 0) for r in rows if isinstance(r.get('score'), (int,float))]
            if not score_list:
                return
            score_mean = sum(score_list)/len(score_list)
            score_var = sum((s-score_mean)**2 for s in score_list)/(len(score_list) or 1)
            importance_lines = []
            for pk in param_keys:
                vals = []
                paired_scores = []
                for r in rows:
                    p = r.get('params') or {}
                    if pk in p and isinstance(r.get('score'), (int,float)):
                        vals.append(p[pk]); paired_scores.append(float(r['score']))
                if len(vals) < 3:
                    continue
                # encode categorical / non-numeric to index if needed
                enc = []
                for v in vals:
                    if isinstance(v,(int,float)):
                        enc.append(float(v))
                    else:
                        try:
                            enc.append(float(hash(str(v)) % 1000))
                        except Exception:
                            enc.append(0.0)
                mean_v = sum(enc)/len(enc)
                var_v = sum((x-mean_v)**2 for x in enc)/(len(enc) or 1)
                # covariance
                cov = sum((enc[i]-mean_v)*(paired_scores[i]-score_mean) for i in range(len(enc)))/(len(enc) or 1)
                corr = cov / math.sqrt(var_v*score_var) if var_v>0 and score_var>0 else 0.0
                importance = abs(corr) * (var_v**0.5)
                importance_lines.append((pk, importance, corr))
            if importance_lines:
                importance_lines.sort(key=lambda x: -x[1])
                txt = 'Param Importance (heuristic)\n'
                for name, imp, corr in importance_lines[:15]:
                    txt += f"{name}: score_corr={corr:.3f} imp={imp:.3f}\n"
                # append to summary box (non-destructive)
                prev = self.summary_box.toPlainText()
                self.summary_box.setPlainText(prev + ('\n' if prev else '') + txt)
        except Exception:
            pass

    def _update_summary_box(self):
        if not self._last_results:
            self.summary_box.clear(); return
        top = self._last_results[:min(len(self._last_results), self.max_results_spin.value())]
        # Aggregate parameter distributions
        freq = {}
        for r in top:
            p = r.get('params') or {}
            if not isinstance(p, dict): continue
            for k,v in p.items():
                freq.setdefault(k, {})[v] = freq.setdefault(k, {}).get(v, 0) + 1
        lines = []
        for k,vals in freq.items():
            total = sum(vals.values()) or 1
            best_v = max(vals.items(), key=lambda x: x[1])
            lines.append(f"{k}: most={best_v[0]} ({best_v[1]}/{total}) unique={len(vals)}")
        self.summary_box.setPlainText('\n'.join(lines))

    def apply_best(self):
        if not self._last_results:
            QMessageBox.information(self,'אין תוצאות','אין תוצאה להחיל'); return
        best = self._last_results[0]
        params = best.get('params') if isinstance(best, dict) else None
        if not isinstance(params, dict):
            QMessageBox.warning(self,'שגיאה','מבנה פרמטרים לא תקין'); return
        self.apply_params_requested.emit(params)

    def show_heatmap_dialog(self, full=False):
        data_src = None
        if full and hasattr(self,'_full_results') and self._full_results:
            data_src = self._full_results
        else:
            data_src = self._last_results
        if not data_src:
            return
        x_key = self.axis_x_combo.currentText(); y_key = self.axis_y_combo.currentText()
        if not x_key or not y_key or x_key==y_key:
            QMessageBox.warning(self,'Heatmap','בחר שני פרמטרים שונים'); return
        # Build matrix (score average)
        matrix = {}
        for r in data_src:
            p = r.get('params') or {}
            if x_key in p and y_key in p:
                xv = p[x_key]; yv = p[y_key]
                matrix.setdefault(xv, {}).setdefault(yv, []).append(r.get('score',0))
        if not matrix:
            QMessageBox.information(self,'Heatmap','אין נתונים זמינים'); return
        xs = sorted(matrix.keys())
        ys = sorted({y for d in matrix.values() for y in d.keys()})
        # Create dialog
        dlg = QDialog(self); dlg.setWindowTitle(f"Heatmap {'FULL ' if full else ''}{x_key} vs {y_key}")
        gl = QGridLayout(dlg)
        # headers
        gl.addWidget(QLabel(f"{x_key} \\ {y_key}"),0,0)
        for j,yv in enumerate(ys, start=1):
            gl.addWidget(QLabel(str(yv)),0,j)
        # compute global min/max for coloring
        all_scores = []
        for xv in xs:
            for yv in ys:
                vals = matrix.get(xv, {}).get(yv, [])
                if vals:
                    all_scores.append(sum(vals)/len(vals))
        if not all_scores:
            dlg.show(); return
        mn, mx = min(all_scores), max(all_scores)
        rng = (mx - mn) or 1.0
        for i,xv in enumerate(xs, start=1):
            gl.addWidget(QLabel(str(xv)), i,0)
            for j,yv in enumerate(ys, start=1):
                vals = matrix.get(xv, {}).get(yv, [])
                if vals:
                    sc = sum(vals)/len(vals)
                else:
                    sc = 0.0
                lab = QLabel(f"{sc:.3f}")
                # color intensity
                norm = (sc - mn)/rng
                col = int(255 - norm*155)  # lighter for low
                lab.setStyleSheet(f"background-color: rgb({255-col},{255},{200}); padding:3px;")
                gl.addWidget(lab,i,j)
        dlg.resize(480,320)
        dlg.exec()

    def show_param_drill_dialog(self):
        # Drilldown distribution of single parameter vs score
        if not (hasattr(self,'_full_results') and self._full_results):
            QMessageBox.information(self,'Drill','אין תוצאות מלאות'); return
        # choose param from axis_x as default
        param = self.axis_x_combo.currentText()
        if not param:
            QMessageBox.information(self,'Drill','בחר פרמטר'); return
        # aggregate
        buckets = {}
        for r in self._full_results:
            p = r.get('params') or {}
            if param in p:
                buckets.setdefault(p[param], []).append(r.get('score',0))
        if not buckets:
            QMessageBox.information(self,'Drill','אין נתונים'); return
        # compute stats
        rows = []
        for k, vals in buckets.items():
            if vals:
                avg = sum(vals)/len(vals)
                rows.append((k, avg, len(vals)))
        rows.sort(key=lambda x: -x[1])
        dlg = QDialog(self); dlg.setWindowTitle(f"Drill {param}")
        gl = QGridLayout(dlg)
        gl.addWidget(QLabel(f"Value"),0,0); gl.addWidget(QLabel("Mean Score"),0,1); gl.addWidget(QLabel("Count"),0,2)
        for i,(k,avg,cnt) in enumerate(rows, start=1):
            gl.addWidget(QLabel(str(k)),i,0)
            gl.addWidget(QLabel(f"{avg:.4f}"),i,1)
            gl.addWidget(QLabel(str(cnt)),i,2)
        dlg.resize(360, min(500, 40 + 22*len(rows)))
        dlg.exec()

    def export_sensitivity(self):
        if not (hasattr(self,'_full_results') and self._full_results):
            QMessageBox.information(self,'Export','אין תוצאות מלאות'); return
        file_path,_=QFileDialog.getSaveFileName(self,'שמור קובץ','sensitivity.csv','CSV Files (*.csv)')
        if not file_path:
            return
        # param,value,mean_score,count
        agg = {}
        for r in self._full_results:
            p = r.get('params') or {}
            sc = r.get('score',0)
            for k,v in (p.items() if isinstance(p,dict) else []):
                agg.setdefault(k, {}).setdefault(v, []).append(sc)
        import csv
        with open(file_path,'w',newline='',encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['param','value','mean_score','count'])
            for k, mp in agg.items():
                for v, lst in mp.items():
                    if lst:
                        w.writerow([k,v,sum(lst)/len(lst),len(lst)])
        QMessageBox.information(self,'הצלחה',f'נשמר: {file_path}')

    def show_error(self, error):
        self.show_progress(False); QMessageBox.critical(self,'שגיאה',f'שגיאה באופטימיזציה: {error}')

    def download_results(self):
        if self.results_table.rowCount()==0:
            QMessageBox.information(self,'מידע','אין תוצאות להורדה'); return
        file_path,_=QFileDialog.getSaveFileName(self,'שמור קובץ','optimize_results.csv','CSV Files (*.csv)')
        if file_path:
            with open(file_path,'w',encoding='utf-8') as f:
                headers=[self.results_table.horizontalHeaderItem(c).text() for c in range(self.results_table.columnCount())]
                f.write(','.join(headers)+'\n')
                for r in range(self.results_table.rowCount()):
                    row_data=[]
                    for c in range(self.results_table.columnCount()):
                        it=self.results_table.item(r,c); row_data.append(it.text() if it else '')
                    f.write(','.join(row_data)+'\n')
            QMessageBox.information(self,'הצלחה',f'הקובץ נשמר: {file_path}')
