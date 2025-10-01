"""
Enhanced UI Demo - Show the Focused Approach
============================================
Quick demonstration of the new Enhanced mode vs Classic mode in the UI.
"""

import sys
import os
import datetime
from dataclasses import dataclass
from typing import List

# Add project root to path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Mock enhanced result for demo
@dataclass
class MockEnhancedResult:
    symbol: str
    status: str = "SUCCESS" 
    technical_signal: str = "Hold"
    technical_age: int = 10
    price_at_signal: float = 150.0
    risk_reward: float = 2.5
    patterns: str = "DOJI,HAMMER"
    composite_score: float = 75.0
    grade: str = "A-"
    recommendation: str = "BUY"
    sector: str = "Technology"
    risk_level: str = "LOW"
    technical_score: float = 70.0
    fundamental_score: float = 80.0
    sector_score: int = 85
    business_quality_score: float = 90.0

def create_mock_results() -> List[MockEnhancedResult]:
    """Create some mock results to demonstrate UI"""
    return [
        MockEnhancedResult(
            symbol="AAPL", composite_score=92.5, grade="A+", recommendation="STRONG BUY",
            technical_score=85.0, fundamental_score=95.0, sector_score=95, business_quality_score=95.0,
            price_at_signal=175.50, risk_reward=3.2, sector="Technology", risk_level="LOW"
        ),
        MockEnhancedResult(
            symbol="GOOGL", composite_score=88.0, grade="A", recommendation="BUY", 
            technical_score=80.0, fundamental_score=90.0, sector_score=90, business_quality_score=92.0,
            price_at_signal=142.30, risk_reward=2.8, sector="Communication", risk_level="LOW"
        ),
        MockEnhancedResult(
            symbol="MSFT", composite_score=85.5, grade="A", recommendation="BUY",
            technical_score=82.0, fundamental_score=85.0, sector_score=88, business_quality_score=87.0,
            price_at_signal=378.90, risk_reward=2.9, sector="Technology", risk_level="LOW"
        ),
        MockEnhancedResult(
            symbol="TSLA", composite_score=72.0, grade="B", recommendation="HOLD",
            technical_score=75.0, fundamental_score=65.0, sector_score=70, business_quality_score=78.0,
            price_at_signal=251.20, risk_reward=2.1, sector="Consumer Cyclical", risk_level="MEDIUM"
        ),
        MockEnhancedResult(
            symbol="NVDA", composite_score=68.5, grade="B-", recommendation="HOLD",
            technical_score=70.0, fundamental_score=60.0, sector_score=75, business_quality_score=69.0,
            price_at_signal=118.75, risk_reward=1.9, sector="Technology", risk_level="MEDIUM"
        ),
        MockEnhancedResult(
            symbol="AMD", composite_score=58.0, grade="C+", recommendation="NEUTRAL",
            technical_score=55.0, fundamental_score=50.0, sector_score=65, business_quality_score=61.0,
            price_at_signal=142.85, risk_reward=1.7, sector="Technology", risk_level="HIGH"
        )
    ]

def print_focused_table(results: List[MockEnhancedResult]):
    """Print the focused enhanced table as it appears in UI"""
    print("\n🎯 ENHANCED MODE TABLE (Focused Approach)")
    print("=" * 80)
    print(f"{'Symbol':<8} {'Signal':<6} {'Age':<4} {'Price':<8} {'R:R':<5} {'Enhanced':<9} {'Grade':<5} {'Recommendation':<12} {'Sector':<15} {'Risk':<6}")
    print("-" * 80)
    
    for result in sorted(results, key=lambda x: x.composite_score, reverse=True):
        price_str = f"${result.price_at_signal:.1f}"
        print(f"{result.symbol:<8} {result.technical_signal:<6} {result.technical_age:<4} {price_str:<8} "
              f"{result.risk_reward:<5.1f} {result.composite_score:<8.1f} {result.grade:<5} "
              f"{result.recommendation:<12} {result.sector[:14]:<15} {result.risk_level:<6}")

