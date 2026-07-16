import os
import cv2
import numpy as np

class LogoDetector:
    def __init__(self, template_path, template_threshold=0.80, yolo_threshold=0.35, yolo_model_path=None, logger=None):
        self.template_path = template_path
        self.template_threshold = template_threshold
        self.yolo_threshold = yolo_threshold
        self.yolo_model_path = yolo_model_path
        self.logger = logger
        
        # Load YOLO if configured and file exists
        self.yolo_model = None
        if self.yolo_model_path and os.path.exists(self.yolo_model_path):
            try:
                from ultralytics import YOLO
                self.yolo_model = YOLO(self.yolo_model_path)
                if self.logger:
                    self.logger.info(f"Loaded YOLOv8 model for logo detection: {self.yolo_model_path}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to load YOLO model: {e}. Falling back to template matching.")

    def preprocess_image(self, img):
        """Preprocesses image to enhance contrast (helpful for low light/dark mode)."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply histogram equalization to improve contrast
        equalized = cv2.equalizeHist(gray)
        return equalized

    def detect(self, screen_path):
        """
        Detects if the logo is present on the screen.
        Returns: (is_detected, bounding_box, confidence)
        bounding_box: (x, y, w, h)
        """
        if not os.path.exists(screen_path):
            if self.logger:
                self.logger.error(f"Screen path does not exist for logo detection: {screen_path}")
            return False, None, 0.0

        # Try YOLO model first
        if self.yolo_model:
            try:
                results = self.yolo_model(screen_path, verbose=False)
                for r in results:
                    boxes = r.boxes
                    if len(boxes) > 0 and self.logger:
                        self.logger.debug(f"YOLO logo raw detections: {[{r.names[int(b.cls[0])]: float(b.conf[0])} for b in boxes]}")
                    for box in boxes:
                        cls_idx = int(box.cls[0])
                        class_name = r.names[cls_idx]
                        conf = float(box.conf[0])
                        if class_name.lower() == "logo" and conf >= self.yolo_threshold:
                            xyxy = box.xyxy[0].tolist()
                            x, y, x2, y2 = map(int, xyxy)
                            w, h = x2 - x, y2 - y
                            if self.logger:
                                self.logger.info(f"Logo detected via CNN/YOLO with confidence {conf:.2f}")
                            return True, (x, y, w, h), conf
            except Exception as e:
                if self.logger:
                    self.logger.error(f"YOLO inference error: {e}. Falling back.")

        # Fallback to OpenCV template matching
        if not os.path.exists(self.template_path):
            if self.logger:
                self.logger.error(f"Logo template image not found at: {self.template_path}")
            return False, None, 0.0

        try:
            screen_img = cv2.imread(screen_path)
            template_img = cv2.imread(self.template_path)
            
            if screen_img is None or template_img is None:
                if self.logger:
                    self.logger.error("Failed to read screen or template image via OpenCV.")
                return False, None, 0.0

            # Convert to gray
            screen_gray = self.preprocess_image(screen_img)
            template_gray = self.preprocess_image(template_img)

            # Perform template matching
            res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            h, w = template_gray.shape[:2]
            top_left = max_loc
            
            if max_val >= self.template_threshold:
                if self.logger:
                    self.logger.info(f"Logo detected via template matching at {top_left} with confidence {max_val:.2f}")
                return True, (top_left[0], top_left[1], w, h), max_val
            else:
                if self.logger:
                    self.logger.debug(f"Logo not found. Best match confidence: {max_val:.2f} at {top_left}")
                return False, None, max_val

        except Exception as e:
            if self.logger:
                self.logger.error(f"Logo detection template matching exception: {e}")
            return False, None, 0.0
