# camera.py - Top Camera Management
import cv2
import numpy as np
import time
import os
from config import TOP_CAMERA_CONFIG, logger

class TopCameraManager:
    """Manages the ICAM-540 top-mounted camera"""
    
    def __init__(self):
        self.config = TOP_CAMERA_CONFIG
        self.logger = logger
        self.cap = None
        self.is_active = False
        self.frame_count = 0
        
        # Initialize based on updated config
        self._initialize_camera()
    
    def _list_available_devices(self):
        """Helper to scan devices if connection fails (like in your test script)"""
        self.logger.info("Scanning for available video devices...")
        available = []
        for i in range(20):  # Check video0 to video19
            if os.path.exists(f"/dev/video{i}"):
                available.append(i)
        self.logger.info(f"Available video devices: {available}")
        return available

    def _initialize_camera(self):
        """Initialize the top camera with ICAM-540 specific settings"""
        try:
            device = self.config.get('device', 10)
            width = self.config.get('width', 1920)
            height = self.config.get('height', 1080)
            fps = self.config.get('fps', 30)
            
            self.logger.info(f"Initializing ICAM-540 at /dev/video{device}: {width}x{height} @ {fps}fps")
            
            # --- CRITICAL UPDATE: Force V4L2 backend for industrial cameras ---
            self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
            
            if not self.cap.isOpened():
                self.logger.error(f"Failed to open camera at device {device}")
                # List available devices to help debug
                available_devs = self._list_available_devices()
                self.logger.warning(f"Did you mean one of these? {available_devs}")
                
                self._create_dummy_cap()
                return
            
            # Apply ICAM-540 Settings
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, fps)
            
            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps:.1f}fps")
            self.is_active = True
            
        except Exception as e:
            self.logger.error(f"Top camera initialization error: {e}")
            self._create_dummy_cap()
    
    def _create_dummy_cap(self):
        """Create dummy camera for fallback"""
        self.logger.warning("Using DUMMY camera mode.")
        class DummyCap:
            def __init__(self, manager):
                self.manager = manager
                self.frame_count = 0
            
            def read(self):
                self.frame_count += 1
                # Create black frame matching configured resolution
                h = self.manager.config.get('height', 1080)
                w = self.manager.config.get('width', 1920)
                frame = np.zeros((h, w, 3), dtype=np.uint8)
                
                # Add error text
                cv2.putText(frame, "CAMERA CONNECT FAIL", (100, 300),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
                cv2.putText(frame, "Check /dev/video10", (100, 450),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                return True, frame
            
            def isOpened(self): return True
            def release(self): pass
            def set(self, prop, val): pass
            def get(self, prop): return 0
        
        self.cap = DummyCap(self)
        self.is_active = False
    
    def start(self):
        """Start camera capture"""
        if self.cap is None:
            self._initialize_camera()
        return self.is_active
    
    def get_overhead_view(self):
        """Get overhead view frame from top camera"""
        if self.cap is None:
            self._initialize_camera()
        
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.logger.warning("Failed to read frame from top camera")
                return False, None
            
            self.frame_count += 1
            return True, frame
            
        except Exception as e:
            self.logger.error(f"Error reading from top camera: {e}")
            return False, None
    
    def stop(self):
        """Stop camera capture"""
        if self.cap and hasattr(self.cap, 'release'):
            self.cap.release()
        self.cap = None
        self.is_active = False
        self.logger.info("Top camera stopped")