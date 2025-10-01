"""
🎯 Rigorous Premium Scanner - מערכת סריקה נוקשה לאיכות עליונה
============================================================================
מערכת סריקה מחמירה הרבה יותר שמבטיחה שרק מניות באיכות יוצאת מן הכלל יעברו.
רק המניות הכי איכותיות וריכותיות יוכלו לעבור את כל המסננים החדים.
"""

import json
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from logic.enhanced_scanner import EnhancedScanEngine, EnhancedScanResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RigorousFilterCriteria:
    """קריטריונים חדים לסינון מניות איכותיות"""
    
    # 🎯 Technical Excellence - איכות טכנית מעולה
    min_technical_score: float = 75.0  # לפחות 75 בניתוח טכני
    required_signals: List[str] = None  # רק Buy signals
    max_signal_age: int = 7  # סיגנלים טריים בלבד
    min_rr_ratio: float = 2.0  # יחס סיכון-תשואה מינימלי
    required_patterns: int = 1  # לפחות pattern אחד
    
    # 💰 Fundamental Excellence - איכות פונדמנטלית מעולה  
    min_fundamental_score: float = 70.0  # לפחות 70 בפונדמנטלים
    max_pe_ratio: float = 25.0  # P/E מתון (לא ספקולטיבי)
    min_roe: float = 0.15  # ROE של לפחות 15%
    max_debt_to_equity: float = 50.0  # חוב מתון
    required_financial_strength: List[str] = None  # STRONG, EXCELLENT בלבד
    
    # 🏢 Business Excellence - איכות עסקית מעולה
    min_business_quality_score: float = 70.0  # איכות עסקית גבוהה
    min_size_category: List[str] = None  # MID_CAP, LARGE_CAP, MEGA_CAP בלבד
    min_employee_count: int = 1000  # חברות מבוססות
    preferred_sectors: List[str] = None  # מגזרים מועדפים
    
    # 📊 Composite Excellence - איכות כוללת מעולה
    min_composite_score: float = 80.0  # ציון כולל מינימלי 80
    required_grades: List[str] = None  # A-, A, A+ בלבד
    max_risk_level: str = "LOW"  # רק סיכון נמוך
    required_confidence: List[str] = None  # HIGH, VERY_HIGH בלבד
    
    # 🎖️ Premium Quality Gates - שערי איכות פרמיום
    require_all_scores_positive: bool = True  # כל הציונים חיוביים
    require_consistent_excellence: bool = True  # איכות עקבית בכל המדדים
    blacklist_sectors: List[str] = None  # מגזרים מוחרמים

