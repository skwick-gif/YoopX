import json
import datetime
import pathlib
import traceback
import pandas as pd
from PySide6.QtCore import Signal, QThread


class WorkerThread(QThread):
    """Legacy WorkerThread extracted from main_content.py for scan/backtest/optimize.
    Kept minimal and compatible with UI consumers in the project.
    """
    progress_updated = Signal(int)
    status_updated = Signal(str)
    results_ready = Signal(object)
    error_occurred = Signal(str)
    finished_work = Signal()

    def __init__(self, operation_type, params, data_map):
        super().__init__()
        self.operation_type = operation_type
        self.params = params
        self.data_map = data_map
        self.is_cancelled = False

    def _normalize_symbols_param(self, params):
        """Normalize symbols param to list of strings."""
        symbols = params.get('symbols', [])
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(',') if s.strip()]
        elif not isinstance(symbols, list):
            symbols = []
        return symbols

    def _normalize_strategies_param(self, params):
        """Normalize strategies param to list of strings."""
        strategies = params.get('strategies', [])
        if isinstance(strategies, str):
            strategies = [s.strip() for s in strategies.split(',') if s.strip()]
        elif not isinstance(strategies, list):
            strategies = []
        return strategies

    def _validate_df(self, df, symbol):
        """Validate DataFrame: check for datetime index, Close column, minimum rows."""
        if df is None:
            return False, None, f"No data for symbol {symbol}"
        if not hasattr(df, 'index') or not hasattr(df, 'columns'):
            return False, None, f"Invalid DataFrame for {symbol}"
        if not isinstance(df.index, pd.DatetimeIndex):
            return False, None, f"DataFrame index not datetime for {symbol}"
        if 'Close' not in df.columns:
            return False, None, f"Missing 'Close' column for {symbol}"
        if len(df) < 50:
            return False, None, f"Insufficient data rows for {symbol} (need at least 50)"
        return True, df, ""

    def _write_log(self, entry):
        """Write newline-delimited JSON to logs/backtest_debug.log."""
        try:
            outdir = pathlib.Path('logs')
            outdir.mkdir(exist_ok=True)
            log_path = outdir / 'backtest_debug.log'
            with open(log_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception:
            pass

    def run(self):
        try:
            if self.operation_type == "scan":
                self.run_scan()
            elif self.operation_type == "backtest":
                self.run_backtest()
            elif self.operation_type == "optimize":
                self.run_optimize()
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

    def run_scan(self):
        results = []
        symbols = list(self.data_map.keys()) if self.data_map else ['AAPL', 'MSFT', 'GOOGL']
        # Normalize and filter symbols if provided in params
        param_symbols = self._normalize_symbols_param(self.params)
        if param_symbols:
            symbols = [s for s in symbols if s.upper() in [ps.upper() for ps in param_symbols]]
        total = len(symbols)

        for i, symbol in enumerate(symbols):
            if self.is_cancelled:
                break
            try:
                # Log start
                self._write_log({'symbol': symbol, 'operation': 'scan', 'status': 'start', 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
                
                try:
                    import backend
                except Exception:
                    try:
                        self.error_occurred.emit("Cannot import backend.py — please ensure backend.py is present and importable")
                    except Exception:
                        pass
                    results.append({'symbol': symbol, 'pass': 'ERROR', 'signal': 'ERROR', 'age': 0, 'price': '', 'rr': 'ERROR', 'patterns': '', 'error': 'Missing backend'})
                    self._write_log({'symbol': symbol, 'operation': 'scan', 'status': 'error', 'error': 'Missing backend', 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
                    continue

                strategy = self.params.get('scan_strategy') if isinstance(self.params, dict) else None
                if not strategy:
                    strategy = self.params.get('strategy') if isinstance(self.params, dict) else None
                if not strategy:
                    strategy = 'Donchian Breakout'

                df = self.data_map.get(symbol) if self.data_map else None
                # Validate DataFrame
                valid, df_valid, err_msg = self._validate_df(df, symbol)
                if not valid:
                    results.append({'symbol': symbol, 'pass': 'ERROR', 'signal': 'ERROR', 'age': 0, 'price': '', 'rr': 'ERROR', 'patterns': '', 'error': err_msg})
                    self._write_log({'symbol': symbol, 'operation': 'scan', 'status': 'invalid_df', 'error': err_msg, 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
                    continue

                now, age, price_at_signal = backend.scan_signal(df_valid, strategy, self.params or {})

                patterns_txt = ''
                try:
                    patterns_txt = (self.params.get('patterns') or '') if isinstance(self.params, dict) else ''
                except Exception:
                    patterns_txt = ''
                selected = [p.strip().upper() for p in patterns_txt.split(',') if p.strip()]
                detected = []
                try:
                    detected = backend.detect_patterns(df_valid, int(self.params.get('lookback', 30) if isinstance(self.params, dict) else 30), selected)
                except Exception:
                    detected = []

                rr_val = None
                rr_target = (self.params.get('rr_target') if isinstance(self.params, dict) else None) or '2xATR'
                try:
                    if rr_target == '2xATR':
                        atr_series = None
                        try:
                            atr_series = backend.atr(df_valid)
                        except Exception:
                            try:
                                from logic.indicators import atr as _atr
                                atr_series = _atr(df_valid)
                            except Exception:
                                atr_series = None
                        if atr_series is not None and len(atr_series) > 0:
                            last_atr = float(atr_series.iloc[-1])
                            if last_atr > 0 and price_at_signal:
                                try:
                                    p = float(price_at_signal)
                                    if now and str(now).lower().startswith('buy'):
                                        target = p + 2.0 * last_atr
                                        stop = p - 1.0 * last_atr
                                    elif now and str(now).lower().startswith('sell'):
                                        target = p - 2.0 * last_atr
                                        stop = p + 1.0 * last_atr
                                    else:
                                        target = p + 2.0 * last_atr
                                        stop = p - 1.0 * last_atr
                                    rr_val = abs((target - p) / (p - stop)) if (p - stop) != 0 else None
                                except Exception:
                                    rr_val = None
                    else:
                        rr_val = 2.0
                except Exception:
                    rr_val = None

                try:
                    rr_num = float(rr_val) if rr_val is not None else 0.0
                except Exception:
                    rr_num = 0.0

                min_rr = float(self.params.get('min_rr', 0.0)) if isinstance(self.params, dict) else 0.0
                passed = 'Pass' if rr_num >= min_rr and now and now != 'Hold' else 'Fail'

                result = {
                    'symbol': symbol,
                    'pass': passed,
                    'signal': now,
                    'age': int(age) if age is not None else 0,
                    'price': float(price_at_signal) if price_at_signal is not None else '',
                    'rr': round(rr_num, 3) if isinstance(rr_num, (int, float)) else rr_num,
                    'patterns': ','.join(detected) if detected else ''
                }
                results.append(result)
                self._write_log({'symbol': symbol, 'operation': 'scan', 'status': 'ok', 'signal': now, 'rr': rr_num, 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                results.append({'symbol': symbol, 'pass': 'ERROR', 'signal': 'ERROR', 'age': 0, 'price': '', 'rr': 'ERROR', 'patterns': '', 'error': f"{e}\n{tb}"})
                self._write_log({'symbol': symbol, 'operation': 'scan', 'status': 'exception', 'error': str(e), 'traceback': tb, 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})

            try:
                self.progress_updated.emit(int((i+1)/total*100))
                self.status_updated.emit(f"סריקה: {i+1}/{total} ({symbol})")
            except Exception:
                pass

        self.results_ready.emit(results)

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
            import pathlib, json, datetime
            outdir = pathlib.Path('logs')
            outdir.mkdir(exist_ok=True)
            log_path = outdir / 'backtest_filter.log'
            def _write_log(entry: dict):
                try:
                    with open(log_path, 'a', encoding='utf-8') as fh:
                        fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
                except Exception:
                    pass

            ts = datetime.datetime.utcnow().isoformat() + 'Z'
            _write_log({'ts': ts, 'event': 'filter_summary', 'requested_symbols': param_syms, 'universe_limit': universe_limit, 'before_count': len(original_symbols), 'after_count': len(symbols)})
            excluded = [s for s in original_symbols if s not in symbols]
            for s in excluded:
                reason = 'excluded_by_symbol_filter' if param_syms and s.upper() not in param_syms else 'excluded_by_universe_limit'
                _write_log({'ts': ts, 'event': 'symbol_excluded', 'symbol': s, 'reason': reason})
        except Exception:
            def _write_log(entry: dict):
                return

        strategies = self._normalize_strategies_param(self.params)
        if not strategies:
            strategies = list(getattr(backend, 'STRAT_MAP', {}).keys())
        start_cash = self.params.get('start_cash', 10000)
        commission = self.params.get('commission', 0.0005)
        slippage = self.params.get('slippage', 0.0005)
        for i, symbol in enumerate(symbols):
            if self.is_cancelled:
                break
            df = self.data_map[symbol]
            # Validate DataFrame
            valid, df_valid, err_msg = self._validate_df(df, symbol)
            if not valid:
                symbol_results = [{'symbol': symbol, 'strategy': 'ALL', 'final_value': 'ERROR', 'sharpe': 'ERROR', 'max_dd': 'ERROR', 'win_rate': 'ERROR', 'trades': 'ERROR', 'cagr': 'ERROR', 'error': err_msg}]
                results.extend(symbol_results)
                self._write_log({'symbol': symbol, 'operation': 'backtest', 'status': 'invalid_df', 'error': err_msg, 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
                continue
            symbol_results = []
            for strat_name in strategies:
                try:
                    # Log start for each strategy
                    self._write_log({'symbol': symbol, 'strategy': strat_name, 'operation': 'backtest', 'status': 'start', 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
                    df_local = df_valid.copy() if df_valid is not None else df_valid
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
                    # attach equity / drawdown series if present
                    try:
                        if isinstance(summary, dict):
                            if summary.get('equity_series'):
                                result['equity_series'] = summary.get('equity_series')
                            if summary.get('drawdown_series'):
                                result['drawdown_series'] = summary.get('drawdown_series')
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
                            # derive aggregate quick stats
                            try:
                                holds = [t.get('hold_days') for t in summary['trade_list'] if isinstance(t, dict) and t.get('hold_days') is not None]
                                pct_rets = [t.get('pct_return') for t in summary['trade_list'] if isinstance(t, dict) and t.get('pct_return') is not None]
                                if holds:
                                    result['avg_hold_days'] = float(sum(holds)/len(holds))
                                if pct_rets:
                                    result['avg_trade_return_pct'] = float(sum(pct_rets)/len(pct_rets))
                            except Exception:
                                pass
                        elif 'trade_analyzer' in summary:
                            result['trade_details'] = summary['trade_analyzer']
                        else:
                            for k in summary.keys():
                                if k.lower().startswith('trade'):
                                    result['trade_details'] = summary.get(k)
                                    break
                    symbol_results.append(result)
                    self._write_log({'symbol': symbol, 'strategy': strat_name, 'operation': 'backtest', 'status': 'ok', 'final_value': result.get('final_value'), 'sharpe': result.get('sharpe'), 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    symbol_results.append({
                        'symbol': symbol,
                        'strategy': strat_name,
                        'final_value': 'ERROR',
                        'sharpe': 'ERROR',
                        'max_dd': 'ERROR',
                        'win_rate': 'ERROR',
                        'trades': 'ERROR',
                        'cagr': 'ERROR',
                        'error': f"{e}\n{tb}"
                    })
                    self._write_log({'symbol': symbol, 'strategy': strat_name, 'operation': 'backtest', 'status': 'exception', 'error': str(e), 'traceback': tb, 'ts': datetime.datetime.utcnow().isoformat() + 'Z'})
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

            total = len(grid)
            for i, params in enumerate(grid):
                if self.is_cancelled:
                    break
                scores = []
                agg = {'Sharpe':0.0, 'CAGR_pct':0.0, 'MaxDD_pct':0.0, 'WinRate_pct':0.0, 'Trades':0}
                cnt = 0
                for sym in symbols:
                    df = self.data_map.get(sym)
                    if df is None or len(df) < 50:
                        continue
                    try:
                        _, summ = backend.run_backtest(df, self.params.get('strategy') or params.get('strategy') or 'SMA Cross', params,
                                                       self.params.get('start_cash', 10000),
                                                       self.params.get('commission', 0.0005),
                                                       self.params.get('slippage', 0.0005),
                                                       0.01, 0.0, None, False)
                        trades = summ.get('Trades', 0) or 0
                        if trades < int(self.params.get('min_trades', 1)):
                            continue
                        score = backend.objective_score(summ, objective)
                        scores.append(score)
                        for k in ('Sharpe','CAGR_pct','MaxDD_pct','WinRate_pct','Trades'):
                            agg[k] += float(summ.get(k, 0.0) or 0.0)
                        cnt += 1
                    except Exception:
                        continue

                if scores:
                    mean_score = float(sum(scores)/len(scores))
                    if cnt > 0:
                        for k in agg:
                            agg[k] = agg[k] / cnt
                    results.append({
                        'params': params,
                        'score': mean_score,
                        'sharpe': agg['Sharpe'],
                        'cagr': agg['CAGR_pct'],
                        'max_dd': agg['MaxDD_pct'],
                        'win_rate': agg['WinRate_pct'],
                        'trades': int(agg['Trades'])
                    })

                try:
                    self.progress_updated.emit(int((i+1)/max(1,total)*100))
                except Exception:
                    pass

            results = sorted(results, key=lambda r: -float(r.get('score', 0)))
            for idx, r in enumerate(results, start=1):
                r['rank'] = idx

            self.results_ready.emit(results)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.error_occurred.emit(f"Optimize failed: {e}\n{tb}")

    def cancel(self):
        self.is_cancelled = True


