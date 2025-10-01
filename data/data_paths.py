"""
Data path management and smart data retrieval functions.

This module provides functions to manage the separation between raw and processed data.
"""

import os
import pandas as pd
from typing import Optional
from .data_utils import load_json, load_csv


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


def get_last_date_smart(raw_dir: str, processed_dir: str, ticker: str) -> Optional[pd.Timestamp]:
	"""Smart function to get the last date for a ticker.
	
	First tries to get from processed data (preferred), then falls back to raw data.
	This ensures we use the most recent processed data when available.
	
	Args:
		raw_dir: Path to raw_data directory
		processed_dir: Path to processed_data directory  
		ticker: Ticker symbol to check
		
	Returns:
		The last available date as pandas.Timestamp (UTC) or None if not found
	"""
	# First try processed data
	last_date = get_last_date_for_ticker_processed(processed_dir, ticker)
	if last_date is not None:
		return last_date
	
	# Fallback to raw data
	return get_last_date_for_ticker_raw(raw_dir, ticker)


def get_data_paths():
	"""Get standard data directory paths relative to project root."""
	import os
	project_root = os.path.dirname(os.path.dirname(__file__))  # Go up from data/ to project root
	return {
		'raw': os.path.join(project_root, 'raw_data'),
		'processed': os.path.join(project_root, 'processed_data'),
		'backup': os.path.join(project_root, 'data backup')  # Keep old path for migration
	}