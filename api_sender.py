# api_sender.py - REST API Client
import requests
import json
from typing import List, Dict, Any, Optional
from config import API_CONFIG, SYSTEM_CONFIG, logger

class APIClient:
    def __init__(self):
        self.logger = logger
        # Get MAC ID from config
        self.mac_id = SYSTEM_CONFIG['mac_id'] 
        self.timeout = API_CONFIG['api_timeout']
        
        # API endpoints
        self.customer_api_url = API_CONFIG['customer_api_url']
        self.pallet_create_url = API_CONFIG['pallet_create_url']
        
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def fetch_customers(self) -> List[Dict[str, str]]:
        """Fetch customer list from cloud API."""
        self.logger.info(f"Fetching customers from: {self.customer_api_url}")
        
        payload = {"macId": self.mac_id}
        
        try:
            response = requests.post(
                self.customer_api_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return self._parse_customers(data)
                except json.JSONDecodeError:
                    self.logger.error("Invalid JSON response from customer API")
                    return []
            else:
                self.logger.warning(f"Customer API status {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching customers: {e}")
            return []

    def _parse_customers(self, data) -> List[Dict[str, str]]:
        """Parse raw API response into standardized list"""
        customers = []
        items = data
        if isinstance(data, dict):
            items = data.get('data', []) or data.get('customers', [])
            
        if not isinstance(items, list):
            return []
            
        for item in items:
            c_name = item.get('customerName') or item.get('name')
            c_id = item.get('_id') or item.get('id')
            if c_name and c_id:
                customers.append({'name': str(c_name), 'id': str(c_id)})
        return customers

    def send_keg_batch(self, keg_ids: List[str], customer_id: str, area_name: str) -> Dict[str, Any]:
        """
        Send the accumulated batch of kegs to the cloud.
        Updated Format: 
        {
            "kegIds": [...], 
            "macId": "...", 
            "customerId": "...", 
            "areaName": "..."
        }
        """
        payload = {
            "kegIds": keg_ids,
            "macId": self.mac_id,
            "customerId": customer_id,
            "areaName": area_name  # <--- Added Field
        }
        
        self.logger.info(f"Sending Batch Payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(
                self.pallet_create_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                self.logger.info("Batch sent successfully")
                return {'success': True, 'data': response.text}
            else:
                self.logger.error(f"Batch API Error {response.status_code}: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            self.logger.error(f"Network Exception during batch send: {e}")
            return {'success': False, 'error': str(e)}

# Singleton instance
_api_client_instance = None
def get_api_client():
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = APIClient()
    return _api_client_instance