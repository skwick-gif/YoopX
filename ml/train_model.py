import os, json, joblib, math, time
import pandas as pd
from typing import Dict, Any, Literal, List, Callable, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, brier_score_loss, log_loss
from sklearn.linear_model import LogisticRegression
from .feature_engineering import build_training_frame, build_training_frames_multi

DEFAULT_MODEL_PATH = 'ml/model_rf.pkl'
XGB_MODEL_PATH = 'ml/model_xgb.pkl'
LGBM_MODEL_PATH = 'ml/model_lgbm.pkl'

def collect_training_data(data_map: Dict[str, pd.DataFrame], min_rows: int = 120, progress_cb: Optional[Callable[[Dict[str,Any]], None]] = None) -> pd.DataFrame:
    frames = []
    total = len(data_map)
    start_t = time.time()
    processed = 0
    for sym, df in data_map.items():
        processed += 1
        if processed == 1 and progress_cb:
            try:
                progress_cb({'phase':'collect_start','total': total})
            except Exception:
                pass
        if df is None or len(df) < min_rows or 'Close' not in df.columns:
            if progress_cb and (processed % 50 == 0 or processed == total):
                try:
                    progress_cb({'phase':'collect','symbol':sym,'i':processed,'total':total,'kept':len(frames),'eta':None})
                except Exception:
                    pass
            continue
        t0 = time.time()
        tf = build_training_frame(df)
        t1 = time.time()
        if not tf.empty:
            tf['symbol'] = sym
            frames.append(tf)
        # ETA estimation each 25 symbols
        if progress_cb and (processed % 25 == 0 or processed == total):
            try:
                elapsed = time.time()-start_t
                rate = processed/elapsed if elapsed>0 else 0
                remain = (total-processed)/rate if rate>0 else None
                progress_cb({'phase':'collect','symbol':sym,'i':processed,'total':total,'kept':len(frames),'eta':remain,'last_symbol_sec':t1-t0})
            except Exception:
                pass
    if not frames:
        return pd.DataFrame()
    all_df = pd.concat(frames).reset_index(drop=True)
    if progress_cb:
        try:
            progress_cb({'phase':'collect_done','i':processed,'total':total,'rows':len(all_df)})
        except Exception:
            pass
    return all_df

def _collect_debug_stats(data_map: Dict[str, pd.DataFrame]):
    stats = {
        'total_symbols': len(data_map),
        'have_close': 0,
        'ge_30_rows': 0,
        'ge_60_rows': 0,
        'ge_120_rows': 0,
        'sample_missing_close': []
    }
    for i, (sym, df) in enumerate(data_map.items()):
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        if 'Close' in df.columns:
            stats['have_close'] += 1
            ln = len(df)
            if ln >= 30: stats['ge_30_rows'] += 1
            if ln >= 60: stats['ge_60_rows'] += 1
            if ln >= 120: stats['ge_120_rows'] += 1
        else:
            if len(stats['sample_missing_close']) < 5:
                stats['sample_missing_close'].append(sym)
    return stats

