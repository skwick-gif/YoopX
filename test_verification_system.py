"""
Comprehensive test of the enhanced verification system for ML/Backtest/Optimize/Scanner compatibility.
"""

import sys
import os
sys.path.append('.')

from data.data_paths import get_data_paths
from data.enhanced_verification import verify_processed_data_structure
import json


def test_verification_system():
    """Test the enhanced verification system."""
    print("=" * 80)
    print("🔍 ENHANCED DATA VERIFICATION SYSTEM TEST")
    print("=" * 80)
    print()
    
    print("🎯 **מה הווריפיקציה בודקת עבור ML/Backtest/Optimize/Scanner:**")
    print()
    
    print("📋 **1. STRUCTURE VERIFICATION:**")
    print("   ✅ Directory structure: processed_data/_parquet/ & _catalog/")
    print("   ✅ File existence: Parquet files + catalog.json + catalog.parquet")
    print("   ✅ File counts match between directories")
    print()
    
    print("📊 **2. DATA COMPATIBILITY:**")
    print("   🤖 **ML Module**: Open, High, Low, Close, Volume, date + sufficient history")
    print("   📈 **Backtest Module**: OHLCV columns + proper date index/column")
    print("   ⚙️ **Optimize Module**: Same as Backtest (parameter optimization)")
    print("   🔎 **Scanner Module**: Same as Backtest (pattern scanning)")
    print()
    
    print("🔍 **3. DATA QUALITY CHECKS:**")
    print("   📅 Date consistency and recent data")
    print("   📊 Column presence and data types")
    print("   📈 Sufficient data rows for analysis")
    print("   🚫 No corruption or read errors")
    print()
    
    print("📚 **4. CATALOG INTEGRITY:**")
    print("   📄 Catalog JSON structure and completeness")
    print("   📦 Catalog Parquet consistency")
    print("   🎯 Entry accuracy and metadata")
    print()
    
    # Run actual verification
    paths = get_data_paths()
    processed_dir = paths['processed']
    
    print(f"🔍 **Running verification on: {processed_dir}**")
    print()
    
    try:
        verification_report = verify_processed_data_structure(processed_dir)
        
        print("📋 **VERIFICATION RESULTS:**")
        print("=" * 50)
        
        # Structure Check
        structure = verification_report.get('structure_check', {})
        print(f"🏗️  **Structure Check**: {'✅ PASS' if structure.get('is_valid') else '❌ FAIL'}")
        print(f"   • Base directory exists: {structure.get('base_dir_exists')}")
        print(f"   • Parquet directory exists: {structure.get('parquet_dir_exists')}")
        print(f"   • Catalog directory exists: {structure.get('catalog_dir_exists')}")
        print(f"   • Parquet files found: {structure.get('parquet_files_count', 0)}")
        print()
        
        # Catalog Check
        catalog = verification_report.get('catalog_check', {})
        print(f"📚 **Catalog Check**: {'✅ PASS' if catalog.get('is_valid') else '❌ FAIL'}")
        print(f"   • Catalog JSON exists: {catalog.get('catalog_json_exists')}")
        print(f"   • Catalog Parquet exists: {catalog.get('catalog_parquet_exists')}")
        print(f"   • Entries count: {catalog.get('entries_count', 0)}")
        print(f"   • JSON-Parquet match: {catalog.get('json_parquet_match')}")
        if catalog.get('issues'):
            for issue in catalog['issues']:
                print(f"   ⚠️  Issue: {issue}")
        print()
        
        # Module Compatibility  
        compatibility = verification_report.get('data_compatibility', {})
        print("🎯 **Module Compatibility:**")
        
        modules = {
            'ml_module': '🤖 ML Module',
            'backtest_module': '📈 Backtest Module', 
            'optimize_module': '⚙️ Optimize Module',
            'scanner_module': '🔎 Scanner Module'
        }
        
        for module_key, module_name in modules.items():
            module_info = compatibility.get(module_key, {})
            compatible = module_info.get('compatible', False)
            issues = module_info.get('issues', [])
            
            status = '✅ COMPATIBLE' if compatible else '❌ INCOMPATIBLE'
            print(f"   {module_name}: {status}")
            
            if issues:
                for issue in issues:
                    print(f"     ⚠️  {issue}")
        
        data_map_ok = compatibility.get('data_map_loadable', False)
        print(f"   📊 Data Map Loadable: {'✅ YES' if data_map_ok else '❌ NO'}")
        print()
        
        # Summary
        summary = verification_report.get('summary', {})
        print("📊 **SUMMARY:**")
        print(f"   • Total tickers checked: {summary.get('total_tickers', 0)}")
        print(f"   • ✅ Verified tickers: {summary.get('verified_tickers', 0)}")
        print(f"   • ⚠️  Warning tickers: {summary.get('warning_tickers', 0)}")
        print(f"   • ❌ Failed tickers: {summary.get('failed_tickers', 0)}")
        print()
        
        # Recommendations
        recommendations = verification_report.get('recommendations', [])
        if recommendations:
            print("💡 **RECOMMENDATIONS:**")
            for rec in recommendations:
                print(f"   {rec}")
            print()
        
        # Overall Status
        total = summary.get('total_tickers', 0)
        verified = summary.get('verified_tickers', 0)
        
        if total == 0:
            print("⚠️  **STATUS: NO DATA FOUND**")
            print("   Run Daily Update first to download and process data")
        elif verified == total:
            print("🎉 **STATUS: ALL SYSTEMS GO!**") 
            print("   ✅ Data is ready for ML, Backtest, Optimize, and Scanner!")
        else:
            failed = summary.get('failed_tickers', 0)
            if failed > 0:
                print("⚠️  **STATUS: ISSUES DETECTED**")
                print(f"   {failed} tickers need attention before running ML/Backtest")
            else:
                print("🟡 **STATUS: MOSTLY READY**")
                print("   Minor warnings present, but should work for most operations")
        
        return verification_report
        
    except Exception as e:
        print(f"❌ **VERIFICATION ERROR**: {e}")
        print("   The verification system encountered an error")
        print("   This might indicate missing directories or corrupted data")
        return None


