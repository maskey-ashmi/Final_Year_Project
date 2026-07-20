"""Ensemble integration helpers for acne prediction."""

import os
import sys
import cv2
import numpy as np

YOLO_CLASSES   = ['Acne']

# Standard OpenCV Cascades
_FACE_CASCADE_PATH  = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_EYE_CASCADE_PATH   = cv2.data.haarcascades + "haarcascade_eye.xml"
_SMILE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_smile.xml"

# Fraction of face HEIGHT to keep (from the top).
# 1.0 keeps the entire face (forehead + cheeks + nose + chin).
_FACE_CROP_HEIGHT_FRACTION = 1.0


# ── YOLO loader ───────────────────────────────────────────────────────────────
def _load_yolo(weights_path: str):
    abs_path = os.path.abspath(weights_path)
    if not os.path.exists(abs_path):
        print(f"[YOLO] weights not found: {abs_path}")
        return None

    # Use ultralytics for single-class YOLOv8 model
    try:
        from ultralytics import YOLO
        model = YOLO(abs_path)
        print(f"[YOLO] loaded via ultralytics: {abs_path}")
        return ("ultralytics", model)
    except Exception as e:
        print(f"[YOLO] ultralytics failed: {e}")

    return None


# ── Main detector ─────────────────────────────────────────────────────────────
class SimpleEnsembleDetector:

    SEVERITY_THRESHOLDS = {"mild": (1, 5), "moderate": (6, 20), "severe": (21, 9999)}

    def __init__(self, yolo_weights_path="models/best_acne_yolov8s_single_class.pt"):
        self.yolo_weights_path = yolo_weights_path
        self._yolo             = _load_yolo(yolo_weights_path)
        # Using standard OpenCV cascades for compatibility
        self.face_cascade      = cv2.CascadeClassifier(_FACE_CASCADE_PATH)
        self.eye_cascade       = cv2.CascadeClassifier(_EYE_CASCADE_PATH)
        self.smile_cascade     = cv2.CascadeClassifier(_SMILE_CASCADE_PATH)

    # ── public API ─────────────────────────────────────────────────────────────
    def predict_acne_severity(self, image_path: str) -> dict:
        image = cv2.imread(image_path)
        if image is None:
            return self._error("Could not load image")

        # 1. detect face
        face_bbox = self._detect_face(image)
        if face_bbox is None:
            return self._error("No face detected. Please look directly at the camera.")

        fx, fy, fw, fh = face_bbox

        # 2. build TIGHT crop:
        #    • tiny side margins (2 %)
        #    • keep only top _FACE_CROP_HEIGHT_FRACTION of face height
        #      → cuts off lips / chin which cause false positives
        side_margin = int(fw * 0.02)
        top_margin  = int(fh * 0.02)

        cx1 = max(0,              fx - side_margin)
        cy1 = max(0,              fy - top_margin)
        cx2 = min(image.shape[1], fx + fw + side_margin)
        cy2 = min(image.shape[0], fy + int(fh * _FACE_CROP_HEIGHT_FRACTION))

        face_crop = image[cy1:cy2, cx1:cx2]
        if face_crop.size == 0:
            return self._error("Face crop is empty")

        # 3. detect on face crop only
        if self._yolo is not None:
            raw_dets = self._run_yolo(face_crop)
        else:
            raw_dets = self._fallback_detection(face_crop)

        # 4. translate bbox back to full-image coordinates
        detections = []
        for d in raw_dets:
            bx1, by1, bx2, by2 = d["bbox"]
            detections.append({
                "type":       d["type"],
                "confidence": d["confidence"],
                "bbox": [float(bx1 + cx1), float(by1 + cy1), float(bx2 + cx1), float(by2 + cy1)],
            })

        # 5. Filter out false positives using feature detection (eyes, nose, mouth)
        detections = self._filter_detections(image, detections, face_bbox)

        count    = len(detections)
        severity = self._determine_severity(count)
        conf     = self._calc_confidence(detections)

        return {
            "severity":      severity,
            "count":         count,
            "confidence":    conf,       # 0-1 float – do NOT ×100 in caller
            "detections":    detections,
            "face_detected": True,
            "face_bbox":     [int(fx), int(fy), int(fw), int(fh)],
            "crop_bbox":     [int(cx1), int(cy1), int(cx2), int(cy2)],
            "image_path":    image_path,
        }

    # ── YOLO inference ────────────────────────────────────────────────────────
    def _run_yolo(self, face_img: np.ndarray) -> list:
        tag, model = self._yolo
        detections = []
        try:
            # Apply CLAHE to enhance contrast flattened by webcam smoothing
            lab = cv2.cvtColor(face_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl,a,b))
            enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            if tag == "ultralytics":
                results = model(enhanced_img, verbose=False)
                for r in results:
                    if r.boxes is None:
                        continue
                    for box in r.boxes:
                        conf = float(box.conf[0])
                        if conf < 0.15:
                            continue
                        cls  = int(box.cls[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        acne_type = YOLO_CLASSES[cls] if cls < len(YOLO_CLASSES) else "Acne"
                        detections.append({
                            "type":       acne_type,
                            "confidence": round(conf, 4),
                            "bbox":       [float(x1), float(y1), float(x2), float(y2)],
                        })
        except Exception as e:
            print(f"[YOLO] inference error: {e}")
        return detections

    # ── fallback colour detector ──────────────────────────────────────────────
    def _fallback_detection(self, face_img: np.ndarray) -> list:
        hsv  = cv2.cvtColor(face_img, cv2.COLOR_BGR2HSV)
        red1 = cv2.inRange(hsv, np.array([0,   50,  50]), np.array([10,  255, 255]))
        red2 = cv2.inRange(hsv, np.array([170, 50,  50]), np.array([180, 255, 255]))
        wht  = cv2.inRange(hsv, np.array([0,   0,  200]), np.array([180,  30, 255]))
        drk  = cv2.inRange(hsv, np.array([0,   0,    0]), np.array([180,  60,  80]))
        mask = cv2.add(cv2.add(red1, red2), cv2.add(wht, drk))

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections  = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if not (15 < area < 600):
                continue
            x, y, w, h = cv2.boundingRect(contour)
            conf = min(float(area) / 400.0, 0.85)
            detections.append({
                "type":       "Acne",
                "confidence": round(conf, 4),
                "bbox":       [float(x), float(y), float(x+w), float(y+h)],
            })
        return detections

    # ── face detection ────────────────────────────────────────────────────────
    def _detect_face(self, image: np.ndarray):
        ih, iw = image.shape[:2]
        image_area = ih * iw

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        # Find face candidates
        candidate_faces = []
        for scale, neighbors, min_size in [
            (1.1, 6, (80, 80)),
            (1.1, 4, (60, 60)),
            (1.05, 4, (50, 50)),
            (1.05, 3, (40, 40)),
        ]:
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=scale, minNeighbors=neighbors, minSize=min_size
            )
            if len(faces) > 0:
                candidate_faces = faces
                break

        if len(candidate_faces) == 0:
            print("[Face] not detected")
            return None

        # Validate: aspect ratio + size + eye check + eye symmetry
        valid_faces = []
        for (fx, fy, fw, fh) in candidate_faces:
            aspect = fw / fh
            if not (0.65 <= aspect <= 1.45):
                continue
            if (fw * fh) / image_area < 0.04:
                continue

            # Validated: aspect ratio + size
            # Removed strict eye checks to prevent false rejections of full faces


            valid_faces.append((fx, fy, fw, fh))

        if not valid_faces:
            print("[Face] no valid human face after validation")
            return None

        face = max(valid_faces, key=lambda f: f[2] * f[3])
        print(f"[Face] detected: {face}")
        return tuple(face)

    # ── false positive filtering ──────────────────────────────────────────────
    def _filter_detections(self, image: np.ndarray, detections: list, face_bbox: tuple) -> list:
        """
        Excludes detections that fall on top of eyes, nose center, or mouth.
        Uses OpenCV cascades for eyes/mouth and geometric proportions for nose.
        """
        fx, fy, fw, fh = face_bbox
        face_roi_gray = cv2.cvtColor(image[fy:fy+fh, fx:fx+fw], cv2.COLOR_BGR2GRAY)

        # 1. Detect Eyes
        eyes = self.eye_cascade.detectMultiScale(face_roi_gray, 1.1, 5)
        eye_zones = []
        for (ex, ey, ew, eh) in eyes:
            # Buffer the eye zone slightly
            eye_zones.append((ex + fx, ey + fy, ew, eh))

        # 2. Detect Mouth
        smiles = self.smile_cascade.detectMultiScale(face_roi_gray, 1.5, 20)
        mouth_zones = []
        for (sx, sy, sw, sh) in smiles:
            # Mouth is usually in the bottom half
            if sy > fh / 2:
                mouth_zones.append((sx + fx, sy + fy, sw, sh))

        # 3. Geometric Nose Zone (approximate)
        # Nose tip is typically in the center of the face
        nose_cx, nose_cy = fx + fw/2, fy + fh * 0.6
        nose_radius = fw * 0.12

        filtered = []
        for det in detections:
            bx1, by1, bx2, by2 = det["bbox"]
            cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2

            is_false_positive = False

            # Check Eyes
            for (ex, ey, ew, eh) in eye_zones:
                if ex <= cx <= ex + ew and ey <= cy <= ey + eh:
                    is_false_positive = True
                    break
            if is_false_positive: 
                print(f"[Filter] Removed {det['type']} on Eye at ({cx:.1f}, {cy:.1f})")
                continue

            # Check Mouth
            for (sx, sy, sw, sh) in mouth_zones:
                if sx <= cx <= sx + sw and sy <= cy <= sy + sh:
                    is_false_positive = True
                    break
            if is_false_positive:
                print(f"[Filter] Removed {det['type']} on Mouth at ({cx:.1f}, {cy:.1f})")
                continue

            # Check Nose (Geometric)
            dist_to_nose = np.sqrt((cx - nose_cx)**2 + (cy - nose_cy)**2)
            if dist_to_nose < nose_radius:
                is_false_positive = True
                print(f"[Filter] Removed {det['type']} on Nose at ({cx:.1f}, {cy:.1f})")

            if not is_false_positive:
                filtered.append(det)

        return filtered

    # ── helpers ───────────────────────────────────────────────────────────────
    def _determine_severity(self, count: int) -> str:
        if count == 0:
            return "clear"
        for label, (lo, hi) in self.SEVERITY_THRESHOLDS.items():
            if lo <= count <= hi:
                return label
        return "severe"

    def _calc_confidence(self, detections: list) -> float:
        if not detections:
            return 0.0
        avg = sum(d["confidence"] for d in detections) / len(detections)
        return round(min(avg, 0.95), 4)

    @staticmethod
    def _error(msg: str) -> dict:
        return {"severity": "unknown", "count": 0, "confidence": 0.0,
                "detections": [], "error": msg}


# ── module-level singleton ────────────────────────────────────────────────────
_detector: SimpleEnsembleDetector | None = None

def get_ensemble_detector() -> SimpleEnsembleDetector:
    global _detector
    if _detector is None:
        _detector = SimpleEnsembleDetector()
    return _detector


def _convert_to_native_types(obj):
    """Convert NumPy types to native Python types recursively"""
    import numpy as np
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: _convert_to_native_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_native_types(x) for x in obj]
    else:
        return obj

def predict_acne_from_image(image_path: str) -> dict:
    """
    Used by prediction_routes.py.
    confidence is always a 0-1 float – prediction_routes must NOT ×100.
    """
    detector = get_ensemble_detector()
    result   = detector.predict_acne_severity(image_path)
    result   = _convert_to_native_types(result)
    return {
        "severity":      result.get("severity", "unknown"),
        "count":         result.get("count", 0),
        "confidence":    result.get("confidence", 0.0),  # 0-1, NOT percent
        "detections":    result.get("detections", []),
        "face_detected": result.get("face_detected", False),
        "face_bbox":     result.get("face_bbox"),
        "image_path":    result.get("image_path", image_path),
        "acne_type":     "Acne" if result.get("count", 0) > 0 else "Clear Skin",
        "label":         result.get("severity", "unknown"),
        **({"error": result["error"]} if "error" in result else {}),
    }