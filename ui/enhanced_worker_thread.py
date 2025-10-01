"""
Enhanced Worker Thread with integrated non-technical analysis
==========================================================
Extends the existing worker thread to support enhanced scanning capabilities
"""

from PySide6.QtCore import QThread, Signal
import json
import datetime
import os
import sys
from typing import Dict, List, Any
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from logic.enhanced_scanner import EnhancedScanEngine, enhanced_scan_symbols
    from ui.shared.logging_utils import write_log
    ENHANCED_AVAILABLE = True
except ImportError as e:
    print(f"Enhanced scanner not available: {e}")
    ENHANCED_AVAILABLE = False
    write_log = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedWorkerThread(QThread):
    """Enhanced worker thread with comprehensive scanning capabilities"""
    
    progress_updated = Signal(int)
    status_updated = Signal(str)
    results_ready = Signal(object)
    intermediate_results = Signal(object)
    full_results_ready = Signal(object)
    error_occurred = Signal(str)
    finished_work = Signal()
    enhanced_results_ready = Signal(object)  # New signal for enhanced results

    def __init__(self, operation_type, params, data_map):
        super().__init__()
        self.operation_type = operation_type
        self.params = params
        self.data_map = data_map
        self.is_cancelled = False
        self.enhanced_engine = None
        
        # Initialize enhanced engine if available
        if ENHANCED_AVAILABLE:
            try:
                self.enhanced_engine = EnhancedScanEngine(data_map)
                logger.info("Enhanced scan engine initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize enhanced engine: {e}")

    def cancel(self):
        """Cancel the running operation"""
        self.is_cancelled = True

    def run(self):
        """Main thread execution"""
        try:
            if self.operation_type == 'enhanced_scan':
                self.run_enhanced_scan()
            elif self.operation_type == 'scan':
                # Decide whether to use enhanced or legacy scan
                use_enhanced = self.params.get('use_enhanced_scan', True)
                if use_enhanced and ENHANCED_AVAILABLE and self.enhanced_engine:
                    self.run_enhanced_scan()
                else:
                    self.run_legacy_scan()
            elif self.operation_type == 'backtest':
                self.run_backtest()
            elif self.operation_type == 'optimize': 
                self.run_optimize()
            else:
                self.error_occurred.emit(f"Unknown operation type: {self.operation_type}")
                
        except Exception as e:
            try:
                self.error_occurred.emit(str(e))
                logger.error(f"Worker thread error: {e}")
            except Exception:
                pass
        finally:
            try:
                self.finished_work.emit()
            except Exception:
                pass

    def run_enhanced_scan(self):
        """Run enhanced scan with non-technical data integration"""
        if not ENHANCED_AVAILABLE or not self.enhanced_engine:
            self.error_occurred.emit("Enhanced scanning not available")
            return
            
        try:
            # Get symbols to scan
            symbols = self._get_symbols_to_scan()
            if not symbols:
                self.error_occurred.emit("No symbols to scan")
                return
                
            total_symbols = len(symbols)
            self.status_updated.emit(f"Starting enhanced scan for {total_symbols} symbols...")
            
            # Process symbols in batches for better progress reporting
            batch_size = 10
            all_results = []
            processed = 0
            
            for i in range(0, total_symbols, batch_size):
                if self.is_cancelled:
                    break
                    
                batch_symbols = symbols[i:i + batch_size]
                self.status_updated.emit(f"Processing batch {i//batch_size + 1} ({len(batch_symbols)} symbols)...")
                
                try:
                    # Run enhanced scan on batch
                    batch_results = self.enhanced_engine.bulk_scan_enhanced(batch_symbols, self.params)
                    all_results.extend(batch_results)
                    
                    # Update progress
                    processed += len(batch_symbols)
                    progress = int((processed / total_symbols) * 100)
                    self.progress_updated.emit(progress)
                    
                    # Emit intermediate results for UI updates
                    self._emit_intermediate_enhanced_results(batch_results)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                    continue
            
            if not self.is_cancelled:
                # Apply filters if specified
                filtered_results = self._apply_enhanced_filters(all_results)
                
                # Apply rigorous filtering if enabled
                if self.params.get('use_rigorous_scan', False):
                    filtered_results = self._apply_rigorous_filtering(filtered_results)
                
                # Get top picks
                top_picks = self.enhanced_engine.get_top_picks(filtered_results, 
                                                             self.params.get('max_results', 50))
                
                # Emit final results
                self.enhanced_results_ready.emit({
                    'all_results': all_results,
                    'filtered_results': filtered_results, 
                    'top_picks': top_picks,
                    'summary': self._generate_enhanced_summary(all_results)
                })
                
                # Also emit in legacy format for compatibility
                legacy_results = self._convert_to_legacy_format(top_picks)
                self.results_ready.emit(legacy_results)
                
                self.status_updated.emit(f"Enhanced scan completed. {len(top_picks)} top results found.")
            
        except Exception as e:
            logger.error(f"Enhanced scan failed: {e}")
            self.error_occurred.emit(f"Enhanced scan failed: {str(e)}")

    def run_legacy_scan(self):
        """Run legacy scan for compatibility"""
        try:
            # Import legacy scanning logic
            from ui.main_content.worker_thread import WorkerThread as LegacyWorkerThread
            
            # Create legacy worker and run
            legacy_worker = LegacyWorkerThread(self.operation_type, self.params, self.data_map)
            legacy_worker.progress_updated.connect(self.progress_updated)
            legacy_worker.status_updated.connect(self.status_updated)
            legacy_worker.results_ready.connect(self.results_ready)
            legacy_worker.error_occurred.connect(self.error_occurred)
            
            legacy_worker.run_scan()
            
        except Exception as e:
            logger.error(f"Legacy scan failed: {e}")
            self.error_occurred.emit(f"Legacy scan failed: {str(e)}")

    def _get_symbols_to_scan(self) -> List[str]:
        """Extract symbols to scan from parameters"""
        symbols = []
        
        # From symbols parameter
        if 'symbols' in self.params:
            if isinstance(self.params['symbols'], str):
                symbols.extend([s.strip().upper() for s in self.params['symbols'].split(',') if s.strip()])
            elif isinstance(self.params['symbols'], list):
                symbols.extend([s.upper() for s in self.params['symbols'] if s])
        
        # From data_map if no specific symbols
        if not symbols and self.data_map:
            symbols = list(self.data_map.keys())
        
        # Remove duplicates and filter out invalid symbols
        symbols = list(set(symbol for symbol in symbols if symbol and len(symbol) <= 10))
        
        return symbols

    def _apply_enhanced_filters(self, results):
        """Apply user-defined filters to enhanced results"""
        if not results:
            return []
            
        filters = {}
        
        # Extract filters from params
        if 'min_composite_score' in self.params:
            filters['min_composite_score'] = self.params['min_composite_score']
        
        if 'technical_signals' in self.params:
            signals = self.params['technical_signals']
            if isinstance(signals, str):
                signals = [s.strip().upper() for s in signals.split(',') if s.strip()]
            filters['technical_signals'] = signals
        
        if 'sectors' in self.params:
            sectors = self.params['sectors'] 
            if isinstance(sectors, str):
                sectors = [s.strip() for s in sectors.split(',') if s.strip()]
            filters['sectors'] = sectors
        
        if 'min_market_cap' in self.params:
            filters['min_market_cap'] = self.params['min_market_cap']
            
        if 'max_risk' in self.params:
            filters['max_risk'] = self.params['max_risk']
        
        if 'grades' in self.params:
            grades = self.params['grades']
            if isinstance(grades, str):
                grades = [s.strip().upper() for s in grades.split(',') if s.strip()]
            filters['grades'] = grades
        
        # Apply filters using engine
        if filters and self.enhanced_engine:
            return self.enhanced_engine.filter_results(results, filters)
        else:
            return [r for r in results if r.status == "SUCCESS"]

    def _emit_intermediate_enhanced_results(self, batch_results):
        """Emit intermediate results for UI updates"""
        try:
            # Convert to display format
            display_results = []
            for result in batch_results:
                display_result = {
                    'symbol': result.symbol,
                    'composite_score': result.composite_score,
                    'grade': result.grade,
                    'technical_signal': result.technical_signal,
                    'recommendation': result.recommendation,
                    'sector': result.sector,
                    'status': result.status
                }
                display_results.append(display_result)
            
            self.intermediate_results.emit(display_results)
            
        except Exception as e:
            logger.error(f"Error emitting intermediate results: {e}")

    def _generate_enhanced_summary(self, results):
        """Generate summary statistics for enhanced scan"""
        if not results:
            return {}
        
        total_scanned = len(results)
        successful = len([r for r in results if r.status == "SUCCESS"])
        
        # Signal distribution
        signals = {}
        for result in results:
            if result.status == "SUCCESS":
                signal = result.technical_signal
                signals[signal] = signals.get(signal, 0) + 1
        
        # Grade distribution  
        grades = {}
        for result in results:
            if result.status == "SUCCESS":
                grade = result.grade
                grades[grade] = grades.get(grade, 0) + 1
        
        # Sector distribution
        sectors = {}
        for result in results:
            if result.status == "SUCCESS" and result.sector:
                sector = result.sector
                sectors[sector] = sectors.get(sector, 0) + 1
        
        # Score statistics
        scores = [r.composite_score for r in results if r.status == "SUCCESS"]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Recommendations
        recommendations = {}
        for result in results:
            if result.status == "SUCCESS":
                rec = result.recommendation
                recommendations[rec] = recommendations.get(rec, 0) + 1
        
        return {
            'total_scanned': total_scanned,
            'successful': successful,
            'failed': total_scanned - successful,
            'average_score': round(avg_score, 1),
            'signal_distribution': signals,
            'grade_distribution': grades,
            'sector_distribution': sectors,
            'recommendation_distribution': recommendations,
            'top_score': max(scores) if scores else 0,
            'timestamp': datetime.datetime.now().isoformat()
        }

    def _convert_to_legacy_format(self, enhanced_results):
        """Convert enhanced results to legacy format for backward compatibility"""
        legacy_results = []
        
        for result in enhanced_results:
            if result.status != "SUCCESS":
                continue
                
            legacy_result = {
                'symbol': result.symbol,
                'pass': 'PASS',
                'signal': result.technical_signal,
                'age': result.technical_age,
                'price': result.price_at_signal,
                'rr': result.rr_ratio if result.rr_ratio else 'N/A',
                'patterns': ','.join(result.patterns) if result.patterns else '',
                'error': '',
                
                # Enhanced fields (if UI supports them)
                'composite_score': result.composite_score,
                'grade': result.grade,
                'recommendation': result.recommendation,
                'sector': result.sector,
                'risk_level': result.risk_level,
                'confidence': result.confidence_level,
                'financial_strength': result.financial_strength
            }
            legacy_results.append(legacy_result)
        
        return legacy_results

    def _apply_rigorous_filtering(self, results):
        """Apply rigorous premium filtering to results"""
        try:
            from logic.rigorous_scanner import RigorousPremiumScanner
            
            # Get profile from parameters
            profile = self.params.get('rigorous_profile', 'conservative')
            
            self.status_updated.emit(f"🎯 Applying rigorous {profile} filters...")
            logger.info(f"Applying rigorous filtering with {profile} profile")
            
            # Create rigorous scanner
            rigorous_scanner = RigorousPremiumScanner(self.data_map)
            
            # Apply rigorous filters
            rigorous_results = rigorous_scanner.apply_rigorous_filters(results, profile)
            
            logger.info(f"Rigorous filtering: {len(results)} → {len(rigorous_results)} results")
            self.status_updated.emit(f"🏆 {len(rigorous_results)} premium stocks passed rigorous {profile} filtering")
            
            return rigorous_results
            
        except ImportError as e:
            logger.error(f"Rigorous scanner not available: {e}")
            self.status_updated.emit("⚠️ Rigorous filtering not available - using standard enhanced results")
            return results
        except Exception as e:
            logger.error(f"Error in rigorous filtering: {e}")
            self.status_updated.emit(f"⚠️ Rigorous filtering failed: {e}")
            return results

    def run_backtest(self):
        """Run backtest - placeholder for future implementation"""
        self.status_updated.emit("Backtesting not yet implemented in enhanced worker")
        self.error_occurred.emit("Backtesting not yet implemented")

    def run_optimize(self):
        """Run optimization - placeholder for future implementation"""  
        self.status_updated.emit("Optimization not yet implemented in enhanced worker")
        self.error_occurred.emit("Optimization not yet implemented")

# Convenience function to create appropriate worker thread
def create_worker_thread(operation_type, params, data_map, use_enhanced=True):
    """Factory function to create appropriate worker thread"""
    if use_enhanced and ENHANCED_AVAILABLE and operation_type in ['scan', 'enhanced_scan']:
        return EnhancedWorkerThread(operation_type, params, data_map)
    else:
        # Fall back to legacy worker thread
        try:
            from ui.main_content.worker_thread import WorkerThread as LegacyWorkerThread
            return LegacyWorkerThread(operation_type, params, data_map)
        except ImportError:
            # If legacy not available, use enhanced anyway
            return EnhancedWorkerThread(operation_type, params, data_map)