def demonstrate_verification_flow():
    """Demonstrate the complete verification flow."""
    print("\n" + "=" * 80) 
    print("🔄 COMPLETE DAILY UPDATE + VERIFICATION FLOW")
    print("=" * 80)
    print()
    
    print("📋 **ההליך המלא שעכשיו מתבצע ב-Daily Update:**")
    print()
    
    print("1️⃣ **Data Download** (0-80%)")
    print("   • 📥 Download from Yahoo Finance + API providers")
    print("   • 💾 Save raw JSON files to raw_data/")
    print("   • 🔄 Smart incremental updates")
    print()
    
    print("2️⃣ **Data Processing** (80-95%)")
    print("   • 🔄 Convert JSON to structured Parquet")
    print("   • 📊 Create standardized columns (OHLCV + metadata)")
    print("   • 📚 Generate catalog for fast access")
    print()
    
    print("3️⃣ **Automatic Verification** (95-99%)")
    print("   • 🔍 Verify ML module compatibility")
    print("   • 📈 Check Backtest data requirements")
    print("   • ⚙️ Validate Optimize/Scanner readiness")
    print("   • 🎯 Test data_map loading")
    print()
    
    print("4️⃣ **Results & Recommendations** (100%)")
    print("   • ✅ Report compatibility status")
    print("   • 📋 Generate detailed verification report")
    print("   • 💡 Provide actionable recommendations")
    print()
    
    print("🎯 **היתרון החדש:**")
    print("   לא צריך לחכות למודול ML/Backtest כדי לגלות שיש בעיה!")
    print("   הווריפיקציה מזהה בעיות מיד ומציעה פתרונות.")


if __name__ == "__main__":
    report = test_verification_system()
    demonstrate_verification_flow()
    
    if report:
        print("\n🎉 Verification system is working!")
    else:
        print("\n⚠️ Run Daily Update first to create processed data.")