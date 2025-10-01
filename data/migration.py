"""
Migration utilities to move data between directories.
"""

import os
import shutil
import json
from typing import List


def copy_sample_data_from_backup(backup_dir: str, raw_dir: str, tickers: List[str] = None):
	"""Copy sample data from backup directory to raw_data for testing.
	
	Args:
		backup_dir: Source backup directory path
		raw_dir: Target raw_data directory path  
		tickers: List of specific tickers to copy (if None, copies a few samples)
	"""
	if tickers is None:
		# Default sample tickers for testing
		tickers = ['MSFT', 'AAPL', 'GOOGL', 'TSLA', 'NVDA']
	
	os.makedirs(raw_dir, exist_ok=True)
	
	copied = []
	for ticker in tickers:
		src_json = os.path.join(backup_dir, f"{ticker}.json")
		dst_json = os.path.join(raw_dir, f"{ticker}.json")
		
		if os.path.exists(src_json):
			try:
				shutil.copy2(src_json, dst_json)
				copied.append(ticker)
				print(f"Copied {ticker}.json to raw_data")
			except Exception as e:
				print(f"Failed to copy {ticker}: {e}")
		else:
			print(f"Source file not found: {src_json}")
	
	return copied


def migrate_processed_data_from_backup(backup_dir: str, processed_dir: str, tickers: List[str] = None):
	"""Copy processed data from backup directory to processed_data.
	
	Args:
		backup_dir: Source backup directory path
		processed_dir: Target processed_data directory path
		tickers: List of specific tickers to copy (if None, copies samples)
	"""
	if tickers is None:
		# Default sample tickers for testing
		tickers = ['MSFT', 'AAPL', 'GOOGL', 'TSLA', 'NVDA']
	
	# Ensure directories exist
	os.makedirs(os.path.join(processed_dir, '_parquet'), exist_ok=True)
	os.makedirs(os.path.join(processed_dir, '_catalog'), exist_ok=True)
	
	copied = []
	
	# Copy parquet files
	backup_parquet = os.path.join(backup_dir, '_parquet')
	if os.path.exists(backup_parquet):
		for ticker in tickers:
			src_pq = os.path.join(backup_parquet, f"{ticker}.parquet")
			dst_pq = os.path.join(processed_dir, '_parquet', f"{ticker}.parquet")
			
			if os.path.exists(src_pq):
				try:
					shutil.copy2(src_pq, dst_pq)
					copied.append(ticker)
					print(f"Copied {ticker}.parquet to processed_data/_parquet")
				except Exception as e:
					print(f"Failed to copy {ticker} parquet: {e}")
	
	# Copy catalog files
	backup_catalog = os.path.join(backup_dir, '_catalog')
	if os.path.exists(backup_catalog):
		for file in ['catalog.json', 'catalog.parquet']:
			src_file = os.path.join(backup_catalog, file)
			dst_file = os.path.join(processed_dir, '_catalog', file)
			
			if os.path.exists(src_file):
				try:
					shutil.copy2(src_file, dst_file)
					print(f"Copied {file} to processed_data/_catalog")
				except Exception as e:
					print(f"Failed to copy {file}: {e}")
	
	return copied


if __name__ == "__main__":
	# Example usage
	from data.data_paths import get_data_paths
	
	paths = get_data_paths()
	
	# Copy sample raw data
	print("Copying sample raw data...")
	copy_sample_data_from_backup(paths['backup'], paths['raw'])
	
	print("\nCopying sample processed data...")
	migrate_processed_data_from_backup(paths['backup'], paths['processed'])