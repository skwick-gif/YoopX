from PySide6.QtCore import QObject, Signal
import datetime
from typing import Optional
import pandas as pd
import os


class DailyUpdateWorker(QObject):
    """Worker QObject to run the daily update plan in a QThread.

    Signals:
        progress(int): emits percent complete (0-100)
        status(str): emits human-readable status updates
        ticker_done(str, bool, object): ticker, success flag, optional meta/error
        finished(dict): final summary dict
        error(str): fatal error message
    """
    progress = Signal(int)
    status = Signal(str)
    ticker_done = Signal(str, bool, object)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, folder: str, parent: Optional[QObject] = None, merge_mode: str = 'none', use_apis: bool = False):
        """merge_mode: 'none' => write CSV only (dry-run),
        'two-step' => write CSV then merge into parquet, 'auto' => merge directly into parquet.
        use_apis: if True, try API providers (Polygon/AlphaVantage) as a final fallback after yfinance and scrape.
        """
        super().__init__(parent)
        self.folder = folder
        self._is_cancelled = False
        self.merge_mode = merge_mode or 'none'
        self.use_apis = bool(use_apis)

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            # local imports to avoid heavy startup when module imported
            from data.daily_update_new import plan_daily_update_new, execute_daily_update_plan
            from data.data_paths import get_data_paths
        except Exception as e:
            self.error.emit(f"Import error in worker: {e}")
            return

        try:
            # Get data paths for new structure
            paths = get_data_paths()
            
            # Create update plan using new system
            self.status.emit("Creating update plan...")
            plan_dict = plan_daily_update_new(
                raw_dir=paths['raw'], 
                processed_dir=paths['processed']
            )
            except Exception:
                # fallback: build plan from catalog if present, otherwise scan folder
                catalog_df = get_catalog(self.folder)
                entries = []
                if catalog_df is not None:
                    entries = [{'ticker': r['ticker'], 'src_path': r.get('src_path'), 'parquet_path': r.get('parquet_path'), 'last_date_present': r.get('max_date')} for _, r in catalog_df.iterrows()]
                else:
                    from data.data_utils import list_tickers_from_folder, get_last_date_for_ticker
                    tickers = list_tickers_from_folder(self.folder)
                    for t in tickers:
                        last = get_last_date_for_ticker(self.folder, t)
                        entries.append({'ticker': t, 'src_path': None, 'parquet_path': os.path.join(self.folder, '_parquet', f"{t}.parquet"), 'last_date_present': last})
                plan = {'data_dir': self.folder, 'plan': entries}

            entries = plan.get('plan', [])
            total = len(entries)
            done = 0
            successes = 0
            failures = []

            from data.data_utils import get_last_date_for_ticker
            from data.rate_limiter import GLOBAL_RATE_LIMITER
            limiter = GLOBAL_RATE_LIMITER
            t_start = datetime.datetime.utcnow()
            for entry in entries:
                if self._is_cancelled:
                    break
                ticker = entry.get('ticker')
                # determine the last date present (some entries may have None)
                last = entry.get('last_date_present')
                if last is None:
                    try:
                        last = get_last_date_for_ticker(self.folder, ticker)
                    except Exception:
                        last = None

                # compute date_from baseline (one day after last present) or default
                date_from = None
                if last is not None:
                    try:
                        ld = pd.to_datetime(last, utc=True)
                        date_from = (ld + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    except Exception:
                        date_from = None
                else:
                    date_from = '2024-01-01'

                # Gap detection (recent window) – if internal missing business days exist, backfill from earliest gap
                gap_start = None
                try:
                    pq_path = os.path.join(self.folder, '_parquet', f"{ticker}.parquet")
                    if os.path.exists(pq_path):
                        try:
                            # read only date-related columns if possible
                            existing_df = pd.read_parquet(pq_path)
                        except Exception:
                            existing_df = None
                        if existing_df is not None and not existing_df.empty:
                            # detect date column
                            dcol = None
                            for cand in ['date','Date','datetime','time']:
                                if cand in existing_df.columns:
                                    dcol = cand; break
                            if dcol is None:
                                # try index
                                if pd.api.types.is_datetime64_any_dtype(existing_df.index):
                                    existing_df = existing_df.reset_index().rename(columns={'index':'date'})
                                    dcol = 'date'
                            if dcol and dcol in existing_df.columns:
                                try:
                                    existing_df[dcol] = pd.to_datetime(existing_df[dcol], errors='coerce', utc=True)
                                    ex_dates = existing_df[dcol].dropna().dt.normalize().unique()
                                    if ex_dates.size > 10:
                                        # focus last 180 days to limit cost
                                        cutoff = pd.Timestamp.utcnow().normalize() - pd.Timedelta(days=180)
                                        ex = sorted([d for d in ex_dates if d >= cutoff])
                                        if len(ex) > 5:
                                            start_d = ex[0]; end_d = ex[-1]
                                            # expected business days range
                                            expected = pd.bdate_range(start=start_d, end=end_d)
                                            have = set([pd.Timestamp(d).normalize() for d in ex])
                                            missing = [d for d in expected if d not in have]
                                            if missing:
                                                gap_start = missing[0].strftime('%Y-%m-%d')
                                except Exception:
                                    pass
                except Exception:
                    pass
                # if detected gap earlier than our nominal date_from, adjust
                try:
                    if gap_start:
                        if date_from is None or pd.to_datetime(gap_start) < pd.to_datetime(date_from):
                            date_from = gap_start
                except Exception:
                    pass

                # Enhanced status with rate + ETA after first item
                if done > 0 and total > 0:
                    try:
                        elapsed = (datetime.datetime.utcnow() - t_start).total_seconds()
                        avg_per = elapsed / done if done else 0
                        remain = total - done
                        eta_sec = avg_per * remain if avg_per > 0 else 0
                        rate = (done / elapsed * 60.0) if elapsed > 0 else 0
                        eta_m = int(eta_sec // 60); eta_s = int(eta_sec % 60)
                        eta_str = f"{eta_m}m{eta_s:02d}s" if eta_sec >= 1 else "<1s"
                        self.status.emit(f"Fetching {ticker} {done+1}/{total} since {date_from or last} | {rate:.1f}/min | ETA {eta_str}")
                    except Exception:
                        self.status.emit(f"Fetching {ticker} {done+1}/{total} since {date_from or last}")
                else:
                    self.status.emit(f"Fetching {ticker} 1/{total} since {date_from or last}")
                try:
                    # attempt Yahoo fetcher first, then scrape fallback, then APIs (if enabled)
                    try:
                        limiter.wait('yahoo')
                    except Exception:
                        pass
                    df_new, meta = fetch_ohlcv_with_fallback(
                        ticker,
                        date_from,
                        use_apis=self.use_apis,
                        cancel_cb=lambda: self._is_cancelled
                    )
                    if df_new is not None and not df_new.empty:
                        # normalize date column
                        if 'date' not in df_new.columns:
                            df_new = df_new.reset_index()
                        df_new.columns = [str(c).strip() for c in df_new.columns]
                        try:
                            df_new['date'] = pd.to_datetime(df_new['date'], utc=True)
                        except Exception:
                            pass
                        # decide action based on merge_mode
                        log_entry = {'ticker': ticker, 'last_date': str(last), 'date_from': date_from, 'fetched_rows': int(len(df_new)), 'provider': meta.get('provider_used') or meta.get('source'), 'meta': meta, 'merge': None}
                        try:
                            import pathlib
                            outdir = pathlib.Path('tmp_live_fetch')
                            outdir.mkdir(exist_ok=True)
                        except Exception:
                            outdir = None

                        if self.merge_mode == 'none':
                            # dry-run: write CSV only for inspection
                            try:
                                if outdir is not None:
                                    fn = outdir / f"{ticker}.csv"
                                    df_new.to_csv(fn, index=False)
                                log_entry['merge'] = 'none:wrote_csv'
                            except Exception as e:
                                log_entry['merge'] = f'none:write_failed:{e}'
                        elif self.merge_mode == 'two-step':
                            # write CSV then merge via safe_append_parquet
                            try:
                                if outdir is not None:
                                    fn = outdir / f"{ticker}.csv"
                                    df_new.to_csv(fn, index=False)
                                ok = safe_append_parquet(self.folder, ticker, df_new, date_col='date')
                                log_entry['merge'] = 'two-step:merged' if ok else 'two-step:merge_failed'
                            except Exception as e:
                                log_entry['merge'] = f'two-step:error:{e}'
                        else:
                            # auto merge directly
                            try:
                                ok = safe_append_parquet(self.folder, ticker, df_new, date_col='date')
                                log_entry['merge'] = 'auto:merged' if ok else 'auto:merge_failed'
                            except Exception as e:
                                log_entry['merge'] = f'auto:error:{e}'

                        successes += 1
                        # emit ticker_done with detailed log entry
                        self.ticker_done.emit(ticker, True, log_entry)
                    else:
                        failures.append({'ticker': ticker, 'meta': meta})
                        self.ticker_done.emit(ticker, False, {'ticker': ticker, 'meta': meta})
                except Exception as e:
                    failures.append({'ticker': ticker, 'error': str(e)})
                    self.ticker_done.emit(ticker, False, {'ticker': ticker, 'error': str(e)})

                done += 1
                pct = int(done / total * 100) if total else 100
                self.progress.emit(pct)

            summary = {'total': total, 'done': done, 'successes': successes, 'failures': failures}
            self.status.emit(f"Daily update completed: {done}/{total} processed")
            self.finished.emit(summary)
        except Exception as e:
            self.error.emit(str(e))
