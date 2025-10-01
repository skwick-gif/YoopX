"""
Enhanced Scanning Engine with Non-Technical Data Integration
=========================================================
Integrates technical analysis with fundamental analysis, sector analysis,
and business quality metrics for comprehensive stock screening.
"""

import json
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import logging

# Import our modules
try:
    import sys
    import os
    # Add parent directory to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import backend  # Technical analysis functions
    from data.non_technical_loader import (
        NonTechnicalDataLoader, 
        CompanyScores, 
        CompanyProfile, 
        CompanyFundamentals,
        get_enhanced_company_data
    )
except ImportError as e:
    print(f"Import error: {e}")
    backend = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TechnicalSignal:
    """Technical analysis results"""
    signal: str = "Hold"  # Buy/Sell/Hold
    age: int = 0
    price_at_signal: float = 0.0
    patterns: List[str] = None
    rr_ratio: Optional[float] = None
    confidence: float = 0.0

@dataclass
class EnhancedScanResult:
    """Comprehensive scan result with all dimensions"""
    # Basic info
    symbol: str
    timestamp: str
    
    # Technical analysis
    technical_signal: str = "Hold"
    technical_age: int = 0
    price_at_signal: float = 0.0
    patterns: List[str] = None
    rr_ratio: Optional[float] = None
    technical_score: float = 0.0
    
    # Fundamental analysis
    fundamental_score: float = 0.0
    pe_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    financial_strength: str = "UNKNOWN"
    
    # Business & Sector
    sector: str = ""
    industry: str = ""
    sector_score: float = 0.0
    business_quality_score: float = 0.0
    size_category: str = "UNKNOWN"
    employee_count: Optional[int] = None
    
    # Composite scores
    composite_score: float = 0.0
    confidence_level: str = "LOW"
    grade: str = "C"
    
    # Additional info
    long_name: str = ""
    business_summary: str = ""
    recommendation: str = ""
    risk_level: str = "MEDIUM"
    
    # Status
    status: str = "SUCCESS"
    error_message: str = ""

