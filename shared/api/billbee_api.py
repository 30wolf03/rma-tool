"""Centralized BillBee API integration for the RMA-Tool.

This module provides a unified interface for accessing BillBee API
that can be used across all modules in the application.
"""

from __future__ import annotations

import requests
import json
import re
from typing import Optional, List, Dict, Any

from ..utils.logger import setup_logger, LogBlock


class CentralBillbeeAPI:
    """Centralized BillBee API client for all modules.
    
    This class provides a unified interface for accessing BillBee API
    that can be used across all modules in the application.
    """
    
    def __init__(self, api_key: str, api_user: str, api_password: str, parent_widget=None):
        """Initialize the BillBee API client.
        
        Args:
            api_key: BillBee API key
            api_user: BillBee API username
            api_password: BillBee API password
            parent_widget: Parent widget for dialogs (optional)
        """
        self.logger = setup_logger("RMA-Tool.BillBee")
        self.api_key = api_key
        self.api_user = api_user
        self.api_password = api_password
        self.base_url = "https://api.billbee.io/api/v1"
        self.headers = {
            "X-Billbee-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.auth = (self.api_user, self.api_password)
        self.parent_widget = parent_widget

        with LogBlock(self.logger, "BillBee API Initialization") as log:
            log("API Headers initialized")
            log("API Key loaded")
            log("Basic Auth loaded")

    def get_customer_id(self, email: str) -> Optional[str]:
        """Get customer ID based on email address.
        
        Args:
            email: Customer email address
            
        Returns:
            Customer ID if found, None otherwise
        """
        try:
            with LogBlock(self.logger, "Customer Search") as log:
                log(f"Searching customer by email: {email}")
                
                search_endpoint = f"{self.base_url}/search"
                search_payload = {
                    "type": ["customer"],
                    "term": f'email:"{email}"'
                }
                
                log.section("API Request")
                log("Sending search request:")
                log(json.dumps(search_payload, indent=2))
                
                response = requests.post(
                    search_endpoint,
                    headers=self.headers,
                    auth=self.auth,
                    json=search_payload
                )
                response.raise_for_status()
                data = response.json()
                
                log.section("API Response")
                log("Search result:")
                log(json.dumps(data, indent=2))

                customers = data.get("Customers", [])
                if len(customers) > 1:
                    self.logger.error("Multiple customers found! Please check the data.")
                    raise ValueError("Multiple customers found! Please check the data.")
                elif len(customers) == 1:
                    customer_id = customers[0]["Id"]
                    log(f"Customer ID found: {customer_id}")
                    return customer_id
                else:
                    log("No customer ID found!")
                    return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error retrieving customer ID: {str(e)}")
            return None

    def get_all_customer_addresses(self, email: str) -> Optional[List[Dict[str, Any]]]:
        """Get all customer addresses based on email address.
        
        Args:
            email: Customer email address
            
        Returns:
            List of customer addresses if found, None otherwise
        """
        with LogBlock(self.logger, "Customer Addresses") as log:
            customer_id = self.get_customer_id(email)
            if not customer_id:
                log("No addresses, no customer ID found!")
                return None

            log(f"Found customer ID: {customer_id}")
            address_endpoint = f"{self.base_url}/customers/{customer_id}/addresses"
            log(f"Retrieving addresses from: {address_endpoint}")
            
            try:
                address_response = requests.get(
                    address_endpoint,
                    headers=self.headers,
                    auth=self.auth
                )
                address_response.raise_for_status()
                address_data = address_response.json()
                
                log.section("API Response")
                log("Found address data:")
                log(json.dumps(address_data, indent=2))
                
                if address_data.get("Data") and len(address_data["Data"]) > 0:
                    addresses = sorted(address_data["Data"], key=lambda x: x["Id"], reverse=True)
                    return addresses
                log("No addresses found!")
                return None
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error retrieving customer addresses: {str(e)}")
                return None

    def get_all_customer_ids(self, email: str) -> List[str]:
        """Get all customer IDs based on email address.
        
        Args:
            email: Customer email address
            
        Returns:
            List of all found customer IDs
        """
        try:
            with LogBlock(self.logger, "Customer Search") as log:
                log(f"Searching customer by email: {email}")
                
                search_endpoint = f"{self.base_url}/search"
                search_payload = {
                    "type": ["customer"],
                    "term": f'email:"{email}"'
                }
                
                log.section("API Request")
                log("Sending search request:")
                log(json.dumps(search_payload, indent=2))
                
                response = requests.post(
                    search_endpoint,
                    headers=self.headers,
                    auth=self.auth,
                    json=search_payload
                )
                response.raise_for_status()
                data = response.json()
                
                log.section("API Response")
                log("Search result:")
                log(json.dumps(data, indent=2))

                customers = data.get("Customers", [])
                if len(customers) > 1:
                    log(f"Multiple customer accounts found ({len(customers)}). All orders will be displayed.")
                    # Show popup with notice
                    if self.parent_widget:
                        from PySide6.QtWidgets import QMessageBox
                        from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog

                        msg = QMessageBox(self.parent_widget)
                        msg.setIcon(QMessageBox.Icon.Information)
                        msg.setWindowTitle("Multiple Customer Accounts Found")
                        msg.setText(f"Found {len(customers)} customer accounts for this email address:")
                        details = "\n".join([f"- {c['Name']}: {c['Addresses']}" for c in customers])
                        msg.setInformativeText(f"All orders will be displayed.\n\nDetails:\n{details}")
                        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                        msg.exec()
                elif len(customers) == 1:
                    log(f"One customer account found: {customers[0]['Id']}")
                else:
                    log("No customer accounts found!")
                    return []

                return [customer["Id"] for customer in customers]

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error retrieving customer IDs: {str(e)}")
            return []

    def get_all_customer_orders(self, email: str) -> Optional[List[Dict[str, Any]]]:
        """Get all customer orders based on email address.
        
        Args:
            email: Customer email address
            
        Returns:
            List of all customer orders if found, None otherwise
        """
        with LogBlock(self.logger, "Customer Orders") as log:
            customer_ids = self.get_all_customer_ids(email)
            if not customer_ids:
                log("No orders, no customer accounts found!")
                return None

            all_orders = []
            for customer_id in customer_ids:
                log(f"Searching orders for customer ID: {customer_id}")
                orders_endpoint = f"{self.base_url}/customers/{customer_id}/orders"
                
                try:
                    response = requests.get(
                        orders_endpoint,
                        headers=self.headers,
                        auth=self.auth
                    )
                    response.raise_for_status()
                    orders_data = response.json()
                    
                    if orders_data.get("Data") and len(orders_data["Data"]) > 0:
                        all_orders.extend(orders_data["Data"])
                        log(f"Orders found for customer ID {customer_id}: {len(orders_data['Data'])}")
                    else:
                        log(f"No orders found for customer ID {customer_id}!")
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error retrieving orders for customer ID {customer_id}: {str(e)}")
                    continue

            if all_orders:
                log(f"Total {len(all_orders)} orders found for all customer accounts")
                return all_orders
            else:
                log("No orders found for all customer accounts!")
                return None

    def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed order information.
        
        Args:
            order_id: BillBee order ID
            
        Returns:
            Order details if found, None otherwise
        """
        try:
            with LogBlock(self.logger, "Order Details") as log:
                order_endpoint = f"{self.base_url}/orders/{order_id}"
                log(f"Retrieving order data from: {order_endpoint}")
                
                response = requests.get(
                    order_endpoint,
                    headers=self.headers,
                    auth=self.auth
                )
                response.raise_for_status()
                order_data = response.json()
                
                log.section("API Response")
                log("Complete order data:")
                log(json.dumps(order_data, indent=2))
                
                if order_data.get("Data"):
                    return order_data["Data"]
                
                log("No order data found")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error retrieving order details: {str(e)}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"API Response: {e.response.text}")
            return None

    def get_order_notes(self, order_id: str) -> Optional[str]:
        """Get order notes.
        
        Args:
            order_id: BillBee order ID
            
        Returns:
            Order notes if found, None otherwise
        """
        try:
            with LogBlock(self.logger, "Order Notes") as log:
                # Direct endpoint for the order
                order_endpoint = f"{self.base_url}/orders/{order_id}"
                log(f"Retrieving order data from: {order_endpoint}")
                
                response = requests.get(
                    order_endpoint,
                    headers=self.headers,
                    auth=self.auth
                )
                response.raise_for_status()
                order_data = response.json()
                
                log.section("API Response")
                log("Complete order data:")
                log(json.dumps(order_data, indent=2))
                
                # Extract notes from order data
                if order_data.get("Data"):
                    notes = order_data["Data"].get("SellerComment", "")
                    log(f"Found notes (SellerComment): {notes}")
                    
                    if notes:
                        log(f"Notes found: {notes}")
                        return notes
                
                log("No notes found for the order")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error retrieving order notes: {str(e)}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"API Response: {e.response.text}")
            return None

    def extract_serial_number(self, notes: str) -> Optional[str]:
        """Extract serial number from order notes.
        
        Args:
            notes: Order notes text
            
        Returns:
            Serial number if found, None otherwise
        """
        if not notes:
            return None
            
        # Common patterns for serial numbers
        patterns = [
            r'SN[:\s]*([A-Z0-9\-]+)',
            r'Serial[:\s]*([A-Z0-9\-]+)',
            r'Seriennummer[:\s]*([A-Z0-9\-]+)',
            r'([A-Z]{2,3}[0-9]{6,})',  # Generic pattern for common serial formats
        ]
        
        for pattern in patterns:
            match = re.search(pattern, notes, re.IGNORECASE)
            if match:
                serial_number = match.group(1).strip()
                self.logger.info(f"Serial number extracted: {serial_number}")
                return serial_number
        
        self.logger.info("No serial number found in notes")
        return None 