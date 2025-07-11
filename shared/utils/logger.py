"""Centralized logging utilities for the RMA-Tool.

This module provides unified logging functionality that can be used across
all modules in the application.
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Global variable to track if cleanup has been performed
_cleanup_performed = False

# Import settings
try:
    from shared.config.settings import Settings
    _settings = Settings()
except ImportError:
    _settings = None


def cleanup_old_logs(log_dir: Path, max_age_days: int = 30, max_files: int = 50) -> None:
    """Clean up old log files.
    
    Args:
        log_dir: Directory containing log files
        max_age_days: Maximum age of log files in days (default: 30)
        max_files: Maximum number of log files to keep (default: 50)
    """
    # Get a logger for cleanup operations
    cleanup_logger = logging.getLogger("RMA-Tool.LogCleanup")
    
    try:
        if not log_dir.exists():
            cleanup_logger.debug("Log-Verzeichnis existiert nicht")
            return
            
        # Get all log files
        log_files = list(log_dir.glob("rma_tool_*.log"))
        if not log_files:
            cleanup_logger.debug("Keine Log-Dateien gefunden")
            return
            
        cleanup_logger.info(f"Starte Log-Bereinigung: {len(log_files)} Dateien gefunden")
        cleanup_logger.info(f"Einstellungen: max_age_days={max_age_days}, max_files={max_files}")
        
        # Sort by modification time (oldest first)
        log_files.sort(key=lambda f: f.stat().st_mtime)
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        deleted_by_age = 0
        # Remove old files based on age
        for log_file in log_files:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                try:
                    log_file.unlink()
                    cleanup_logger.info(f"Gelöscht (Alter): {log_file.name} (älter als {max_age_days} Tage)")
                    deleted_by_age += 1
                except Exception as e:
                    cleanup_logger.error(f"Fehler beim Löschen von {log_file.name}: {e}")
        
        # Remove excess files based on count (keep newest)
        remaining_files = list(log_dir.glob("rma_tool_*.log"))
        remaining_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        deleted_by_count = 0
        if len(remaining_files) > max_files:
            files_to_delete = remaining_files[max_files:]
            for log_file in files_to_delete:
                try:
                    log_file.unlink()
                    cleanup_logger.info(f"Gelöscht (Anzahl): {log_file.name} (zu viele Dateien)")
                    deleted_by_count += 1
                except Exception as e:
                    cleanup_logger.error(f"Fehler beim Löschen von {log_file.name}: {e}")
        
        # Summary
        total_deleted = deleted_by_age + deleted_by_count
        if total_deleted > 0:
            cleanup_logger.info(f"Log-Bereinigung abgeschlossen: {total_deleted} Dateien gelöscht "
                              f"({deleted_by_age} wegen Alter, {deleted_by_count} wegen Anzahl)")
        else:
            cleanup_logger.info("Log-Bereinigung abgeschlossen: Keine Dateien gelöscht")
                    
    except Exception as e:
        cleanup_logger.error(f"Fehler bei der Log-Bereinigung: {e}")


def setup_logger(name: str = "RMA-Tool") -> logging.Logger:
    """Set up a centralized logger.
    
    Args:
        name: Logger name (default: "RMA-Tool")
        
    Returns:
        Configured logger instance
    """
    global _cleanup_performed
    
    logger = logging.getLogger(name)
    
    if not logger.hasHandlers():
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Clean up old log files only once per application start
        if not _cleanup_performed:
            # Get settings from config if available
            if _settings and _settings.is_log_cleanup_enabled():
                max_age_days = _settings.get_log_cleanup_max_age_days()
                max_files = _settings.get_log_cleanup_max_files()
                cleanup_old_logs(log_dir, max_age_days, max_files)
            else:
                # Fallback to defaults
                cleanup_old_logs(log_dir)
            _cleanup_performed = True
            
            # Log the cleanup completion after logger is fully set up
            logger.info("Log-Bereinigung beim Start abgeschlossen")

        # Log filename with timestamp
        log_filename = f"rma_tool_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log"
        log_filepath = log_dir / log_filename

        # File handler
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)

        # Formatter for both handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)
        
    return logger


class LogBlock:
    """Context manager for aggregating multiple log messages in a common block.
    
    This class provides a way to group related log messages together
    and automatically add separators for better readability.
    """
    
    def __init__(self, logger: logging.Logger, level: int = logging.INFO):
        """Initialize the log block.
        
        Args:
            logger: Logger instance to use
            level: Log level for messages (default: INFO)
        """
        self.logger = logger
        self.level = level

    def __enter__(self) -> LogBlock:
        """Enter the context."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the context and add separator."""
        self.logger.log(self.level, "-" * 80)

    def __call__(self, message: str) -> None:
        """Log a message.
        
        Args:
            message: Message to log
        """
        self.logger.log(self.level, message)
    
    def section(self, title: str) -> None:
        """Log a section header.
        
        Args:
            title: Section title
        """
        self.logger.log(self.level, f"\n--- {title} ---")


def get_log_file() -> Path:
    """Get the path to the current log file.
    
    Returns:
        Path to the current log file
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Find the most recent log file
    log_files = list(log_dir.glob("rma_tool_*.log"))
    if log_files:
        return max(log_files, key=lambda f: f.stat().st_mtime)
    else:
        # Create a new log file if none exists
        log_filename = f"rma_tool_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log"
        return log_dir / log_filename


def setup_module_logger(module_name: str) -> logging.Logger:
    """Set up a logger for a specific module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        Configured logger instance for the module
    """
    return setup_logger(f"RMA-Tool.{module_name}")


def log_function_call(logger: logging.Logger, func_name: str, **kwargs) -> None:
    """Log a function call with parameters.
    
    Args:
        logger: Logger instance
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"Calling {func_name}({params})")


def log_function_result(logger: logging.Logger, func_name: str, result: any) -> None:
    """Log a function result.
    
    Args:
        logger: Logger instance
        func_name: Name of the function
        result: Function result to log
    """
    logger.debug(f"{func_name} returned: {result}")


def manual_cleanup_logs(max_age_days: int = 30, max_files: int = 50) -> None:
    """Manually clean up log files.
    
    Args:
        max_age_days: Maximum age of log files in days (default: 30)
        max_files: Maximum number of log files to keep (default: 50)
    """
    log_dir = Path("logs")
    cleanup_old_logs(log_dir, max_age_days, max_files)


def show_log_statistics() -> None:
    """Show statistics about current log files."""
    log_dir = Path("logs")
    
    if not log_dir.exists():
        print("Log-Verzeichnis existiert nicht.")
        return
        
    log_files = list(log_dir.glob("rma_tool_*.log"))
    
    if not log_files:
        print("Keine Log-Dateien gefunden.")
        return
        
    # Sort by modification time
    log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    total_size = sum(f.stat().st_size for f in log_files)
    total_size_mb = total_size / (1024 * 1024)
    
    print(f"Log-Statistiken:")
    print(f"  Anzahl Dateien: {len(log_files)}")
    print(f"  Gesamtgröße: {total_size_mb:.2f} MB")
    print(f"  Älteste Datei: {log_files[-1].name}")
    print(f"  Neueste Datei: {log_files[0].name}")
    
    if len(log_files) > 10:
        print(f"  ⚠️  Viele Log-Dateien ({len(log_files)}). Bereinigung empfohlen.")
    
    if total_size_mb > 100:
        print(f"  ⚠️  Große Log-Dateien ({total_size_mb:.2f} MB). Bereinigung empfohlen.") 