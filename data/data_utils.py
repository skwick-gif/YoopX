import pandas as pd
import json
import numpy as np
import warnings
from typing import Optional

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
	"""Normalize common column names to canonical OHLCV names (case-insensitive)."""
	mapping = {}
	for c in df.columns:
		lc = str(c).strip().lower()
		if lc in ('open', 'o'):
			mapping[c] = 'Open'
		elif lc in ('high', 'h'):
			mapping[c] = 'High'
		elif lc in ('low', 'l'):
			mapping[c] = 'Low'
		elif lc in ('close', 'c'):
			mapping[c] = 'Close'
		elif lc in ('adj close', 'adj_close', 'adjclose'):
			mapping[c] = 'Adj Close'
		elif lc in ('volume', 'vol', 'v'):
			mapping[c] = 'Volume'
		else:
			# leave other columns as-is
			mapping[c] = c
	return df.rename(columns=mapping)


def _ensure_datetime_index(df: pd.DataFrame, path: Optional[str] = None) -> pd.DataFrame:
	"""Try to set a datetime index on the DataFrame using common columns or parsing the index."""
	# prefer explicit date columns
	for candidate in list(df.columns):
		if str(candidate).strip().lower() in ('date', 'datetime', 'time', 'index'):
			try:
				df[candidate] = pd.to_datetime(df[candidate], errors='coerce')
				df = df.set_index(candidate)
				return df
			except Exception:
				continue

	# try parsing the existing index
	try:
		parsed = pd.to_datetime(df.index, errors='coerce')
		if not parsed.isna().all():
			df.index = parsed
			return df
	except Exception:
		pass

	# last resort: try to infer date-like column names
	for c in df.columns:
		try:
			parsed = pd.to_datetime(df[c], errors='coerce')
			if not parsed.isna().all():
				df[c] = parsed
				df = df.set_index(c)
				return df
		except Exception:
			continue

	# Could not find a datetime index — warn but return original
	warnings.warn(f"Could not determine datetime index for file: {path}")
	return df


def load_csv(path: str) -> pd.DataFrame:
	"""Load a CSV to a cleaned DataFrame suitable for backtesting.

	- parses dates when possible
	- normalizes column names
	- coerces numeric OHLCV columns
	"""
	try:
		df = pd.read_csv(path)
	except Exception as e:
		raise

	df.columns = [str(c).strip() for c in df.columns]
	df = _standardize_columns(df)
	df = _ensure_datetime_index(df, path)

	# coerce required numeric columns
	required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
	for col in required_cols:
		if col not in df.columns:
			df[col] = np.nan
		else:
			df[col] = pd.to_numeric(df[col], errors='coerce')

	# fallback: use Adj Close if Close is empty
	if 'Close' in df.columns and df['Close'].isnull().all() and 'Adj Close' in df.columns:
		df['Close'] = pd.to_numeric(df['Adj Close'], errors='coerce')

	try:
		if pd.api.types.is_datetime64_any_dtype(df.index):
			df = df.sort_index()
	except Exception:
		pass

	return df