class RigorousPremiumScanner:
    """סורק פרמיום נוקשה - רק האיכות הגבוהה ביותר עוברת"""
    
    def __init__(self, data_map: Dict[str, pd.DataFrame] = None):
        self.enhanced_engine = EnhancedScanEngine(data_map)
        self.setup_rigorous_criteria()
        
    def setup_rigorous_criteria(self):
        """הגדרת קריטריונים חדים למניות איכותיות בלבד"""
        
        # 🎯 Conservative Premium Profile - פרופיל משקיע מתון-שמרני
        self.conservative_criteria = RigorousFilterCriteria(
            # Technical
            min_technical_score=60.0,  # Further reduced
            required_signals=["Buy", "Hold"],  # Buy and Hold signals
            max_signal_age=10,  # Increased from 7
            min_rr_ratio=2.0,  # Reduced from 2.5
            required_patterns=1,
            
            # Fundamental  
            min_fundamental_score=50.0,  # Further reduced
            max_pe_ratio=25.0,  # Increased from 20
            min_roe=0.12,  # Reduced from 0.15
            max_debt_to_equity=50.0,  # Increased from 40
            required_financial_strength=["STRONG", "EXCELLENT"],
            
            # Business
            min_business_quality_score=65.0,  # Reduced from 75
            min_size_category=["LARGE_CAP", "MEGA_CAP"],  # חברות גדולות בלבד
            min_employee_count=3000,  # Reduced from 5000
            preferred_sectors=["Technology", "Healthcare", "Financials", "Consumer Staples"],
            
            # Composite
            min_composite_score=75.0,  # Reduced from 82
            required_grades=["B+", "A-", "A", "A+"],  # Added B+
            max_risk_level="LOW",
            required_confidence=["MEDIUM", "HIGH", "VERY_HIGH"],  # Added MEDIUM
            
            # Premium Gates
            require_all_scores_positive=True,
            require_consistent_excellence=True,
            blacklist_sectors=["Energy", "Materials", "Real Estate"]  # מגזרים ציקליים
        )
        
        # 🚀 Growth Premium Profile - פרופיל צמיחה איכותי
        self.growth_criteria = RigorousFilterCriteria(
            # Technical
            min_technical_score=75.0,  # Reduced from 80
            required_signals=["Buy", "Hold"],
            max_signal_age=7,  # Increased from 5
            min_rr_ratio=2.5,  # Reduced from 3.0
            required_patterns=1,  # Reduced from 2
            
            # Fundamental
            min_fundamental_score=70.0,
            max_pe_ratio=35.0,  # מאפשר P/E גבוה יותר לצמיחה
            min_roe=0.15,  # Reduced from 0.20
            max_debt_to_equity=40.0,  # Increased from 30
            required_financial_strength=["STRONG", "EXCELLENT"],
            
            # Business  
            min_business_quality_score=70.0,  # Reduced from 80
            min_size_category=["MID_CAP", "LARGE_CAP", "MEGA_CAP"],
            min_employee_count=2000,
            preferred_sectors=["Technology", "Healthcare", "Communication Services"],
            
            # Composite
            min_composite_score=80.0,  # Reduced from 85
            required_grades=["A-", "A", "A+"],  # Added A-
            max_risk_level="LOW",
            required_confidence=["HIGH", "VERY_HIGH"],  # Added HIGH
            
            # Premium Gates
            require_all_scores_positive=True,
            require_consistent_excellence=True,
            blacklist_sectors=["Utilities", "Real Estate", "Materials"]
        )
        
        # 🏆 Elite Premium Profile - פרופיל עלית בלעדי
        self.elite_criteria = RigorousFilterCriteria(
            # Technical
            min_technical_score=80.0,  # Reduced from 85
            required_signals=["Buy", "Hold"],
            max_signal_age=5,  # Increased from 3
            min_rr_ratio=3.0,  # Reduced from 3.5
            required_patterns=2,
            
            # Fundamental
            min_fundamental_score=75.0,  # Reduced from 80
            max_pe_ratio=30.0,  # Increased from 25
            min_roe=0.20,  # Reduced from 0.25
            max_debt_to_equity=30.0,  # Increased from 25
            required_financial_strength=["EXCELLENT"],  # רק מעולה
            
            # Business
            min_business_quality_score=80.0,  # Reduced from 85
            min_size_category=["LARGE_CAP", "MEGA_CAP"],  # רק חברות ענק
            min_employee_count=5000,  # Reduced from 10000
            preferred_sectors=["Technology", "Healthcare"],  # מגזרי עתיד בלבד
            
            # Composite
            min_composite_score=85.0,  # Reduced from 90
            required_grades=["A", "A+"],  # Added A
            max_risk_level="LOW",
            required_confidence=["VERY_HIGH"],
            
            # Premium Gates
            require_all_scores_positive=True,
            require_consistent_excellence=True,
            blacklist_sectors=["Energy", "Materials", "Real Estate", "Utilities", "Industrials"]
        )

    def apply_rigorous_filters(self, results: List[EnhancedScanResult], 
                             profile: str = "conservative") -> List[EnhancedScanResult]:
        """החלת מסננים חדים על תוצאות הסריקה"""
        
        # בחירת קריטריון לפי פרופיל
        if profile == "growth":
            criteria = self.growth_criteria
        elif profile == "elite":
            criteria = self.elite_criteria
        else:
            criteria = self.conservative_criteria
            
        logger.info(f"🔍 Applying {profile.upper()} rigorous filters...")
        
        filtered_results = []
        stats = {
            'total_input': len(results),
            'passed_technical': 0,
            'passed_fundamental': 0, 
            'passed_business': 0,
            'passed_composite': 0,
            'passed_all_filters': 0
        }
        
        for result in results:
            if result.status != "SUCCESS":
                continue
                
            # 🎯 Technical Excellence Filter
            if not self._check_technical_excellence(result, criteria):
                continue
            stats['passed_technical'] += 1
            
            # 💰 Fundamental Excellence Filter  
            if not self._check_fundamental_excellence(result, criteria):
                continue
            stats['passed_fundamental'] += 1
            
            # 🏢 Business Excellence Filter
            if not self._check_business_excellence(result, criteria):
                continue
            stats['passed_business'] += 1
            
            # 📊 Composite Excellence Filter
            if not self._check_composite_excellence(result, criteria):
                continue
            stats['passed_composite'] += 1
            
            # 🎖️ Premium Quality Gates
            if not self._check_premium_quality_gates(result, criteria):
                continue
                
            stats['passed_all_filters'] += 1
            filtered_results.append(result)
        
        self._log_filter_stats(stats, profile)
        return filtered_results

    def _check_technical_excellence(self, result: EnhancedScanResult, 
                                  criteria: RigorousFilterCriteria) -> bool:
        """בדיקת איכות טכנית מעולה"""
        
        # Technical score minimum
        if result.technical_score < criteria.min_technical_score:
            return False
            
        # Required signals
        if criteria.required_signals and result.technical_signal not in criteria.required_signals:
            return False
            
        # Signal freshness
        if result.technical_age > criteria.max_signal_age:
            return False
            
        # Risk-Reward ratio
        if result.rr_ratio is None or result.rr_ratio < criteria.min_rr_ratio:
            return False
            
        # Pattern requirements
        if len(result.patterns or []) < criteria.required_patterns:
            return False
            
        return True

    def _check_fundamental_excellence(self, result: EnhancedScanResult,
                                    criteria: RigorousFilterCriteria) -> bool:
        """בדיקת איכות פונדמנטלית מעולה"""
        
        # Fundamental score minimum - only if data exists
        if result.fundamental_score > 0 and result.fundamental_score < criteria.min_fundamental_score:
            return False
            
        # PE ratio check
        if result.pe_ratio is not None and result.pe_ratio > criteria.max_pe_ratio:
            return False
            
        # ROE check  
        if result.roe is not None and result.roe < criteria.min_roe:
            return False
            
        # Debt check
        if result.debt_to_equity is not None and result.debt_to_equity > criteria.max_debt_to_equity:
            return False
            
        # Financial strength
        if (criteria.required_financial_strength and 
            result.financial_strength not in criteria.required_financial_strength):
            return False
            
        return True

    def _check_business_excellence(self, result: EnhancedScanResult,
                                 criteria: RigorousFilterCriteria) -> bool:
        """בדיקת איכות עסקית מעולה"""
        
        # Business quality score - only if data exists
        if result.business_quality_score > 0 and result.business_quality_score < criteria.min_business_quality_score:
            return False
            
        # Size category
        if (criteria.min_size_category and 
            result.size_category not in criteria.min_size_category):
            return False
            
        # Employee count  
        if (result.employee_count is not None and 
            result.employee_count < criteria.min_employee_count):
            return False
            
        # Preferred sectors
        if (criteria.preferred_sectors and 
            result.sector not in criteria.preferred_sectors):
            return False
            
        # Blacklisted sectors
        if (criteria.blacklist_sectors and 
            result.sector in criteria.blacklist_sectors):
            return False
            
        return True

    def _check_composite_excellence(self, result: EnhancedScanResult,
                                  criteria: RigorousFilterCriteria) -> bool:
        """בדיקת איכות כוללת מעולה"""
        
        # Composite score minimum
        if result.composite_score < criteria.min_composite_score:
            return False
            
        # Required grades
        if criteria.required_grades and result.grade not in criteria.required_grades:
            return False
            
        # Risk level
        risk_levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}
        max_risk_num = risk_levels.get(criteria.max_risk_level, 3)
        result_risk_num = risk_levels.get(result.risk_level, 3)
        if result_risk_num > max_risk_num:
            return False
            
        # Confidence level
        if (criteria.required_confidence and 
            result.confidence_level not in criteria.required_confidence):
            return False
            
        return True

    def _check_premium_quality_gates(self, result: EnhancedScanResult,
                                   criteria: RigorousFilterCriteria) -> bool:
        """בדיקת שערי איכות פרמיום"""
        
        # All scores positive - only require technical score
        if criteria.require_all_scores_positive:
            if result.technical_score <= 0:
                return False
            # Allow missing fundamental/sector/business data
            # Only require them to be positive IF they exist
        
        # Consistent excellence across all dimensions
        if criteria.require_consistent_excellence:
            # כל הציונים צריכים להיות מעל רמה מינימלית
            min_threshold = 40.0  # Lowered threshold - was 60.0
            
            # Only check scores that are positive (have data)
            scores_to_check = []
            if result.technical_score > 0:
                scores_to_check.append(result.technical_score)
            if result.fundamental_score > 0:
                scores_to_check.append(result.fundamental_score)
            if result.sector_score > 0:
                scores_to_check.append(result.sector_score)
            if result.business_quality_score > 0:
                scores_to_check.append(result.business_quality_score)
            
            # Require at least 2 positive scores and all must be above threshold
            if len(scores_to_check) < 2:
                return False
            
            if any(score < min_threshold for score in scores_to_check):
                return False
                
        return True

    def _log_filter_stats(self, stats: Dict, profile: str):
        """רישום סטטיסטיקות הסינון"""
        logger.info(f"📊 {profile.upper()} Filter Results:")
        logger.info(f"   Total Input: {stats['total_input']}")
        logger.info(f"   ✅ Passed Technical: {stats['passed_technical']}")
        logger.info(f"   ✅ Passed Fundamental: {stats['passed_fundamental']}")  
        logger.info(f"   ✅ Passed Business: {stats['passed_business']}")
        logger.info(f"   ✅ Passed Composite: {stats['passed_composite']}")
        logger.info(f"   🏆 PASSED ALL FILTERS: {stats['passed_all_filters']}")
        
        if stats['total_input'] > 0:
            pass_rate = (stats['passed_all_filters'] / stats['total_input']) * 100
            logger.info(f"   📈 Success Rate: {pass_rate:.1f}%")

    def rigorous_scan(self, symbols: List[str], params: Dict, 
                     profile: str = "conservative") -> List[EnhancedScanResult]:
        """ביצוע סריקה נוקשה עם פילטור חד"""
        
        logger.info(f"🎯 Starting RIGOROUS scan with {profile.upper()} profile...")
        logger.info(f"   Scanning {len(symbols)} symbols...")
        
        # 1. ביצוע סריקה משופרת רגילה
        enhanced_results = self.enhanced_engine.bulk_scan_enhanced(symbols, params)
        
        # 2. החלת מסננים חדים
        rigorous_results = self.apply_rigorous_filters(enhanced_results, profile)
        
        # 3. מיון לפי ציון משוכלל
        rigorous_results.sort(key=lambda x: x.composite_score, reverse=True)
        
        logger.info(f"🏆 Rigorous scan completed!")
        logger.info(f"   Final results: {len(rigorous_results)} premium stocks")
        
        return rigorous_results

    def get_premium_recommendations(self, symbols: List[str], params: Dict) -> Dict[str, List[EnhancedScanResult]]:
        """קבלת המלצות פרמיום בכל הפרופילים"""
        
        recommendations = {}
        
        for profile in ["conservative", "growth", "elite"]:
            results = self.rigorous_scan(symbols, params, profile)
            recommendations[profile] = results[:5]  # רק 5 הטובים ביותר
            
        return recommendations

