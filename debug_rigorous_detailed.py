
def debug_rigorous_scan():
    """Debug mode for rigorous scan - shows why stocks are filtered"""
    
    from logic.rigorous_scanner import RigorousPremiumScanner
    from debug_real_scan import create_test_data, test_enhanced_scan
    
    print("🔍 DEBUG: Rigorous Scan Analysis")
    print("=" * 50)
    
    # Create data and run enhanced scan
    data_map = create_test_data()
    enhanced_results = test_enhanced_scan(data_map)
    
    if not enhanced_results:
        print("❌ No enhanced results to analyze")
        return
    
    # Analyze each stock in detail
    scanner = RigorousPremiumScanner()
    
    for result in enhanced_results:
        if result.status != "SUCCESS":
            continue
            
        print(f"\n📊 Analyzing {result.symbol}:")
        print(f"   Technical Signal: {result.technical_signal}")
        print(f"   Technical Score: {result.technical_score}")
        print(f"   Fundamental Score: {result.fundamental_score}")
        print(f"   Composite Score: {result.composite_score}")
        print(f"   Grade: {result.grade}")
        print(f"   Risk: {result.risk_level}")
        
        # Test against conservative criteria
        criteria = scanner.conservative_criteria
        
        reasons = []
        if result.technical_signal not in criteria.required_signals:
            reasons.append(f"Signal {result.technical_signal} not in {criteria.required_signals}")
        
        if result.technical_score < criteria.min_technical_score:
            reasons.append(f"Technical score {result.technical_score} < {criteria.min_technical_score}")
            
        if result.fundamental_score < criteria.min_fundamental_score:
            reasons.append(f"Fundamental score {result.fundamental_score} < {criteria.min_fundamental_score}")
            
        if result.composite_score < criteria.min_composite_score:
            reasons.append(f"Composite score {result.composite_score} < {criteria.min_composite_score}")
        
        if reasons:
            print(f"   ❌ FILTERED OUT:")
            for reason in reasons:
                print(f"      • {reason}")
        else:
            print(f"   ✅ WOULD PASS conservative filter")

if __name__ == "__main__":
    debug_rigorous_scan()