def train_model(data_map: Dict[str, pd.DataFrame], model: Literal['rf','xgb','lgbm']='rf', model_path: str|None=None, xgb_params: dict|None=None, lgbm_params: dict|None=None, multi_horizons: list[int]|None=None, progress_cb: Optional[Callable[[Dict[str,Any]], None]] = None) -> Dict[str, Any]:
    """Train selected model type.
    If multi_horizons provided (length > 1), trains a separate model per horizon and stores them
    inside a single container object saved at model_path. Returns metadata including per-horizon
    metrics and validation probability arrays for threshold optimization.
    """
    print('[TRAIN_DEBUG] train_model entered. data_map size=', len(data_map), 'model=', model, 'multi_horizons=', multi_horizons, flush=True)
    # quick sanity: count symbols with Close & rows
    try:
        c_ok = sum(1 for d in data_map.values() if d is not None and 'Close' in d.columns and len(d) >= 50)
        print(f'[TRAIN_DEBUG] symbols with Close & >=50 rows: {c_ok}', flush=True)
    except Exception:
        pass
    # Detect special case: single pre-built combined dataset (historical path)
    prebuilt_dataset: pd.DataFrame|None = None
    if len(data_map) == 1:
        try:
            only_key = next(iter(data_map.keys()))
            df0 = data_map[only_key]
            if isinstance(df0, pd.DataFrame) and 'label' in df0.columns and (only_key.startswith('combined_') or only_key.startswith('hist_')):
                prebuilt_dataset = df0.copy()
                # If symbol column missing, add placeholder
                if 'symbol' not in prebuilt_dataset.columns:
                    prebuilt_dataset['symbol'] = 'cmb'
                print('[TRAIN_DEBUG] Using prebuilt combined dataset rows=', len(prebuilt_dataset), flush=True)
        except Exception:
            pass

    # --- Helper utilities ---
    def _emit(ev: Dict[str,Any]):
        if progress_cb:
            try:
                progress_cb(ev)
            except Exception:
                pass

    def _validate_dataset(ds: pd.DataFrame, context: str="dataset") -> Dict[str, Any]:
        """Perform basic integrity checks; emit progress events around validation.
        Returns dict of metrics and a 'status'.
        """
        meta: Dict[str, Any] = {}
        try:
            _emit({'phase':'dataset_validation_start','context': context, 'rows': len(ds)})
            rows = len(ds)
            symbols = ds['symbol'].nunique() if 'symbol' in ds.columns else None
            pos_rate = float(ds['label'].mean()) if 'label' in ds.columns and rows>0 else None
            feature_cols = [c for c in ds.columns if c not in ('label','symbol')]
            feature_count = len(feature_cols)
            # missing values stats
            missing_total = 0.0; missing_cells = 0
            try:
                missing_cells = int(ds[feature_cols].isna().sum().sum())
                missing_total = float(missing_cells) / float(rows * max(feature_count,1)) if rows>0 else 0.0
            except Exception:
                pass
            # simple pass criteria (can tune): rows>100, feature_count>5
            status = 'ok'
            if rows < 50 or feature_count < 5:
                status = 'warn'
            if rows < 10:
                status = 'fail'
            meta = {
                'rows': rows,
                'symbols': symbols,
                'positive_rate': pos_rate,
                'feature_count': feature_count,
                'missing_ratio': round(missing_total,4),
                'status': status
            }
            _emit({'phase':'dataset_validation_result', **meta})
        except Exception as e:
            meta = {'status':'error','error': str(e)}
            _emit({'phase':'dataset_validation_result', **meta})
        return meta

    # --- Helper to train a single model on a provided dataset ---
    def _train_single(dataset: pd.DataFrame, base_model: str, model_path_hint: str|None=None) -> Dict[str, Any]:
        if dataset.empty:
            raise ValueError('Empty dataset for training')
        y_full = dataset['label']
        X_full = dataset.drop(columns=['label','symbol'])
        n = len(dataset)
        val_size = max(int(n * 0.2), 50)
        if val_size >= n - 20:
            val_size = min(max(int(n*0.15), 20), n//3)
        split_idx = n - val_size
        if split_idx < 30:
            split_idx = n
        X_train, y_train = X_full.iloc[:split_idx], y_full.iloc[:split_idx]
        X_val, y_val = X_full.iloc[split_idx:], y_full.iloc[split_idx:]
        has_validation = len(X_val) > 0 and y_val.nunique() == 2
        fi_list_local: List[Dict[str, Any]] = []
        chosen_path = model_path_hint
        # train model by type
        if base_model == 'xgb':
            try:
                import xgboost as xgb
            except Exception as e:
                raise RuntimeError(f"xgboost not installed: {e}")
            dtrain = xgb.DMatrix(X_train, label=y_train)
            params = {'objective':'binary:logistic','eval_metric':'auc','max_depth':5,'eta':0.05,'subsample':0.9,'colsample_bytree':0.9,'min_child_weight':2}
            if xgb_params: params.update(xgb_params)
            if progress_cb:
                try: progress_cb({'phase':'xgb_train_start','iters':400})
                except Exception: pass
            bst = xgb.train(params, dtrain, num_boost_round=400)
            preds_train_prob = bst.predict(dtrain)
            preds_train = (preds_train_prob > 0.5).astype(int)
            report = classification_report(y_train, preds_train, output_dict=True, zero_division=0)
            model_obj_local = {'model': bst, 'features': list(X_full.columns), 'type':'xgb', 'params': params}
            if not chosen_path: chosen_path = XGB_MODEL_PATH
            try:
                score_dict = bst.get_score(importance_type='gain') or {}
                for f in X_full.columns:
                    fi_list_local.append({'feature': f, 'importance': float(score_dict.get(f, 0.0))})
            except Exception:
                pass
        elif base_model == 'lgbm':
            try:
                import lightgbm as lgb
            except Exception as e:
                raise RuntimeError(f"lightgbm not installed: {e}")
            params = {'n_estimators':600,'learning_rate':0.02,'num_leaves':48,'subsample':0.9,'colsample_bytree':0.9,'reg_lambda':1.0,'random_state':42}
            if lgbm_params: params.update(lgbm_params)
            clf = lgb.LGBMClassifier(**params)
            clf.fit(X_train, y_train)
            preds_train = clf.predict(X_train)
            report = classification_report(y_train, preds_train, output_dict=True, zero_division=0)
            model_obj_local = {'model': clf, 'features': list(X_full.columns), 'type':'lgbm', 'params': params}
            if not chosen_path: chosen_path = LGBM_MODEL_PATH
            try:
                imps = getattr(clf,'feature_importances_',None)
                if imps is not None:
                    for f, v in zip(X_full.columns, imps):
                        fi_list_local.append({'feature': f, 'importance': float(v)})
            except Exception:
                pass
        else:  # rf with incremental progress
            target_estimators = 300
            step = 50
            rf = RandomForestClassifier(n_estimators=step, max_depth=7, random_state=42, n_jobs=-1, warm_start=True)
            started = time.time()
            current = 0
            while current < target_estimators:
                current += step
                if current > target_estimators:
                    current = target_estimators
                    rf.n_estimators = current
                else:
                    rf.n_estimators = current
                rf.fit(X_train, y_train)
                if progress_cb:
                    try:
                        elapsed = time.time() - started
                        pct = current/target_estimators
                        eta = (elapsed/pct - elapsed) if pct>0 else None
                        progress_cb({'phase':'rf_progress','done': current,'total': target_estimators,'eta': eta})
                    except Exception:
                        pass
            preds_train = rf.predict(X_train)
            report = classification_report(y_train, preds_train, output_dict=True, zero_division=0)
            model_obj_local = {'model': rf, 'features': list(X_full.columns), 'type':'rf'}
            if not chosen_path: chosen_path = DEFAULT_MODEL_PATH
            try:
                imps = getattr(rf,'feature_importances_', None)
                if imps is not None:
                    for f, v in zip(X_full.columns, imps):
                        fi_list_local.append({'feature': f, 'importance': float(v)})
            except Exception:
                pass
        # validation & calibration
        val_metrics = {}
        val_probs = []
        val_labels = []
        if has_validation:
            try:
                if model_obj_local['type'] == 'xgb':
                    import xgboost as xgb
                    dval = xgb.DMatrix(X_val, label=y_val)
                    val_prob = model_obj_local['model'].predict(dval)
                elif model_obj_local['type'] == 'lgbm':
                    val_prob = model_obj_local['model'].predict_proba(X_val)[:,1]
                else:
                    val_prob = model_obj_local['model'].predict_proba(X_val)[:,1]
                val_probs = [float(p) for p in val_prob]
                val_labels = [int(v) for v in y_val]
                val_pred = (val_prob > 0.5).astype(int)
                val_metrics['report'] = classification_report(y_val, val_pred, output_dict=True, zero_division=0)
                try: val_metrics['auc'] = float(roc_auc_score(y_val, val_prob))
                except Exception: pass
                try: val_metrics['brier'] = float(brier_score_loss(y_val, val_prob))
                except Exception: pass
                try: val_metrics['log_loss'] = float(log_loss(y_val, val_prob))
                except Exception: pass
                calibrated = False
                try:
                    if y_val.nunique()==2 and len(y_val) >= 30:
                        lr = LogisticRegression(max_iter=500)
                        lr.fit(val_prob.reshape(-1,1), y_val)
                        coef = float(lr.coef_[0][0]); intercept = float(lr.intercept_[0])
                        model_obj_local['calibration'] = {'type':'platt','coef':coef,'intercept':intercept}
                        calibrated = True
                except Exception:
                    pass
                val_metrics['calibrated'] = calibrated
            except Exception:
                pass
        # feature stats for drift
        feat_stats_local = {}
        try:
            for col in X_full.columns:
                try:
                    series = X_full[col].astype(float)
                    feat_stats_local[col] = {'mean': float(series.mean()), 'std': float(series.std(ddof=0) or 0.0)}
                except Exception:
                    continue
        except Exception:
            pass
        # CV (unchanged simplified reuse of earlier logic) - optional for single model helper
        cv_results = []
        try:
            folds = 3
            if len(X_full) > 300 and y_full.nunique() == 2:
                seg_size = len(X_full) // (folds + 1)
                for i in range(1, folds+1):
                    tr_end = seg_size * i
                    va_end = seg_size * (i+1) if i < folds else len(X_full)
                    if va_end - tr_end < 25 or tr_end < 50:
                        continue
                    X_tr, y_tr = X_full.iloc[:tr_end], y_full.iloc[:tr_end]
                    X_va, y_va = X_full.iloc[tr_end:va_end], y_full.iloc[tr_end:va_end]
                    if y_va.nunique() < 2:
                        continue
                    if progress_cb:
                        try: progress_cb({'phase':'cv_progress','fold': i, 'folds': folds})
                        except Exception: pass
                    if model_obj_local['type'] == 'rf':
                        fm = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42, n_jobs=-1)
                        fm.fit(X_tr, y_tr); prob_va = fm.predict_proba(X_va)[:,1]
                    elif model_obj_local['type'] == 'xgb':
                        import xgboost as xgb
                        fm = xgb.train(model_obj_local.get('params', {}), xgb.DMatrix(X_tr, label=y_tr), num_boost_round=400)
                        prob_va = fm.predict(xgb.DMatrix(X_va))
                    else:
                        import lightgbm as lgb
                        fm = lgb.LGBMClassifier(**model_obj_local.get('params', {}))
                        fm.fit(X_tr, y_tr); prob_va = fm.predict_proba(X_va)[:,1]
                    fold = {'fold': i, 'train_size': int(len(X_tr)), 'val_size': int(len(X_va))}
                    try: fold['auc'] = float(roc_auc_score(y_va, prob_va))
                    except Exception: pass
                    try: fold['brier'] = float(brier_score_loss(y_va, prob_va))
                    except Exception: pass
                    cv_results.append(fold)
        except Exception:
            cv_results = cv_results
        if fi_list_local:
            fi_list_local = sorted(fi_list_local, key=lambda r: -r['importance'])
        top_features_local = [f['feature'] for f in fi_list_local[:10]] if fi_list_local else []
        # class balance
        try:
            pos_rate = float(y_full.sum())/float(len(y_full)) if len(y_full) > 0 else 0.0
            class_balance = {'positive_rate': round(pos_rate,4), 'n_pos': int(y_full.sum()), 'n_total': int(len(y_full))}
        except Exception:
            class_balance = None
        return {
            'model_obj': model_obj_local,
            'report': report,
            'validation': val_metrics if val_metrics else None,
            'cv': cv_results if cv_results else None,
            'cv_mean_auc': (sum([c.get('auc',0) for c in cv_results])/len(cv_results)) if cv_results else None,
            'feature_importance': fi_list_local,
            'top_features': top_features_local,
            'feature_stats': feat_stats_local or None,
            'samples': int(len(dataset)),
            'train_size': int(len(X_train)),
            'val_size': int(len(X_val)) if has_validation else 0,
            'val_probs': val_probs,
            'val_labels': val_labels,
            'features': list(X_full.columns),
            'path_hint': chosen_path,
            'class_balance': class_balance,
        }

    # --- Multi-horizon path ---
    if prebuilt_dataset is not None and (not multi_horizons or len(multi_horizons) <= 1):
        # Simple single-model path on already prepared dataset
        _validate_dataset(prebuilt_dataset, context='prebuilt_single')
        meta_single = _train_single(prebuilt_dataset, model, model_path)
        model_obj = meta_single.pop('model_obj')
        chosen_path = meta_single.get('path_hint') or model_path or (DEFAULT_MODEL_PATH if model=='rf' else (XGB_MODEL_PATH if model=='xgb' else LGBM_MODEL_PATH))
        os.makedirs(os.path.dirname(chosen_path), exist_ok=True)
        try:
            joblib.dump(model_obj, chosen_path)
        except Exception:
            pass
        return {
            'type': 'single_prebuilt',
            'model_type': model,
            'path': chosen_path,
            'samples': meta_single.get('samples'),
            'train_size': meta_single.get('train_size'),
            'val_size': meta_single.get('val_size'),
            'validation': meta_single.get('validation'),
            'cv_mean_auc': meta_single.get('cv_mean_auc'),
            'feature_importance': meta_single.get('feature_importance'),
            'top_features': meta_single.get('top_features'),
            'feature_stats': meta_single.get('feature_stats'),
            'val_probs': meta_single.get('val_probs'),
            'val_labels': meta_single.get('val_labels'),
            'horizons': multi_horizons or None,
            'class_balance': meta_single.get('class_balance')
        }

    if multi_horizons and len(multi_horizons) > 1:
        horizon_datasets: Dict[int, pd.DataFrame] = {}
        for h in sorted(set(multi_horizons)):
            frames = []
            for sym, df in data_map.items():
                if df is None or len(df) < 120 or 'Close' not in df.columns:
                    continue
                try:
                    fr = build_training_frame(df, horizon=h)
                    if not fr.empty:
                        fr2 = fr.copy(); fr2['symbol'] = sym
                        frames.append(fr2)
                except Exception:
                    continue
            if frames:
                horizon_datasets[h] = pd.concat(frames).reset_index(drop=True)
        if not horizon_datasets:
            raise ValueError('No training data produced for requested horizons')
        if progress_cb:
            try: progress_cb({'phase':'multi_datasets_built','horizons':list(horizon_datasets.keys())})
            except Exception: pass
        container_models = {}
        horizon_meta_list = []
        root_feature_stats = None
        root_features = None
        for idx, (h, ds) in enumerate(horizon_datasets.items()):
            _validate_dataset(ds, context=f'horizon_{h}')
            single_meta = _train_single(ds, model, None)
            mobj = single_meta.pop('model_obj')
            container_models[h] = mobj
            h_entry = { 'horizon': h }
            for k in ('samples','train_size','val_size','cv_mean_auc','validation','feature_importance','top_features','val_probs','val_labels'):
                h_entry[k] = single_meta.get(k)
            # class balance for this horizon
            try:
                if 'label' in ds.columns:
                    pos_rate = float(ds['label'].sum())/float(len(ds)) if len(ds) > 0 else 0.0
                    h_entry['class_balance'] = {'positive_rate': round(pos_rate,4), 'n_pos': int(ds['label'].sum()), 'n_total': int(len(ds))}
            except Exception:
                pass
            horizon_meta_list.append(h_entry)
            if idx == 0:
                root_feature_stats = single_meta.get('feature_stats')
                root_features = single_meta.get('features')
            # emit per-horizon completion progress event
            if progress_cb:
                try:
                    ds_len = int(len(ds))
                    auc_val = None
                    try:
                        auc_val = (single_meta.get('validation') or {}).get('auc')
                    except Exception:
                        pass
                    progress_cb({'phase':'multi_horizon_complete', 'horizon': h, 'index': idx+1, 'total': len(horizon_datasets), 'samples': ds_len, 'auc': auc_val})
                except Exception:
                    pass
        # build container object
        container_path = model_path or (DEFAULT_MODEL_PATH if model=='rf' else (XGB_MODEL_PATH if model=='xgb' else LGBM_MODEL_PATH))
        if container_path and os.path.dirname(container_path):
            os.makedirs(os.path.dirname(container_path), exist_ok=True)
        container_obj = {
            'type': f'{model}_multi',
            'models': container_models,
            'features': root_features,
            'multi': True,
            'feature_stats': root_feature_stats,
            'horizons': sorted(container_models.keys()),
        }
        joblib.dump(container_obj, container_path)
        if progress_cb:
            try: progress_cb({'phase':'saved','path':container_path})
            except Exception: pass
        # aggregate metrics (e.g., mean of AUCs)
        mean_auc_vals = [ (h_m.get('validation') or {}).get('auc') for h_m in horizon_meta_list]
        mean_auc_vals = [v for v in mean_auc_vals if isinstance(v,(int,float))]
        agg_auc = sum(mean_auc_vals)/len(mean_auc_vals) if mean_auc_vals else None
        return {
            'path': container_path,
            'model_type': container_obj['type'],
            'samples': sum(hm.get('samples',0) for hm in horizon_meta_list),
            'symbols': None,
            'report': None,
            'validation': {'auc_mean': agg_auc} if agg_auc else None,
            'train_size': None,
            'val_size': None,
            'cv': None,
            'cv_mean_auc': agg_auc,
            'feature_importance': None,
            'top_features': horizon_meta_list[0].get('top_features') if horizon_meta_list else None,
            'feature_stats': container_obj.get('feature_stats'),
            'horizons': container_obj.get('horizons'),
            'horizon_models': horizon_meta_list,
            'class_balance': {hm['horizon']: hm.get('class_balance') for hm in horizon_meta_list if hm.get('class_balance')} or None,
        }

    # --- Single-horizon (original) path ---
    dataset = collect_training_data(data_map, min_rows=60, progress_cb=progress_cb)  # lowered threshold during debug
    print('[TRAIN_DEBUG] aggregate dataset len=', len(dataset), 'unique symbols=', dataset['symbol'].nunique() if not dataset.empty else 0, flush=True)
    if dataset.empty:
        # gather diagnostics
        dbg = _collect_debug_stats(data_map)
        print('[TRAIN_DEBUG] diagnostics:', dbg, flush=True)
        # Relax further: try min_rows=10
        if dbg.get('have_close',0) > 0:
            dataset = collect_training_data(data_map, min_rows=10)
            print('[TRAIN_DEBUG] retry with min_rows=10 len=', len(dataset), flush=True)
        if dataset.empty:
            # last resort: build minimal frame for first up to 20 symbols with Close to surface more info
            mini_frames = []
            count = 0
            for sym, df in data_map.items():
                if count >= 20: break
                if not isinstance(df, pd.DataFrame) or 'Close' not in df.columns or len(df) < 15:
                    continue
                try:
                    tmp = build_training_frame(df.head(120))
                    if not tmp.empty:
                        tmp['symbol'] = sym
                        mini_frames.append(tmp)
                        count += 1
                except Exception as e:
                    print(f'[TRAIN_DEBUG] mini build failed for {sym}: {e}', flush=True)
            if mini_frames:
                dataset = pd.concat(mini_frames).reset_index(drop=True)
                print('[TRAIN_DEBUG] using MINI dataset len=', len(dataset), 'symbols=', dataset['symbol'].nunique(), flush=True)
        if dataset.empty:
            raise ValueError('No training data produced')
    # sample report of columns
    try:
        print('[TRAIN_DEBUG] dataset columns sample:', list(dataset.columns)[:12], flush=True)
        print('[TRAIN_DEBUG] label balance: total=', len(dataset), 'positive=', int(dataset['label'].sum()), flush=True)
    except Exception:
        pass
    if progress_cb:
        try: progress_cb({'phase':'train_start','rows':len(dataset)})
        except Exception: pass
    # dataset validation (single path)
    _validate_dataset(dataset, context='single')
    single_meta = _train_single(dataset, model, model_path)
    if progress_cb:
        try: progress_cb({'phase':'finalize'})
        except Exception: pass
    model_obj = single_meta.pop('model_obj')
    final_path = single_meta.get('path_hint') or model_path or DEFAULT_MODEL_PATH
    if final_path and os.path.dirname(final_path):
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
    # assemble object to persist (include feature_stats for drift)
    persist_obj = model_obj
    if single_meta.get('feature_stats'):
        persist_obj['feature_stats'] = single_meta.get('feature_stats')
    joblib.dump(persist_obj, final_path)
    if progress_cb:
        try: progress_cb({'phase':'model_persisted','path':final_path})
        except Exception: pass
    if progress_cb:
        try: progress_cb({'phase':'saved','path':final_path})
        except Exception: pass
    # class balance overall
    try:
        y_full = dataset['label']
        pos_rate_global = float(y_full.sum())/float(len(y_full)) if len(y_full)>0 else 0.0
    except Exception:
        pos_rate_global = None
    result = {
        'path': final_path,
        'samples': single_meta.get('samples'),
        'symbols': dataset['symbol'].nunique(),
        'report': single_meta.get('report'),
        'model_type': model_obj['type'],
        'feature_importance': single_meta.get('feature_importance'),
        'top_features': single_meta.get('top_features'),
        'validation': single_meta.get('validation'),
        'train_size': single_meta.get('train_size'),
        'val_size': single_meta.get('val_size'),
        'cv': single_meta.get('cv'),
        'cv_mean_auc': single_meta.get('cv_mean_auc'),
        'feature_stats': single_meta.get('feature_stats'),
        'val_probs': single_meta.get('val_probs'),
        'val_labels': single_meta.get('val_labels'),
        'class_balance': {'positive_rate': round(pos_rate_global,4)} if pos_rate_global is not None else None,
    }
    if progress_cb:
        try: progress_cb({'phase':'done','samples': result.get('samples')})
        except Exception: pass
    return result
    if model == 'xgb':
        try:
            import xgboost as xgb
        except Exception as e:
            raise RuntimeError(f"xgboost not installed: {e}")
        dtrain = xgb.DMatrix(X_train, label=y_train)
        params = {'objective':'binary:logistic','eval_metric':'auc','max_depth':5,'eta':0.05,'subsample':0.9,'colsample_bytree':0.9,'min_child_weight':2}
        if xgb_params:
            params.update(xgb_params)
        bst = xgb.train(params, dtrain, num_boost_round=400)
        preds_train_prob = bst.predict(dtrain)
        preds_train = (preds_train_prob > 0.5).astype(int)
        report = classification_report(y_train, preds_train, output_dict=True)
        model_obj = {'model': bst, 'features': list(X_full.columns), 'type':'xgb', 'params': params}
        if not model_path:
            model_path = XGB_MODEL_PATH
        try:
            # importance by gain
            score_dict = bst.get_score(importance_type='gain') or {}
            # map to all features for consistency
            for f in X_full.columns:
                fi_list.append({'feature': f, 'importance': float(score_dict.get(f, 0.0))})
        except Exception:
            pass
    elif model == 'lgbm':
        try:
            import lightgbm as lgb
        except Exception as e:
            raise RuntimeError(f"lightgbm not installed: {e}")
        params = {
            'n_estimators': 600,
            'learning_rate': 0.02,
            'num_leaves': 48,
            'subsample': 0.9,
            'colsample_bytree': 0.9,
            'reg_lambda': 1.0,
            'random_state': 42,
        }
        if lgbm_params:
            params.update(lgbm_params)
        clf = lgb.LGBMClassifier(**params)
        clf.fit(X_train, y_train)
        preds_train = clf.predict(X_train)
        report = classification_report(y_train, preds_train, output_dict=True)
        model_obj = {'model': clf, 'features': list(X_full.columns), 'type': 'lgbm', 'params': params}
        if not model_path:
            model_path = LGBM_MODEL_PATH
        try:
            importances = getattr(clf, 'feature_importances_', None)
            if importances is not None:
                for f, v in zip(X_full.columns, importances):
                    fi_list.append({'feature': f, 'importance': float(v)})
        except Exception:
            pass
    else:
        rf = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        preds_train = rf.predict(X_train)
        report = classification_report(y_train, preds_train, output_dict=True)
        model_obj = {'model': rf, 'features': list(X_full.columns), 'type':'rf'}
        if not model_path:
            model_path = DEFAULT_MODEL_PATH
        try:
            import numpy as _np
            importances = getattr(rf, 'feature_importances_', None)
            if importances is not None:
                for f, v in zip(X_full.columns, importances):
                    fi_list.append({'feature': f, 'importance': float(v)})
        except Exception:
            pass
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    # Validation metrics & calibration
    val_metrics = {}
    if has_validation:
        try:
            if model_obj['type'] == 'xgb':
                import xgboost as xgb
                dval = xgb.DMatrix(X_val, label=y_val)
                val_prob = model_obj['model'].predict(dval)
            elif model_obj['type'] == 'lgbm':
                val_prob = model_obj['model'].predict_proba(X_val)[:,1]
            else:
                val_prob = model_obj['model'].predict_proba(X_val)[:,1]
            val_pred = (val_prob > 0.5).astype(int)
            val_metrics['report'] = classification_report(y_val, val_pred, output_dict=True)
            try:
                val_metrics['auc'] = float(roc_auc_score(y_val, val_prob))
            except Exception:
                pass
            try:
                val_metrics['brier'] = float(brier_score_loss(y_val, val_prob))
            except Exception:
                pass
            try:
                val_metrics['log_loss'] = float(log_loss(y_val, val_prob))
            except Exception:
                pass
            # simple Platt scaling calibration
            calibrated = False
            try:
                if y_val.nunique() == 2 and len(y_val) >= 30:
                    import numpy as _np
                    lr = LogisticRegression(max_iter=500)
                    lr.fit(val_prob.reshape(-1,1), y_val)
                    coef = float(lr.coef_[0][0])
                    intercept = float(lr.intercept_[0])
                    model_obj['calibration'] = {'type':'platt','coef':coef,'intercept':intercept}
                    calibrated = True
            except Exception:
                pass
            val_metrics['calibrated'] = calibrated
        except Exception:
            pass
    # Walk-forward CV (3 folds) for stability metrics
    cv_results = []
    try:
        folds = 3
        if n > 300 and y_full.nunique() == 2:
            seg_size = n // (folds + 1)
            import numpy as _np
            for i in range(1, folds+1):
                train_end = seg_size * i
                val_end = seg_size * (i+1) if i < folds else n
                if val_end - train_end < 25 or train_end < 50:
                    continue
                X_tr, y_tr = X_full.iloc[:train_end], y_full.iloc[:train_end]
                X_va, y_va = X_full.iloc[train_end:val_end], y_full.iloc[train_end:val_end]
                if y_va.nunique() < 2:
                    continue
                # Fresh model each fold (same type)
                fold_model = None
                if model_obj['type'] == 'rf':
                    fm = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42, n_jobs=-1)
                    fm.fit(X_tr, y_tr)
                    prob_va = fm.predict_proba(X_va)[:,1]
                elif model_obj['type'] == 'xgb':
                    import xgboost as xgb
                    fm = xgb.train(model_obj.get('params', {}), xgb.DMatrix(X_tr, label=y_tr), num_boost_round=400)
                    prob_va = fm.predict(xgb.DMatrix(X_va))
                else:  # lgbm
                    import lightgbm as lgb
                    fm = lgb.LGBMClassifier(**model_obj.get('params', {}))
                    fm.fit(X_tr, y_tr)
                    prob_va = fm.predict_proba(X_va)[:,1]
                pred_va = (prob_va > 0.5).astype(int)
                fold = {
                    'fold': i,
                    'train_size': int(len(X_tr)),
                    'val_size': int(len(X_va)),
                }
                try:
                    fold['auc'] = float(roc_auc_score(y_va, prob_va))
                except Exception:
                    pass
                try:
                    fold['brier'] = float(brier_score_loss(y_va, prob_va))
                except Exception:
                    pass
                cv_results.append(fold)
    except Exception:
        cv_results = cv_results
    joblib.dump(model_obj, model_path)
    # sort feature importance
    if fi_list:
        fi_list = sorted(fi_list, key=lambda r: -r['importance'])
    top_features = [f['feature'] for f in fi_list[:10]] if fi_list else []
    # feature statistics for drift monitoring
    feat_stats = {}
    try:
        import numpy as _np
        for col in X_full.columns:
            try:
                series = X_full[col].astype(float)
                feat_stats[col] = {
                    'mean': float(series.mean()),
                    'std': float(series.std(ddof=0) or 0.0)
                }
            except Exception:
                continue
    except Exception:
        pass
    result = {
        'path': model_path,
        'samples': len(dataset),
        'symbols': dataset['symbol'].nunique(),
        'report': report,
        'model_type': model_obj['type'],
        'feature_importance': fi_list,
        'top_features': top_features,
        'validation': val_metrics if val_metrics else None,
        'train_size': int(len(X_train)),
        'val_size': int(len(X_val)) if has_validation else 0,
        'cv': cv_results if cv_results else None,
        'cv_mean_auc': (sum([c.get('auc',0) for c in cv_results])/len(cv_results)) if cv_results else None,
        'feature_stats': feat_stats or None,
    }
    if multi_horizons:
        try:
            result['horizons'] = sorted(set(dataset['horizon'].unique()))
        except Exception:
            pass
    return result