def load_json(path: str) -> pd.DataFrame:
	"""Load a JSON file that may contain multiple shapes and return a cleaned DataFrame.

	Supports:
	- top-level dict with 'price' -> 'yahoo' -> 'daily' list
	- top-level dict with flattened key 'price.yahoo.daily' (list of rows)
	- dict of date->values
	- list of row dicts
	"""
	from dateutil import parser as _dateparser

	try:
		with open(path, 'r', encoding='utf-8') as f:
			obj = json.load(f)
	except Exception as e:
		raise

	df = None

	def _finalize_daily(daily_list) -> pd.DataFrame:
		"""Helper: build a proper OHLCV DataFrame from a list of dict rows."""
		try:
			_df = pd.DataFrame(daily_list)
		except Exception:
			return pd.DataFrame()
		# common rename patterns
		ren = {
			'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
			'adj_close': 'Adj Close', 'adjclose': 'Adj Close', 'adj close': 'Adj Close',
			'volume': 'Volume', 'date': 'Date'
		}
		_df = _df.rename(columns={c: ren.get(str(c).lower(), c) for c in _df.columns})
		if 'Date' not in _df.columns:
			# try detect a date-like column
			for cand in _df.columns:
				lc = str(cand).lower()
				if lc in ('time','timestamp','datetime'):
					_df = _df.rename(columns={cand: 'Date'})
					break
		if 'Date' in _df.columns:
			_df['Date'] = pd.to_datetime(_df['Date'], errors='coerce', utc=True)
			_df = _df.dropna(subset=['Date']).set_index('Date')
		return _df

	# Handle various JSON shapes
	if isinstance(obj, dict):
		# 1. Nested yahoo.daily structure
		if isinstance(obj.get('price'), dict):
			daily = obj.get('price', {}).get('yahoo', {}).get('daily')
		else:
			daily = None
		# 2. Flattened key style: 'price.yahoo.daily'
		if daily is None and 'price.yahoo.daily' in obj:
			daily = obj.get('price.yahoo.daily')
		# Build from daily if available
		if daily is not None:
			if isinstance(daily, dict):
				# Could be date->row mapping
				try:
					# Prefer treat keys as index
					candidate = pd.DataFrame.from_dict(daily, orient='index')
					candidate.index.name = 'Date'
					candidate['Date'] = pd.to_datetime(candidate.index, errors='coerce', utc=True)
					candidate = candidate.dropna(subset=['Date']).set_index('Date')
					df = candidate
				except Exception:
					# Fallback: treat values list
					df = _finalize_daily(list(daily.values()))
			elif isinstance(daily, list):
				df = _finalize_daily(daily)
		# If still None, attempt date->dict mapping
		if df is None:
			if obj and all(isinstance(k, str) and isinstance(v, dict) for k, v in obj.items()):
				try:
					df = pd.DataFrame.from_dict(obj, orient='index')
					df.index.name = 'Date'
				except Exception:
					df = pd.DataFrame([obj])
			else:
				df = pd.DataFrame([obj])
	elif isinstance(obj, list):
		df = pd.DataFrame(obj)
	else:
		df = pd.DataFrame([obj])

	# Post-process case: single-row with an embedded daily list column (e.g., 'price.yahoo.daily')
	if df is not None and len(df) == 1:
		for col in list(df.columns):
			val = df.iloc[0][col]
			if isinstance(val, list) and val and isinstance(val[0], dict):
				# Heuristic: expand this column if it has typical price keys
				lower_keys = {k.lower() for k in val[0].keys()}
				if {'open','high','low','close'}.intersection(lower_keys):
					expanded = _finalize_daily(val)
					if not expanded.empty:
						df = expanded
						break

	# normalize and coerce
	df.columns = [str(c).strip() for c in df.columns]
	df = _standardize_columns(df)
	df = _ensure_datetime_index(df, path)

	required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
	for col in required_cols:
		if col not in df.columns:
			df[col] = np.nan
		else:
			df[col] = pd.to_numeric(df[col], errors='coerce')

	if 'Close' in df.columns and df['Close'].isnull().all() and 'Adj Close' in df.columns:
		df['Close'] = pd.to_numeric(df['Adj Close'], errors='coerce')

	try:
		if pd.api.types.is_datetime64_any_dtype(df.index):
			df = df.sort_index()
	except Exception:
		pass

	# If file seems invalid (no numeric price data) warn
	if df[required_cols].isnull().all().all():
		warnings.warn(f"Loaded JSON but no numeric OHLCV columns found or all NaN: {path}")

	return df


def maybe_adjust_with_adj(df: pd.DataFrame, use_adj: bool = True) -> pd.DataFrame:
	"""If use_adj and 'Adj Close' exists, replace 'Close' with adjusted values."""
	try:
		if use_adj and 'Adj Close' in df.columns:
			df['Close'] = pd.to_numeric(df['Adj Close'], errors='coerce')
	except Exception:
		pass
	return df


