"""Shared utilities for the RMA-Tool.

This module provides common utility functions that can be used across
all modules in the application.
"""

from .logger import setup_logger, LogBlock

__all__ = ["setup_logger", "LogBlock"] 