import os
import json
import cv2
import numpy as np
import importlib

class ButtonDetector:
    def __init__(self, templates_dict, template_threshold=0.80, yolo_threshold=0.35, ocr_threshold=0.80, yolo_model_path=None, mock_mode=True, mock_metadata_path=None, logger=None):
        self.templates_dict = templates_dict  # e.g. {"OK": "images/ok_button.png", "YES": "images/yes_button.png"}
        self.template_threshold = template_threshold
        self.yolo_threshold = yolo_threshold
        self.ocr_threshold = ocr_threshold
        self.yolo_model_path = yolo_model_path
        self.mock_mode = mock_mode
        self.mock_metadata_path = mock_metadata_path
        self.logger = logger
        
        # Load YOLO if configured and exists
        self.yolo_model = None
        if self.yolo_model_path and os.path.exists(self.yolo_model_path):
            try:
                from ultralytics import YOLO
                self.yolo_model = YOLO(self.yolo_model_path)
                if self.logger:
                    self.logger.info(f"Loaded YOLOv8 model for button detection: {self.yolo_model_path}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to load YOLO model: {e}. Falling back.")

        # Try to initialize EasyOCR or Tesseract
        self.ocr_engine = None
        self.easyocr_reader = None
        
        # In mock mode, we bypass physical OCR setup.
        if not self.mock_mode:
            try:
                easyocr = importlib.import_module("easyocr")
                self.easyocr_reader = easyocr.Reader(['en'])
                self.ocr_engine = "easyocr"
                if self.logger:
                    self.logger.info("Initialized EasyOCR successfully.")
            except ImportError:
                try:
                    importlib.import_module("pytesseract")
                    self.ocr_engine = "pytesseract"
                    if self.logger:
                        self.logger.info("Initialized PyTesseract fallback successfully.")
                except ImportError:
                    if self.logger:
                        self.logger.warning("No physical OCR library found (easyocr/pytesseract). Template matching will be the main physical fallback.")

    @staticmethod
    def matches_target(target, label):
        if not target or not label:
            return False

        target_norm = str(target).strip().lower()
        label_norm = str(label).strip().lower()

        if not target_norm or not label_norm:
            return False

        if target_norm in label_norm or label_norm in target_norm:
            return True

        alias_map = {
            "ok": ("ok", "button_ok", "accept"),
            "yes": ("yes", "button_yes", "continue"),
            "accept": ("accept", "ok", "button_ok"),
            "continue": ("continue", "yes", "button_yes"),
        }
        known_aliases = alias_map.get(target_norm, ())
        return label_norm in known_aliases

    def detect_via_yolo(self, screen_path, targets):
        if not self.yolo_model:
            return None
        try:
            results = self.yolo_model(screen_path, verbose=False)
            for r in results:
                boxes = r.boxes
                if len(boxes) > 0 and self.logger:
                    self.logger.debug(f"YOLO button raw detections: {[{r.names[int(b.cls[0])]: float(b.conf[0])} for b in boxes]}")
                for box in boxes:
                    cls_idx = int(box.cls[0])
                    class_name = r.names[cls_idx]
                    conf = float(box.conf[0])
                    # Check if class matches any of our targets
                    # YOLO classes are 'logo' (0), 'button_ok' (1), 'button_yes' (2)
                    # We map class_name like 'button_ok' -> matches 'ok' in targets
                    matched = False
                    matched_target = None
                    for target in targets:
                        if self.matches_target(target, class_name):
                            matched = True
                            matched_target = target
                            break
                    
                    if matched and conf >= self.yolo_threshold:
                        xyxy = box.xyxy[0].tolist()
                        x, y, x2, y2 = map(int, xyxy)
                        w, h = x2 - x, y2 - y
                        center_x = x + w // 2
                        center_y = y + h // 2
                        if self.logger:
                            self.logger.info(f"Button '{matched_target}' detected via YOLO at ({center_x}, {center_y}) with confidence {conf:.2f}")
                        return {
                            "text": matched_target,
                            "box": (x, y, w, h),
                            "center": (center_x, center_y),
                            "confidence": conf,
                            "method": "yolo"
                        }
        except Exception as e:
            if self.logger:
                self.logger.error(f"YOLO button detection error: {e}")
        return None

    def detect_via_mock_ocr(self, screen_path, targets):
        if not self.mock_metadata_path or not os.path.exists(self.mock_metadata_path):
            return None
        
        try:
            with open(self.mock_metadata_path, 'r') as f:
                data = json.load(f)
            
            basename = os.path.basename(screen_path)
            # Find matching file in metadata
            matched_key = None
            for key in data.keys():
                if key in basename or basename in key:
                    matched_key = key
                    break
            
            if matched_key:
                elements = data[matched_key]
                for elem in elements:
                    text = elem["text"]
                    if any(target.lower() == text.lower() for target in targets):
                        # box is [x, y, x2, y2]
                        x, y, x2, y2 = elem["box"]
                        w = x2 - x
                        h = y2 - y
                        center_x = x + w // 2
                        center_y = y + h // 2
                        if self.logger:
                            self.logger.info(f"Button '{text}' detected via Mock OCR at ({center_x}, {center_y})")
                        return {
                            "text": text,
                            "box": (x, y, w, h),
                            "center": (center_x, center_y),
                            "confidence": 1.0,
                            "method": "mock_ocr"
                        }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Mock OCR read error: {e}")
        return None

    def detect_via_physical_ocr(self, screen_path, targets):
        if self.ocr_engine == "easyocr" and self.easyocr_reader:
            try:
                results = self.easyocr_reader.readtext(screen_path)
                for bbox, text, prob in results:
                    if any(self.matches_target(target, text) for target in targets) and prob >= self.ocr_threshold:
                        # bbox format: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
                        x = int(bbox[0][0])
                        y = int(bbox[0][1])
                        w = int(bbox[2][0] - x)
                        h = int(bbox[2][1] - y)
                        center_x = x + w // 2
                        center_y = y + h // 2
                        if self.logger:
                            self.logger.info(f"Button '{text}' detected via EasyOCR at ({center_x}, {center_y}) with confidence {prob:.2f}")
                        return {
                            "text": text,
                            "box": (x, y, w, h),
                            "center": (center_x, center_y),
                            "confidence": prob,
                            "method": "easyocr"
                        }
            except Exception as e:
                if self.logger:
                    self.logger.error(f"EasyOCR error: {e}")
        
        elif self.ocr_engine == "pytesseract":
            try:
                pytesseract = importlib.import_module("pytesseract")
                # Get detailed data including boxes and text
                data = pytesseract.image_to_data(screen_path, output_type=pytesseract.Output.DICT)
                n_boxes = len(data['text'])
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i]) / 100.0
                    if any(self.matches_target(target, text) for target in targets) and conf >= self.ocr_threshold:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        center_x = x + w // 2
                        center_y = y + h // 2
                        if self.logger:
                            self.logger.info(f"Button '{text}' detected via PyTesseract at ({center_x}, {center_y}) with confidence {conf:.2f}")
                        return {
                            "text": text,
                            "box": (x, y, w, h),
                            "center": (center_x, center_y),
                            "confidence": conf,
                            "method": "pytesseract"
                        }
            except Exception as e:
                if self.logger:
                    self.logger.error(f"PyTesseract error: {e}")
        return None

    def detect_via_template_matching(self, screen_path, targets):
        """Matches OK/YES button template images."""
        try:
            screen_img = cv2.imread(screen_path)
            if screen_img is None:
                return None
            
            screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
            
            for target in targets:
                # Find matching template file path in templates_dict
                template_file = self.templates_dict.get(target.upper())
                if not template_file or not os.path.exists(template_file):
                    continue
                
                template_img = cv2.imread(template_file)
                if template_img is None:
                    continue
                
                template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
                h, w = template_gray.shape[:2]
                
                res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                if max_val >= self.template_threshold:
                    top_left = max_loc
                    center_x = top_left[0] + w // 2
                    center_y = top_left[1] + h // 2
                    if self.logger:
                        self.logger.info(f"Button '{target}' detected via Template Matching at ({center_x}, {center_y}) with confidence {max_val:.2f}")
                    return {
                        "text": target,
                        "box": (top_left[0], top_left[1], w, h),
                        "center": (center_x, center_y),
                        "confidence": max_val,
                        "method": "template_matching"
                    }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Template matching button detection error: {e}")
        return None

    def detect(self, screen_path, targets):
        """
        Executes hybrid search pipeline: YOLO -> OCR (Mock/Real) -> Template Matching.
        Returns: Dict containing text, box, center (x, y), confidence, method. Or None.
        """
        # 1. YOLO
        result = self.detect_via_yolo(screen_path, targets)
        if result:
            return result
        
        # 2. OCR (Mock mode first if enabled, else physical OCR)
        if self.mock_mode:
            result = self.detect_via_mock_ocr(screen_path, targets)
            if result:
                return result
        else:
            result = self.detect_via_physical_ocr(screen_path, targets)
            if result:
                return result
        
        # 3. OpenCV Template Matching
        result = self.detect_via_template_matching(screen_path, targets)
        if result:
            return result
            
        return None
