"""Centralized API integrations for the RMA-Tool.

This module provides unified API interfaces that can be used across
all modules in the application.
"""

from .billbee_api import CentralBillbeeAPI

__all__ = ["CentralBillbeeAPI"] 