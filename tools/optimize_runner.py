"""Parallel optimize runner using backend.run_backtest, param_grid_from_ranges and walk_forward_splits.

Usage: import tools.optimize_runner and call run_optimization(...)
This module runs independent backtests in subprocesses and aggregates objective scores.
"""
from __future__ import annotations
import concurrent.futures
import itertools
import csv
import os
import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Worker must be at top level so it can be pickled by ProcessPoolExecutor
def _worker_run_backtest(df_slice: pd.DataFrame, strategy_name: str, params: Dict[str, Any],
                         start_cash: float, commission: float, slippage_perc: float,
                         figscale: float, x_margin: float, plot: bool) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Import backend in worker and run a single backtest on df_slice.
    Returns (summary, error_str)
    """
    try:
        # Import here so subprocess has correct import context
        import backend as be
        # backend.run_backtest returns (figs, summary) for single-df runs
        figs, summary = be.run_backtest(df_slice, params.get('__strategy_name_placeholder__', strategy_name), params,
                                        start_cash, commission, slippage_perc, figscale, x_margin, None, plot)
        return summary, None
    except Exception as e:
        return None, str(e)


def _score_for_combo_on_splits(df: pd.DataFrame, strategy_name: str, params: Dict[str, Any],
                               splits: List[Tuple[int,int,int,int]], objective: str,
                               start_cash: float, commission: float, slippage_perc: float,
                               figscale: float, x_margin: float, plot: bool) -> Dict[str, Any]:
    """Run a param combo across the given splits (walk-forward) and return fold scores and average score."""
    from backend import objective_score
    fold_scores = []
    fold_summaries = []
    for (train_start, train_end, test_start, test_end) in splits:
        # Use out-of-sample window for scoring
        df_oos = df.iloc[test_start:test_end]
        if df_oos.empty:
            fold_scores.append(float('nan'))
            fold_summaries.append({'error': 'empty_oos'})
            continue
        summary, err = None, None
        # run in-process call; keep lightweight here (used when not parallelizing across folds)
        try:
            # call backend directly to avoid extra subprocess overhead
            import backend as be
            _, summary = be.run_backtest(df_oos, strategy_name, params, start_cash, commission, slippage_perc, figscale, x_margin, None, plot)
        except Exception as e:
            summary = {'error': str(e)}
        fold_summaries.append(summary)
        score = objective_score(summary, objective)
        fold_scores.append(float(score))
    # compute aggregated score (mean of non-nan)
    valid = [s for s in fold_scores if s == s]
    avg = float(sum(valid)/len(valid)) if valid else float('nan')
    return {'params': params, 'fold_scores': fold_scores, 'avg_score': avg, 'fold_summaries': fold_summaries}


def run_optimization(df: Any, strategy_name: str, base_params: Dict[str, Any],
                     param_grid: List[Dict[str, Any]], folds: int = 3, oos_frac: float = 0.2,
                     objective: str = 'Sharpe', max_workers: int = 4,
                     start_cash: float = 10000.0, commission: float = 0.0005, slippage_perc: float = 0.0005,
                     figscale: float = 1.0, x_margin: float = 0.1, plot: bool = False,
                     output_csv: Optional[str] = None, checkpoint_csv: Optional[str] = None) -> List[Dict[str, Any]]:
    """Run optimization over the provided parameter grid using walk-forward splits.

    Args:
      df: pandas.DataFrame or dict of symbol->DataFrame. If dict, results are aggregated across symbols by averaging combo scores.
      strategy_name: name of strategy (must exist in STRAT_MAP in logic/strategies.py)
      base_params: base params to merge with each combo
      param_grid: list of param dicts (from backend.param_grid_from_ranges)
      folds: number of walk-forward folds
      oos_frac: out-of-sample fraction for walk-forward
      objective: objective string passed to backend.objective_score
      max_workers: number of parallel worker processes
      output_csv: optional path to write results CSV

    Returns:
      list of result dicts sorted by avg_score descending.
    """
    from backend import walk_forward_splits
    results = []

    # checkpoint handling: use checkpoint_csv if provided, else fall back to output_csv
    checkpoint_path = checkpoint_csv or output_csv
    seen_params = set()
    if checkpoint_path:
        try:
            if os.path.isfile(checkpoint_path):
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        p = row.get('params') or row.get('params_json') or row.get('params_str')
                        if p:
                            # normalize JSON ordering to avoid dupes
                            try:
                                js = json.loads(p)
                                seen_params.add(json.dumps(js, sort_keys=True))
                            except Exception:
                                seen_params.add(p)
        except Exception:
            # non-fatal: continue without resume
            seen_params = set()

    # Accept dict of symbols
    is_multi = isinstance(df, dict)
    symbol_items = df.items() if is_multi else [(None, df)]

    # For each grid combo, compute score (average over symbols and folds)
    def _evaluate_combo_local(combo: Dict[str, Any]) -> Dict[str, Any]:
        # merge base params and combo
        params = dict(base_params or {})
        params.update(combo)
        per_symbol_scores = {}
        for sym, d in symbol_items:
            n = len(d)
            splits = walk_forward_splits(n, folds, oos_frac)
            # For symbol-level scoring, run folds sequentially in this process
            score_res = _score_for_combo_on_splits(d, strategy_name, params, splits, objective,
                                                   start_cash, commission, slippage_perc, figscale, x_margin, plot)
            per_symbol_scores[sym if sym is not None else 'single'] = score_res
        # Aggregate across symbols by averaging avg_score
        avg_scores = [v['avg_score'] for v in per_symbol_scores.values() if v['avg_score'] == v['avg_score']]
        final_avg = float(sum(avg_scores)/len(avg_scores)) if avg_scores else float('nan')
        return {'params': params, 'per_symbol': per_symbol_scores, 'avg_score': final_avg}

    # If max_workers <= 1 run sequentially in-process to avoid pickling/subprocess overhead
    # Safety guard for Windows: require caller to use __main__ guard or use sequential mode
    import sys
    if max_workers and max_workers > 1 and sys.platform == 'win32':
        # allow override via environment variable for explicit CLI/script runs
        allow = os.environ.get('OPTIMIZE_ALLOW_PARALLEL', '')
        if allow != '1':
            raise RuntimeError(
                "Parallel mode (max_workers>1) on Windows requires running under a script entrypoint. "
                "Set max_workers=1 to run sequentially or set environment OPTIMIZE_ALLOW_PARALLEL=1 when invoking from a dedicated script.")

    if not max_workers or max_workers <= 1:
        for combo in param_grid:
            # skip combos already present in checkpoint
            try:
                combo_key = json.dumps(combo, sort_keys=True)
            except Exception:
                combo_key = str(combo)
            if combo_key in seen_params:
                # optionally load previous result? we just skip duplicate combos
                continue
            try:
                res = _evaluate_combo_local(combo)
            except Exception as e:
                res = {'params': combo, 'error': str(e), 'avg_score': float('nan')}
            results.append(res)
            # write immediate checkpoint if requested
            if checkpoint_path:
                try:
                    write_header = not os.path.isfile(checkpoint_path)
                    with open(checkpoint_path, 'a', newline='', encoding='utf-8') as cf:
                        writer = csv.writer(cf)
                        if write_header:
                            writer.writerow(['avg_score', 'params'])
                        writer.writerow([res.get('avg_score'), json.dumps(res.get('params') or {}, ensure_ascii=False)])
                        # update seen set so resuming won't duplicate
                        try:
                            seen_params.add(json.dumps(res.get('params') or {}, sort_keys=True))
                        except Exception:
                            seen_params.add(str(res.get('params') or {}))
                except Exception:
                    pass
    else:
        # Run combos in parallel using ProcessPoolExecutor. Note: this requires
        # that the environment be able to pickle callables and dataframes.
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_evaluate_combo_local, combo): combo for combo in param_grid}
            for fut in concurrent.futures.as_completed(futures):
                combo = futures[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = {'params': combo, 'error': str(e), 'avg_score': float('nan')}
                results.append(res)

    # sort by avg_score desc
    results.sort(key=lambda r: (r.get('avg_score') if r.get('avg_score') == r.get('avg_score') else float('-inf')), reverse=True)

    # Optionally write CSV
    if output_csv:
        try:
            out_dir = os.path.dirname(output_csv)
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['rank', 'avg_score', 'params'])
                for i, r in enumerate(results, start=1):
                    writer.writerow([i, r.get('avg_score'), r.get('params')])
        except Exception:
            pass

    return results


def _cli_main():
    """Simple CLI for running optimization from command line.
    Usage: python -m tools.optimize_runner --csv data.csv --ranges ranges.json --max-workers 2 --checkpoint out.csv
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='Path to single-symbol CSV file (index/date + OHLCV)')
    parser.add_argument('--ranges', required=True, help='Path to ranges JSON file')
    parser.add_argument('--strategy', default='SMA Cross')
    parser.add_argument('--max-workers', type=int, default=1)
    parser.add_argument('--checkpoint', default=None)
    args = parser.parse_args()

    # allow parallel override for Windows when running via CLI
    if args.max_workers and args.max_workers > 1:
        os.environ['OPTIMIZE_ALLOW_PARALLEL'] = '1'

    import pandas as pd
    with open(args.ranges, 'r', encoding='utf-8') as f:
        ranges = json.load(f)
    df = pd.read_csv(args.csv, parse_dates=True, index_col=0)
    from backend import param_grid_from_ranges
    grid = param_grid_from_ranges(ranges)
    res = run_optimization(df, args.strategy, {}, grid, max_workers=args.max_workers, checkpoint_csv=args.checkpoint)
    print('Done, got', len(res), 'results')


if __name__ == '__main__':
    _cli_main()
