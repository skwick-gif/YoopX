from PySide6.QtCore import QThread, Signal
import json, datetime
from ui.shared.logging_utils import write_log

class WorkerThread(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    results_ready = Signal(object)
    intermediate_results = Signal(object)
    full_results_ready = Signal(object)
    error_occurred = Signal(str)
    finished_work = Signal()

    def __init__(self, operation_type, params, data_map):
        super().__init__()
        self.operation_type = operation_type
        self.params = params
        self.data_map = data_map
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            if self.operation_type == 'scan':
                self.run_scan()
            elif self.operation_type == 'backtest':
                self.run_backtest()
            elif self.operation_type == 'optimize':
                self.run_optimize()
            elif self.operation_type == 'walkforward':
                self.run_walkforward()
            elif self.operation_type == 'auto_discovery':
                self.run_auto_discovery()
        except Exception as e:
            try:
                self.error_occurred.emit(str(e))
            except Exception:
                pass
        finally:
            try:
                self.finished_work.emit()
            except Exception:
                pass

    # --- Extracted logic from original file (kept minimal to avoid circular imports) ---
    def run_scan(self):
        results = []
        # Attempt to load requested ML model (optional)
        ml_model = None
        selected_model = None
        ml_min_prob = 0.0
        # dynamic thresholds from active snapshot
        per_horizon_thresholds = {}
        global_threshold_override = None
        if isinstance(self.params, dict):
            selected_model = (self.params.get('ml_model') or 'rf').lower().strip()
            try:
                ml_min_prob = float(self.params.get('ml_min_prob', 0.0) or 0.0)
            except Exception:
                ml_min_prob = 0.0
            # load active snapshot thresholds if available
            try:
                active_snap = self.params.get('active_snapshot')
                if active_snap and isinstance(active_snap,str):
                    import os, json as _json
                    thr_path = os.path.join(active_snap,'thresholds.json')
                    if os.path.exists(thr_path):
                        with open(thr_path,'r',encoding='utf-8') as f:
                            thr_data = _json.load(f)
                        global_threshold_override = thr_data.get('global') if isinstance(thr_data.get('global'), (int,float)) else None
                        ph = thr_data.get('per_horizon') or {}
                        for k,v in ph.items():
                            try:
                                if isinstance(v,(int,float)):
                                    per_horizon_thresholds[int(k)] = float(v)
                            except Exception:
                                pass
            except Exception:
                pass
        # optional horizon selection for multi-horizon models
        use_horizon = None
        try:
            if isinstance(self.params, dict):
                uh = self.params.get('use_horizon')
                if uh:
                    use_horizon = int(uh)
        except Exception:
            use_horizon = None
        try:
            from ml.train_model import load_model, DEFAULT_MODEL_PATH, XGB_MODEL_PATH, LGBM_MODEL_PATH, predict_latest
            if selected_model == 'ensemble':
                # attempt to load all available base models + ensemble config
                base_paths = [('rf',DEFAULT_MODEL_PATH), ('xgb',XGB_MODEL_PATH), ('lgbm',LGBM_MODEL_PATH)]
                ensemble_models = []
                model_names = []
                for name, p in base_paths:
                    m = load_model(p)
                    if m is not None:
                        ensemble_models.append(m); model_names.append(name)
                # load optional ensemble.json for weights / meta model
                ens_cfg = {}
                try:
                    import os, json as _json
                    cfg_path = os.path.join('ml','ensemble.json')
                    if os.path.exists(cfg_path):
                        with open(cfg_path,'r',encoding='utf-8') as cf:
                            ens_cfg = _json.load(cf) or {}
                except Exception:
                    ens_cfg = {}
                if ensemble_models:
                    # detect stacking availability (we stored only meta_auc so meta model may not be serialized; placeholder for future)
                    ml_model = {'type':'ensemble','models': ensemble_models, 'names': model_names, 'cfg': ens_cfg}
                else:
                    ml_model = None
            else:
                model_path = DEFAULT_MODEL_PATH
                if selected_model == 'xgb':
                    model_path = XGB_MODEL_PATH
                elif selected_model == 'lgbm':
                    model_path = LGBM_MODEL_PATH
                ml_model = load_model(model_path)
            if ml_model is None and selected_model:
                try:
                    self.status_updated.emit(f"ML model '{selected_model}' not found – continuing without ML")
                except Exception:
                    pass
        except Exception:
            ml_model = None
        symbols = list(self.data_map.keys()) if self.data_map else []
        total = len(symbols) if symbols else 0
        # Extract numeric filter parameters (None means ignore)
        try:
            self._min_price = float(self.params.get('min_price')) if self.params.get('min_price') is not None else None
        except Exception: self._min_price = None
        try:
            self._max_price = float(self.params.get('max_price')) if self.params.get('max_price') is not None else None
        except Exception: self._max_price = None
        try:
            self._min_atr = float(self.params.get('min_atr')) if self.params.get('min_atr') is not None else None
        except Exception: self._min_atr = None
        try:
            self._max_atr = float(self.params.get('max_atr')) if self.params.get('max_atr') is not None else None
        except Exception: self._max_atr = None
        try:
            self._max_age = int(self.params.get('max_age')) if self.params.get('max_age') is not None else None
        except Exception: self._max_age = None
        try:
            import backend
        except Exception:
            self.error_occurred.emit("Missing backend.py for scan")
            self.results_ready.emit([])
            return
        # Prepare strategy list (single or all)
        strategy_param = None
        custom_list = None
        try:
            if isinstance(self.params, dict):
                # new multi-select list
                if isinstance(self.params.get('scan_strategies'), list) and self.params.get('scan_strategies'):
                    custom_list = [str(s) for s in self.params.get('scan_strategies') if isinstance(s, str)]
                strategy_param = self.params.get('scan_strategy') or self.params.get('strategy')
        except Exception:
            strategy_param = None
        all_strategies_list = []
        if custom_list is not None:
            all_strategies_list = custom_list[:]
        elif strategy_param == '__ALL__':
            try:
                all_strategies_list = list(getattr(backend, 'STRAT_MAP', {}).keys()) or ['Donchian Breakout','SMA Cross','EMA Cross','MACD Trend','RSI(2) @ Bollinger']
            except Exception:
                all_strategies_list = ['Donchian Breakout','SMA Cross','EMA Cross','MACD Trend','RSI(2) @ Bollinger']
        # Debug: report symbol count
        try:
            self.status_updated.emit(f"Preparing scan: {len(symbols)} symbols")
            # Sample first few symbols for diagnostics
            sample_syms = symbols[:5]
            self.status_updated.emit(f"Sample symbols: {','.join(sample_syms)}")
        except Exception:
            pass
        processed_symbols = 0
        per_symbol_errors = 0
        for i, symbol in enumerate(symbols):
            if self.is_cancelled:
                break
            df = self.data_map.get(symbol)
            if df is None or len(df) < 20:
                results.append({'symbol': symbol,'strategy':'','pass':'ERROR','signal':'ERROR','age':0,'price':'','atr':'','rr':'ERROR','target':'','patterns':'','ml_prob':'','score':'','drift':'','error':'insufficient data'})
                continue
            processed_symbols += 1
            strategies_to_run = []
            if all_strategies_list:
                strategies_to_run = all_strategies_list[:]
            else:
                s = strategy_param or 'Donchian Breakout'
                strategies_to_run = [s]
            strat_param_map = {}
            try:
                if isinstance(self.params, dict) and isinstance(self.params.get('strategy_param_map'), dict):
                    strat_param_map = self.params.get('strategy_param_map')
            except Exception:
                strat_param_map = {}
            for strategy in strategies_to_run:
                try:
                    # -------- Strategy signal --------
                    scan_params = {}
                    if isinstance(self.params, dict):
                        for k in ('fast','slow','upper','lower','ema_trend','rsi_p','rsi_buy','bb_p','bb_k','signal'):
                            if k in self.params:
                                scan_params[k] = self.params[k]
                    if strategy in strat_param_map:
                        for k,v in (strat_param_map.get(strategy) or {}).items():
                            scan_params[k] = v
                    now, age, price_at_signal = backend.scan_signal(df, strategy, scan_params)
                    patterns_txt = (self.params.get('patterns','') or '') if isinstance(self.params, dict) else ''
                    selected = [p.strip().upper() for p in patterns_txt.split(',') if p.strip()]
                    try:
                        detected = backend.detect_patterns(df, int(self.params.get('lookback',30)), selected)
                    except Exception:
                        detected = []
                    # -------- ATR / RR computation --------
                    last_atr = None; target_price_calc = None; rr_val = None
                    try:
                        atr_series = backend.atr(df)
                        if atr_series is not None and len(atr_series) > 0:
                            last_atr = float(atr_series.iloc[-1])
                    except Exception:
                        last_atr = None
                    try:
                        if last_atr and price_at_signal:
                            p = float(price_at_signal)
                            if now and str(now).lower().startswith('buy'):
                                target_price_calc = p + 2*last_atr; stop = p - last_atr
                            elif now and str(now).lower().startswith('sell'):
                                target_price_calc = p - 2*last_atr; stop = p + last_atr
                            else:
                                target_price_calc = p + 2*last_atr; stop = p - last_atr
                            rr_val = abs((target_price_calc - p) / (p - stop)) if (p - stop) != 0 else None
                    except Exception:
                        rr_val = None
                    try: rr_num = float(rr_val) if rr_val is not None else 0.0
                    except Exception: rr_num = 0.0
                    min_rr = float(self.params.get('min_rr',0.0)) if isinstance(self.params, dict) else 0.0
                    passed = 'Pass' if rr_num >= min_rr and now and now != 'Hold' else 'Fail'
                    # -------- ML probability & horizons --------
                    ml_prob = None; horizon_probs = {}; latest_features = None; drift_val = ''
                    try:
                        if ml_model is not None:
                            from ml.train_model import predict_latest
                            if isinstance(ml_model, dict) and ml_model.get('type') == 'ensemble':
                                ens_probs = []
                                sub_models = ml_model.get('models') or []
                                for sub in sub_models:
                                    try:
                                        p = predict_latest(df, sub, horizon=use_horizon)
                                        ens_probs.append(p if isinstance(p,(int,float)) else None)
                                    except Exception:
                                        ens_probs.append(None)
                                weights = None
                                try:
                                    cfg = ml_model.get('cfg') or {}
                                    raw_w = cfg.get('weights')
                                    if isinstance(raw_w, dict) and ml_model.get('names'):
                                        weights = [raw_w[n] for n in ml_model.get('names') if n in raw_w and isinstance(raw_w[n], (int,float))]
                                    if weights and abs(sum(weights)-1.0) > 1e-5:
                                        s = sum(weights); weights = [w/s for w in weights]
                                except Exception:
                                    weights = None
                                if weights and len(weights)==len(ens_probs) and all(isinstance(p,(int,float)) for p in ens_probs):
                                    try: ml_prob = float(sum(p*w for p,w in zip(ens_probs,weights)))
                                    except Exception: pass
                                else:
                                    vals = [p for p in ens_probs if isinstance(p,(int,float))]
                                    if vals: ml_prob = float(sum(vals)/len(vals))
                            else:
                                ml_prob = predict_latest(df, ml_model, horizon=use_horizon)
                    except Exception:
                        ml_prob = None
                    # Drift
                    try:
                        from ml.feature_engineering import compute_features
                        stats = ml_model.get('feature_stats') if isinstance(ml_model, dict) else None
                        if stats:
                            feats_row = compute_features(df)
                            if not feats_row.empty:
                                feats_row = feats_row.tail(1)
                                latest_features = feats_row.to_dict(orient='records')[0]
                                z_sum=0.0; count=0
                                for f_name, st in stats.items():
                                    if f_name in feats_row.columns:
                                        try:
                                            val = float(feats_row[f_name].iloc[-1])
                                            mean = st.get('mean'); std = st.get('std') or 0.0
                                            if std and isinstance(mean,(int,float)):
                                                z_sum += abs((val-mean)/std); count+=1
                                        except Exception: pass
                                if count>0: drift_val = round(z_sum/count,3)
                    except Exception:
                        drift_val = ''
                    # Feature store
                    try:
                        if latest_features:
                            from ml.feature_store import put_features
                            put_features(symbol, latest_features)
                    except Exception:
                        pass
                    # Threshold gating
                    try:
                        eff_thr = None
                        if use_horizon is not None and use_horizon in per_horizon_thresholds:
                            eff_thr = per_horizon_thresholds.get(use_horizon)
                        elif global_threshold_override is not None:
                            eff_thr = global_threshold_override
                        else:
                            eff_thr = ml_min_prob if ml_min_prob > 0 else None
                        if ml_prob is not None and eff_thr is not None and ml_prob < eff_thr:
                            passed = 'Fail'
                    except Exception:
                        pass
                    # Scoring
                    try:
                        prob_comp = float(ml_prob) if isinstance(ml_prob,(int,float)) else 0.5
                        rr_norm = min(float(rr_val)/3.0,1.0) if rr_val is not None else 0.0
                        a = float(age) if age is not None else 99
                        freshness = 0.0 if a >= 10 else max(0.0,1.0-(a/10.0))
                        pattern_ct = len(detected) if detected else 0
                        pattern_comp = min(pattern_ct/3.0,1.0)
                        formula = (self.params.get('score_formula') or 'weighted').lower() if isinstance(self.params, dict) else 'weighted'
                        W_PROB = float(self.params.get('w_prob',0.55)) if isinstance(self.params, dict) else 0.55
                        W_RR = float(self.params.get('w_rr',0.25)) if isinstance(self.params, dict) else 0.25
                        W_FRESH = float(self.params.get('w_fresh',0.15)) if isinstance(self.params, dict) else 0.15
                        W_PATTERN = float(self.params.get('w_pattern',0.05)) if isinstance(self.params, dict) else 0.05
                        w_sum = W_PROB+W_RR+W_FRESH+W_PATTERN
                        if w_sum>0: W_PROB,W_RR,W_FRESH,W_PATTERN = [w/w_sum for w in (W_PROB,W_RR,W_FRESH,W_PATTERN)]
                        if formula=='geometric':
                            import math
                            comps=[max(prob_comp,1e-6),max(rr_norm,1e-6),max(freshness,1e-6),max(pattern_comp,1e-6)]
                            score_val=1.0
                            for cval,w in zip(comps,(W_PROB,W_RR,W_FRESH,W_PATTERN)):
                                score_val*=cval**w
                        else:
                            score_val = W_PROB*prob_comp + W_RR*rr_norm + W_FRESH*freshness + W_PATTERN*pattern_comp
                    except Exception:
                        score_val = None
                    # Derived expected columns
                    exp_target = target_price_calc
                    try:
                        exp_move_pct = ((exp_target - float(price_at_signal))/float(price_at_signal))*100.0 if exp_target and price_at_signal else None
                    except Exception:
                        exp_move_pct = None
                    exp_rr = rr_val
                    row_obj = {
                        'symbol': symbol,
                        'strategy': strategy,
                        'pass': passed,
                        'signal': now,
                        'age': int(age) if age is not None else 0,
                        'price': float(price_at_signal) if price_at_signal is not None else '',
                        'atr': round(last_atr,4) if last_atr is not None else '',
                        'rr': round(rr_num,3),
                        'target': round(target_price_calc,4) if target_price_calc is not None else '',
                        'exp_target': round(exp_target,4) if isinstance(exp_target,(int,float)) else '',
                        'exp_move_pct': round(exp_move_pct,2) if isinstance(exp_move_pct,(int,float)) else '',
                        'exp_rr': round(exp_rr,3) if isinstance(exp_rr,(int,float)) else '',
                        'patterns': ','.join(detected) if detected else '',
                        'ml_prob': round(ml_prob,4) if isinstance(ml_prob,(int,float)) else '',
                        'score': round(score_val,4) if isinstance(score_val,(int,float)) else '',
                        'drift': drift_val,
                        '_features': latest_features or {},
                    }
                    # Filters
                    try:
                        if self._min_price is not None and isinstance(row_obj.get('price'), (int,float)) and row_obj['price'] < self._min_price: continue
                        if self._max_price is not None and isinstance(row_obj.get('price'), (int,float)) and row_obj['price'] > self._max_price: continue
                        if self._min_atr is not None and isinstance(last_atr,(int,float)) and last_atr < self._min_atr: continue
                        if self._max_atr is not None and isinstance(last_atr,(int,float)) and last_atr > self._max_atr: continue
                        if self._max_age is not None and isinstance(age,(int,float)) and age > self._max_age: continue
                    except Exception:
                        pass
                    # Horizon probs (if computed earlier when multi horizon supported)
                    if horizon_probs:
                        for h,pv in horizon_probs.items():
                            if isinstance(pv,(int,float)):
                                row_obj[f'prob_h_{h}']=round(float(pv),4)
                    results.append(row_obj)
                except Exception as e:
                    per_symbol_errors += 1
                    results.append({'symbol': symbol,'strategy': strategy,'pass':'ERROR','signal':'ERROR','age':0,'price':'','atr':'','rr':'ERROR','target':'','patterns':'','ml_prob':'','score':'','drift':'','error':str(e)})
            try:
                self.progress_updated.emit(int((i+1)/max(1,total)*100))
                self.status_updated.emit(f"סריקה: {i+1}/{total} ({symbol})")
            except Exception:
                pass
        self.results_ready.emit(results)
        # Post-scan summary diagnostics
        try:
            self.status_updated.emit(f"Scan done: rows={len(results)} symbols_with_data={processed_symbols} errors={per_symbol_errors}")
        except Exception:
            pass
        # Emit aggregate drift info via status_updated for lifecycle automation (mean of numeric drift values)
        try:
            drift_vals = []
            for r in results:
                dv = r.get('drift')
                if isinstance(dv,(int,float)):
                    drift_vals.append(float(dv))
            if drift_vals:
                mean_drift = round(sum(drift_vals)/len(drift_vals),4)
                self.status_updated.emit(f"DriftAvg={mean_drift}")
        except Exception:
            pass
        # --- Prediction logging for live performance tracking ---
        try:
            import os, uuid, datetime as _dt
            os.makedirs('logs', exist_ok=True)
            log_path = os.path.join('logs','predictions.jsonl')
            active_snapshot = None
            try:
                if isinstance(self.params, dict):
                    active_snapshot = self.params.get('active_snapshot')
            except Exception:
                active_snapshot = None
            with open(log_path,'a',encoding='utf-8') as lf:
                now_iso = _dt.datetime.utcnow().isoformat()+'Z'
                for rec in results:
                    try:
                        if not isinstance(rec.get('ml_prob'), (int,float)):
                            continue
                        symbol = rec.get('symbol')
                        # basic horizon probabilities
                        prob_h = {k.replace('prob_h_',''): rec[k] for k in rec.keys() if k.startswith('prob_h_') and isinstance(rec[k], (int,float))}
                        # derive horizons list
                        horizons_list = sorted([int(h) for h in prob_h.keys() if str(h).isdigit()]) if prob_h else []
                        # attempt last bar date from data map via self.data_map
                        last_date_str = ''
                        try:
                            df = self.data_map.get(symbol)
                            if df is not None and len(df) > 0:
                                idx_last = df.index[-1]
                                last_date_str = str(idx_last)[:10]
                        except Exception:
                            pass
                        base_price = rec.get('price') if isinstance(rec.get('price'), (int,float)) else None
                        future_due = {}
                        if horizons_list and last_date_str:
                            try:
                                import pandas as _pd
                                base_date = _pd.to_datetime(last_date_str)
                                for h in horizons_list:
                                    future_due[str(h)] = (base_date + _pd.Timedelta(days=int(h))).strftime('%Y-%m-%d')
                            except Exception:
                                pass
                        entry = {
                            'id': str(uuid.uuid4()),
                            'ts': now_iso,
                            'model_snapshot': active_snapshot,
                            'symbol': symbol,
                            'prob': rec.get('ml_prob'),
                            'prob_h': prob_h or None,
                            'horizons': horizons_list or None,
                            'price': base_price,
                            'bar_date': last_date_str,
                            'future_due': future_due or None
                        }
                        lf.write(json.dumps(entry, ensure_ascii=False) + '\n')
                    except Exception:
                        continue
        except Exception:
            pass

    def run_backtest(self):
        import traceback
        results = []
        symbols = list(self.data_map.keys()) if self.data_map else ['AAPL', 'MSFT', 'GOOGL']
        total = len(symbols)
        try:
            import backend
        except Exception:
            self.error_occurred.emit("לא ניתן לייבא backend.py")
            return
        # --- Benchmark preparation (best-effort) ---
        benchmark_df = None
        benchmark_symbol = None
        try:
            # preference order: '^GSPC', 'SPY', 'QQQ'
            for cand in ['^GSPC','SPY','QQQ']:
                for k in self.data_map.keys():
                    if k.upper() == cand.upper():
                        benchmark_symbol = k
                        benchmark_df = self.data_map.get(k)
                        break
                if benchmark_df is not None:
                    break
        except Exception:
            benchmark_df = None
        def _benchmark_period_stats(df_local):
            """Compute benchmark cumulative return subset matching df_local index span."""
            if benchmark_df is None or df_local is None or len(df_local) < 2:
                return None
            try:
                idx0 = df_local.index[0]; idx1 = df_local.index[-1]
                sub = benchmark_df.loc[(benchmark_df.index >= idx0) & (benchmark_df.index <= idx1)]
                if len(sub) < 2:
                    return None
                # detect close column
                ccol = None
                for c in sub.columns:
                    if 'close' in c.lower():
                        ccol = c; break
                if not ccol:
                    return None
                import numpy as _np
                prices = sub[ccol].dropna()
                if len(prices) < 2:
                    return None
                ret = (float(prices.iloc[-1]) / float(prices.iloc[0])) - 1.0
                # simple daily returns std (tracking error piece baseline)
                daily = prices.pct_change().dropna()
                if len(daily) > 1:
                    vol = float(daily.std())
                else:
                    vol = None
                return {'bench_return': ret, 'bench_vol': vol}
            except Exception:
                return None
        try:
            params = self.params if isinstance(self.params, dict) else {}
            param_syms_txt = (params.get('symbols') or '').strip()
            param_syms = [s.strip().upper() for s in param_syms_txt.split(',') if s.strip()] if param_syms_txt else []
            universe_limit = int(params.get('universe_limit', 0) or 0)
            start_date = params.get('start_date') or None
            end_date = params.get('end_date') or None
            use_adj = bool(params.get('use_adj', True))
            min_volume = float(params.get('min_volume', 0) or 0)
            min_close = float(params.get('min_close', 0) or 0)
            min_trades = int(params.get('min_trades', 0) or 0)
        except Exception:
            param_syms = []
            universe_limit = 0
            start_date = end_date = None
            use_adj = True
            min_volume = 0.0
            min_close = 0.0
            min_trades = 0
        try:
            original_symbols = list(symbols)
            if param_syms:
                symbols = [s for s in symbols if s.upper() in param_syms]
            if universe_limit and universe_limit > 0:
                symbols = symbols[:universe_limit]
        except Exception:
            original_symbols = list(symbols)
        try:
            ts = datetime.datetime.utcnow().isoformat() + 'Z'
            write_log({'ts': ts, 'event': 'filter_summary', 'requested_symbols': param_syms, 'universe_limit': universe_limit, 'before_count': len(original_symbols), 'after_count': len(symbols)})
            excluded = [s for s in original_symbols if s not in symbols]
            for s in excluded:
                reason = 'excluded_by_symbol_filter' if param_syms and s.upper() not in param_syms else 'excluded_by_universe_limit'
                write_log({'ts': ts, 'event': 'symbol_excluded', 'symbol': s, 'reason': reason})
        except Exception:
            pass
        strategies = self.params.get('strategies') if isinstance(self.params, dict) else None
        if not strategies:
            strategies = list(getattr(backend, 'STRAT_MAP', {}).keys())
        start_cash = self.params.get('start_cash', 10000)
        commission = self.params.get('commission', 0.0005)
        slippage = self.params.get('slippage', 0.0005)
        for i, symbol in enumerate(symbols):
            if self.is_cancelled:
                break
            df = self.data_map[symbol]
            symbol_results = []
            for strat_name in strategies:
                try:
                    df_local = df.copy() if df is not None else df
                    try:
                        import pandas as _pd
                        if df_local is not None and start_date:
                            try:
                                df_local = df_local[df_local.index >= _pd.to_datetime(start_date)]
                            except Exception:
                                if 'date' in (c.lower() for c in df_local.columns):
                                    df_local = df_local[_pd.to_datetime(df_local['date']) >= _pd.to_datetime(start_date)]
                        if df_local is not None and end_date:
                            try:
                                df_local = df_local[df_local.index <= _pd.to_datetime(end_date)]
                            except Exception:
                                if 'date' in (c.lower() for c in df_local.columns):
                                    df_local = df_local[_pd.to_datetime(df_local['date']) <= _pd.to_datetime(end_date)]
                    except Exception:
                        pass
                    try:
                        if df_local is not None and min_volume > 0:
                            vol_col = None
                            for c in df_local.columns:
                                if c.lower() in ('volume', 'vol'):
                                    vol_col = c
                                    break
                            if vol_col:
                                avg_vol = float(df_local[vol_col].dropna().mean()) if len(df_local) > 0 else 0.0
                                if avg_vol < min_volume:
                                    continue
                    except Exception:
                        pass
                    try:
                        if df_local is not None and min_close > 0:
                            close_col = None
                            for c in df_local.columns:
                                if 'close' in c.lower():
                                    close_col = c
                                    break
                            if close_col and len(df_local) > 0:
                                last_close = float(df_local[close_col].dropna().iloc[-1])
                                if last_close < min_close:
                                    continue
                    except Exception:
                        pass
                    res = backend.run_backtest(
                        df_local,
                        strat_name,
                        {},
                        start_cash,
                        commission,
                        slippage,
                        1.0,
                        0.05,
                        None,
                        False,
                    )
                    if isinstance(res, tuple) and len(res) > 1:
                        figs_res = res[0] or []
                        summary = res[1] or {}
                    elif isinstance(res, dict):
                        summary = res
                    else:
                        summary = {}
                    _l = {k.lower(): v for k, v in summary.items()}
                    def sv(*cands, default=0):
                        for c in cands:
                            if c in _l:
                                return _l[c]
                        return default
                    result = {
                        'symbol': symbol,
                        'strategy': strat_name,
                        'final_value': sv('final_value','finalvalue','final_value','finalvalue', default=0),
                        'sharpe': sv('sharpe','sharperatio', default=0),
                        'max_dd': sv('max_dd','maxdd','maxdd_pct','maxdd_pct', default=0),
                        'win_rate': sv('win_rate','winrate','winrate_pct','win_rate_pct', default=0),
                        'trades': sv('trades','total_trades','trades_total', default=0),
                        'cagr': sv('cagr','cagr_pct','cagrpct', default=0)
                    }
                    # --- Benchmark relative metrics ---
                    try:
                        bm_stats = _benchmark_period_stats(df_local)
                        if bm_stats and isinstance(result.get('cagr'), (int,float)):
                            # derive strategy total return approximation if not given: use final_value vs start_cash
                            strat_ret = None
                            try:
                                fv = float(result.get('final_value') or 0)
                                sc = float(start_cash)
                                if sc > 0:
                                    strat_ret = (fv / sc) - 1.0
                            except Exception:
                                strat_ret = None
                            bench_ret = bm_stats.get('bench_return')
                            if strat_ret is not None and isinstance(bench_ret,(int,float)):
                                alpha = strat_ret - bench_ret
                                result['alpha'] = alpha
                            else:
                                result['alpha'] = None
                            # crude information ratio: sharpe - bench_sharpe estimate fallback -> (alpha / bench_vol) if bench_vol
                            if result.get('alpha') is not None and bm_stats.get('bench_vol'):
                                try:
                                    ir = float(result['alpha']) / float(bm_stats['bench_vol']) if bm_stats['bench_vol'] else None
                                except Exception:
                                    ir = None
                                result['info_ratio'] = ir
                            else:
                                result['info_ratio'] = None
                            result['benchmark'] = benchmark_symbol or ''
                        else:
                            result['alpha'] = None; result['info_ratio'] = None
                            if benchmark_symbol:
                                result['benchmark'] = benchmark_symbol
                    except Exception:
                        pass
                    try:
                        trades_val = float(result.get('trades') or 0)
                        if min_trades > 0 and trades_val < min_trades:
                            continue
                    except Exception:
                        pass
                    if 'figs_res' in locals() and figs_res:
                        result['figs'] = figs_res
                    if isinstance(summary, dict):
                        if 'trade_list' in summary and isinstance(summary['trade_list'], list):
                            result['trade_details'] = summary['trade_list']
                        elif 'trade_analyzer' in summary:
                            result['trade_details'] = summary['trade_analyzer']
                        else:
                            for k in summary.keys():
                                if k.lower().startswith('trade'):
                                    result['trade_details'] = summary.get(k)
                                    break
                    symbol_results.append(result)
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    symbol_results.append({'symbol': symbol,'strategy': strat_name,'final_value': 'ERROR','sharpe': 'ERROR','max_dd': 'ERROR','win_rate': 'ERROR','trades': 'ERROR','cagr': 'ERROR','error': f"{e}\n{tb}"})
            passed_strategies = [r['strategy'] for r in symbol_results if isinstance(r.get('sharpe', 0), (int, float)) and r.get('sharpe', 0) > 0.5]
            for r in symbol_results:
                r['passed_strategies'] = ', '.join(passed_strategies) if passed_strategies else ''
                results.append(r)
            self.progress_updated.emit(int((i+1)/total*100))
        self.results_ready.emit(results)

    def run_optimize(self):
        results = []
        try:
            try:
                import backend
            except Exception:
                try:
                    self.error_occurred.emit("Cannot import backend.py — optimization requires backend module")
                except Exception:
                    pass
                self.results_ready.emit([])
                return
            ranges_json = None
            if isinstance(self.params, dict):
                ranges_json = self.params.get('ranges_json') or self.params.get('ranges')
            if not ranges_json:
                self.results_ready.emit([])
                return
            if isinstance(ranges_json, str):
                try:
                    ranges = json.loads(ranges_json)
                except Exception:
                    ranges = {}
            elif isinstance(ranges_json, dict):
                ranges = ranges_json
            else:
                ranges = {}
            grid = backend.param_grid_from_ranges(ranges)
            if not grid:
                self.results_ready.emit([])
                return
            symbols = list(self.data_map.keys()) if self.data_map else []
            universe_limit = int(self.params.get('universe_limit', 50)) if isinstance(self.params, dict) else 50
            if universe_limit > 0:
                symbols = symbols[:universe_limit]
            objective = self.params.get('objective', 'Sharpe') if isinstance(self.params, dict) else 'Sharpe'
            folds = int(self.params.get('folds', 1) or 1)
            stream = bool(self.params.get('stream')) if isinstance(self.params, dict) else False
            patience = int(self.params.get('patience', 0) or 0)
            best_score_so_far = None
            epochs_without_improve = 0
            total = len(grid)
            for i, params in enumerate(grid):
                if self.is_cancelled:
                    break
                sharpe_list = []
                obj_scores = []
                cagr_list = []
                maxdd_list = []
                win_list = []
                trades_list = []
                # simple K-fold style re-sampling across universe slices to estimate stability
                # fold implementation: stride partitions of symbols
                if folds <= 1:
                    fold_slices = [symbols]
                else:
                    fold_slices = []
                    for f in range(folds):
                        fold_slices.append(symbols[f::folds])
                for f_slice in fold_slices:
                    agg = {'Sharpe':0.0, 'CAGR_pct':0.0, 'MaxDD_pct':0.0, 'WinRate_pct':0.0, 'Trades':0}
                    cnt = 0
                    for sym in f_slice:
                        df = self.data_map.get(sym)
                        if df is None or len(df) < 50:
                            continue
                        try:
                            _, summ = backend.run_backtest(df, self.params.get('strategy') or params.get('strategy') or 'SMA Cross', params,
                                                           self.params.get('start_cash', 10000), self.params.get('commission', 0.0005), self.params.get('slippage', 0.0005), 0.01, 0.0, None, False)
                            trades = summ.get('Trades', 0) or 0
                            if trades < int(self.params.get('min_trades', 1)):
                                continue
                            score_val = backend.objective_score(summ, objective)
                            obj_scores.append(score_val)
                            sharpe_list.append(float(summ.get('Sharpe') or 0.0))
                            cagr_list.append(float(summ.get('CAGR_pct') or 0.0))
                            maxdd_list.append(float(summ.get('MaxDD_pct') or 0.0))
                            win_list.append(float(summ.get('WinRate_pct') or 0.0))
                            trades_list.append(int(trades))
                            for k in ('Sharpe','CAGR_pct','MaxDD_pct','WinRate_pct','Trades'):
                                agg[k] += float(summ.get(k, 0.0) or 0.0)
                            cnt += 1
                        except Exception:
                            continue
                    # could store per-fold metrics if needed later
                if obj_scores:
                    import math
                    mean_score = float(sum(obj_scores)/len(obj_scores))
                    sharpe_mean = sum(sharpe_list)/len(sharpe_list) if sharpe_list else 0.0
                    # stability metrics
                    sharpe_std = 0.0
                    if sharpe_list and len(sharpe_list) > 1:
                        m = sharpe_mean
                        sharpe_std = math.sqrt(sum((s-m)**2 for s in sharpe_list)/(len(sharpe_list)-1))
                    pos_sharpe_pct = 0.0
                    if sharpe_list:
                        pos_sharpe_pct = 100.0 * sum(1 for s in sharpe_list if s > 0)/len(sharpe_list)
                    cagr_mean = sum(cagr_list)/len(cagr_list) if cagr_list else 0.0
                    maxdd_mean = sum(maxdd_list)/len(maxdd_list) if maxdd_list else 0.0
                    win_mean = sum(win_list)/len(win_list) if win_list else 0.0
                    trades_mean = int(sum(trades_list)/len(trades_list)) if trades_list else 0
                    rec = {'params': params,'score': mean_score,'sharpe': sharpe_mean,'sharpe_std': sharpe_std,'pos_sharpe_pct': pos_sharpe_pct,
                           'cagr': cagr_mean,'max_dd': maxdd_mean,'win_rate': win_mean,'trades': trades_mean,
                           'universe': len(symbols),'folds': folds}
                    results.append(rec)
                    # early stopping check
                    if best_score_so_far is None or mean_score > best_score_so_far:
                        best_score_so_far = mean_score
                        epochs_without_improve = 0
                    else:
                        epochs_without_improve += 1
                    if patience > 0 and epochs_without_improve >= patience:
                        try:
                            self.status_updated.emit(f"Early stop at {i+1}/{total} (patience {patience})")
                        except Exception:
                            pass
                        break
                try:
                    # sort interim for streaming stability
                    if results:
                        results_sorted = sorted(results, key=lambda r: -float(r.get('score', 0)))
                        for idx, r in enumerate(results_sorted, start=1):
                            r['rank'] = idx
                        if stream:
                            self.intermediate_results.emit(results_sorted[:int(self.params.get('max_results',50))])
                except Exception:
                    pass
                try:
                    self.progress_updated.emit(int((i+1)/max(1,total)*100))
                except Exception:
                    pass
            full_results = sorted(results, key=lambda r: -float(r.get('score', 0)))
            for idx, r in enumerate(full_results, start=1):
                r['rank'] = idx
            try:
                self.full_results_ready.emit(full_results)
            except Exception:
                pass
            # produce trimmed view
            trimmed = list(full_results)
            try:
                mx = int(self.params.get('max_results', 50))
                if mx > 0:
                    trimmed = trimmed[:mx]
            except Exception:
                pass
            self.results_ready.emit(trimmed)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.error_occurred.emit(f"Optimize failed: {e}\n{tb}")

    def run_auto_discovery(self):
        # Auto-Discovery: multi-strategy + param grid exploration per symbol.
        # Expects params possibly containing:
        #  symbols: list[str]
        #  strategies: list[str]
        #  grid_json: str (either global param grid or mapping strategy->param grid)
        #  min_trades: int
        #  apply_bar_filters: bool, min_price_bar, min_vol_bar
        try:
            import json as _json, math
            from backend import run_backtest
        except Exception as e:
            try: self.error_occurred.emit(f"Auto-Discovery import error: {e}")
            except Exception: pass
            return
        p = self.params if isinstance(self.params, dict) else {}
        symbols = list(p.get('symbols') or [])
        if not symbols:
            # fallback to data_map keys
            try:
                symbols = list(self.data_map.keys())
            except Exception:
                symbols = []
        strategies = list(p.get('strategies') or [])
        if not strategies:
            strategies = ["SMA Cross","EMA Cross","Donchian Breakout","MACD Trend","RSI(2) @ Bollinger"]
        grid_raw = p.get('grid_json') or ''
        min_trades = int(p.get('min_trades', 0) or 0)
        apply_bar_filters = bool(p.get('apply_bar_filters', False))
        min_price_bar = float(p.get('min_price_bar', 0) or 0)
        min_vol_bar = float(p.get('min_vol_bar', 0) or 0)
        objective = (p.get('objective') or 'Sharpe').strip().lower()
        # map objective to lambda(row)->score; row fields use computed summary values later
        def _score_fn(r):
            try:
                if objective == 'cagr':
                    return float(r.get('CAGR',0) or 0)
                if objective == 'winrate':
                    return float(r.get('WinRate',0) or 0)
                if objective.startswith('return'):
                    # Return/DD = CAGR / abs(MaxDD)
                    dd = abs(float(r.get('MaxDD',0) or 0)) or 1e-9
                    return float(r.get('CAGR',0) or 0) / dd
                # default sharpe
                return float(r.get('Sharpe',0) or 0)
            except Exception:
                return 0.0
        # --- Parse grid ---
        # Supported forms:
        # 1) Global param grid: {"fast":[5,10],"slow":[50,100]}
        # 2) Per-strategy: {"SMA Cross":{"fast":[5,10]}, "Donchian Breakout":{"upper":[20,55]}}
        def _expand(grid_dict):
            # grid_dict: param -> list/scalar
            keys = list(grid_dict.keys())
            lists = []
            for k in keys:
                v = grid_dict[k]
                if isinstance(v, (list, tuple)):
                    lists.append((k, list(v)))
                elif isinstance(v, dict) and all(isinstance(x,(int,float)) for x in v.values()):
                    # treat dict of numeric? skip – user error
                    lists.append((k, [v]))
                else:
                    lists.append((k, [v]))
            from itertools import product
            combos = []
            if not lists:
                return [{}]
            names = [k for k,_ in lists]
            value_lists = [vs for _,vs in lists]
            for tup in product(*value_lists):
                combos.append({k: tup[i] for i,k in enumerate(names)})
            return combos
        strategy_param_grids = {}
        parsed = None
        if grid_raw.strip():
            try:
                parsed = _json.loads(grid_raw)
            except Exception as e:
                try: self.status_updated.emit(f"Grid JSON parse failed: {e}")
                except Exception: pass
                parsed = None
        if isinstance(parsed, dict):
            # detect form: if any key matches strategy names, treat per-strategy
            keys_lower = {k.lower(): k for k in parsed.keys()}
            strat_name_lowers = {s.lower(): s for s in strategies}
            intersect = [keys_lower[k] for k in keys_lower if k in strat_name_lowers]
            if intersect:
                # per strategy grids
                for strat in strategies:
                    val = parsed.get(strat) or parsed.get(strat.lower())
                    if isinstance(val, dict):
                        strategy_param_grids[strat] = _expand(val)
            else:
                # global grid – apply to all
                combos = _expand(parsed)
                for strat in strategies:
                    strategy_param_grids[strat] = combos
        # defaults for strategies without grid
        default_param_map = {
            'SMA Cross': {'fast':10,'slow':20},
            'EMA Cross': {'fast':10,'slow':20},
            'Donchian Breakout': {'upper':20,'lower':10},
            'MACD Trend': {'ema_trend':200,'fast':12,'slow':26,'signal':9},
            'RSI(2) @ Bollinger': {'rsi_p':2,'rsi_buy':10,'rsi_exit':60,'bb_p':20,'bb_k':2.0},
        }
        for strat in strategies:
            if strat not in strategy_param_grids or not strategy_param_grids[strat]:
                strategy_param_grids[strat] = [default_param_map.get(strat, {})]
        # --- Build total work size ---
        total_combos = 0
        for strat in strategies:
            total_combos += len(strategy_param_grids.get(strat, [])) * max(1,len(symbols))
        total_combos = max(1, total_combos)
        results = []
        done = 0
        # Logging
        import os, datetime as _dt
        log_path = os.path.join('logs','auto_discovery.log')
        try: os.makedirs('logs', exist_ok=True)
        except Exception: pass
        try:
            with open(log_path,'a',encoding='utf-8') as lf:
                lf.write(f"[{_dt.datetime.utcnow().isoformat()}Z] START auto-discovery symbols={len(symbols)} strategies={len(strategies)}\n")
        except Exception: pass
        # Iterate
        for strat in strategies:
            if self.is_cancelled:
                try: self.status_updated.emit("Auto-Discovery cancelled")
                except Exception: pass
                break
            param_list = strategy_param_grids.get(strat, [])
            for param_obj in param_list:
                if self.is_cancelled:
                    try: self.status_updated.emit("Auto-Discovery cancelled")
                    except Exception: pass
                    break
                for sym in symbols:
                    if self.is_cancelled:
                        try: self.status_updated.emit("Auto-Discovery cancelled")
                        except Exception: pass
                        break
                    df = self.data_map.get(sym)
                    if df is None or len(df) < 50:
                        done += 1
                        continue
                    # bar filters
                    try:
                        if apply_bar_filters:
                            last_close = float(df['Close'].iloc[-1]) if 'Close' in df.columns else None
                            last_vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
                            if min_price_bar and last_close is not None and last_close < min_price_bar:
                                done += 1; continue
                            if min_vol_bar and last_vol < min_vol_bar:
                                done += 1; continue
                    except Exception:
                        pass
                    # run backtest (no walk-forward here)
                    try:
                        _, summ = run_backtest(df, strat, param_obj,
                                               start_cash=10000.0, commission=0.0005, slippage_perc=0.0005,
                                               figscale=0.01, x_margin=0.0, scheme_colors=None, plot=False)
                    except Exception:
                        done += 1
                        continue
                    trades = int(summ.get('Trades',0) or 0)
                    if trades < min_trades:
                        done += 1
                        continue
                    row = {
                        'Symbol': sym,
                        'Strategy': strat,
                        'Params': _json.dumps(param_obj, separators=(',',':')),
                        'CAGR': round(summ.get('CAGR_pct',0.0) or 0.0, 2),
                        'Sharpe': round(summ.get('Sharpe',0.0) or 0.0, 3),
                        'WinRate': round(summ.get('WinRate_pct',0.0) or 0.0, 2),
                        'MaxDD': round(summ.get('MaxDD_pct',0.0) or 0.0, 2),
                        'Trades': trades,
                    }
                    try:
                        row['Score'] = round(_score_fn(row), 5)
                    except Exception:
                        row['Score'] = 0.0
                    results.append(row)
                    # append to log
                    try:
                        with open(log_path,'a',encoding='utf-8') as lf:
                            lf.write(_json.dumps(row, ensure_ascii=False)+"\n")
                    except Exception:
                        pass
                    done += 1
                    if (done % 10)==0 or done==total_combos:
                        try:
                            prog = int(done/total_combos*100)
                            self.progress_updated.emit(prog)
                            self.status_updated.emit(f"Auto-Discovery: {done}/{total_combos}")
                        except Exception:
                            pass
            # strategy-level progress update
            try:
                self.status_updated.emit(f"Completed strategy {strat}")
            except Exception:
                pass
        # Sort results by Score desc; fallback inside key if missing
        try:
            results = sorted(results, key=lambda r: -float(r.get('Score', r.get('Sharpe',0) or 0)))
        except Exception:
            pass
        try:
            self.results_ready.emit(results)
        except Exception:
            pass
        try:
            with open(log_path,'a',encoding='utf-8') as lf:
                lf.write(f"[{_dt.datetime.utcnow().isoformat()}Z] END auto-discovery rows={len(results)}\n")
        except Exception:
            pass

    def run_walkforward(self):
        """Walk-forward evaluation per symbol & strategy across folds with OOS fraction."""
        try:
            import backend
        except Exception as e:
            try: self.error_occurred.emit(f"walkforward import error: {e}")
            except Exception: pass
            self.results_ready.emit([])
            return
        folds = int(self.params.get('folds',4) or 4)
        oos_frac = float(self.params.get('oos_frac',0.2) or 0.2)
        min_trades = int(self.params.get('min_trades',0) or 0)
        strategies = []
        try:
            raw = self.params.get('strategies')
            if isinstance(raw,str):
                strategies = [s.strip() for s in raw.split(',') if s.strip()]
            elif isinstance(raw,(list,tuple)):
                strategies = list(raw)
        except Exception:
            strategies = []
        if not strategies:
            strategies = list(getattr(backend,'STRAT_MAP',{}).keys())[:5]
        symbols = list(self.data_map.keys())
        total_steps = max(1, len(symbols) * max(1,len(strategies)))
        progress_step = 0
        out_rows = []
        for sym in symbols:
            if self.is_cancelled: break
            df = self.data_map.get(sym)
            if df is None or len(df) < 120:
                continue
            n = len(df)
            for strat in strategies:
                if self.is_cancelled: break
                try:
                    splits = backend.walk_forward_splits(n, folds, oos_frac)
                except Exception:
                    splits = []
                for fold_idx,(tr_s,tr_e,te_s,te_e) in enumerate(splits, start=1):
                    if self.is_cancelled: break
                    # slice once for speed (train+test contiguous)
                    sub = df.iloc[tr_s:te_e].copy()
                    try:
                        _, summ = backend.run_backtest(sub, strat, {},
                                                       self.params.get('start_cash',10000.0),
                                                       self.params.get('commission',0.0005),
                                                       self.params.get('slippage',0.0005),
                                                       0.01,0.0,None,False)
                    except Exception as e:
                        out_rows.append({'symbol':sym,'strategy':strat,'fold':fold_idx,'error':str(e)})
                        continue
                    if (summ.get('Trades') or 0) < min_trades:
                        continue
                    def _ix(i):
                        try:
                            return str(df.index[i])
                        except Exception:
                            return ''
                    out_rows.append({
                        'symbol': sym,
                        'strategy': strat,
                        'fold': fold_idx,
                        'train_start': _ix(tr_s),
                        'train_end': _ix(tr_e-1),
                        'test_start': _ix(te_s),
                        'test_end': _ix(te_e-1),
                        'sharpe': summ.get('Sharpe'),
                        'cagr': summ.get('CAGR_pct'),
                        'max_dd': summ.get('MaxDD_pct'),
                        'win_rate': summ.get('WinRate_pct'),
                        'trades': summ.get('Trades')
                    })
                progress_step += 1
                try:
                    self.progress_updated.emit(int(progress_step/total_steps*100))
                except Exception:
                    pass
        try:
            self.results_ready.emit(out_rows)
        except Exception:
            pass