class EnhancedScanEngine:
    """Enhanced scanning engine combining technical and fundamental analysis"""
    
    def __init__(self, data_map: Dict[str, pd.DataFrame] = None):
        self.data_map = data_map or {}
        self.non_tech_loader = NonTechnicalDataLoader()
        
        # Scoring weights for composite score
        self.weights = {
            'technical': 0.40,      # Technical analysis weight
            'fundamental': 0.35,    # Fundamental analysis weight  
            'sector': 0.15,         # Sector momentum weight
            'business_quality': 0.10 # Business quality weight
        }
        
        # Risk tolerance settings
        self.risk_settings = {
            'conservative': {'min_market_cap': 10_000_000_000, 'max_pe': 25, 'min_roe': 0.10},
            'moderate': {'min_market_cap': 2_000_000_000, 'max_pe': 35, 'min_roe': 0.05},
            'aggressive': {'min_market_cap': 300_000_000, 'max_pe': 50, 'min_roe': 0.00}
        }

    def analyze_technical(self, symbol: str, df: pd.DataFrame, params: Dict) -> TechnicalSignal:
        """Perform technical analysis using existing backend functions"""
        technical = TechnicalSignal()
        
        try:
            if backend is None:
                raise ImportError("Backend module not available")
            
            # Get strategy from params
            strategy = params.get('scan_strategy', 'Donchian Breakout')
            
            # Get signal from backend
            signal, age, price = backend.scan_signal(df, strategy, params)
            technical.signal = signal
            technical.age = age
            technical.price_at_signal = price
            
            # Get patterns
            patterns_txt = params.get('patterns', '')
            selected_patterns = [p.strip().upper() for p in patterns_txt.split(',') if p.strip()]
            lookback = int(params.get('lookback', 30))
            
            if selected_patterns:
                detected_patterns = backend.detect_patterns(df, lookback, selected_patterns)
                technical.patterns = detected_patterns
            else:
                technical.patterns = []
            
            # Calculate technical confidence based on signal strength and patterns
            confidence = 50  # Base confidence
            
            if technical.signal == "Buy":
                confidence += 20
            elif technical.signal == "Sell":
                confidence += 15
            
            if technical.patterns:
                confidence += len(technical.patterns) * 5
                
            if technical.age <= 5:  # Fresh signal
                confidence += 15
            elif technical.age <= 10:
                confidence += 10
            elif technical.age <= 20:
                confidence += 5
            
            technical.confidence = min(confidence, 100)
            
            # Calculate RR ratio if specified
            rr_target = params.get('rr_target', '2xATR')
            if rr_target == '2xATR':
                try:
                    atr_series = backend.atr(df)
                    if atr_series is not None and len(atr_series) > 0:
                        current_atr = atr_series.iloc[-1]
                        if current_atr > 0 and technical.price_at_signal > 0:
                            current_price = df['Close'].iloc[-1]
                            if technical.signal == "Buy":
                                target = current_price + (2 * current_atr)
                                stop = current_price - current_atr
                            else:
                                target = current_price - (2 * current_atr)  
                                stop = current_price + current_atr
                            
                            if stop != current_price:
                                technical.rr_ratio = abs(target - current_price) / abs(stop - current_price)
                except Exception as e:
                    logger.warning(f"Could not calculate RR ratio for {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Technical analysis failed for {symbol}: {e}")
            technical.signal = "ERROR"
            technical.confidence = 0
            
        return technical

    def calculate_technical_score(self, technical: TechnicalSignal) -> float:
        """Convert technical signal to numerical score (0-100)"""
        score = 50  # Base score
        
        # Signal scoring
        if technical.signal == "Buy":
            score += 30
        elif technical.signal == "Sell":
            score += 15  # Sell signals can be valuable too
        elif technical.signal == "ERROR":
            return 0
        
        # Age scoring (fresher is better)
        if technical.age <= 3:
            score += 20
        elif technical.age <= 7:
            score += 15
        elif technical.age <= 14:
            score += 10
        elif technical.age <= 30:
            score += 5
        
        # Pattern scoring
        if technical.patterns:
            score += min(len(technical.patterns) * 5, 15)
        
        # RR ratio scoring  
        if technical.rr_ratio is not None:
            if technical.rr_ratio >= 2.0:
                score += 15
            elif technical.rr_ratio >= 1.5:
                score += 10
            elif technical.rr_ratio >= 1.0:
                score += 5
        
        return min(score, 100)

    def scan_symbol_enhanced(self, symbol: str, params: Dict) -> EnhancedScanResult:
        """Perform comprehensive enhanced scan on a single symbol"""
        result = EnhancedScanResult(
            symbol=symbol,
            timestamp=datetime.datetime.now().isoformat()
        )
        
        try:
            # 1. Technical Analysis
            df = self.data_map.get(symbol)
            if df is not None and len(df) > 0:
                technical = self.analyze_technical(symbol, df, params)
                result.technical_signal = technical.signal
                result.technical_age = technical.age
                result.price_at_signal = technical.price_at_signal
                result.patterns = technical.patterns or []
                result.rr_ratio = technical.rr_ratio
                result.technical_score = self.calculate_technical_score(technical)
            else:
                result.status = "ERROR"
                result.error_message = "No price data available"
                return result
            
            # 2. Non-Technical Analysis
            enhanced_data = get_enhanced_company_data(symbol)
            fundamentals = enhanced_data.get('fundamentals')
            profile = enhanced_data.get('profile')
            scores = enhanced_data.get('scores')
            
            if scores:
                result.fundamental_score = scores.fundamental_score
                result.sector_score = scores.sector_score  
                result.business_quality_score = scores.business_quality_score
                result.size_category = scores.size_category
                result.financial_strength = scores.financial_strength
            
            if fundamentals:
                result.pe_ratio = fundamentals.pe_ratio
                result.roe = fundamentals.roe
                result.debt_to_equity = fundamentals.debt_to_equity
            
            if profile:
                result.sector = profile.sector
                result.industry = profile.industry
                result.employee_count = profile.employees
                result.long_name = profile.long_name
                result.business_summary = profile.business_summary
            
            # 3. Composite Score Calculation
            result.composite_score = self._calculate_composite_score(result)
            
            # 4. Risk Assessment
            result.risk_level = self._assess_risk(result)
            
            # 5. Confidence and Grade
            result.confidence_level, result.grade = self._calculate_confidence_and_grade(result)
            
            # 6. Recommendation
            result.recommendation = self._generate_recommendation(result)
            
        except Exception as e:
            logger.error(f"Enhanced scan failed for {symbol}: {e}")
            result.status = "ERROR"
            result.error_message = str(e)
        
        return result

    def _calculate_composite_score(self, result: EnhancedScanResult) -> float:
        """Calculate weighted composite score"""
        try:
            composite = (
                result.technical_score * self.weights['technical'] +
                result.fundamental_score * self.weights['fundamental'] +
                result.sector_score * self.weights['sector'] +
                result.business_quality_score * self.weights['business_quality']
            )
            return round(composite, 1)
        except Exception:
            return 0.0

    def _assess_risk(self, result: EnhancedScanResult) -> str:
        """Assess overall risk level"""
        risk_factors = []
        
        # Technical risk
        if result.technical_signal == "Sell":
            risk_factors.append("technical_negative")
        if result.technical_age > 30:
            risk_factors.append("stale_signal")
        
        # Fundamental risk  
        if result.pe_ratio and result.pe_ratio > 40:
            risk_factors.append("high_valuation")
        if result.debt_to_equity and result.debt_to_equity > 80:
            risk_factors.append("high_debt")
        if result.financial_strength in ["POOR", "WEAK"]:
            risk_factors.append("weak_fundamentals")
        
        # Size risk
        if result.size_category in ["MICRO_CAP", "SMALL_CAP"]:
            risk_factors.append("small_cap")
        
        # Determine overall risk
        if len(risk_factors) >= 3:
            return "HIGH"
        elif len(risk_factors) >= 1:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_confidence_and_grade(self, result: EnhancedScanResult) -> Tuple[str, str]:
        """Calculate confidence level and assign grade"""
        score = result.composite_score
        
        # Confidence based on data availability and score
        confidence_factors = 0
        if result.technical_score > 0:
            confidence_factors += 1
        if result.fundamental_score > 0:
            confidence_factors += 1
        if result.sector_score > 0:
            confidence_factors += 1
        if result.business_quality_score > 0:
            confidence_factors += 1
        
        # Confidence level
        if confidence_factors >= 4 and score >= 70:
            confidence = "VERY_HIGH"
        elif confidence_factors >= 3 and score >= 60:
            confidence = "HIGH"  
        elif confidence_factors >= 2 and score >= 40:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        # Grade assignment
        if score >= 85:
            grade = "A+"
        elif score >= 80:
            grade = "A"
        elif score >= 75:
            grade = "A-"
        elif score >= 70:
            grade = "B+"
        elif score >= 65:
            grade = "B"
        elif score >= 60:
            grade = "B-"
        elif score >= 55:
            grade = "C+"
        elif score >= 50:
            grade = "C"
        elif score >= 45:
            grade = "C-"
        elif score >= 40:
            grade = "D+"
        elif score >= 35:
            grade = "D"
        else:
            grade = "F"
        
        return confidence, grade

    def _generate_recommendation(self, result: EnhancedScanResult) -> str:
        """Generate action recommendation"""
        score = result.composite_score
        signal = result.technical_signal
        risk = result.risk_level
        
        # Strong recommendations based on high scores
        if score >= 85 and signal == "Buy" and risk == "LOW":
            return "STRONG BUY"
        elif score >= 75 and signal == "Buy" and risk in ["LOW", "MEDIUM"]:
            return "BUY" 
        elif score >= 65 and signal in ["Buy", "Hold"]:
            return "HOLD"
        elif score >= 50 and signal != "Sell":
            return "NEUTRAL"
        
        # Negative recommendations
        elif signal == "Sell" or score < 35:
            return "AVOID"
        elif score < 50 and risk == "HIGH":
            return "AVOID"
        
        # Default based on signal when score is moderate
        elif signal == "Buy":
            return "HOLD"  # Buy signal but moderate score
        elif signal == "Sell":
            return "AVOID"
        else:
            return "NEUTRAL"

    def bulk_scan_enhanced(self, symbols: List[str], params: Dict) -> List[EnhancedScanResult]:
        """Perform enhanced scan on multiple symbols"""
        results = []
        
        logger.info(f"Starting enhanced scan for {len(symbols)} symbols...")
        
        for i, symbol in enumerate(symbols):
            try:
                result = self.scan_symbol_enhanced(symbol, params)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(symbols)} symbols...")
                    
            except Exception as e:
                logger.error(f"Failed to scan {symbol}: {e}")
                error_result = EnhancedScanResult(
                    symbol=symbol,
                    timestamp=datetime.datetime.now().isoformat(),
                    status="ERROR",
                    error_message=str(e)
                )
                results.append(error_result)
        
        logger.info(f"Enhanced scan completed. {len(results)} results generated.")
        return results

    def filter_results(self, results: List[EnhancedScanResult], 
                      filters: Dict[str, Any]) -> List[EnhancedScanResult]:
        """Filter scan results based on criteria"""
        filtered = []
        
        for result in results:
            if result.status != "SUCCESS":
                continue
                
            # Apply filters
            passed = True
            
            if 'min_composite_score' in filters:
                if result.composite_score < filters['min_composite_score']:
                    passed = False
            
            if 'technical_signals' in filters:
                if result.technical_signal not in filters['technical_signals']:
                    passed = False
            
            if 'sectors' in filters:
                if result.sector not in filters['sectors']:
                    passed = False
            
            if 'min_market_cap' in filters and result.size_category:
                size_caps = {
                    'MEGA_CAP': 200_000_000_000,
                    'LARGE_CAP': 10_000_000_000, 
                    'MID_CAP': 2_000_000_000,
                    'SMALL_CAP': 300_000_000,
                    'MICRO_CAP': 50_000_000
                }
                if size_caps.get(result.size_category, 0) < filters['min_market_cap']:
                    passed = False
            
            if 'max_risk' in filters:
                risk_levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}
                if risk_levels.get(result.risk_level, 3) > risk_levels.get(filters['max_risk'], 3):
                    passed = False
            
            if 'grades' in filters:
                if result.grade not in filters['grades']:
                    passed = False
            
            if passed:
                filtered.append(result)
        
        return filtered

    def get_top_picks(self, results: List[EnhancedScanResult], 
                     count: int = 10) -> List[EnhancedScanResult]:
        """Get top picks based on composite score"""
        # Filter successful results only
        valid_results = [r for r in results if r.status == "SUCCESS"]
        
        # Sort by composite score descending
        sorted_results = sorted(valid_results, key=lambda x: x.composite_score, reverse=True)
        
        return sorted_results[:count]

