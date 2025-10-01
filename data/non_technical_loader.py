"""
Non-Technical Data Loader for Enhanced Scanning
==============================================
Loads and processes non-technical company information from data backup files
for integration into the scanning and ML processes.
"""

import json
import os
import pandas as pd
from typing import Dict, List, Optional, Any
import numpy as np
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CompanyFundamentals:
    """Company fundamental data structure"""
    symbol: str
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    market_cap: Optional[float] = None
    beta: Optional[float] = None
    gross_margin: Optional[float] = None
    op_margin: Optional[float] = None
    ev_ebitda: Optional[float] = None

@dataclass  
class CompanyProfile:
    """Company profile and business information"""
    symbol: str
    long_name: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    employees: Optional[int] = None
    website: str = ""
    business_summary: str = ""
    currency: str = "USD"

@dataclass
class CompanyScores:
    """Processed scores for scanning"""
    symbol: str
    fundamental_score: float = 0.0
    sector_score: float = 0.0  
    business_quality_score: float = 0.0
    size_category: str = "UNKNOWN"
    financial_strength: str = "UNKNOWN"

class NonTechnicalDataLoader:
    """Loads and processes non-technical company data"""
    
    def __init__(self, data_backup_path: str = None):
        if data_backup_path is None:
            # Default to data backup directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_backup_path = os.path.join(base_dir, "data backup")
        
        self.data_backup_path = data_backup_path
        self.fundamentals_cache: Dict[str, CompanyFundamentals] = {}
        self.profiles_cache: Dict[str, CompanyProfile] = {}
        self.scores_cache: Dict[str, CompanyScores] = {}
        
        logger.info(f"NonTechnicalDataLoader initialized with path: {data_backup_path}")

    def load_company_data(self, symbol: str) -> Optional[Dict]:
        """Load raw company data from JSON file"""
        try:
            file_path = os.path.join(self.data_backup_path, f"{symbol}.json")
            if not os.path.exists(file_path):
                logger.warning(f"No data file found for symbol: {symbol}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
                
        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
            return None

    def extract_fundamentals(self, symbol: str, raw_data: Dict) -> CompanyFundamentals:
        """Extract fundamental metrics from raw data"""
        fundamentals = CompanyFundamentals(symbol=symbol)
        
        try:
            # Try alphavantage fundamentals first
            if 'fundamentals' in raw_data and 'alphavantage' in raw_data['fundamentals']:
                av_data = raw_data['fundamentals']['alphavantage']
                fundamentals.pe_ratio = av_data.get('pe')
                fundamentals.pb_ratio = av_data.get('pb') 
                fundamentals.ps_ratio = av_data.get('ps')
                fundamentals.roe = av_data.get('roe')
                fundamentals.roa = av_data.get('roa')
                fundamentals.debt_to_equity = av_data.get('debt_to_equity')
                fundamentals.market_cap = av_data.get('market_cap')
                fundamentals.beta = av_data.get('beta')
                fundamentals.gross_margin = av_data.get('gross_margin')
                fundamentals.op_margin = av_data.get('op_margin')
                fundamentals.ev_ebitda = av_data.get('ev_ebitda')
            
            # Fallback to yahoo fundamentals
            elif 'fundamentals' in raw_data and 'yahoo' in raw_data['fundamentals']:
                yahoo_data = raw_data['fundamentals']['yahoo'].get('overview', {})
                fundamentals.market_cap = yahoo_data.get('marketCap')
                
        except Exception as e:
            logger.error(f"Error extracting fundamentals for {symbol}: {e}")
            
        return fundamentals

    def extract_profile(self, symbol: str, raw_data: Dict) -> CompanyProfile:
        """Extract company profile from raw data"""
        profile = CompanyProfile(symbol=symbol)
        
        try:
            # Try yahoo overview first
            if 'fundamentals' in raw_data and 'yahoo' in raw_data['fundamentals']:
                overview = raw_data['fundamentals']['yahoo'].get('overview', {})
                profile.long_name = overview.get('longName', '')
                profile.sector = overview.get('sector', '')
                profile.industry = overview.get('industry', '')
                profile.country = overview.get('country', '')
                profile.employees = overview.get('fullTimeEmployees')
                profile.website = overview.get('website', '')
                profile.business_summary = overview.get('longBusinessSummary', '')
                profile.currency = overview.get('currency', 'USD')
            
            # Fallback to alphavantage
            elif 'fundamentals' in raw_data and 'alphavantage' in raw_data['fundamentals']:
                av_data = raw_data['fundamentals']['alphavantage']
                profile.sector = av_data.get('sector', '')
                profile.industry = av_data.get('industry', '')
                
        except Exception as e:
            logger.error(f"Error extracting profile for {symbol}: {e}")
            
        return profile

    def calculate_scores(self, symbol: str, fundamentals: CompanyFundamentals, profile: CompanyProfile) -> CompanyScores:
        """Calculate processed scores for scanning"""
        scores = CompanyScores(symbol=symbol)
        
        try:
            # Fundamental Score (0-100)
            fund_score = 0.0
            score_components = 0
            
            # PE Ratio scoring (lower is better, but not too low)
            if fundamentals.pe_ratio is not None:
                if 10 <= fundamentals.pe_ratio <= 25:
                    fund_score += 20
                elif 5 <= fundamentals.pe_ratio <= 35:
                    fund_score += 15
                elif fundamentals.pe_ratio > 0:
                    fund_score += 5
                score_components += 1
            
            # ROE scoring (higher is better)
            if fundamentals.roe is not None:
                if fundamentals.roe >= 0.15:  # 15%+
                    fund_score += 25
                elif fundamentals.roe >= 0.10:  # 10%+
                    fund_score += 15
                elif fundamentals.roe >= 0.05:  # 5%+
                    fund_score += 10
                score_components += 1
            
            # Debt to Equity scoring (lower is better)
            if fundamentals.debt_to_equity is not None:
                if fundamentals.debt_to_equity <= 30:
                    fund_score += 20
                elif fundamentals.debt_to_equity <= 60:
                    fund_score += 15
                elif fundamentals.debt_to_equity <= 100:
                    fund_score += 10
                score_components += 1
            
            # Gross Margin scoring (higher is better)
            if fundamentals.gross_margin is not None:
                if fundamentals.gross_margin >= 0.50:  # 50%+
                    fund_score += 20
                elif fundamentals.gross_margin >= 0.30:  # 30%+
                    fund_score += 15
                elif fundamentals.gross_margin >= 0.15:  # 15%+
                    fund_score += 10
                score_components += 1
            
            # Operating Margin scoring
            if fundamentals.op_margin is not None:
                if fundamentals.op_margin >= 0.20:  # 20%+
                    fund_score += 15
                elif fundamentals.op_margin >= 0.10:  # 10%+
                    fund_score += 10
                elif fundamentals.op_margin >= 0.05:  # 5%+
                    fund_score += 5
                score_components += 1
            
            # Normalize fundamental score
            if score_components > 0:
                scores.fundamental_score = (fund_score / score_components) * (100 / 20)
            
            # Sector Score (based on popular sectors)
            sector_scores = {
                'Technology': 85,
                'Healthcare': 80, 
                'Consumer Discretionary': 75,
                'Financials': 70,
                'Communication Services': 75,
                'Industrials': 70,
                'Consumer Staples': 65,
                'Materials': 60,
                'Energy': 55,
                'Utilities': 50,
                'Real Estate': 60
            }
            scores.sector_score = sector_scores.get(profile.sector, 50)
            
            # Business Quality Score
            quality_score = 50  # Base score
            
            # Employee count factor
            if profile.employees is not None:
                if profile.employees >= 50000:
                    quality_score += 20
                elif profile.employees >= 10000:
                    quality_score += 15
                elif profile.employees >= 1000:
                    quality_score += 10
                elif profile.employees >= 100:
                    quality_score += 5
            
            # Business summary quality (length and content indicators)
            if profile.business_summary:
                summary_len = len(profile.business_summary)
                if summary_len >= 1000:
                    quality_score += 15
                elif summary_len >= 500:
                    quality_score += 10
                elif summary_len >= 200:
                    quality_score += 5
                
                # Keyword indicators for quality companies
                quality_keywords = ['leader', 'leading', 'global', 'international', 
                                  'innovative', 'technology', 'solutions', 'market']
                keyword_count = sum(1 for keyword in quality_keywords 
                                  if keyword.lower() in profile.business_summary.lower())
                quality_score += min(keyword_count * 2, 15)
            
            scores.business_quality_score = min(quality_score, 100)
            
            # Size Category
            if fundamentals.market_cap is not None:
                if fundamentals.market_cap >= 200_000_000_000:  # $200B+
                    scores.size_category = "MEGA_CAP"
                elif fundamentals.market_cap >= 10_000_000_000:  # $10B+
                    scores.size_category = "LARGE_CAP"
                elif fundamentals.market_cap >= 2_000_000_000:   # $2B+
                    scores.size_category = "MID_CAP"
                elif fundamentals.market_cap >= 300_000_000:     # $300M+
                    scores.size_category = "SMALL_CAP"
                else:
                    scores.size_category = "MICRO_CAP"
            
            # Financial Strength
            if scores.fundamental_score >= 80:
                scores.financial_strength = "EXCELLENT"
            elif scores.fundamental_score >= 60:
                scores.financial_strength = "GOOD"
            elif scores.fundamental_score >= 40:
                scores.financial_strength = "AVERAGE"
            elif scores.fundamental_score >= 20:
                scores.financial_strength = "POOR"
            else:
                scores.financial_strength = "WEAK"
                
        except Exception as e:
            logger.error(f"Error calculating scores for {symbol}: {e}")
            
        return scores

    def get_company_fundamentals(self, symbol: str, refresh: bool = False) -> Optional[CompanyFundamentals]:
        """Get company fundamentals with caching"""
        if not refresh and symbol in self.fundamentals_cache:
            return self.fundamentals_cache[symbol]
        
        raw_data = self.load_company_data(symbol)
        if not raw_data:
            return None
            
        fundamentals = self.extract_fundamentals(symbol, raw_data)
        self.fundamentals_cache[symbol] = fundamentals
        return fundamentals

    def get_company_profile(self, symbol: str, refresh: bool = False) -> Optional[CompanyProfile]:
        """Get company profile with caching"""
        if not refresh and symbol in self.profiles_cache:
            return self.profiles_cache[symbol]
        
        raw_data = self.load_company_data(symbol)
        if not raw_data:
            return None
            
        profile = self.extract_profile(symbol, raw_data)
        self.profiles_cache[symbol] = profile
        return profile

    def get_company_scores(self, symbol: str, refresh: bool = False) -> Optional[CompanyScores]:
        """Get company scores with caching"""
        if not refresh and symbol in self.scores_cache:
            return self.scores_cache[symbol]
        
        fundamentals = self.get_company_fundamentals(symbol, refresh)
        profile = self.get_company_profile(symbol, refresh)
        
        if not fundamentals or not profile:
            return None
            
        scores = self.calculate_scores(symbol, fundamentals, profile)
        self.scores_cache[symbol] = scores
        return scores

    def bulk_load_symbols(self, symbols: List[str]) -> Dict[str, CompanyScores]:
        """Bulk load multiple symbols efficiently"""
        results = {}
        
        for symbol in symbols:
            try:
                scores = self.get_company_scores(symbol)
                if scores:
                    results[symbol] = scores
                else:
                    logger.warning(f"No scores available for symbol: {symbol}")
            except Exception as e:
                logger.error(f"Error processing symbol {symbol}: {e}")
        
        logger.info(f"Loaded non-technical data for {len(results)} symbols")
        return results

    def get_sector_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """Analyze sector distribution and performance"""
        sector_data = {}
        
        for symbol in symbols:
            profile = self.get_company_profile(symbol)
            scores = self.get_company_scores(symbol)
            
            if profile and profile.sector and scores:
                if profile.sector not in sector_data:
                    sector_data[profile.sector] = {
                        'count': 0,
                        'symbols': [],
                        'avg_fundamental_score': 0,
                        'avg_business_quality': 0
                    }
                
                sector_data[profile.sector]['count'] += 1
                sector_data[profile.sector]['symbols'].append(symbol)
                sector_data[profile.sector]['avg_fundamental_score'] += scores.fundamental_score
                sector_data[profile.sector]['avg_business_quality'] += scores.business_quality_score
        
        # Calculate averages
        for sector, data in sector_data.items():
            if data['count'] > 0:
                data['avg_fundamental_score'] /= data['count']
                data['avg_business_quality'] /= data['count']
        
        return sector_data

# Global instance for easy access
non_technical_loader = NonTechnicalDataLoader()

def get_enhanced_company_data(symbol: str) -> Dict[str, Any]:
    """Convenience function to get all company data"""
    fundamentals = non_technical_loader.get_company_fundamentals(symbol)
    profile = non_technical_loader.get_company_profile(symbol)
    scores = non_technical_loader.get_company_scores(symbol)
    
    return {
        'fundamentals': fundamentals,
        'profile': profile, 
        'scores': scores
    }

if __name__ == "__main__":
    # Test the loader
    loader = NonTechnicalDataLoader()
    
    # Test with a sample symbol
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    print("Testing Non-Technical Data Loader...")
    print("="*50)
    
    for symbol in test_symbols:
        print(f"\n--- {symbol} ---")
        
        fundamentals = loader.get_company_fundamentals(symbol)
        profile = loader.get_company_profile(symbol)
        scores = loader.get_company_scores(symbol)
        
        if fundamentals:
            print(f"PE Ratio: {fundamentals.pe_ratio}")
            print(f"ROE: {fundamentals.roe}")
            print(f"Market Cap: {fundamentals.market_cap}")
        
        if profile:
            print(f"Sector: {profile.sector}")
            print(f"Industry: {profile.industry}")
            print(f"Employees: {profile.employees}")
        
        if scores:
            print(f"Fundamental Score: {scores.fundamental_score:.1f}")
            print(f"Sector Score: {scores.sector_score}")
            print(f"Business Quality: {scores.business_quality_score:.1f}")
            print(f"Size Category: {scores.size_category}")
            print(f"Financial Strength: {scores.financial_strength}")
    
    # Sector analysis
    print(f"\n--- Sector Analysis ---")
    sector_analysis = loader.get_sector_analysis(test_symbols)
    for sector, data in sector_analysis.items():
        print(f"{sector}: {data['count']} companies, avg scores: F={data['avg_fundamental_score']:.1f}, Q={data['avg_business_quality']:.1f}")