def load_model(model_path: str = DEFAULT_MODEL_PATH):
    if not os.path.exists(model_path):
        return None
    try:
        obj = joblib.load(model_path)
        return obj
    except Exception:
        return None

def calibrate_model(data_map: Dict[str, pd.DataFrame], model: Literal['rf','xgb','lgbm']='rf') -> Dict[str, Any]:
    """Load existing model and perform calibration-only (no retrain). Returns calibration metrics.
    Recomputes dataset to build validation slice; if no validation slice possible, raises.
    """
    # choose path
    if model == 'xgb':
        path = XGB_MODEL_PATH
    elif model == 'lgbm':
        path = LGBM_MODEL_PATH
    else:
        path = DEFAULT_MODEL_PATH
    model_obj = load_model(path)
    if model_obj is None:
        raise FileNotFoundError(f"Model file not found for {model}")
    dataset = collect_training_data(data_map)
    if dataset.empty:
        raise ValueError('No data for calibration')
    y_full = dataset['label']
    X_full = dataset.drop(columns=['label','symbol'])
    n = len(dataset)
    val_size = max(int(n*0.2), 50)
    if val_size >= n - 20:
        val_size = min(max(int(n*0.15),20), n//3)
    split_idx = n - val_size
    if split_idx < 30:
        raise ValueError('Not enough data to create validation slice for calibration')
    X_val = X_full.iloc[split_idx:]
    y_val = y_full.iloc[split_idx:]
    if y_val.nunique() < 2:
        raise ValueError('Validation slice lacks both classes')
    # align features
    feats = model_obj.get('features')
    try:
        X_val = X_val[feats]
    except Exception:
        raise ValueError('Feature mismatch for calibration')
    # get probabilities
    if model_obj.get('type') == 'xgb':
        import xgboost as xgb
        dval = xgb.DMatrix(X_val)
        val_prob = model_obj['model'].predict(dval)
    elif model_obj.get('type') == 'lgbm':
        val_prob = model_obj['model'].predict_proba(X_val)[:,1]
    else:
        val_prob = model_obj['model'].predict_proba(X_val)[:,1]
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression(max_iter=500)
    lr.fit(val_prob.reshape(-1,1), y_val)
    coef = float(lr.coef_[0][0]); intercept = float(lr.intercept_[0])
    model_obj['calibration'] = {'type':'platt','coef':coef,'intercept':intercept}
    joblib.dump(model_obj, path)
    # metrics
    val_pred = (val_prob > 0.5).astype(int)
    metrics = {
        'samples': n,
        'val_size': len(X_val),
        'report': classification_report(y_val, val_pred, output_dict=True)
    }
    try:
        metrics['auc'] = float(roc_auc_score(y_val, val_prob))
    except Exception:
        pass
    try:
        metrics['brier'] = float(brier_score_loss(y_val, val_prob))
    except Exception:
        pass
    try:
        metrics['log_loss'] = float(log_loss(y_val, val_prob))
    except Exception:
        pass
    metrics['calibrated'] = True
    return metrics

def predict_latest(df: pd.DataFrame, model_obj, horizon: int|None=None) -> float|None:
    """Return probability for latest row; supports multi-horizon container objects.
    If horizon specified and multi container provided, selects that horizon model; otherwise
    averages across available horizons.
    """
    if model_obj is None:
        return None
    # detect multi-horizon container
    if isinstance(model_obj, dict) and model_obj.get('multi') and 'models' in model_obj:
        models = model_obj.get('models') or {}
        # key types may be int or str
        chosen_keys = []
        if horizon is not None:
            for k in models.keys():
                if int(k) == int(horizon):
                    chosen_keys = [k]; break
        if not chosen_keys:
            chosen_keys = list(models.keys())
        probs = []
        for k in chosen_keys:
            sub = models[k]
            p = predict_latest(df, sub, None)  # recurse on plain model_obj
            if isinstance(p,(int,float)):
                probs.append(p)
        if probs:
            return float(sum(probs)/len(probs))
        return None
    feats = model_obj.get('features')
    model = model_obj.get('model')
    from .feature_engineering import compute_features
    f = compute_features(df)
    if f.empty:
        return None
    try:
        f = f[feats].tail(1)
    except Exception:
        return None
    mtype = model_obj.get('type')
    try:
        if mtype == 'xgb':
            import xgboost as xgb
            prob = float(model.predict(xgb.DMatrix(f))[0])
        elif mtype == 'lgbm':
            prob = float(model.predict_proba(f)[0][1])
        elif mtype == 'rf':
            prob = float(model.predict_proba(f)[0][1])
        else:
            # unknown model type
            return None
    except Exception:
        return None
    try:
        calib = model_obj.get('calibration')
        if calib and calib.get('type') == 'platt':
            coef = calib.get('coef'); intercept = calib.get('intercept')
            if isinstance(coef,(int,float)) and isinstance(intercept,(int,float)):
                z = coef * prob + intercept
                prob = 1.0 / (1.0 + math.exp(-z))
    except Exception:
        pass
    return prob

def suggest_probability_threshold(probs, labels, metric: str = 'f1'):
    """Given validation probabilities and labels, brute-force threshold suggestion.
    metric options: 'f1','youden','precision_recall_balance'
    Returns dict with best threshold and metric score.
    """
    try:
        import numpy as _np
        import math
        if not probs or not labels or len(probs) != len(labels):
            return None
        arr_p = _np.array(probs, dtype=float)
        arr_y = _np.array(labels, dtype=int)
        best = {'threshold': 0.5, 'score': -1}
        for t in _np.linspace(0.05, 0.95, 19):
            pred = (arr_p >= t).astype(int)
            tp = ((pred==1) & (arr_y==1)).sum()
            fp = ((pred==1) & (arr_y==0)).sum()
            fn = ((pred==0) & (arr_y==1)).sum()
            tn = ((pred==0) & (arr_y==0)).sum()
            prec = tp / (tp+fp) if (tp+fp)>0 else 0.0
            rec = tp / (tp+fn) if (tp+fn)>0 else 0.0
            f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0.0
            youden = rec + (tn/(tn+fp) if (tn+fp)>0 else 0.0) - 1
            pr_bal = 1 - abs(prec - rec)
            if metric == 'youden': score = youden
            elif metric == 'precision_recall_balance': score = pr_bal
            else: score = f1
            if score > best['score']:
                best = {'threshold': float(round(t,3)), 'score': float(round(score,4)), 'f1': float(round(f1,4)), 'precision': float(round(prec,4)), 'recall': float(round(rec,4))}
        return best
    except Exception:
        return None

def optimize_scoring_weights(rows, metric: str = 'corr'):
    """Placeholder weight optimization: evaluate simple grid for correlation of score with R:R or ml_prob.
    rows: list of dicts from scan results including ml_prob and rr
    metric: 'corr' or 'prob_rr_harmonic'
    Returns dict of suggested weights.
    """
    try:
        import numpy as _np
        if not rows:
            return None
        rr = _np.array([r.get('rr',0.0) for r in rows], dtype=float)
        prob = _np.array([r.get('ml_prob',0.5) if isinstance(r.get('ml_prob'),(int,float)) else 0.5 for r in rows], dtype=float)
        if rr.size == 0 or prob.size == 0:
            return None
        candidates = [
            (0.6,0.2,0.15,0.05),
            (0.5,0.3,0.15,0.05),
            (0.55,0.25,0.15,0.05),
            (0.4,0.4,0.15,0.05),
            (0.5,0.2,0.2,0.1)
        ]
        best = None; best_score = -1
        for w_prob,w_rr,w_fresh,w_pat in candidates:
            # simple synthetic features
            freshness = _np.linspace(1,0,len(prob))  # placeholder monotonic decay
            pattern = _np.ones_like(prob)*0.5
            score = w_prob*prob + w_rr*(rr/3.0).clip(0,1) + w_fresh*freshness + w_pat*pattern
            if metric == 'prob_rr_harmonic':
                import math
                hm = 0.0
                try:
                    hm = len(score) / ((1/prob)+(1/(rr+1e-9))).mean()
                except Exception:
                    hm = 0.0
                mscore = hm
            else:
                # correlation with rr
                if rr.std() == 0 or score.std()==0:
                    mscore = 0.0
                else:
                    mscore = float(_np.corrcoef(score, rr)[0,1])
            if mscore > best_score:
                best_score = mscore
                best = {'w_prob':w_prob,'w_rr':w_rr,'w_fresh':w_fresh,'w_pattern':w_pat,'metric':metric,'score':float(round(mscore,4))}
        return best
    except Exception:
        return None


# ============================================================================
# HISTORICAL MULTI-HORIZON TRAINING FUNCTIONS  
# ============================================================================

def train_multi_horizon_model(cutoff_date: str, horizon_days: int, algorithm: str = 'rf', 
                              data_map: Dict[str, pd.DataFrame] = None,
                              progress_cb: Optional[Callable[[Dict[str,Any]], None]] = None) -> str:
    """
    אימון מודל עד תאריך מסוים עם אופק זמן ספציפי
    
    Args:
        cutoff_date: תאריך גבול לנתונים (YYYY-MM-DD)
        horizon_days: אופק החזאי (1, 5, או 10 ימים)
        algorithm: RF/XGB/LGBM
        data_map: נתוני מניות (אם לא סופק - ינסה לטעון)
        progress_cb: callback לעדכון התקדמות
    
    Returns:
        נתיב למודל שנשמר
    """
    import os
    from datetime import datetime
    
    if progress_cb:
        progress_cb({'phase': 'multi_horizon_start', 'cutoff_date': cutoff_date, 
                    'horizon': horizon_days, 'algorithm': algorithm})
    
    # בדיקת תקינות פרמטרים (לא להגביל רק ל-1/5/10 – לאפשר גם 20 וכד')
    if not isinstance(horizon_days, int) or horizon_days <= 0 or horizon_days > 250:
        raise ValueError(f"Invalid horizon {horizon_days} (must be 1..250)")
    
    if algorithm.lower() not in ['rf', 'xgb', 'lgbm']:
        raise ValueError(f"Algorithm must be rf/xgb/lgbm, got {algorithm}")
    
    try:
        cutoff_dt = datetime.strptime(cutoff_date, '%Y-%m-%d')
    except:
        raise ValueError(f"Invalid date format: {cutoff_date}. Use YYYY-MM-DD")
    
    # טעינת נתונים אם לא סופקו
    if data_map is None:
        if progress_cb:
            progress_cb({'phase': 'loading_data', 'cutoff_date': cutoff_date})
        
        # כאן צריך לטעון נתונים מהמערכת הקיימת
        # כרגע נשתמש בplaceholder
        from data.data_utils import load_json
        try:
            data_map = load_json()  # או פונקציה אחרת שטוענת נתונים
        except:
            raise RuntimeError("Could not load data_map. Please provide it explicitly.")
    
    # סינון נתונים עד תאריך הגבול
    filtered_data_map = filter_data_until_date(data_map, cutoff_date)
    if progress_cb:
        try:
            progress_cb({'phase': 'filtered_symbols', 'symbols': len(filtered_data_map), 'horizon': horizon_days})
        except Exception:
            pass
    
    if progress_cb:
        progress_cb({'phase': 'building_labels', 'horizon': horizon_days, 'symbols': len(filtered_data_map)})
    
    # בניית dataset עם labels מותאמים לאופק
    training_dataset = build_multi_horizon_dataset(filtered_data_map, horizon_days, progress_cb)
    
    if training_dataset.empty:
        raise RuntimeError(f"No training data available for horizon {horizon_days}D until {cutoff_date}")
    
    if progress_cb:
        progress_cb({'phase': 'training_model', 'algorithm': algorithm, 'dataset_size': len(training_dataset), 'horizon': horizon_days})
    
    # הכנת נתיב שמירה
    cutoff_clean = cutoff_date.replace('-', '')
    model_dir = f"ml/models/historical/{cutoff_clean}"
    os.makedirs(model_dir, exist_ok=True)
    model_filename = f"model_{algorithm.lower()}_{horizon_days}d.pkl"
    model_path = os.path.join(model_dir, model_filename)
    
    # אימון המודל בפועל
    result = train_model(
        data_map={f'combined_{horizon_days}d': training_dataset},  # hack לעבור את הvalidation
        model=algorithm.lower(),
        model_path=model_path,
        progress_cb=progress_cb
    )
    
    if progress_cb:
        progress_cb({'phase': 'multi_horizon_complete', 'model_path': model_path, 'result': result, 'horizon': horizon_days})
    
    return model_path


def filter_data_until_date(data_map: Dict[str, pd.DataFrame], cutoff_date: str) -> Dict[str, pd.DataFrame]:
    """
    סינון נתוני מניות עד תאריך מסוים
    
    Args:
        data_map: מיפוי symbol -> DataFrame
        cutoff_date: תאריך גבול (YYYY-MM-DD)
    
    Returns:
        data_map מסונן
    """
    from datetime import datetime
    import pandas as pd
    

    
    cutoff_dt = datetime.strptime(cutoff_date, '%Y-%m-%d')
    filtered_map = {}
    
    for symbol, df in data_map.items():
        if df is None or df.empty:
            continue
            
        # בדיקה שיש עמודת תאריך או index תאריכים  
        if isinstance(df.index, pd.DatetimeIndex) or hasattr(df.index, 'to_pydatetime'):
            # Index הוא תאריכים (יכול להיות עם timezone)
            try:
                idx = df.index
                cutoff_ts = pd.Timestamp(cutoff_dt)
                # יישור timezones אם צריך
                if getattr(idx, 'tz', None) is not None and cutoff_ts.tzinfo is None:
                    # index tz-aware, cutoff naive -> תן cutoff tz של האינדקס
                    cutoff_ts = cutoff_ts.tz_localize(idx.tz)  # type: ignore
                elif getattr(idx, 'tz', None) is None and cutoff_ts.tzinfo is not None:
                    # index naive, cutoff tz-aware -> הפוך ל-naive
                    cutoff_ts = cutoff_ts.tz_convert(None)  # type: ignore
                # במידה ושניהם tz-aware אך שונים -> המרה ל-UTC
                if getattr(idx, 'tz', None) is not None and cutoff_ts.tzinfo is not None and str(idx.tz) != str(cutoff_ts.tzinfo):
                    try:
                        cutoff_ts = cutoff_ts.tz_convert(idx.tz)  # type: ignore
                    except Exception:
                        # fallback: הפוך את שניהם ל-naive
                        idx = idx.tz_convert(None)  # type: ignore
                        cutoff_ts = pd.Timestamp(cutoff_ts.tz_convert(None))  # type: ignore
                mask = idx <= cutoff_ts
                filtered_df = df.loc[mask]
            except Exception as e:
                print(f"[FILTER] timezone compare failed for {symbol}: {e}")
                # fallback naive compare
                try:
                    idx_naive = df.index
                    if getattr(idx_naive, 'tz', None) is not None:
                        idx_naive = idx_naive.tz_convert(None)  # type: ignore
                    cutoff_naive = pd.Timestamp(cutoff_dt)
                    mask = idx_naive <= cutoff_naive
                    filtered_df = df.loc[mask]
                except Exception:
                    continue
        elif 'Date' in df.columns:
            # יש עמודת Date
            df_copy = df.copy()
            df_copy['Date'] = pd.to_datetime(df_copy['Date'], errors='coerce')
            # טיפול ב-timezone
            if getattr(df_copy['Date'].dt, 'tz', None) is not None:
                try:
                    df_copy['Date'] = df_copy['Date'].dt.tz_convert(None)
                except Exception:
                    try:
                        df_copy['Date'] = df_copy['Date'].dt.tz_localize(None)
                    except Exception:
                        pass
            mask = df_copy['Date'] <= pd.Timestamp(cutoff_dt)
            filtered_df = df_copy.loc[mask]
        else:
            # אין מידע תאריכים - נניח שהנתונים כבר מסודרים כרונולוגית
            # ונקח רק חלק מהנתונים (זהירות!)
            print(f"Warning: No date info for {symbol}, taking first 80% of data")
            take_rows = int(len(df) * 0.8)
            filtered_df = df.head(take_rows) if take_rows > 0 else df
        
        if len(filtered_df) >= 50:  # מינימום נתונים לאימון
            filtered_map[symbol] = filtered_df
    
    return filtered_map


def build_multi_horizon_dataset(data_map: Dict[str, pd.DataFrame], horizon_days: int,
                               progress_cb: Optional[Callable[[Dict[str,Any]], None]] = None) -> pd.DataFrame:
    """
    בניית dataset אימון עם labels מותאמים לאופק זמן
    
    Args:
        data_map: נתוני מניות מסוננים
        horizon_days: אופק החזאי (1, 5, 10)
        progress_cb: callback התקדמות
    
    Returns:
        DataFrame מוכן לאימון עם labels מותאמים
    """
    from .feature_engineering import build_training_frame
    import pandas as pd
    
    frames = []
    total_symbols = len(data_map)
    
    for i, (symbol, df) in enumerate(data_map.items()):
        # granular progress every 50 symbols (or first) for smoother UI between 10..25%
        if progress_cb and (i == 0 or i % 50 == 0):
            try:
                progress_cb({'phase': 'build_labels_tick', 'i': i, 'total': total_symbols})
            except Exception:
                pass
        
        if df is None or len(df) < 50:
            continue
            
        try:
            # בניית פיצ'רים רגילה
            features_df = build_training_frame(df)
            
            if features_df.empty:
                continue
            
            # החלפת Labels ב-horizon specific labels
            horizon_labels = build_labels_for_horizon(df, horizon_days)
            
            # התאמת גדלים
            min_len = min(len(features_df), len(horizon_labels))
            if min_len > 0:
                features_df = features_df.tail(min_len).copy()
                features_df['label'] = horizon_labels.tail(min_len).values
                features_df['symbol'] = symbol
                frames.append(features_df)
                
        except Exception as e:
            if progress_cb:
                progress_cb({'phase': 'build_labels_error', 'symbol': symbol, 'error': str(e)})
            continue
    
    if not frames:
        return pd.DataFrame()
    
    combined_df = pd.concat(frames, ignore_index=True)
    
    if progress_cb:
        try:
            progress_cb({'phase': 'build_labels_complete', 'total_rows': len(combined_df), 
                        'positive_rate': combined_df['label'].mean()})
        except Exception:
            pass
    
    return combined_df


def build_labels_for_horizon(df: pd.DataFrame, horizon_days: int) -> pd.Series:
    """
    בניית labels לאופק זמן ספציפי
    
    Args:
        df: נתוני מניה (עם Close)
        horizon_days: אופק זמן (1, 5, 10 ימים)
    
    Returns:
        Series של labels (1=הצלחה, 0=כישלון)
        
    Logic:
        לכל שורה, בדוק מחיר אחרי horizon_days ימי עסקים
        אם המחיר עלה ב-1%+ → label=1, אחרת label=0
    """
    import pandas as pd
    import numpy as np
    
    if 'Close' not in df.columns:
        raise ValueError("DataFrame must have 'Close' column")
    
    close_prices = df['Close'].copy()
    labels = pd.Series(0, index=close_prices.index, dtype=int)
    
    # עבור כל תאריך, בדוק מה קורה אחרי horizon_days
    for i in range(len(close_prices) - horizon_days):
        current_price = close_prices.iloc[i]
        
        # מחיר אחרי horizon_days (פשוט עם offset - לא ימי עסקים מדויקים)
        future_idx = min(i + horizon_days, len(close_prices) - 1)
        future_price = close_prices.iloc[future_idx]
        
        # בדיקת הצלחה - עלייה של 1%+
        if pd.notna(current_price) and pd.notna(future_price) and current_price > 0:
            return_pct = (future_price - current_price) / current_price
            labels.iloc[i] = 1 if return_pct >= 0.01 else 0  # 1%+ = הצלחה
    
    return labels


def get_business_day_offset(start_date: str, offset_days: int) -> str:
    """
    חישוב תאריך + offset ימי עסקים
    
    Args:
        start_date: תאריך התחלה (YYYY-MM-DD)
        offset_days: מספר ימי עסקים להוסיף
    
    Returns:
        תאריך חדש (YYYY-MM-DD)
    """
    from datetime import datetime, timedelta
    import pandas as pd
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    
    # שימוש ב-pandas business day offset
    from pandas.tseries.offsets import BDay
    result_dt = start_dt + BDay(offset_days)
    
    return result_dt.strftime('%Y-%m-%d')


def test_multi_horizon_training():
    """
    בדיקת תקינות למערכת multi-horizon
    """
    print("🧪 Testing Multi-Horizon Training System...")
    
    try:
        # בדיקה 1: סינון תאריכים
        print("  Testing date filtering...")
        import pandas as pd
        # צור נתונים גדולים יותר כדי לעבור את המינימום של 50 שורות
        large_sample_data = {
            'TEST': pd.DataFrame({
                'Close': list(range(100, 200)),  # 100 שורות
                'Volume': list(range(1000, 2000, 10))
            }, index=pd.date_range('2024-06-01', periods=100))
        }
        
        filtered = filter_data_until_date(large_sample_data, '2024-06-30')
        
        # צריך להיות 30 ימים (יוני)
        if 'TEST' in filtered and len(filtered['TEST']) == 30:
            print("    ✅ Date filtering works")
        else:
            actual_len = len(filtered.get('TEST', [])) if 'TEST' in filtered else 0
            print(f"    ❌ Date filtering failed: expected 30, got {actual_len}")
            return False
        
        # בדיקה 2: בניית labels
        print("  Testing label building...")
        test_df = pd.DataFrame({
            'Close': [100, 102, 101, 105, 103]  # +2%, +1%, +4%, -2%
        })
        
        labels_1d = build_labels_for_horizon(test_df, 1)
        # אמור להיות [1, 0, 1, 0] (רק 4 כי האחרון לא יכול להיבדק)
        
        if len(labels_1d) == 5 and labels_1d.iloc[0] == 1:  # +2% = success
            print("    ✅ Label building works")
        else:
            print(f"    ❌ Label building failed: {labels_1d.tolist()}")
            return False
        
        print("  ✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed with error: {e}")
        return False
