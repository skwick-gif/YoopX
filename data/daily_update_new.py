"""
New daily update planning and execution system that works with the separated raw/processed data structure.
"""

import os
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from data.data_paths import get_data_paths, get_last_date_smart
from data.fetchers import fetch_yahoo_since
from data.api_fetchers import fetch_via_apis
from config.keys_loader import load_keys


def fetch_comprehensive_data(ticker: str, start_date: str, end_date: str,
                           include_fundamentals: bool = True,
                           include_esg: bool = True, 
                           include_corporate_actions: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive data for a ticker including all requested components.
    
    Returns a dictionary with the following structure:
    {
        "ticker": "MSFT",
        "collected_at": "2025-09-30T10:00:00Z",
        "date_range": {"start": "2024-01-01", "end": "2025-09-30"},
        "updated_at": "2025-09-30T10:00:00Z",
        "price": {
            "yahoo.daily": [{"date": "2024-01-01", "open": 100, "high": 105, ...}],
            "alphavantage.daily": [...]  # if available
        },
        "corporate_actions": {
            "dividends": [{"date": "2024-03-15", "amount": 0.5}],
            "splits": [{"date": "2024-06-01", "ratio": "2:1"}]
        },
        "fundamentals": {
            "company_name": "Microsoft Corporation",
            "sector": "Technology", 
            "industry": "Software",
            "employees": 181000,
            "marketCap": 2500000000000,
            "pe_ratio": 25.5,
            "pb_ratio": 4.2,
            "longBusinessSummary": "..."
        },
        "additional_data": {
            "esg_score": [...],
            "earnings_calendar": [...]
        }
    }
    """
    try:
        collected_at = datetime.now().isoformat()
        
        # Initialize result structure
        result = {
            "ticker": ticker,
            "collected_at": collected_at,
            "date_range": {"start": start_date, "end": end_date},
            "updated_at": collected_at,
            "price": {},
            "corporate_actions": {},
            "fundamentals": {},
            "additional_data": {}
        }
        
        # Load API keys
        api_keys = load_keys()
        
        # 1. Fetch daily price data - try multiple sources
        price_sources_tried = []
        
        # First try Yahoo Finance
        try:
            df, meta = fetch_yahoo_since(ticker, start_date)
            price_sources_tried.append("yahoo")
            if not df.empty:
                # Convert DataFrame to records
                price_records = []
                for _, row in df.iterrows():
                    price_records.append({
                        "date": row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name),
                        "open": float(row.get('Open', 0)) if pd.notna(row.get('Open')) else None,
                        "high": float(row.get('High', 0)) if pd.notna(row.get('High')) else None,  
                        "low": float(row.get('Low', 0)) if pd.notna(row.get('Low')) else None,
                        "close": float(row.get('Close', 0)) if pd.notna(row.get('Close')) else None,
                        "adj_close": float(row.get('Adj Close', 0)) if pd.notna(row.get('Adj Close')) else None,
                        "volume": int(row.get('Volume', 0)) if pd.notna(row.get('Volume')) else None
                    })
                result["price"]["yahoo.daily"] = price_records
                print(f"✅ Yahoo: Fetched {len(price_records)} price records for {ticker}")
        except Exception as e:
            print(f"Warning: Failed to fetch Yahoo price data for {ticker}: {e}")
        
        # If Yahoo failed or returned no data, try API providers as fallback
        if not result["price"].get("yahoo.daily"):
            try:
                providers = ['polygon', 'alphavantage'] if api_keys.get('polygon') or api_keys.get('alphavantage') else []
                if providers:
                    df_api, meta_api = fetch_via_apis(ticker, start_date, providers=providers, keys=api_keys)
                    provider_used = meta_api.get('used_provider')
                    price_sources_tried.append(provider_used or 'api_failed')
                    
                    if not df_api.empty and provider_used:
                        # Convert API data to records
                        price_records = []
                        for _, row in df_api.iterrows():
                            price_records.append({
                                "date": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                                "open": float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                                "high": float(row.get('high', 0)) if pd.notna(row.get('high')) else None,  
                                "low": float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                                "close": float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
                                "adj_close": float(row.get('adj_close', 0)) if pd.notna(row.get('adj_close')) else None,
                                "volume": int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None
                            })
                        result["price"][f"{provider_used}.daily"] = price_records
                        print(f"✅ {provider_used}: Fetched {len(price_records)} price records for {ticker}")
            except Exception as e:
                print(f"Warning: Failed to fetch API price data for {ticker}: {e}")
        
        # Add metadata about sources tried
        result["data_sources"] = {
            "price_sources_tried": price_sources_tried,
            "price_sources_successful": [k for k in result["price"].keys() if result["price"][k]]
        }
        
        # 2. Fetch fundamentals data (if requested and yfinance available)
        if include_fundamentals:
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker)
                info = stock.info
                
                result["fundamentals"] = {
                    "company_name": info.get("longName", ""),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""), 
                    "employees": info.get("fullTimeEmployees"),
                    "marketCap": info.get("marketCap"),
                    "pe_ratio": info.get("forwardPE") or info.get("trailingPE"),
                    "pb_ratio": info.get("priceToBook"),
                    "ps_ratio": info.get("priceToSalesTrailing12Months"),
                    "ev_ebitda": info.get("enterpriseToEbitda"),
                    "longBusinessSummary": info.get("longBusinessSummary", ""),
                    "website": info.get("website", ""),
                    "headquarters": {
                        "city": info.get("city", ""),
                        "state": info.get("state", ""), 
                        "country": info.get("country", "")
                    }
                }
            except Exception as e:
                print(f"Warning: Failed to fetch fundamentals for {ticker}: {e}")
        
        # 3. Fetch corporate actions (if requested)
        if include_corporate_actions:
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker)
                
                # Get dividends
                dividends = stock.dividends
                if not dividends.empty:
                    div_records = []
                    for date, amount in dividends.items():
                        if pd.to_datetime(date).date() >= pd.to_datetime(start_date).date():
                            div_records.append({
                                "date": date.strftime('%Y-%m-%d'),
                                "amount": float(amount)
                            })
                    result["corporate_actions"]["dividends"] = div_records
                
                # Get splits
                splits = stock.splits
                if not splits.empty:
                    split_records = []
                    for date, ratio in splits.items():
                        if pd.to_datetime(date).date() >= pd.to_datetime(start_date).date():
                            split_records.append({
                                "date": date.strftime('%Y-%m-%d'),
                                "ratio": f"{ratio}:1"
                            })
                    result["corporate_actions"]["splits"] = split_records
                    
            except Exception as e:
                print(f"Warning: Failed to fetch corporate actions for {ticker}: {e}")
        
        # 4. Fetch ESG and additional data using enhanced providers
        if include_esg:
            try:
                from data.enhanced_providers import fetch_esg_data, fetch_earnings_calendar
                
                # Fetch ESG data
                esg_data = fetch_esg_data(ticker, api_keys)
                result["additional_data"]["esg_data"] = esg_data
                print(f"✅ ESG data fetched from {esg_data.get('data_source', 'unknown')} for {ticker}")
                
                # Fetch earnings calendar
                earnings_data = fetch_earnings_calendar(ticker, api_keys)
                result["additional_data"]["earnings_data"] = earnings_data
                print(f"✅ Earnings data fetched from {earnings_data.get('data_source', 'unknown')} for {ticker}")
                
            except Exception as e:
                print(f"Warning: Failed to fetch enhanced data for {ticker}: {e}")
                # Fallback to empty structures
                result["additional_data"]["esg_data"] = {"esg_scores": [], "data_source": "failed"}
                result["additional_data"]["earnings_data"] = {"upcoming_earnings": [], "data_source": "failed"}
        
        return result
        
    except Exception as e:
        print(f"Error fetching comprehensive data for {ticker}: {e}")
        return None


def get_default_tickers() -> List[str]:
    """Get default list of tickers to update."""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK-B', 'UNH', 'JNJ',
        'V', 'JPM', 'PG', 'MA', 'XOM', 'HD', 'CVX', 'ABBV', 'PFE', 'KO', 'AVGO', 'PEP',
        'COST', 'TMO', 'WMT', 'BAC', 'NFLX', 'CRM', 'ACN', 'LLY', 'CSCO', 'ADBE',
        'WFC', 'TXN', 'VZ', 'CMCSA', 'ORCL', 'AMD', 'QCOM', 'DHR', 'NEE', 'BMY', 'PM'
    ]


def plan_daily_update_new(raw_dir: str = None, processed_dir: str = None, 
                         tickers: List[str] = None, 
                         max_days_back: int = 30) -> Dict[str, Any]:
    """
    Create a comprehensive daily update plan using the new data structure.
    
    Args:
        raw_dir: Path to raw_data directory
        processed_dir: Path to processed_data directory  
        tickers: List of tickers to update (if None, uses default list)
        max_days_back: Maximum days to look back for missing data
        
    Returns:
        Dictionary with update plan for each ticker
    """
    if raw_dir is None or processed_dir is None:
        paths = get_data_paths()
        raw_dir = raw_dir or paths['raw']
        processed_dir = processed_dir or paths['processed']
    
    if tickers is None:
        tickers = get_default_tickers()
    
    # Ensure directories exist
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    plan = []
    today = date.today()
    min_valid_date = date(2024, 1, 1)
    
    for ticker in tickers:
        try:
            # Get last available date using smart detection
            last_date = get_last_date_smart(raw_dir, processed_dir, ticker)
            
            if last_date is not None:
                # Convert to date and add 1 day
                last_date_obj = pd.to_datetime(last_date).date()
                next_date = last_date_obj + timedelta(days=1)
                
                # Don't fetch future dates or weekends unnecessarily
                if next_date > today:
                    next_date = None
                    status = "up_to_date"
                else:
                    status = "needs_update"
            else:
                # No data found, start from minimum valid date
                next_date = min_valid_date
                status = "new_ticker"
            
            # Calculate days to fetch
            days_to_fetch = 0
            if next_date and next_date <= today:
                days_to_fetch = (today - next_date).days + 1
                # Limit to max_days_back to avoid overwhelming requests
                if days_to_fetch > max_days_back:
                    days_to_fetch = max_days_back
                    next_date = today - timedelta(days=max_days_back-1)
            
            plan_item = {
                "ticker": ticker,
                "status": status,
                "last_date_available": str(last_date.date()) if last_date else None,
                "next_date_to_fetch": str(next_date) if next_date else None,
                "fetch_end_date": str(today),
                "days_to_fetch": days_to_fetch,
                "raw_path": os.path.join(raw_dir, f"{ticker}.json"),
                "processed_path": os.path.join(processed_dir, "_parquet", f"{ticker}.parquet"),
                "priority": _calculate_priority(status, days_to_fetch)
            }
            
            plan.append(plan_item)
            
        except Exception as e:
            # Add error item to plan for debugging
            plan.append({
                "ticker": ticker,
                "status": "error",
                "error": str(e),
                "last_date_available": None,
                "next_date_to_fetch": None,
                "fetch_end_date": str(today),
                "days_to_fetch": 0,
                "raw_path": os.path.join(raw_dir, f"{ticker}.json"),
                "processed_path": os.path.join(processed_dir, "_parquet", f"{ticker}.parquet"),
                "priority": 0
            })
    
    # Sort by priority (higher first)
    plan.sort(key=lambda x: x.get("priority", 0), reverse=True)
    
    summary = {
        "total_tickers": len(plan),
        "needs_update": len([p for p in plan if p["status"] == "needs_update"]),
        "new_tickers": len([p for p in plan if p["status"] == "new_ticker"]),
        "up_to_date": len([p for p in plan if p["status"] == "up_to_date"]),
        "errors": len([p for p in plan if p["status"] == "error"]),
        "total_days_to_fetch": sum(p.get("days_to_fetch", 0) for p in plan),
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "summary": summary,
        "plan": plan,
        "raw_dir": raw_dir,
        "processed_dir": processed_dir
    }


def _calculate_priority(status: str, days_to_fetch: int) -> int:
    """Calculate priority for fetching order."""
    base_priority = {
        "new_ticker": 100,
        "needs_update": 50,
        "up_to_date": 0,
        "error": 0
    }.get(status, 0)
    
    # Add days to fetch as bonus (more urgent if more days behind)
    return base_priority + min(days_to_fetch, 50)


def execute_daily_update_plan(plan_dict: Dict[str, Any], 
                                  progress_callback=None,
                                  status_callback=None,
                                  cancel_callback=None) -> Dict[str, Any]:
    """
    Execute the daily update plan by fetching comprehensive data for each ticker.
    
    Args:
        plan_dict: Plan dictionary from plan_daily_update_new()
        progress_callback: Function to call with progress updates (0-100)
        status_callback: Function to call with status messages
        cancel_callback: Function that returns True if operation should be cancelled
        
    Returns:
        Results dictionary with success/failure information
    """
    plan = plan_dict["plan"]
    raw_dir = plan_dict["raw_dir"]
    processed_dir = plan_dict["processed_dir"]
    
    results = {
        "started_at": datetime.now().isoformat(),
        "total_tickers": len(plan),
        "successful": [],
        "failed": [],
        "skipped": [],
        "details": []
    }
    
    for i, item in enumerate(plan):
        # Check for cancellation at the start of each iteration
        if cancel_callback and cancel_callback():
            if status_callback:
                status_callback("Operation cancelled by user")
            results["details"].append({
                "status": "cancelled",
                "message": "Operation cancelled by user request"
            })
            break
            
        ticker = item["ticker"]
        
        # Update progress
        progress = int((i / len(plan)) * 100)
        if progress_callback:
            progress_callback(progress)
        
        # Skip if no fetching needed
        if item["status"] in ["up_to_date", "error"] or item["days_to_fetch"] == 0:
            if status_callback:
                status_callback(f"Skipping {ticker} - {item['status']}")
            results["skipped"].append(ticker)
            results["details"].append({
                "ticker": ticker,
                "status": "skipped",
                "reason": item["status"]
            })
            continue
        
        try:
            if status_callback:
                status_callback(f"Fetching {ticker} from {item['next_date_to_fetch']} ({item['days_to_fetch']} days)")
            
            # Check for cancellation before expensive fetch operation
            if cancel_callback and cancel_callback():
                if status_callback:
                    status_callback(f"Cancelled during {ticker} fetch")
                break
            
            # Fetch comprehensive data
            data = fetch_comprehensive_data(
                ticker=ticker,
                start_date=item["next_date_to_fetch"],
                end_date=item["fetch_end_date"],
                include_fundamentals=True,
                include_esg=True,
                include_corporate_actions=True
            )
            
            if data:
                # Save to raw directory
                raw_path = item["raw_path"]
                os.makedirs(os.path.dirname(raw_path), exist_ok=True)
                
                # Merge with existing data if it exists
                if os.path.exists(raw_path):
                    existing_data = _load_existing_raw_data(raw_path)
                    data = _merge_data(existing_data, data, ticker)
                
                # Save updated data
                with open(raw_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
                
                results["successful"].append(ticker)
                results["details"].append({
                    "ticker": ticker,
                    "status": "success",
                    "days_fetched": item["days_to_fetch"],
                    "raw_path": raw_path
                })
                
            else:
                raise Exception("No data returned from fetch")
                
        except Exception as e:
            if status_callback:
                status_callback(f"Failed to fetch {ticker}: {str(e)}")
            
            results["failed"].append(ticker)
            results["details"].append({
                "ticker": ticker,
                "status": "failed",
                "error": str(e)
            })
    
    # Final progress update
    if progress_callback:
        progress_callback(100)
    
    results["completed_at"] = datetime.now().isoformat()
    results["success_rate"] = len(results["successful"]) / len(plan) if plan else 0
    
    return results


def _load_existing_raw_data(file_path: str) -> Dict[str, Any]:
    """Load existing raw data file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _merge_data(existing: Dict[str, Any], new_data: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    """Merge new data with existing data, preserving structure and avoiding duplicates."""
    if not existing:
        return new_data
    
    merged = existing.copy()
    
    # Update metadata
    merged.update({
        "ticker": ticker,
        "updated_at": datetime.now().isoformat(),
        "collected_at": new_data.get("collected_at", datetime.now().isoformat())
    })
    
    # Merge price data (avoiding duplicates by date)
    for source in ["yahoo.daily", "alphavantage.daily"]:
        if source in new_data.get("price", {}):
            if "price" not in merged:
                merged["price"] = {}
            if source not in merged["price"]:
                merged["price"][source] = []
            
            # Convert to DataFrame for easier merging
            existing_df = pd.DataFrame(merged["price"][source])
            new_df = pd.DataFrame(new_data["price"][source])
            
            if not existing_df.empty and not new_df.empty:
                # Merge on date, keeping new data for duplicates
                combined = pd.concat([existing_df, new_df]).drop_duplicates(subset=["date"], keep="last")
                merged["price"][source] = combined.to_dict("records")
            elif not new_df.empty:
                merged["price"][source] = new_df.to_dict("records")
    
    # Merge other sections (corporate_actions, fundamentals, additional_data)
    for section in ["corporate_actions", "fundamentals", "additional_data"]:
        if section in new_data:
            merged[section] = {**merged.get(section, {}), **new_data[section]}
    
    return merged


if __name__ == "__main__":
    # Test the planning function
    plan = plan_daily_update_new(tickers=["MSFT", "AAPL", "GOOGL"])
    print(json.dumps(plan, indent=2, default=str))