def print_classic_table(results: List[MockEnhancedResult]):
    """Print how it would look in classic mode (too many columns)"""
    print("\n❌ CLASSIC MODE TABLE (Too Much Information)")
    print("=" * 120)
    print(f"{'Symbol':<6} {'Signal':<6} {'Age':<3} {'Price':<7} {'PE':<5} {'ROE':<5} {'Debt':<5} {'Employees':<9} "
          f"{'Tech':<5} {'Fund':<5} {'Sect':<5} {'Qual':<5} {'Enhanced':<8} {'Grade':<5} {'Rec':<8} {'Risk':<6}")
    print("-" * 120)
    
    for result in sorted(results, key=lambda x: x.composite_score, reverse=True):
        # Simulate the noisy detailed breakdown
        price_str = f"${result.price_at_signal:.0f}"
        fake_pe = "22.5"
        fake_roe = "18.2" 
        fake_debt = "0.25"
        fake_emp = "143,000"
        
        print(f"{result.symbol:<6} {result.technical_signal:<6} {result.technical_age:<3} {price_str:<7} "
              f"{fake_pe:<5} {fake_roe:<5} {fake_debt:<5} {fake_emp:<9} "
              f"{result.technical_score:<5.0f} {result.fundamental_score:<5.0f} {result.sector_score:<5} {result.business_quality_score:<5.0f} "
              f"{result.composite_score:<7.1f} {result.grade:<5} {result.recommendation[:8]:<8} {result.risk_level:<6}")

def main():
    print("🚀 Enhanced UI Demo - Focused vs Cluttered Approach")
    print(f"Demo time: {datetime.datetime.now()}")
    print("\nThis demonstrates the user's request: 'הרעיון שלי היה שאני לא אראה נתונים כאלה אלא ציון משוכלל סופי'")
    
    # Create mock results
    results = create_mock_results()
    
    # Show the bad old way (too many columns)
    print_classic_table(results)
    
    print("\n" + "🔄" * 40)
    print("TRANSFORMATION: From cluttered → focused")
    print("🔄" * 40)
    
    # Show the new focused way
    print_focused_table(results)
    
    print(f"\n💡 KEY INSIGHTS FROM FOCUSED APPROACH:")
    print("-" * 40)
    
    top_3 = sorted(results, key=lambda x: x.composite_score, reverse=True)[:3]
    for i, result in enumerate(top_3, 1):
        tooltip_info = f"Tech:{result.technical_score:.0f} + Fund:{result.fundamental_score:.0f} + Sector:{result.sector_score} + Quality:{result.business_quality_score:.0f}"
        print(f"\n#{i} {result.symbol}: Enhanced Score {result.composite_score:.1f}")
        print(f"   📊 Breakdown: {tooltip_info}")
        print(f"   🎯 Action: {result.grade} grade → {result.recommendation}")
        print(f"   💼 Context: {result.sector} sector, {result.risk_level} risk")
        
        if result.composite_score >= 85:
            print(f"   💚 Excellent - strong across all dimensions")
        elif result.composite_score >= 75:
            print(f"   💛 Good candidate with solid fundamentals")
        else:
            print(f"   🟨 Decent option, review breakdown details")
    
    print(f"\n🎯 UI DESIGN BENEFITS:")
    print("✅ Single Enhanced Score - instant understanding")
    print("✅ Color-coded grades - visual hierarchy") 
    print("✅ Action-oriented recommendations - clear next steps")
    print("✅ Essential context only - sector + risk level")
    print("✅ Detailed breakdown in tooltips - available when needed")
    print("❌ No PE ratios, employee counts, or other noise in main view")
    print("❌ No cognitive overload from 18+ columns")
    
    print(f"\n🏆 RESULT: המערכת מראה 'ציון משוכלל סופי' כמו שהמשתמש ביקש!")
    print("The Enhanced Score combines all the intelligence without the clutter.")

if __name__ == "__main__":
    main()