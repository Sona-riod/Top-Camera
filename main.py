# main.py
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from kivy.app import App
from config import logger
from camera import TopCameraManager
from pallet_controller import CustomPalletController
from hmi import ProfessionalTopCameraHMI
from ws_client import CloudWebSocket  # <--- NEW IMPORT

class TopCameraApp(App):
    def build(self):
        logger.info("Initializing Top Camera Application...")
        
        # 1. Initialize Camera Hardware
        self.top_camera = TopCameraManager()
        if not self.top_camera.start():
            logger.error("Camera failed to start")
        
        # 2. Initialize Logic Controller
        self.controller = CustomPalletController()
        
        # 3. Initialize UI (HMI)
        self.hmi = ProfessionalTopCameraHMI(
            top_camera=self.top_camera,
            controller=self.controller
        )

        # 4. Initialize WebSocket (Using the logic from ForkliftFrontSystem)
        self._init_websocket()
        
        return self.hmi

    def _init_websocket(self):
        """Setup the websocket connection and callbacks"""
        
        def ws_response(data):
            """Handle messages FROM Cloud"""
            try:
                # 1. Check for location updates
                if data.get("type") == "location_update" or "location" in data:
                    new_loc = data.get("location", "Unknown")
                    logger.info(f"Cloud Popup Trigger: {new_loc}")
                    
                    # Trigger the popup on the UI thread
                    if self.hmi:
                        self.hmi.on_websocket_message(data)

            except Exception as e:
                logger.error(f"Error processing WS message: {e}")

        def ws_status_change(status):
            """Optional: Update UI with connection status"""
            logger.info(f"WS Status: {status}")

        # Start the client
        self.ws_client = CloudWebSocket(
            on_response=ws_response,
            on_connection_change=ws_status_change
        )

    def on_stop(self):
        """Cleanup on exit"""
        logger.info("Application stopping...")
        if hasattr(self, 'top_camera') and self.top_camera:
            self.top_camera.stop()
        # SocketIO client runs on a daemon thread, so it dies automatically with the app

if __name__ == '__main__':
    try:
        TopCameraApp().run()
    except Exception as e:
        logger.critical(f"Unhandled Application Error: {e}")