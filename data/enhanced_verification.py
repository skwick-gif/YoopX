"""
Enhanced data verification system for the new daily update pipeline.
Verifies that processed data is compatible with ML, Backtest, Optimize, Scanner modules.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


def verify_processed_data_structure(processed_dir: str) -> Dict[str, Any]:
    """
    Comprehensive verification of processed data structure for ML/Backtest/Optimize/Scanner compatibility.
    
    Checks:
    1. File structure integrity
    2. DataFrame columns and types 
    3. Date consistency and gaps
    4. Data completeness for each module's needs
    5. Catalog accuracy
    """
    
    verification_report = {
        "timestamp": datetime.now().isoformat(),
        "processed_dir": processed_dir,
        "status": "checking",
        "summary": {
            "total_tickers": 0,
            "verified_tickers": 0,
            "failed_tickers": 0,
            "warning_tickers": 0
        },
        "structure_check": {},
        "catalog_check": {},
        "data_compatibility": {},
        "detailed_results": {},
        "recommendations": []
    }
    
    try:
        # 1. Check directory structure
        verification_report["structure_check"] = _verify_directory_structure(processed_dir)
        
        # 2. Verify catalog integrity 
        verification_report["catalog_check"] = _verify_catalog_integrity(processed_dir)
        
        # 3. Check data compatibility for each module
        verification_report["data_compatibility"] = _verify_module_compatibility(processed_dir)
        
        # 4. Detailed per-ticker verification
        verification_report["detailed_results"] = _verify_individual_files(processed_dir)
        
        # 5. Generate summary and recommendations
        _generate_summary_and_recommendations(verification_report)
        
        verification_report["status"] = "completed"
        
    except Exception as e:
        verification_report["status"] = "error"
        verification_report["error"] = str(e)
    
    return verification_report


def _verify_directory_structure(processed_dir: str) -> Dict[str, Any]:
    """Verify the expected directory structure exists."""
    
    structure_check = {
        "base_dir_exists": os.path.exists(processed_dir),
        "parquet_dir_exists": False,
        "catalog_dir_exists": False,
        "parquet_files_count": 0,
        "catalog_files_found": []
    }
    
    if structure_check["base_dir_exists"]:
        parquet_dir = os.path.join(processed_dir, "_parquet")
        catalog_dir = os.path.join(processed_dir, "_catalog")
        
        structure_check["parquet_dir_exists"] = os.path.exists(parquet_dir)
        structure_check["catalog_dir_exists"] = os.path.exists(catalog_dir)
        
        if structure_check["parquet_dir_exists"]:
            parquet_files = [f for f in os.listdir(parquet_dir) if f.endswith('.parquet')]
            structure_check["parquet_files_count"] = len(parquet_files)
        
        if structure_check["catalog_dir_exists"]:
            catalog_files = os.listdir(catalog_dir)
            structure_check["catalog_files_found"] = catalog_files
    
    structure_check["is_valid"] = (
        structure_check["base_dir_exists"] and
        structure_check["parquet_dir_exists"] and  
        structure_check["catalog_dir_exists"] and
        structure_check["parquet_files_count"] > 0
    )
    
    return structure_check


def _verify_catalog_integrity(processed_dir: str) -> Dict[str, Any]:
    """Verify catalog files exist and are consistent."""
    
    catalog_check = {
        "catalog_json_exists": False,
        "catalog_parquet_exists": False,
        "entries_count": 0,
        "json_parquet_match": False,
        "catalog_entries_valid": True,
        "issues": []
    }
    
    catalog_dir = os.path.join(processed_dir, "_catalog")
    json_path = os.path.join(catalog_dir, "catalog.json")
    parquet_path = os.path.join(catalog_dir, "catalog.parquet")
    
    # Check file existence
    catalog_check["catalog_json_exists"] = os.path.exists(json_path)
    catalog_check["catalog_parquet_exists"] = os.path.exists(parquet_path)
    
    if catalog_check["catalog_json_exists"]:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
            catalog_check["entries_count"] = len(catalog_data)
            
            # Verify entry structure
            required_fields = ['ticker', 'parquet_path', 'n_rows', 'n_cols', 'min_date', 'max_date']
            for entry in catalog_data[:5]:  # Check first 5 entries
                missing_fields = [f for f in required_fields if f not in entry]
                if missing_fields:
                    catalog_check["catalog_entries_valid"] = False
                    catalog_check["issues"].append(f"Missing fields in catalog entry: {missing_fields}")
                    break
                    
        except Exception as e:
            catalog_check["issues"].append(f"Error reading catalog JSON: {e}")
    
    if catalog_check["catalog_parquet_exists"]:
        try:
            catalog_df = pd.read_parquet(parquet_path)
            json_count = catalog_check["entries_count"]
            parquet_count = len(catalog_df)
            catalog_check["json_parquet_match"] = (json_count == parquet_count)
            
            if not catalog_check["json_parquet_match"]:
                catalog_check["issues"].append(f"Catalog JSON has {json_count} entries but Parquet has {parquet_count}")
                
        except Exception as e:
            catalog_check["issues"].append(f"Error reading catalog Parquet: {e}")
    
    catalog_check["is_valid"] = (
        catalog_check["catalog_json_exists"] and
        catalog_check["catalog_parquet_exists"] and
        catalog_check["json_parquet_match"] and
        catalog_check["catalog_entries_valid"] and
        len(catalog_check["issues"]) == 0
    )
    
    return catalog_check


def _verify_module_compatibility(processed_dir: str) -> Dict[str, Any]:
    """Verify data is compatible with ML, Backtest, Optimize, Scanner modules."""
    
    compatibility = {
        "ml_module": {"compatible": False, "issues": []},
        "backtest_module": {"compatible": False, "issues": []}, 
        "optimize_module": {"compatible": False, "issues": []},
        "scanner_module": {"compatible": False, "issues": []},
        "data_map_loadable": False
    }
    
    # Test loading data_map (what modules expect)
    try:
        data_map = _load_processed_data_map(processed_dir)
        compatibility["data_map_loadable"] = len(data_map) > 0
        
        if compatibility["data_map_loadable"]:
            # Test first ticker for module compatibility
            sample_ticker = list(data_map.keys())[0]
            sample_df = data_map[sample_ticker]
            
            # ML Module requirements
            ml_requirements = ['Open', 'High', 'Low', 'Close', 'Volume', 'date']
            missing_ml = [col for col in ml_requirements if col not in sample_df.columns]
            if not missing_ml and len(sample_df) > 20:  # Need some history
                compatibility["ml_module"]["compatible"] = True
            else:
                compatibility["ml_module"]["issues"] = missing_ml or ["Insufficient data rows"]
            
            # Backtest Module requirements  
            bt_requirements = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_bt = [col for col in bt_requirements if col not in sample_df.columns]
            has_date_index = pd.api.types.is_datetime64_any_dtype(sample_df.index) or 'date' in sample_df.columns
            if not missing_bt and has_date_index:
                compatibility["backtest_module"]["compatible"] = True
            else:
                compatibility["backtest_module"]["issues"] = missing_bt + ([] if has_date_index else ["No date index/column"])
            
            # Optimize/Scanner modules (similar requirements to backtest)
            compatibility["optimize_module"] = compatibility["backtest_module"].copy()
            compatibility["scanner_module"] = compatibility["backtest_module"].copy()
            
    except Exception as e:
        for module in ['ml_module', 'backtest_module', 'optimize_module', 'scanner_module']:
            compatibility[module]["issues"].append(f"Data loading error: {e}")
    
    return compatibility


def _verify_individual_files(processed_dir: str) -> Dict[str, Any]:
    """Verify individual parquet files for data quality."""
    
    parquet_dir = os.path.join(processed_dir, "_parquet") 
    results = {}
    
    if not os.path.exists(parquet_dir):
        return {"error": "Parquet directory not found"}
    
    parquet_files = [f for f in os.listdir(parquet_dir) if f.endswith('.parquet')]
    
    for file in parquet_files[:10]:  # Check first 10 files
        ticker = os.path.splitext(file)[0]
        file_path = os.path.join(parquet_dir, file)
        
        file_result = {
            "ticker": ticker,
            "file_size_mb": round(os.path.getsize(file_path) / 1024 / 1024, 2),
            "readable": False,
            "row_count": 0,
            "column_count": 0,
            "date_range": {},
            "required_columns_present": False,
            "data_quality_score": 0,
            "issues": []
        }
        
        try:
            df = pd.read_parquet(file_path)
            file_result["readable"] = True
            file_result["row_count"] = len(df)
            file_result["column_count"] = len(df.columns)
            
            # Check required columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'date']
            present_cols = [col for col in required_cols if col in df.columns]
            file_result["required_columns_present"] = len(present_cols) == len(required_cols)
            
            # Date range analysis
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                file_result["date_range"] = {
                    "min_date": df['date'].min().isoformat(),
                    "max_date": df['date'].max().isoformat(),
                    "days_span": (df['date'].max() - df['date'].min()).days
                }
                
                # Check for recent data
                days_since_last = (datetime.now() - df['date'].max().to_pydatetime()).days
                if days_since_last > 7:
                    file_result["issues"].append(f"Data is {days_since_last} days old")
            
            # Calculate data quality score
            quality_score = 0
            if file_result["readable"]: quality_score += 25
            if file_result["required_columns_present"]: quality_score += 25
            if file_result["row_count"] > 100: quality_score += 25
            if len(file_result["issues"]) == 0: quality_score += 25
            
            file_result["data_quality_score"] = quality_score
            
        except Exception as e:
            file_result["issues"].append(f"File error: {e}")
        
        results[ticker] = file_result
    
    return results


def _load_processed_data_map(processed_dir: str) -> Dict[str, pd.DataFrame]:
    """Load processed parquet files into data_map format (same as main_content expects)."""
    
    data_map = {}
    parquet_dir = os.path.join(processed_dir, "_parquet")
    
    if not os.path.exists(parquet_dir):
        return data_map
    
    parquet_files = [f for f in os.listdir(parquet_dir) if f.endswith('.parquet')]
    
    for file in parquet_files[:5]:  # Test with first 5 files
        ticker = os.path.splitext(file)[0]
        file_path = os.path.join(parquet_dir, file)
        
        try:
            df = pd.read_parquet(file_path)
            # Ensure date column is datetime and set as index (expected by modules)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
            data_map[ticker] = df
        except Exception as e:
            print(f"Failed to load {ticker}: {e}")
    
    return data_map


def _generate_summary_and_recommendations(report: Dict[str, Any]):
    """Generate summary statistics and recommendations."""
    
    # Count results from detailed verification
    detailed = report.get("detailed_results", {})
    total = len(detailed)
    verified = sum(1 for r in detailed.values() if r["data_quality_score"] >= 75)
    warnings = sum(1 for r in detailed.values() if 50 <= r["data_quality_score"] < 75)
    failed = sum(1 for r in detailed.values() if r["data_quality_score"] < 50)
    
    report["summary"].update({
        "total_tickers": total,
        "verified_tickers": verified, 
        "warning_tickers": warnings,
        "failed_tickers": failed
    })
    
    # Generate recommendations
    recommendations = []
    
    structure = report.get("structure_check", {})
    if not structure.get("is_valid", False):
        recommendations.append("❌ Fix directory structure - missing required folders or files")
    
    catalog = report.get("catalog_check", {})
    if not catalog.get("is_valid", False):
        recommendations.append("❌ Rebuild catalog - catalog files are missing or inconsistent")
    
    compatibility = report.get("data_compatibility", {})
    incompatible_modules = [name for name, info in compatibility.items() 
                           if isinstance(info, dict) and not info.get("compatible", True)]
    if incompatible_modules:
        recommendations.append(f"⚠️ Fix data compatibility for: {', '.join(incompatible_modules)}")
    
    if failed > 0:
        recommendations.append(f"❌ {failed} tickers failed verification - need data repair")
    
    if warnings > 0:
        recommendations.append(f"⚠️ {warnings} tickers have warnings - check data quality")
        
    if verified == total and total > 0:
        recommendations.append("✅ All data verified successfully - ready for ML/Backtest/Optimize/Scanner!")
    
    report["recommendations"] = recommendations


if __name__ == "__main__":
    # Test verification
    from data.data_paths import get_data_paths
    
    paths = get_data_paths()
    report = verify_processed_data_structure(paths['processed'])
    
    print(json.dumps(report, indent=2, default=str))