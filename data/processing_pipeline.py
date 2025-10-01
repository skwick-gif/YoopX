"""
Data processing pipeline to convert raw JSON data to processed Parquet format.
"""

import os
import json
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np


def process_raw_to_parquet(raw_dir: str, processed_dir: str, 
                          tickers: Optional[List[str]] = None,
                          progress_callback=None) -> Dict[str, Any]:
    """
    Process raw JSON files to structured Parquet format.
    
    Args:
        raw_dir: Path to raw_data directory
        processed_dir: Path to processed_data directory  
        tickers: List of specific tickers to process (if None, processes all)
        progress_callback: Function to call with progress updates (0-100)
        
    Returns:
        Results dictionary with processing statistics
    """
    # Ensure output directories exist
    parquet_dir = os.path.join(processed_dir, '_parquet')
    catalog_dir = os.path.join(processed_dir, '_catalog')
    os.makedirs(parquet_dir, exist_ok=True)
    os.makedirs(catalog_dir, exist_ok=True)
    
    results = {
        "started_at": datetime.now().isoformat(),
        "processed": [],
        "failed": [],
        "skipped": [],
        "catalog_entries": []
    }
    
    # Get list of raw JSON files to process
    if tickers is None:
        json_files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
        tickers = [os.path.splitext(f)[0] for f in json_files]
    else:
        json_files = [f"{ticker}.json" for ticker in tickers]
    
    total_files = len(json_files)
    if total_files == 0:
        results["completed_at"] = datetime.now().isoformat()
        return results
    
    for i, json_file in enumerate(json_files):
        ticker = os.path.splitext(json_file)[0]
        raw_path = os.path.join(raw_dir, json_file)
        parquet_path = os.path.join(parquet_dir, f"{ticker}.parquet")
        
        # Update progress
        if progress_callback:
            progress_callback(int((i / total_files) * 100))
        
        if not os.path.exists(raw_path):
            results["skipped"].append(ticker)
            continue
        
        try:
            # Process the raw JSON file
            processed_data, catalog_entry = _process_single_file(raw_path, parquet_path, ticker)
            
            if processed_data is not None:
                results["processed"].append(ticker)
                results["catalog_entries"].append(catalog_entry)
            else:
                results["skipped"].append(ticker)
                
        except Exception as e:
            results["failed"].append({
                "ticker": ticker,
                "error": str(e)
            })
    
    # Update final progress
    if progress_callback:
        progress_callback(100)
    
    # Create catalog files
    if results["catalog_entries"]:
        _create_catalog_files(catalog_dir, results["catalog_entries"])
    
    results["completed_at"] = datetime.now().isoformat()
    results["summary"] = {
        "total": total_files,
        "processed": len(results["processed"]),
        "failed": len(results["failed"]), 
        "skipped": len(results["skipped"])
    }
    
    return results


def _process_single_file(raw_path: str, parquet_path: str, ticker: str) -> tuple:
    """Process a single raw JSON file to Parquet."""
    try:
        # Load raw data
        with open(raw_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Extract price data
        price_data = raw_data.get("price", {})
        
        # Combine all price sources into one DataFrame
        all_price_records = []
        
        for source, records in price_data.items():
            if records and isinstance(records, list):
                for record in records:
                    if record.get("date"):
                        # Add source information
                        record_copy = record.copy()
                        record_copy["source"] = source
                        all_price_records.append(record_copy)
        
        if not all_price_records:
            return None, None
        
        # Create DataFrame
        df = pd.DataFrame(all_price_records)
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # Add metadata columns
        df['ticker'] = ticker
        df['processed_at'] = datetime.now().isoformat()
        
        # Add fundamental data as separate columns (latest values)
        fundamentals = raw_data.get("fundamentals", {})
        if fundamentals:
            for key, value in fundamentals.items():
                if key not in ['headquarters'] and value is not None:
                    # Add as constant column (same value for all rows)
                    df[f"fund_{key}"] = value
        
        # Add corporate actions info
        corp_actions = raw_data.get("corporate_actions", {})
        if corp_actions:
            # Add flags for dividend and split dates
            dividends = corp_actions.get("dividends", [])
            splits = corp_actions.get("splits", [])
            
            df['has_dividend'] = df['date'].dt.strftime('%Y-%m-%d').isin([d['date'] for d in dividends])
            df['has_split'] = df['date'].dt.strftime('%Y-%m-%d').isin([s['date'] for s in splits])
            
            # Add dividend amounts where applicable
            div_dict = {d['date']: d['amount'] for d in dividends}
            df['dividend_amount'] = df['date'].dt.strftime('%Y-%m-%d').map(div_dict).fillna(0.0)
        
        # Save to Parquet
        os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
        df.to_parquet(parquet_path, index=False)
        
        # Create catalog entry
        catalog_entry = {
            "ticker": ticker,
            "raw_path": raw_path,
            "parquet_path": parquet_path,
            "n_rows": len(df),
            "n_cols": len(df.columns),
            "min_date": df['date'].min().isoformat() if not df.empty else None,
            "max_date": df['date'].max().isoformat() if not df.empty else None,
            "date_col": "date",
            "sources": list(set(df['source'].unique())) if 'source' in df.columns else [],
            "has_fundamentals": bool(fundamentals),
            "has_corporate_actions": bool(corp_actions),
            "processed_at": datetime.now().isoformat()
        }
        
        return df, catalog_entry
        
    except Exception as e:
        print(f"Error processing {ticker}: {e}")
        return None, None


def _create_catalog_files(catalog_dir: str, entries: List[Dict]):
    """Create catalog.json and catalog.parquet files."""
    # Create catalog.json
    catalog_json_path = os.path.join(catalog_dir, "catalog.json")
    with open(catalog_json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, default=str)
    
    # Create catalog.parquet
    catalog_parquet_path = os.path.join(catalog_dir, "catalog.parquet")
    catalog_df = pd.DataFrame(entries)
    catalog_df.to_parquet(catalog_parquet_path, index=False)
    
    print(f"Created catalog with {len(entries)} entries")


if __name__ == "__main__":
    # Test the processing pipeline
    from data.data_paths import get_data_paths
    
    paths = get_data_paths()
    
    def progress_callback(p):
        print(f"Processing: {p}%")
    
    results = process_raw_to_parquet(
        paths['raw'], 
        paths['processed'],
        progress_callback=progress_callback
    )
    
    print(f"Processing complete: {results['summary']}")