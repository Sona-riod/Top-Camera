# pallet_controller.py
import logging
from datetime import datetime
from typing import List, Dict, Any, Set
from api_sender import get_api_client
from detector import KegDetector
from database import get_database
from config import logger, QRCODE_MODEL_PATH

class CustomPalletController:
    def __init__(self):
        self.logger = logger
        self.api_client = get_api_client()
        self.db = get_database()
        
        # Initialize Detector
        self.detector = KegDetector(model_path=QRCODE_MODEL_PATH)
        
        # State variables
        # self.target_count = 0  # Removed
        self.selected_customer_id = None
        self.current_pallet_id = None
        
        # Using a set to ensure unique IDs
        self.scanned_kegs: Set[str] = set()
        self.saved_kegs: Set[str] = set() # To track what has been committed to DB
        
        # Start the first session immediately
        self.reset_session()

    def get_customers(self) -> List[Dict[str, str]]:
        return self.api_client.fetch_customers()
    
    def reset_session(self):
        """Clears current data and starts a new pallet record"""
        self.scanned_kegs.clear()
        self.saved_kegs.clear()
        
        # Generate new Pallet ID
        self.current_pallet_id = f"PAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info(f"Session Reset. New Pallet ID: {self.current_pallet_id}")

        # Create initial record in DB
        self.db.create_custom_pallet({
            "pallet_id": self.current_pallet_id,
            "status": "assembling",
            "total_kegs": 0,
            "created_at": datetime.now().isoformat()
        })

    def set_customer(self, customer_id: str):
        self.selected_customer_id = customer_id # target removal
        
        if customer_id:
            self.db.update_pallet_status(
                self.current_pallet_id, 
                status="assembling",
                customer_name=customer_id
            )

    def process_frame(self, frame):
        # If target is 0 (not set), return raw frame and 0 count.
        # This stops detection and counting when system is idle.
        # if self.target_count <= 0:
        #     return frame, 0, False

        # If target is set, proceed with detection
        annotated_frame, new_ids = self.detector.detect_and_decode(frame)
        
        for kid in new_ids:
            # Only add if not already in our session list
            if kid not in self.scanned_kegs:
                self.scanned_kegs.add(kid)
                self.logger.info(f"New Keg Detected: {kid} - Auto-saving...")
                self.save_locally()
                
        current_count = len(self.scanned_kegs)
        # is_target_reached = (current_count >= self.target_count)
            
        return annotated_frame, current_count, False

    def get_scanned_list(self) -> List[str]:
        """Returns list of IDs for the UI to display"""
        return sorted(list(self.scanned_kegs))

    def save_locally(self) -> int:
        """
        Manually triggered by the SAVE button.
        Saves pending kegs to the database.
        """
        count_saved = 0
        for kid in self.scanned_kegs:
            if kid not in self.saved_kegs:
                success = self.db.add_keg_entry(
                    pallet_id=self.current_pallet_id,
                    location="TopCamera",
                    count=1,
                    qr_codes=[kid]
                )
                if success:
                    self.saved_kegs.add(kid)
                    count_saved += 1
        
        return count_saved

    def submit_batch(self, area_name: str):
        """Finalize and send to cloud"""
        # Ensure we save locally first before sending
        self.save_locally()
        
        if not self.selected_customer_id:
            return {'success': False, 'error': "No Customer Selected"}
            
        keg_list = list(self.scanned_kegs)
        
        # Send to Cloud with Area Name
        response = self.api_client.send_keg_batch(
            keg_ids=keg_list, 
            customer_id=self.selected_customer_id,
            area_name=area_name # <--- Updated to pass area_name
        )
        
        if response.get('success'):
            self.logger.info(f"Successfully dispatched {len(keg_list)} kegs.")
            self.db.update_pallet_status(self.current_pallet_id, "dispatched")
        else:
            self.logger.error(f"API Failed: {response.get('error')}")
            self.db.update_pallet_status(self.current_pallet_id, "error_dispatch")
            
        return response