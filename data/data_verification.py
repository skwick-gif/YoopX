import os, datetime as _dt
import pandas as pd
from typing import Dict, Any, List

REQUIRED_COLS = ['Open','High','Low','Close','Volume']

def _count_weekend_days(start, end):
    # count weekend days between two dates exclusive
    cnt = 0
    cur = start + pd.Timedelta(days=1)
    while cur < end:
        if cur.weekday() >= 5:
            cnt += 1
        cur += pd.Timedelta(days=1)
    return cnt

def verify_data_consistency(data_dir: str) -> Dict[str, Any]:
    """Verify parquet dataset integrity.
    Checks:
      - Required columns present
      - Dates sorted, no duplicates
      - Gap detection (business-day approximation)
      - Last date recency (should be within 5 calendar days of today)
    Returns summary dict with per-ticker issues and aggregates.
    """
    parquet_root = os.path.join(data_dir, '_parquet')
    res: Dict[str, Any] = {
        'data_dir': data_dir,
        'timestamp': _dt.datetime.utcnow().isoformat()+ 'Z',
        'tickers': [],
        'issues': {},
        'ok_tickers': [],
        'gap_tickers': [],
        'missing_cols_tickers': [],
        'duplicate_date_tickers': [],
        'stale_tickers': [],
    }
    if not os.path.isdir(parquet_root):
        res['error'] = f"Parquet folder missing: {parquet_root}"
        return res
    files = [f for f in os.listdir(parquet_root) if f.endswith('.parquet')]
    for fname in files:
        ticker = os.path.splitext(fname)[0]
        path = os.path.join(parquet_root, fname)
        res['tickers'].append(ticker)
        issues: List[str] = []
        try:
            df = pd.read_parquet(path)
        except Exception as e:
            issues.append(f'read_error:{e}')
            res['issues'][ticker] = issues
            continue
        # identify date column
        date_col = None
        for c in ['date','Date','datetime','time']:
            if c in df.columns:
                date_col = c; break
        if date_col is None:
            # try index
            if df.index.name and 'date' in str(df.index.name).lower():
                date_col = df.index.name
                df = df.reset_index()
            else:
                issues.append('no_date_col')
                res['issues'][ticker] = issues
                continue
        try:
            df['__dt'] = pd.to_datetime(df[date_col], errors='coerce', utc=True)
            df = df.dropna(subset=['__dt']).sort_values('__dt').reset_index(drop=True)
        except Exception as e:
            issues.append(f'date_parse_error:{e}')
            res['issues'][ticker] = issues
            continue
        # duplicates
        dup_count = int(df['__dt'].duplicated().sum())
        if dup_count > 0:
            issues.append(f'duplicate_dates:{dup_count}')
            res['duplicate_date_tickers'].append(ticker)
        # missing columns
        missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing_cols:
            issues.append('missing_cols:'+','.join(missing_cols))
            res['missing_cols_tickers'].append(ticker)
        # gap detection
        gap_segments = []
        dates = df['__dt'].tolist()
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i-1]).days
            if delta > 1:
                weekend_days = _count_weekend_days(dates[i-1], dates[i])
                business_gap = delta - weekend_days
                # allow weekend bridging (business_gap <=1 acceptable)
                if business_gap > 1:
                    gap_segments.append({
                        'from': str(dates[i-1].date()),
                        'to': str(dates[i].date()),
                        'delta_days': int(delta),
                        'business_gap': int(business_gap)
                    })
        if gap_segments:
            issues.append(f'gaps:{len(gap_segments)}')
            res['gap_tickers'].append(ticker)
        # staleness (last date recency)
        last_dt = dates[-1]
        if (_dt.datetime.utcnow().replace(tzinfo=last_dt.tzinfo) - last_dt).days > 5:
            issues.append('stale_data')
            res['stale_tickers'].append(ticker)
        if issues:
            res['issues'][ticker] = issues
        else:
            res['ok_tickers'].append(ticker)
    res['total'] = len(res['tickers'])
    res['ok'] = len(res['ok_tickers'])
    res['with_issues'] = res['total'] - res['ok']
    return res

def write_verification_log(report: Dict[str, Any], log_path='logs/data_verification.log'):
    import json
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path,'a',encoding='utf-8') as f:
            f.write(json.dumps(report, ensure_ascii=False) + '\n')
    except Exception:
        pass
