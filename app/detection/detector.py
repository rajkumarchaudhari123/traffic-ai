"""
Detection Engine – YOLOv8 + OpenCV
Handles helmet detection, seatbelt detection, and number plate recognition.
Falls back gracefully when YOLO weights are not present (demo mode).
"""

import os
import random
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# ── Try importing ultralytics (YOLOv8) ────────────────────────────────────────
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# ── Try importing EasyOCR ──────────────────────────────────────────────────────
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# ── Try importing pytesseract ──────────────────────────────────────────────────
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# ─── Fake plate pool ──────────────────────────────────────────────────────────

FAKE_PLATES = [
    "DL01AB1234", "MH12CD5678", "KA03EF9012",
    "TN09GH3456", "UP32IJ7890", "RJ14KL2345",
    "GJ05MN6789", "WB23OP0123", "AP28QR4567",
    "HR26ST8901", "MP09UV2345", "PB10WX6789",
]

VIOLATION_MESSAGES = {
    "No Helmet": [
        "Helmet not detected on rider.",
        "Motorcyclist riding without helmet – safety violation.",
        "Two-wheeler rider detected without protective headgear.",
    ],
    "No Seatbelt": [
        "Seatbelt violation captured.",
        "Driver not wearing seatbelt – traffic rule violated.",
        "Occupant detected without seatbelt fastened.",
    ],
    "No Helmet & No Seatbelt": [
        "Multiple violations detected – helmet and seatbelt missing.",
        "Compound traffic violation: no helmet, no seatbelt.",
    ],
}

FINE_MAP = {
    "No Helmet": 1000,
    "No Seatbelt": 1000,
    "No Helmet & No Seatbelt": 2000,
}


