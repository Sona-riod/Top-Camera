# ws_client.py
import socketio
import json
import threading
import time
from typing import Callable, Optional, Dict, Any
from config import WEBSOCKET_CONFIG, SYSTEM_CONFIG, logger

class CloudWebSocket:
    def __init__(self, on_response: Callable[[Dict[str, Any]], None], on_connection_change: Optional[Callable[[str], None]] = None):
        self.config = WEBSOCKET_CONFIG
        self.mac_id = SYSTEM_CONFIG['mac_id']
        self.forklift_id = SYSTEM_CONFIG['forklift_id']
        
        # Initialize SocketIO
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.url = self.config['url']
        self.on_response = on_response
        self.on_connection_change = on_connection_change
        self.is_connected = False
        
        self._setup_callbacks()
        self._start_connection_thread()
    
    def _setup_callbacks(self):
        @self.sio.event
        def connect():
            logger.info(f"WebSocket: Connected to {self.url}")
            self.is_connected = True
            if self.on_connection_change:
                self.on_connection_change("connected")
            
            self._register()
            
        @self.sio.event
        def disconnect():
            logger.warning("WebSocket: Disconnected")
            self.is_connected = False
            if self.on_connection_change:
                self.on_connection_change("disconnected")
        
        @self.sio.event
        def connect_error(data):
            # logger.error(f"WebSocket Connection error: {data}")
            self.is_connected = False
            if self.on_connection_change:
                self.on_connection_change("disconnected")

        @self.sio.on('message')
        def on_message(data):
            logger.debug(f"WebSocket msg: {data}")
            self._process_message(data)
            
        # Listen to personal channel (MAC address) - CRITICAL FOR POPUPS
        @self.sio.on(self.mac_id)
        def on_personal_message(data):
            logger.info(f"WebSocket Personal Msg: {data}")
            self._process_message(data)

    def _process_message(self, data):
        """Normalize data and send to UI"""
        # If server sends just a string like "Storage Area", wrap it
        if isinstance(data, str):
            normalized = {
                "type": "location_update",
                "location": data
            }
            self.on_response(normalized)
        else:
            self.on_response(data)

    def _register(self):
        """Tell the server who we are so it can send us popups"""
        register_payload = {
            "type": "register",
            "forklift_id": self.forklift_id,
            "mac_id": self.mac_id,
            "device_type": "top_camera"
        }
        # Use send() for standard messages if that's what your backend expects
        self.sio.send(register_payload)
        logger.info(f"WebSocket: Registered as {self.forklift_id}")

    def _start_connection_thread(self):
        def run():
            while True:
                if not self.is_connected:
                    try:
                        if self.on_connection_change:
                            self.on_connection_change("connecting")
                        self.sio.connect(self.url, transports=['websocket'], wait_timeout=5)
                        self.sio.wait()
                    except Exception as e:
                        # logger.error(f"WS Connect Failed: {e}")
                        if self.on_connection_change:
                            self.on_connection_change("disconnected")
                        self.sio.disconnect()
                        time.sleep(5) # Reconnect delay
                else:
                    time.sleep(1)
                    
        t = threading.Thread(target=run, daemon=True)
        t.start()