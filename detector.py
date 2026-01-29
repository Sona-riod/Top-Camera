# detector.py
import cv2
import numpy as np
from ultralytics import YOLO
from pyzbar.pyzbar import decode
from config import logger, QRCODE_MODEL_PATH # Imported the specific path

class KegDetector:
    def __init__(self, model_path=None):
        self.logger = logger
        self.model = None
        
        # Use the passed path or fallback to the config path
        # str() is used because YOLO sometimes prefers string over Path objects
        self.model_path = str(model_path) if model_path else str(QRCODE_MODEL_PATH)
        
        try:
            self.model = YOLO(self.model_path)
            self.logger.info(f"YOLO model loaded successfully from: {self.model_path}")
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model from {self.model_path}: {e}")

    def detect_and_decode(self, frame):
        if self.model is None or frame is None:
            return frame, []

        detected_ids = set()
        annotated_frame = frame.copy()
        
        try:
            # Run Inference
            results = self.model(frame, verbose=False, conf=0.5)
            
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Draw Searching Box (Orange)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                    
                    # Crop logic
                    h, w, _ = frame.shape
                    pad = 10
                    crop_y1, crop_y2 = max(0, y1-pad), min(h, y2+pad)
                    crop_x1, crop_x2 = max(0, x1-pad), min(w, x2+pad)
                    crop_img = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                    
                    if crop_img.size > 0:
                        decoded_objs = decode(crop_img)
                        for obj in decoded_objs:
                            qr_data = obj.data.decode('utf-8')
                            if qr_data:
                                detected_ids.add(qr_data)
                                # Success Box (Green)
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                                cv2.putText(annotated_frame, qr_data, (x1, y1-10),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                                      
        except Exception as e:
            self.logger.error(f"Error during detection: {e}")
            
        return annotated_frame, list(detected_ids)