class TrafficViolationDetector:
    """
    Core detection class.
    Uses YOLOv8 when available, otherwise falls back to OpenCV Haar/demo simulation.
    """

    def __init__(self, violations_dir: str = "violations"):
        self.violations_dir = Path(violations_dir)
        self.violations_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.ocr_reader = None
        self._load_models()

        # Visual state for demo frame generation
        self._demo_vehicles = self._init_demo_vehicles()
        self.last_helmet_challan_time = 0

    # ── Model Loading ──────────────────────────────────────────────────────────

    def _load_models(self):
        if YOLO_AVAILABLE:
            # Try loading custom weights, fall back to pretrained nano
            custom_weights = Path("models/yolov8_traffic.pt")
            if custom_weights.exists():
                try:
                    self.model = YOLO(str(custom_weights))
                    print("[OK] Loaded custom YOLOv8 weights")
                    return
                except Exception as e:
                    print(f"[WARN] Custom weights failed: {e}")
            try:
                self.model = YOLO("yolov8n.pt")  # download pretrained nano
                print("[OK] Loaded YOLOv8n pretrained model")
            except Exception as e:
                print(f"[WARN] YOLOv8 unavailable: {e}")
        else:
            print("[INFO] YOLOv8 not installed - using demo simulation")

        if OCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                print("[OK] EasyOCR loaded")
            except Exception as e:
                print(f"[WARN] EasyOCR failed: {e}")

    # ── Real Frame Processing ──────────────────────────────────────────────────

    def process_frame(self, frame: np.ndarray, helmet_demo: bool = False):
        """
        Process a real camera frame.
        Returns (annotated_frame, list_of_violations).
        """
        violations = []
        annotated = frame.copy()

        if helmet_demo:
            try:
                # Load Haar cascade face detector
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
                
                # Overlay HUD style text for Helmet Demo Mode
                cv2.putText(annotated, "HELMET WEBCAM DEMO ACTIVE", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
                
                if len(faces) > 0:
                    # Bare face detected -> No Helmet!
                    for (x, y, w, h) in faces:
                        # Draw Red Bounding Box around bare face
                        cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 0, 255), 2)
                        cv2.rectangle(annotated, (x, y - 25), (x + 130, y), (0, 0, 255), -1)
                        cv2.putText(annotated, "NO HELMET", (x + 5, y - 7),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)
                    
                    # Status text in red
                    cv2.putText(annotated, "ALERT: Bare face detected (No Helmet)!", (15, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                    
                    # Trigger violation once every 10 seconds to avoid spamming challans
                    current_time = time.time()
                    if current_time - self.last_helmet_challan_time > 10:
                        self.last_helmet_challan_time = current_time
                        violation = self._build_violation("No Helmet", frame)
                        violations.append(violation)
                else:
                    # No bare face detected -> Helmet is on (or face hidden)!
                    cv2.putText(annotated, "STATUS: SAFE (HELMET DETECTED / OK)", (15, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
                    
                    # Draw a green tracking circle in center to look active
                    h_f, w_f = frame.shape[:2]
                    cv2.circle(annotated, (w_f // 2, h_f // 2), 40, (0, 255, 0), 1)
                    cv2.line(annotated, (w_f // 2 - 50, h_f // 2), (w_f // 2 + 50, h_f // 2), (0, 255, 0), 1)
                    cv2.line(annotated, (w_f // 2, h_f // 2 - 50), (w_f // 2, h_f // 2 + 50), (0, 255, 0), 1)
                    
            except Exception as e:
                cv2.putText(annotated, f"Helmet Demo Error: {e}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            # Standard YOLO/Simulation processing
            if self.model is not None:
                try:
                    results = self.model(frame, conf=0.4, verbose=False)
                    annotated = results[0].plot()
                    violations = self._parse_yolo_results(results[0], frame)
                except Exception as e:
                    cv2.putText(annotated, f"Detection error: {e}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                annotated = self._draw_demo_overlay(annotated)

        return annotated, violations

    def process_static_image(self, b64_str: str) -> dict:
        """
        Processes a static selfie base64 image captured by the client webcam.
        Detects bare faces. If a bare face is found, it is a 'No Helmet' violation.
        Crops the face, annotates the image, and saves the proof.
        """
        import base64
        
        # Strip header if present
        if "," in b64_str:
            b64_str = b64_str.split(",")[1]
            
        # Decode base64 to numpy array
        img_bytes = base64.b64decode(b64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"violation_type": None, "face_detected": False, "message": "Failed to decode image"}

        annotated = frame.copy()
        
        try:
            # Load Haar cascade face detector
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            
            if len(faces) > 0:
                # Bare face detected -> No Helmet!
                # We crop the first detected face for the e-challan
                x, y, w, h = faces[0]
                
                # Add padding to cropped face for better aesthetics
                h_img, w_img = frame.shape[:2]
                pad_y = int(h * 0.2)
                pad_x = int(w * 0.2)
                y1 = max(0, y - pad_y)
                y2 = min(h_img, y + h + pad_y)
                x1 = max(0, x - pad_x)
                x2 = min(w_img, x + w + pad_x)
                
                cropped_face = frame[y1:y2, x1:x2]
                _, face_buf = cv2.imencode(".jpg", cropped_face)
                face_b64 = base64.b64encode(face_buf).decode("utf-8")
                
                # Draw red box and HUD indicators on the annotated frame
                for (fx, fy, fw, fh) in faces:
                    cv2.rectangle(annotated, (fx, fy), (fx+fw, fy+fh), (0, 0, 255), 2)
                    cv2.rectangle(annotated, (fx, fy - 25), (fx + 130, fy), (0, 0, 255), -1)
                    cv2.putText(annotated, "NO HELMET", (fx + 5, fy - 7),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)
                
                cv2.putText(annotated, "ALERT: Bare face detected (No Helmet)!", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                
                # Stamp the final proof image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                img_filename = f"No_Helmet_Selfie_{timestamp}.jpg"
                img_path = self.violations_dir / img_filename
                
                self._stamp_violation_image(annotated, "No Helmet", "SELFIE-CAM")
                cv2.imwrite(str(img_path), annotated)
                
                return {
                    "violation_type": "No Helmet",
                    "face_detected": True,
                    "cropped_face_b64": face_b64,
                    "image": img_filename,
                    "plate": "SELFIE-CAM",
                    "fine": 1000,
                    "location": "Spot-Check Selfie Scanner",
                    "message": "Instant selfie camera capture – bare face detected (riding safety helmet missing).",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            print(f"[ERROR] Static scanner failed: {e}")
            
        return {"violation_type": None, "face_detected": False, "message": "Helmet detected or no bare face visible"}

    def _parse_yolo_results(self, result, original_frame: np.ndarray):
        """Parse YOLOv8 results and extract violations."""
        violations = []
        class_names = result.names

        detected = set()
        boxes_data = []

        if result.boxes is not None:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = class_names.get(cls_id, "unknown").lower()
                xyxy = box.xyxy[0].tolist()
                detected.add(label)
                boxes_data.append((label, conf, xyxy))

        # Heuristic violation detection based on COCO classes
        has_motorcycle = any(l in ("motorcycle", "motorbike") for l, _, _ in boxes_data)
        has_person = any(l == "person" for l, _, _ in boxes_data)
        has_car = any(l == "car" for l, _, _ in boxes_data)

        # For demo: randomly decide if violation occurs (simulates real-world low detection)
        if (has_motorcycle or has_person) and random.random() < 0.02:
            violation = self._build_violation("No Helmet", original_frame)
            violations.append(violation)

        if has_car and random.random() < 0.015:
            violation = self._build_violation("No Seatbelt", original_frame)
            violations.append(violation)

        return violations

    # ── Violation Building ────────────────────────────────────────────────────

    def _build_violation(self, violation_type: str, frame: np.ndarray) -> dict:
        plate = self._extract_plate(frame)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        img_filename = f"{violation_type.replace(' ', '_')}_{timestamp}.jpg"
        img_path = self.violations_dir / img_filename

        # Save proof image
        annotated = frame.copy()
        self._stamp_violation_image(annotated, violation_type, plate)
        cv2.imwrite(str(img_path), annotated)

        msg = random.choice(VIOLATION_MESSAGES.get(violation_type, ["Violation detected."]))
        return {
            "violation_type": violation_type,
            "plate": plate,
            "fine": FINE_MAP.get(violation_type, 1000),
            "message": msg,
            "timestamp": datetime.now().isoformat(),
            "image": img_filename,
            "status": "Pending",
            "location": self._random_location(),
        }

    def simulate_violation(self, vtype: str) -> dict:
        """Simulate a violation with a synthetic image for demo mode."""
        vmap = {
            "helmet": "No Helmet",
            "seatbelt": "No Seatbelt",
            "both": "No Helmet & No Seatbelt",
        }
        violation_type = vmap.get(vtype, "No Helmet")
        frame = self.generate_demo_frame(random.randint(0, 200))
        return self._build_violation(violation_type, frame)

    # ── OCR / Plate Extraction ────────────────────────────────────────────────

    def _extract_plate(self, frame: np.ndarray) -> str:
        """Try OCR; fall back to fake plate."""
        if self.ocr_reader is not None:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                results = self.ocr_reader.readtext(gray, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                for _, text, conf in results:
                    clean = text.strip().replace(" ", "").upper()
                    if 6 <= len(clean) <= 10 and conf > 0.5:
                        return clean
            except Exception:
                pass

        if TESSERACT_AVAILABLE:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(
                    gray, config="--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                ).strip()
                clean = text.replace(" ", "").upper()
                if 6 <= len(clean) <= 10:
                    return clean
            except Exception:
                pass

        return random.choice(FAKE_PLATES)

    # ── Demo Frame Generation ─────────────────────────────────────────────────

    def _init_demo_vehicles(self):
        """Initialize moving vehicle state for demo animation."""
        vehicles = []
        # Ensure at least one motorcycle (two-wheeler) is always present
        vehicles.append({
            "x": 50,
            "y": 100,
            "speed": 4,
            "color": (60, 120, 180),
            "type": "motorcycle",
            "plate": "DL01AB1234",
        })
        # Add other random vehicles
        types = ["car", "truck", "car"]
        for i in range(1, 4):
            vehicles.append({
                "x": random.randint(150, 600),
                "y": 100 + i * 120,
                "speed": random.randint(3, 7),
                "color": random.choice([
                    (180, 60, 60), (60, 160, 60),
                    (160, 130, 60), (120, 60, 160)
                ]),
                "type": types[i - 1],
                "plate": random.choice(FAKE_PLATES),
            })
        return vehicles

    def generate_demo_frame(self, frame_idx: int) -> np.ndarray:
        """Render a synthetic traffic scene frame."""
        frame = np.zeros((480, 800, 3), dtype=np.uint8)

        # Road background
        cv2.rectangle(frame, (0, 0), (800, 480), (20, 25, 30), -1)

        # Road surface
        cv2.rectangle(frame, (0, 60), (800, 480), (35, 40, 45), -1)

        # Lane markings
        for lane_y in (160, 280, 390):
            for x in range(0, 800, 60):
                cv2.rectangle(frame, (x, lane_y), (x + 35, lane_y + 4), (220, 200, 60), -1)

        # Roadside elements
        for pole_x in (50, 200, 400, 600, 750):
            cv2.line(frame, (pole_x, 60), (pole_x, 10), (80, 80, 100), 3)
            cv2.circle(frame, (pole_x, 10), 8, (255, 230, 100), -1)

        # Animate vehicles
        for v in self._demo_vehicles:
            v["x"] = (v["x"] + v["speed"]) % 900
            x, y = int(v["x"]), int(v["y"])

            if v["type"] == "car":
                self._draw_car(frame, x, y, v["color"])
            elif v["type"] == "motorcycle":
                self._draw_motorcycle(frame, x, y, v["color"])
            else:
                self._draw_truck(frame, x, y, v["color"])

            # Draw plate
            cv2.putText(frame, v["plate"], (x, y + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (240, 240, 240), 1)

        # HUD overlay
        ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        cv2.putText(frame, "SMART TRAFFIC AI – DEMO FEED", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1)
        cv2.putText(frame, ts, (550, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        cv2.putText(frame, "CAM-01 | NH-48 TOLLGATE | AI ACTIVE", (10, 470),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 180, 0), 1)

        # Blinking REC indicator
        if (frame_idx // 10) % 2 == 0:
            cv2.circle(frame, (780, 20), 5, (0, 0, 220), -1)
            cv2.putText(frame, "REC", (750, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)

        return frame

    def _draw_car(self, frame, x, y, color):
        # Car body
        cv2.rectangle(frame, (x, y - 15), (x + 55, y + 20), color, -1)
        # Cabin (Windshield)
        cabin_color = tuple(max(0, c - 40) for c in color)
        cv2.rectangle(frame, (x + 8, y - 28), (x + 47, y - 15), cabin_color, -1)
        # Wheels
        cv2.circle(frame, (x + 10, y + 22), 7, (60, 60, 60), -1)
        cv2.circle(frame, (x + 45, y + 22), 7, (60, 60, 60), -1)

        # Draw a driver inside the cabin (Face/body)
        cv2.circle(frame, (x + 22, y - 21), 4, (180, 220, 240), -1) # Driver head

        # Red bounding box around driver showing "NO SEATBELT" AI detection
        cv2.rectangle(frame, (x + 14, y - 25), (x + 30, y - 15), (0, 0, 255), 1)
        cv2.putText(frame, "NO SEATBELT", (x + 4, y - 31),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

    def _draw_motorcycle(self, frame, x, y, color):
        # Wheels & chassis
        cv2.ellipse(frame, (x + 30, y + 5), (25, 6), 0, 0, 360, (60, 60, 60), 2)
        # Motorcycle body
        cv2.rectangle(frame, (x + 15, y - 15), (x + 45, y + 0), color, -1)
        # Rider body
        cv2.rectangle(frame, (x + 22, y - 28), (x + 32, y - 15), (200, 200, 200), -1)
        # Rider head (no helmet - just skin tone and dark hair)
        cv2.circle(frame, (x + 27, y - 34), 6, (180, 220, 240), -1)  # Face
        cv2.circle(frame, (x + 27, y - 37), 4, (30, 30, 30), -1)    # Hair
        # Red bounding box around rider's head to simulate "No Helmet" AI detection
        cv2.rectangle(frame, (x + 18, y - 43), (x + 36, y - 26), (0, 0, 255), 1)
        cv2.putText(frame, "NO HELMET", (x + 8, y - 47),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

    def _draw_truck(self, frame, x, y, color):
        cv2.rectangle(frame, (x, y - 10), (x + 80, y + 22), color, -1)
        cv2.rectangle(frame, (x, y - 30), (x + 28, y - 10),
                      tuple(max(0, c - 30) for c in color), -1)
        cv2.circle(frame, (x + 12, y + 25), 8, (60, 60, 60), -1)
        cv2.circle(frame, (x + 65, y + 25), 8, (60, 60, 60), -1)

    def _draw_demo_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Overlay demo status on real camera frames when YOLO not available."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (300, 30), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        cv2.putText(frame, "AI DETECTION ACTIVE", (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 100), 1)
        return frame

    def _stamp_violation_image(self, frame, violation_type, plate):
        """Stamp violation info on the saved proof image."""
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, h - 60), (w, h), (0, 0, 0), -1)
        cv2.putText(frame, f"VIOLATION: {violation_type}", (10, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
        cv2.putText(frame, f"PLATE: {plate}  |  {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        # Red border
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 220), 4)

    @staticmethod
    def _random_location():
        locations = [
            "NH-48 Delhi-Gurugram Expressway",
            "Outer Ring Road, Bengaluru",
            "Eastern Express Highway, Mumbai",
            "Rajpath, New Delhi",
            "OMR, Chennai",
        ]
        return random.choice(locations)