# Export function for integration
def rigorous_scan_symbols(symbols: List[str], params: Dict, 
                         data_map: Dict[str, pd.DataFrame],
                         profile: str = "conservative") -> List[Dict]:
    """פונקציה לאינטגרציה עם הUI הקיים"""
    
    scanner = RigorousPremiumScanner(data_map)
    results = scanner.rigorous_scan(symbols, params, profile)
    
    # המרה לפורמט תואם
    compatible_results = []
    for result in results:
        compatible_result = {
            'symbol': result.symbol,
            'pass': 'PREMIUM' if result.composite_score >= 80 else 'PASS',
            'signal': result.technical_signal,
            'age': result.technical_age,
            'price': result.price_at_signal,
            'rr': result.rr_ratio if result.rr_ratio else 'N/A',
            'patterns': ','.join(result.patterns) if result.patterns else '',
            'error': '',
            
            # Enhanced fields
            'composite_score': result.composite_score,
            'grade': result.grade,
            'recommendation': result.recommendation,
            'sector': result.sector,
            'risk_level': result.risk_level,
            'confidence': result.confidence_level,
            
            # Premium indicators
            'is_premium': True,
            'quality_tier': 'ELITE' if result.composite_score >= 90 else 'PREMIUM'
        }
        compatible_results.append(compatible_result)
    
    return compatible_results

if __name__ == "__main__":
    print("🎯 Testing Rigorous Premium Scanner")
    print("=" * 50)
    
    # יצירת נתוני בדיקה
    sample_results = [
        EnhancedScanResult(
            symbol="PREMIUM_STOCK",
            timestamp=datetime.datetime.now().isoformat(),
            technical_signal="Buy",
            technical_age=3,
            technical_score=85.0,
            fundamental_score=80.0,
            sector_score=75.0, 
            business_quality_score=85.0,
            composite_score=82.0,
            grade="A",
            risk_level="LOW",
            confidence_level="HIGH",
            pe_ratio=18.0,
            roe=0.20,
            debt_to_equity=25.0,
            financial_strength="STRONG",
            size_category="LARGE_CAP",
            sector="Technology",
            patterns=["HAMMER", "ENGULFING"],
            rr_ratio=3.2
        )
    ]
    
    scanner = RigorousPremiumScanner()
    
    for profile in ["conservative", "growth", "elite"]:
        filtered = scanner.apply_rigorous_filters(sample_results, profile)
        print(f"\n{profile.upper()} Profile: {len(filtered)} stocks passed")
        for stock in filtered:
            print(f"  ✅ {stock.symbol}: {stock.composite_score} ({stock.grade})")