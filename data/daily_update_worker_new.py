from PySide6.QtCore import QObject, Signal
import datetime
from typing import Optional
import pandas as pd
import os


class DailyUpdateWorkerNew(QObject):
    """New worker QObject to run comprehensive daily updates using the separated data structure.

    Signals:
        progress(int): emits percent complete (0-100)
        status(str): emits human-readable status updates
        ticker_done(str, bool, object): ticker, success flag, optional meta/error
        finished(dict): final summary dict
        error(str): fatal error message
    """
    progress = Signal(int)
    status = Signal(str)
    ticker_done = Signal(str, bool, object)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the new daily update worker."""
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        """Execute the comprehensive daily update process."""
        try:
            # Local imports to avoid heavy startup when module imported
            from data.daily_update_new import plan_daily_update_new, execute_daily_update_plan
            from data.data_paths import get_data_paths
        except Exception as e:
            self.error.emit(f"Import error in worker: {e}")
            return

        try:
            # Get data paths for new structure
            paths = get_data_paths()
            
            # Create update plan using new system
            self.status.emit("Creating comprehensive update plan...")
            plan_dict = plan_daily_update_new(
                raw_dir=paths['raw'], 
                processed_dir=paths['processed']
            )
            
            # Show plan summary
            summary = plan_dict["summary"]
            self.status.emit(
                f"Plan ready: {summary['total_tickers']} tickers, "
                f"{summary['needs_update']} need updates, "
                f"{summary['new_tickers']} new, "
                f"{summary['total_days_to_fetch']} total days to fetch"
            )
            
            if summary['total_tickers'] == 0:
                self.finished.emit({"success": True, "message": "No tickers to update"})
                return
            
            # Execute the plan with callbacks
            def progress_callback(progress):
                if not self._is_cancelled:
                    self.progress.emit(progress)
            
            def status_callback(status):
                if not self._is_cancelled:
                    self.status.emit(status)
            
            # Check for cancellation before starting – emit finished so UI resets
            if self._is_cancelled:
                self.status.emit("Cancelled by user (pre-start)")
                self.finished.emit({
                    "success": False,
                    "cancelled": True,
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "skipped": 0,
                    "message": "Cancelled before execution began"
                })
                return
            
            # Execute the comprehensive data fetching
            self.status.emit("Starting comprehensive data fetching...")
            
            def cancel_callback():
                return self._is_cancelled
            
            results = execute_daily_update_plan(
                plan_dict, 
                progress_callback=progress_callback,
                status_callback=status_callback,
                cancel_callback=cancel_callback
            )
            
            # Process raw data to parquet automatically
            if results['successful'] and not self._is_cancelled:
                self.status.emit("Processing raw data to structured format...")
                try:
                    from data.processing_pipeline import process_raw_to_parquet
                    
                    def processing_progress_callback(p):
                        if not self._is_cancelled:
                            self.progress.emit(int(80 + (p * 0.15)))  # Use 80-95% for processing
                    
                    processing_results = process_raw_to_parquet(
                        paths['raw'],
                        paths['processed'],
                        tickers=results['successful'],
                        progress_callback=processing_progress_callback
                    )
                    
                    self.status.emit(f"Processing complete: {processing_results['summary']['processed']} files processed")
                    
                    # Add processing results to final results
                    results['processing'] = processing_results['summary']
                    
                    # Auto-verify processed data for ML/Backtest/Optimize/Scanner compatibility
                    if not self._is_cancelled and processing_results['summary']['processed'] > 0:
                        self.status.emit("Verifying data compatibility with ML/Backtest modules...")
                        try:
                            from data.enhanced_verification import verify_processed_data_structure
                            
                            verification_results = verify_processed_data_structure(paths['processed'])
                            
                            # Update progress to 95-99% for verification
                            self.progress.emit(97)
                            
                            summary = verification_results['summary']
                            compatibility = verification_results['data_compatibility']
                            
                            # Report verification results
                            verified_count = summary.get('verified_tickers', 0)
                            total_count = summary.get('total_tickers', 0)
                            
                            if verified_count == total_count and total_count > 0:
                                self.status.emit(f"✅ Data verification passed: {verified_count}/{total_count} tickers compatible with all modules")
                            else:
                                failed = summary.get('failed_tickers', 0)
                                warnings = summary.get('warning_tickers', 0)
                                if failed > 0:
                                    self.status.emit(f"⚠️ Data verification: {verified_count} OK, {failed} failed, {warnings} warnings")
                                else:
                                    self.status.emit(f"✅ Data verification: {verified_count}/{total_count} verified, {warnings} minor warnings")
                            
                            results['verification'] = verification_results['summary']
                            
                        except Exception as e:
                            self.status.emit(f"Warning: Data verification failed: {str(e)}")
                            results['verification'] = {"error": str(e)}
                    
                except Exception as e:
                    self.status.emit(f"Warning: Processing failed: {str(e)}")
                    results['processing'] = {"error": str(e)}
            
            # Check for cancellation after execution
            if self._is_cancelled:
                # Emit a partial summary so the UI can re-enable controls
                self.status.emit("Cancelled by user")
                try:
                    final_result = {
                        "success": False,
                        "cancelled": True,
                        "total": results.get('total_tickers', 0),
                        "successful": len(results.get('successful', [])),
                        "failed": len(results.get('failed', [])),
                        "skipped": len(results.get('skipped', [])),
                        "message": "Cancelled after partial execution"
                    }
                except Exception:
                    final_result = {"success": False, "cancelled": True, "message": "Cancelled"}
                self.finished.emit(final_result)
                return
            
            # Emit individual ticker results
            for detail in results["details"]:
                ticker = detail["ticker"]
                success = detail["status"] in ["success", "skipped"]
                
                # Add more detailed information for UI
                meta_info = {
                    "status": detail["status"],
                    "message": self._format_ticker_message(detail)
                }
                
                if "error" in detail:
                    meta_info["error"] = detail["error"]
                if "days_fetched" in detail:
                    meta_info["days_fetched"] = detail["days_fetched"]
                if "raw_path" in detail:
                    meta_info["raw_path"] = detail["raw_path"]
                
                self.ticker_done.emit(ticker, success, meta_info)
            
            # Final summary message
            success_msg = f"Completed: {len(results['successful'])}/{results['total_tickers']} successful"
            if results['failed']:
                success_msg += f", {len(results['failed'])} failed"
            if results['skipped']:
                success_msg += f", {len(results['skipped'])} skipped"
            
            self.status.emit(success_msg)
            
            # Emit final results
            final_result = {
                "success": True,
                "cancelled": False,
                "total": results['total_tickers'],
                "successful": len(results['successful']),
                "failed": len(results['failed']),
                "skipped": len(results['skipped']),
                "success_rate": results['success_rate'],
                "started_at": results.get("started_at"),
                "completed_at": results.get("completed_at"),
                "summary": summary
            }
            self.finished.emit(final_result)

        except Exception as e:
            error_msg = f"Daily update failed: {str(e)}"
            self.error.emit(error_msg)

    def _format_ticker_message(self, detail: dict) -> str:
        """Format a user-friendly message for ticker completion."""
        status = detail["status"]
        ticker = detail["ticker"]
        
        if status == "success":
            days = detail.get("days_fetched", 0)
            return f"Fetched comprehensive data for {days} days"
        elif status == "skipped":
            reason = detail.get("reason", "unknown")
            return f"Skipped - {reason}"
        elif status == "failed":
            error = detail.get("error", "unknown error")
            return f"Failed - {error}"
        else:
            return f"Status: {status}"