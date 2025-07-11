"""Enhanced logging system for RMA-Tool.

This module provides enhanced logging functionality that automatically logs
all QMessageBox calls and provides consistent error handling across the application.
"""

from __future__ import annotations

import sys
import logging
import traceback
import inspect
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, Union
from functools import wraps

from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QObject, Signal

from .logger import setup_logger, LogBlock


def get_current_module_name() -> str:
    """Get the current module name from the call stack.
    
    Returns:
        Current module name (e.g., 'DHL-Label-Tool', 'RMA-Database-GUI')
    """
    try:
        # Get the current frame
        frame = inspect.currentframe()
        
        # Walk up the call stack to find the module
        while frame:
            module_name = frame.f_globals.get('__name__', '')
            file_path = frame.f_code.co_filename
            
            # Check if we're in a specific module
            if 'dhl_label_tool' in file_path or 'dhl_label_tool' in module_name:
                return 'DHL-Label-Tool'
            elif 'rma_db_gui' in file_path or 'rma_db_gui' in module_name:
                return 'RMA-Database-GUI'
            elif 'shared' in file_path or 'shared' in module_name:
                return 'Shared-Infrastructure'
            elif 'main' in file_path and 'main.py' in file_path:
                return 'RMA-Tool-Main'
            
            frame = frame.f_back
            
        return 'Unknown-Module'
    except Exception:
        return 'Unknown-Module'


def get_module_logger(name: str = "") -> logging.Logger:
    """Get a logger with the current module name.
    
    Args:
        name: Additional logger name
        
    Returns:
        Logger with module-specific name
    """
    module_name = get_current_module_name()
    if name:
        logger_name = f"RMA-Tool.{module_name}.{name}"
    else:
        logger_name = f"RMA-Tool.{module_name}"
    
    return setup_logger(logger_name)


class EnhancedMessageBox(QMessageBox):
    """Enhanced QMessageBox that automatically logs all messages."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the enhanced message box."""
        super().__init__(*args, **kwargs)
        self.logger = get_module_logger("EnhancedMessageBox")
        
    def log_message(self, level: str, title: str, message: str) -> None:
        """Log a message with the specified level.
        
        Args:
            level: Log level (error, warning, info, critical)
            title: Message box title
            message: Message content
        """
        log_message = f"QMessageBox.{level.upper()}: {title} - {message}"
        
        if level.lower() == "error":
            self.logger.error(log_message)
        elif level.lower() == "warning":
            self.logger.warning(log_message)
        elif level.lower() == "critical":
            self.logger.critical(log_message)
        else:
            self.logger.info(log_message)


class LoggingMessageBox:
    """Static class for logging message box calls."""
    
    @classmethod
    def _get_logger(cls) -> logging.Logger:
        """Get a logger for the current module."""
        return get_module_logger("MessageBox")
    
    @classmethod
    def critical(cls, parent: Optional[QObject], title: str, message: str) -> int:
        """Show critical message box and log it.
        
        Args:
            parent: Parent widget
            title: Message box title
            message: Message content
            
        Returns:
            Standard button result
        """
        logger = cls._get_logger()
        logger.critical(f"QMessageBox.CRITICAL: {title} - {message}")
        return QMessageBox.critical(parent, title, message)
    
    @classmethod
    def warning(cls, parent: Optional[QObject], title: str, message: str) -> int:
        """Show warning message box and log it.
        
        Args:
            parent: Parent widget
            title: Message box title
            message: Message content
            
        Returns:
            Standard button result
        """
        logger = cls._get_logger()
        logger.warning(f"QMessageBox.WARNING: {title} - {message}")
        return QMessageBox.warning(parent, title, message)
    
    @classmethod
    def information(cls, parent: Optional[QObject], title: str, message: str) -> int:
        """Show information message box and log it.
        
        Args:
            parent: Parent widget
            title: Message box title
            message: Message content
            
        Returns:
            Standard button result
        """
        logger = cls._get_logger()
        logger.info(f"QMessageBox.INFORMATION: {title} - {message}")
        return QMessageBox.information(parent, title, message)
    
    @classmethod
    def question(cls, parent: Optional[QObject], title: str, message: str) -> int:
        """Show question message box and log it.
        
        Args:
            parent: Parent widget
            title: Message box title
            message: Message content
            
        Returns:
            Standard button result
        """
        logger = cls._get_logger()
        logger.info(f"QMessageBox.QUESTION: {title} - {message}")
        return QMessageBox.question(parent, title, message)


