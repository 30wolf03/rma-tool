"""Centralized logging utilities for the RMA-Tool.

This module provides unified logging functionality that can be used across
all modules in the application.
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(name: str = "RMA-Tool") -> logging.Logger:
    """Set up a centralized logger.
    
    Args:
        name: Logger name (default: "RMA-Tool")
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.hasHandlers():
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

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