# Export functions for backward compatibility
def enhanced_scan_symbols(symbols: List[str], params: Dict, data_map: Dict[str, pd.DataFrame]) -> List[Dict]:
    """Enhanced scanning function compatible with existing UI"""
    engine = EnhancedScanEngine(data_map)
    results = engine.bulk_scan_enhanced(symbols, params)
    
    # Convert to compatible format
    compatible_results = []
    for result in results:
        compatible_result = {
            'symbol': result.symbol,
            'pass': 'PASS' if result.status == 'SUCCESS' else 'ERROR',
            'signal': result.technical_signal,
            'age': result.technical_age,
            'price': result.price_at_signal,
            'rr': result.rr_ratio if result.rr_ratio else 'N/A',
            'patterns': ','.join(result.patterns) if result.patterns else '',
            'error': result.error_message if result.status == 'ERROR' else '',
            
            # Enhanced fields
            'composite_score': result.composite_score,
            'grade': result.grade,
            'recommendation': result.recommendation,
            'sector': result.sector,
            'risk_level': result.risk_level,
            'confidence': result.confidence_level
        }
        compatible_results.append(compatible_result)
    
    return compatible_results

if __name__ == "__main__":
    # Test the enhanced scanner
    print("Testing Enhanced Scan Engine...")
    print("="*50)
    
    # Create sample data for testing
    import yfinance as yf
    
    test_symbols = ['MSFT', 'GOOGL']
    data_map = {}
    
    # Download some test data
    for symbol in test_symbols:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1y")
            if not data.empty:
                data_map[symbol] = data
        except Exception as e:
            print(f"Could not get data for {symbol}: {e}")
    
    # Test scan
    if data_map:
        engine = EnhancedScanEngine(data_map)
        
        params = {
            'scan_strategy': 'Donchian Breakout',
            'upper': 20,
            'lower': 10,
            'patterns': 'ENGULFING,DOJI',
            'lookback': 30
        }
        
        results = engine.bulk_scan_enhanced(list(data_map.keys()), params)
        
        for result in results:
            print(f"\n--- {result.symbol} ---")
            print(f"Status: {result.status}")
            if result.status == "SUCCESS":
                print(f"Technical Signal: {result.technical_signal}")
                print(f"Composite Score: {result.composite_score}")
                print(f"Grade: {result.grade}")
                print(f"Recommendation: {result.recommendation}")
                print(f"Sector: {result.sector}")
                print(f"Risk Level: {result.risk_level}")
                print(f"Financial Strength: {result.financial_strength}")
    else:
        print("No test data available")