class ErrorLogger:
    """Centralized error logging with context information."""
    
    def __init__(self, module_name: str = ""):
        """Initialize the error logger.
        
        Args:
            module_name: Name of the module using this logger
        """
        if module_name:
            self.logger = get_module_logger(module_name)
        else:
            self.logger = get_module_logger("ErrorLogger")
        
    def log_exception(
        self, 
        exception: Exception, 
        context: str = "", 
        additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an exception with context information.
        
        Args:
            exception: The exception that occurred
            context: Additional context about where the error occurred
            additional_info: Additional information to log
        """
        error_msg = f"Exception: {type(exception).__name__}: {str(exception)}"
        
        if context:
            error_msg += f" | Context: {context}"
            
        if additional_info:
            error_msg += f" | Additional Info: {additional_info}"
            
        self.logger.error(error_msg)
        self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
        
    def log_error_with_message_box(
        self,
        exception: Exception,
        title: str,
        message: str,
        context: str = "",
        show_dialog: bool = True
    ) -> None:
        """Log an error and optionally show a message box.
        
        Args:
            exception: The exception that occurred
            title: Message box title
            message: Message box content
            context: Additional context
            show_dialog: Whether to show the message box
        """
        # Log the error
        self.log_exception(exception, context)
        
        # Show message box if requested
        if show_dialog:
            LoggingMessageBox.critical(None, title, message)


class LoggingDecorator:
    """Decorator for automatic function call logging."""
    
    def __init__(self, logger_name: str = "FunctionLogger"):
        """Initialize the logging decorator.
        
        Args:
            logger_name: Name for the logger
        """
        self.logger = get_module_logger(logger_name)
        
    def __call__(self, func):
        """Decorate a function with logging.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                self.logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
                result = func(*args, **kwargs)
                self.logger.debug(f"{func.__name__} returned: {result}")
                return result
            except Exception as e:
                self.logger.error(f"Exception in {func.__name__}: {str(e)}")
                raise
        return wrapper


class UnhandledExceptionHandler:
    """Handler for unhandled exceptions."""
    
    def __init__(self):
        """Initialize the unhandled exception handler."""
        self.logger = get_module_logger("UnhandledExceptionHandler")
        
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle unhandled exceptions.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        # Log the exception
        self.logger.critical("Unhandled exception occurred:")
        self.logger.critical(f"Type: {exc_type.__name__}")
        self.logger.critical(f"Value: {exc_value}")
        self.logger.critical(f"Traceback:\n{''.join(traceback.format_tb(exc_traceback))}")
        
        # Show error dialog
        try:
            app = QApplication.instance()
            if app:
                error_msg = f"Ein unerwarteter Fehler ist aufgetreten:\n\n{exc_type.__name__}: {exc_value}"
                LoggingMessageBox.critical(None, "Kritischer Fehler", error_msg)
        except Exception as dialog_error:
            self.logger.error(f"Failed to show error dialog: {dialog_error}")
            
        # Call the original exception handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


def setup_enhanced_logging() -> None:
    """Set up enhanced logging for the entire application.
    
    This function should be called at application startup to enable
    automatic logging of all QMessageBox calls and unhandled exceptions.
    """
    # Set up unhandled exception handler
    exception_handler = UnhandledExceptionHandler()
    sys.excepthook = exception_handler.handle_exception
    
    # Log application startup
    logger = get_module_logger("Application")
    logger.info("Enhanced logging system initialized")


def log_function_call(func):
    """Decorator to log function calls automatically.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    logger = get_module_logger("FunctionLogger")
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.debug(f"Calling {func.__name__}")
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {str(e)}")
            raise
    return wrapper


# Convenience functions for common logging patterns
def log_error_and_show_dialog(
    exception: Exception,
    title: str,
    message: str,
    logger_name: str = "ErrorLogger"
) -> None:
    """Log an error and show a dialog.
    
    Args:
        exception: The exception that occurred
        title: Dialog title
        message: Dialog message
        logger_name: Name for the logger
    """
    error_logger = ErrorLogger(logger_name)
    error_logger.log_error_with_message_box(exception, title, message)


def log_warning_and_show_dialog(
    message: str,
    title: str = "Warnung",
    logger_name: str = "WarningLogger"
) -> None:
    """Log a warning and show a dialog.
    
    Args:
        message: Warning message
        title: Dialog title
        logger_name: Name for the logger
    """
    logger = get_module_logger(logger_name)
    logger.warning(f"Warning: {message}")
    LoggingMessageBox.warning(None, title, message)


def log_info_and_show_dialog(
    message: str,
    title: str = "Information",
    logger_name: str = "InfoLogger"
) -> None:
    """Log an info message and show a dialog.
    
    Args:
        message: Info message
        title: Dialog title
        logger_name: Name for the logger
    """
    logger = get_module_logger(logger_name)
    logger.info(f"Info: {message}")
    LoggingMessageBox.information(None, title, message) 