# ----------------- Parquet / catalog helpers (lightweight adapter of ForReferenceOnly/data_setup.py)
import os
import json
from typing import List, Dict, Optional

def _catalog_paths_for(data_dir: str):
	cat_dir = os.path.join(data_dir, '_catalog')
	os.makedirs(cat_dir, exist_ok=True)
	return os.path.join(cat_dir, 'catalog.parquet'), os.path.join(cat_dir, 'catalog.json')

def get_catalog(data_dir: str) -> Optional[pd.DataFrame]:
	"""Return a DataFrame catalog if present. Tries parquet then json.

	Catalog schema expected to include: ticker, parquet_path, src_path, date_col, min_date, max_date, fields
	"""
	cat_parquet, cat_json = _catalog_paths_for(data_dir)
	if os.path.exists(cat_parquet):
		try:
			return pd.read_parquet(cat_parquet)
		except Exception:
			pass
	if os.path.exists(cat_json):
		try:
			with open(cat_json, 'r', encoding='utf-8') as f:
				return pd.DataFrame(json.load(f))
		except Exception:
			return None
	return None

def load_tickers_on_demand(
	tickers: List[str],
	data_dir: Optional[str] = None,
	catalog_df: Optional[pd.DataFrame] = None,
	columns: Optional[List[str]] = None,
	date_from: Optional[str] = None,
	date_to: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
	"""Load a set of tickers from parquet files referenced by the catalog.

	This is intentionally small and returns a dict mapping ticker->DataFrame.
	"""
	assert (catalog_df is not None) or (data_dir is not None), "Provide data_dir or catalog_df"
	if catalog_df is None:
		catalog_df = get_catalog(data_dir)
		assert catalog_df is not None, "Catalog not found. Run build_or_refresh_catalog first."

	colmap = { r['ticker']: r['parquet_path'] for _, r in catalog_df.iterrows() }
	date_col_map = { r['ticker']: r.get('date_col') for _, r in catalog_df.iterrows() }

	out: Dict[str, pd.DataFrame] = {}
	for t in tickers:
		pq = colmap.get(t)
		if not pq or not os.path.exists(pq):
			continue
		try:
			df = pd.read_parquet(pq, columns=columns)
		except Exception:
			# best-effort: try without columns
			try:
				df = pd.read_parquet(pq)
			except Exception:
				continue
		dcol = date_col_map.get(t)
		if dcol and dcol in df.columns:
			try:
				if not pd.api.types.is_datetime64_any_dtype(df[dcol]):
					df[dcol] = pd.to_datetime(df[dcol], errors='coerce', utc=True)
			except Exception:
				pass
			if date_from:
				df = df[df[dcol] >= pd.to_datetime(date_from, utc=True)]
			if date_to:
				dt_to = pd.to_datetime(date_to, utc=True)
				df = df[df[dcol] <= dt_to]
			try:
				df = df.sort_values(by=dcol).reset_index(drop=True)
			except Exception:
				pass
		out[t] = df
	return out


def safe_append_parquet(data_dir: str, ticker: str, new_df: pd.DataFrame, date_col: Optional[str] = None) -> bool:
	"""Safely append/merge new_df into existing parquet for ticker.

	Behaviour:
	- If parquet missing, write new_df as parquet.
	- Else, read existing parquet, concat, dedupe on date_col (if provided), sort and atomically replace file.
	- Returns True on success.
	"""
	try:
		pq_path = os.path.join(data_dir, '_parquet', f"{ticker}.parquet")
		os.makedirs(os.path.dirname(pq_path), exist_ok=True)
		tmp_path = pq_path + '.tmp'

		# helper: flatten tuple/multiindex column names to single strings
		def _flatten_columns(df):
			# preserve a copy
			df = df.copy()
			new_cols = []
			for c in df.columns:
				if isinstance(c, str):
					new_cols.append(c)
				else:
					# for tuple/other, join parts with '_' and strip
					try:
						parts = [str(x) for x in c]
						joined = '_'.join([p for p in parts if p is not None and p != ''])
						new_cols.append(joined if joined else str(c))
					except Exception:
						new_cols.append(str(c))
			df.columns = new_cols
			return df

		if not os.path.exists(pq_path):
			# ensure new_df has a normalized 'date' column
			try:
				nd = new_df.copy()
				# detect date column if not provided; also flatten any tuple columns
				nd = _flatten_columns(nd)
				if not date_col:
					for c in nd.columns:
						if 'date' in str(c).lower() or str(c).lower() in ('datetime', 'time'):
							date_col = c
							break
				if date_col and date_col in nd.columns:
					nd['date'] = pd.to_datetime(nd[date_col], errors='coerce', utc=True)
				else:
					# try index
					try:
						nd = nd.reset_index()
						nd['date'] = pd.to_datetime(nd['index'], errors='coerce', utc=True)
					except Exception:
						pass
				# prefer 'date' column for storage
				if 'date' in nd.columns:
					# drop old ambiguous date cols to reduce duplicates
					cols_to_drop = [c for c in ['Date', 'datetime', 'time', 'index'] if c in nd.columns and c != 'date']
					try:
						nd = nd.drop(columns=cols_to_drop)
					except Exception:
						pass
			except Exception:
				nd = new_df
			nd.to_parquet(tmp_path, index=False)
			os.replace(tmp_path, pq_path)
			return True

			# read existing
		try:
			old = pd.read_parquet(pq_path)
		except Exception:
			# fallback: overwrite with new
			new_df.to_parquet(tmp_path, index=False)
			os.replace(tmp_path, pq_path)
			return True

		# Normalize date column in old and new to a canonical 'date' column (datetime UTC)
		def _ensure_date_col(df, preferred=date_col):
			d = df.copy()
			# flatten columns first to simplify detection
			d = _flatten_columns(d)
			col = None
			# preferred may be from previous detection; otherwise look for any column containing 'date'
			if preferred and preferred in d.columns:
				col = preferred
			else:
				for c in d.columns:
					if 'date' in str(c).lower() or str(c).lower() in ('datetime', 'time'):
						col = c
						break
			if col and col in d.columns:
				try:
					d['date'] = pd.to_datetime(d[col], errors='coerce', utc=True)
				except Exception:
					d['date'] = pd.to_datetime(d[col], errors='coerce')
			else:
				# try index
				try:
					idx = pd.to_datetime(d.index, errors='coerce', utc=True)
					if not idx.isna().all():
						d = d.reset_index()
						d['date'] = idx
					else:
						# last resort: create date column as NaT
						d['date'] = pd.NaT
				except Exception:
					d['date'] = pd.NaT
			return d

		# flatten old columns as well
		old = _flatten_columns(old)
		old_n = _ensure_date_col(old, date_col)
		new_n = _ensure_date_col(new_df, date_col)

		# concat and drop duplicates by 'date', keeping last (so new rows override)
		combined = pd.concat([old_n, new_n], ignore_index=True)
		try:
			combined['date'] = pd.to_datetime(combined['date'], errors='coerce', utc=True)
		except Exception:
			pass
		# drop rows where date is NaT to avoid ambiguous duplicates
		try:
			combined = combined.dropna(subset=['date'])
		except Exception:
			pass
		combined = combined.drop_duplicates(subset=['date'], keep='last')
		try:
			combined = combined.sort_values(by='date').reset_index(drop=True)
		except Exception:
			combined = combined.reset_index(drop=True)

		combined.to_parquet(tmp_path, index=False)
		os.replace(tmp_path, pq_path)
		return True
	except Exception:
		return False


def plan_daily_update_adapter(data_dir: str):
	"""Thin adapter that proxies to ForReferenceOnly.data_setup.plan_daily_update if available.

	Returns a plan dict or raises if not available.
	"""
	try:
		from ForReferenceOnly.data_setup import plan_daily_update
		return plan_daily_update(data_dir)
	except Exception as e:
		raise RuntimeError("plan_daily_update not available: " + str(e))


def get_last_date_for_ticker(data_dir: str, ticker: str) -> Optional[pd.Timestamp]:
	"""Return the last date present for a ticker by inspecting parquet or json/csv files.

	Returns a pandas.Timestamp (UTC) or None if not found.
	"""
	# check parquet in _parquet
	try:
		pq_path = os.path.join(data_dir, '_parquet', f"{ticker}.parquet")
		if os.path.exists(pq_path):
			try:
				df = pd.read_parquet(pq_path)
				# try common date columns
				for c in ['date', 'Date', 'datetime', 'time']:
					if c in df.columns:
						try:
							candidate = pd.to_datetime(df[c], errors='coerce', utc=True)
							if not candidate.isna().all():
								# If the candidate date is clearly invalid/epoch (before 2024-01-01), treat as not found
								min_valid = pd.to_datetime('2024-01-01', utc=True)
								if pd.to_datetime(candidate.max(), utc=True) < min_valid:
									return None
								return candidate.max()
						except Exception:
							continue
				# try index
				try:
					idx = pd.to_datetime(df.index, errors='coerce', utc=True)
					if not idx.isna().all():
						candidate = idx.max()
						min_valid = pd.to_datetime('2024-01-01', utc=True)
						if pd.to_datetime(candidate, utc=True) < min_valid:
							return None
						return candidate
				except Exception:
					pass
			except Exception:
				pass

		# check top-level json/csv files
		json_path = os.path.join(data_dir, f"{ticker}.json")
		csv_path = os.path.join(data_dir, f"{ticker}.csv")
		if os.path.exists(json_path):
			try:
				df = load_json(json_path)
				# load_json returns df with datetime index or date column
				if pd.api.types.is_datetime64_any_dtype(df.index):
					candidate = df.index.max()
					min_valid = pd.to_datetime('2024-01-01', utc=True)
					try:
						if pd.to_datetime(candidate, utc=True) < min_valid:
							return None
					except Exception:
						pass
					return candidate
				for c in ['date', 'Date', 'datetime', 'time']:
					if c in df.columns:
						try:
							candidate = pd.to_datetime(df[c], errors='coerce', utc=True)
							if not candidate.isna().all():
								min_valid = pd.to_datetime('2024-01-01', utc=True)
								if pd.to_datetime(candidate.max(), utc=True) < min_valid:
									return None
								return candidate.max()
						except Exception:
							continue
			except Exception:
				pass

		if os.path.exists(csv_path):
			try:
				df = load_csv(csv_path)
				if pd.api.types.is_datetime64_any_dtype(df.index):
					candidate = df.index.max()
					min_valid = pd.to_datetime('2024-01-01', utc=True)
					try:
						if pd.to_datetime(candidate, utc=True) < min_valid:
							return None
					except Exception:
						pass
					return candidate
				for c in ['date', 'Date', 'datetime', 'time']:
					if c in df.columns:
						try:
							candidate = pd.to_datetime(df[c], errors='coerce', utc=True)
							if not candidate.isna().all():
								min_valid = pd.to_datetime('2024-01-01', utc=True)
								if pd.to_datetime(candidate.max(), utc=True) < min_valid:
									return None
								return candidate.max()
						except Exception:
							continue
			except Exception:
				pass
	except Exception:
		pass
	return None


def list_tickers_from_folder(data_dir: str) -> List[str]:
	"""Return a list of tickers inferred from files in the data_dir (json and parquet)."""
	out = set()
	try:
		for name in os.listdir(data_dir):
			if name.lower().endswith('.json') or name.lower().endswith('.csv'):
				out.add(os.path.splitext(name)[0])
		# check _parquet subfolder
		pq_dir = os.path.join(data_dir, '_parquet')
		if os.path.isdir(pq_dir):
			for name in os.listdir(pq_dir):
				if name.lower().endswith('.parquet'):
					out.add(os.path.splitext(name)[0])
	except Exception:
		pass
	return sorted(list(out))


def get_last_date_for_ticker_processed(processed_dir: str, ticker: str) -> Optional[pd.Timestamp]:
	"""Return the last date present for a ticker by inspecting processed parquet files.
	
	This function looks specifically in the processed_data/_parquet directory.
	Returns a pandas.Timestamp (UTC) or None if not found.
	"""
	try:
		pq_path = os.path.join(processed_dir, '_parquet', f"{ticker}.parquet")
		if os.path.exists(pq_path):
			try:
				df = pd.read_parquet(pq_path)
				# try common date columns
				for c in ['date', 'Date', 'datetime', 'time']:
					if c in df.columns:
						try:
							candidate = pd.to_datetime(df[c], errors='coerce', utc=True)
							if not candidate.isna().all():
								# If the candidate date is clearly invalid/epoch (before 2024-01-01), treat as not found
								min_valid = pd.to_datetime('2024-01-01', utc=True)
								if pd.to_datetime(candidate.max(), utc=True) < min_valid:
									return None
								return candidate.max()
						except Exception:
							continue
				# try index
				try:
					idx = pd.to_datetime(df.index, errors='coerce', utc=True)
					if not idx.isna().all():
						candidate = idx.max()
						min_valid = pd.to_datetime('2024-01-01', utc=True)
						if pd.to_datetime(candidate, utc=True) < min_valid:
							return None
						return candidate
				except Exception:
					pass
			except Exception:
				pass
	except Exception:
		pass
	return None


def get_last_date_for_ticker_raw(raw_dir: str, ticker: str) -> Optional[pd.Timestamp]:
	"""Return the last date present for a ticker by inspecting raw json/csv files.
	
	This function looks specifically in the raw_data directory.
	Returns a pandas.Timestamp (UTC) or None if not found.
	"""
	try:
		# check raw json/csv files
		json_path = os.path.join(raw_dir, f"{ticker}.json")
		csv_path = os.path.join(raw_dir, f"{ticker}.csv")
		
		if os.path.exists(json_path):
			try:
				df = load_json(json_path)
				# load_json returns df with datetime index or date column
				if pd.api.types.is_datetime64_any_dtype(df.index):
					candidate = df.index.max()
					min_valid = pd.to_datetime('2024-01-01', utc=True)
					try:
						if pd.to_datetime(candidate, utc=True) < min_valid:
							return None
					except Exception:
						pass
					return candidate
				for c in ['date', 'Date', 'datetime', 'time']:
					if c in df.columns:
						try:
							candidate = pd.to_datetime(df[c], errors='coerce', utc=True)
							if not candidate.isna().all():
								min_valid = pd.to_datetime('2024-01-01', utc=True)
								if pd.to_datetime(candidate.max(), utc=True) < min_valid:
									return None
								return candidate.max()
						except Exception:
							continue
			except Exception:
				pass

		if os.path.exists(csv_path):
			try:
				df = load_csv(csv_path)
				if pd.api.types.is_datetime64_any_dtype(df.index):
					candidate = df.index.max()
					min_valid = pd.to_datetime('2024-01-01', utc=True)
					try:
						if pd.to_datetime(candidate, utc=True) < min_valid:
							return None
					except Exception:
						pass
					return candidate
				for c in ['date', 'Date', 'datetime', 'time']:
					if c in df.columns:
						try:
							candidate = pd.to_datetime(df[c], errors='coerce', utc=True)
							if not candidate.isna().all():
								min_valid = pd.to_datetime('2024-01-01', utc=True)
								if pd.to_datetime(candidate.max(), utc=True) < min_valid:
									return None
								return candidate.max()
						except Exception:
							continue
			except Exception:
				pass
	except Exception:
		pass
	return None

