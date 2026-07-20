import os
import sys
import cv2
import joblib
import traceback
import numpy as np
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.join(PROJECT_ROOT, "rf"))

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required, current_user

from database.user_models import User, Prediction, Routine
from ensemble_web_integration import predict_acne_from_image

# Enhanced routine functions
def get_enhanced_basic_routine(age, skin_type, severity, class_scores):
    """Enhanced basic routine with age and skin type customization"""
    # Age-based customization
    if age < 20:
        morning_base = ["Gentle cleanser", "Light moisturizer", "SPF 30+"]
    elif age < 30:
        morning_base = ["Gentle cleanser", "Balanced moisturizer", "SPF 30+"]
    else:
        morning_base = ["Anti-aging cleanser", "Rich moisturizer", "SPF 50+"]
    
    # Skin type customization
    if skin_type.lower() == "oily":
        morning_base.append("Oil-control primer")
    elif skin_type.lower() == "dry":
        morning_base.append("Hydrating serum")
    elif skin_type.lower() == "combination":
        morning_base.append("Balancing toner")
    elif skin_type.lower() == "sensitive":
        morning_base = ["Ultra-gentle cleanser", "Soothing moisturizer", "Mineral SPF 30+"]
    
    return {
        "morning": morning_base,
        "evening": get_evening_basic(age, skin_type),
        "weekly": get_weekly_basic(severity)
    }

def get_enhanced_active_routine(age, skin_type, severity, class_scores):
    """Enhanced active treatment routine"""
    # Severity-based intensity
    if severity == "severe":
        active_ingredients = ["Benzoyl peroxide", "Retinol", "Salicylic acid"]
        base_products = ["Medicated cleanser", "Oil-free gel moisturizer"]
    elif severity == "moderate":
        active_ingredients = ["Niacinamide", "BHA", "Tea tree oil"]
        base_products = ["Gentle cleanser", "Lightweight moisturizer"]
    else:
        active_ingredients = ["Gentle BHA", "Light spot treatment"]
        base_products = ["Gentle cleanser", "Lightweight moisturizer"]
    
    # Skin type adaptation
    if skin_type.lower() == "oily":
        base_products = ["Oil-free cleanser", "Gel moisturizer"]
    elif skin_type.lower() == "dry":
        base_products = ["Cream cleanser", "Rich moisturizer"]
    elif skin_type.lower() == "sensitive":
        active_ingredients = ["Azelaic acid", "Green tea extract"]
    
    return {
        "morning": base_products + ["SPF 30+"],
        "evening": base_products + active_ingredients[:2],
        "weekly": ["Clay mask", "Chemical exfoliant"]
    }

def get_enhanced_premium_routine(age, skin_type, severity, class_scores):
    """Enhanced premium routine — most comprehensive tier. Builds on the
    active routine with additional targeted treatment and richer weekly care.
    NOTE: placeholder ingredient choices — review with a dermatologist
    before shipping this content to real users."""
    if severity == "severe":
        active_ingredients = ["Benzoyl peroxide", "Retinol", "Salicylic acid", "Azelaic acid"]
        base_products = ["Medicated cleanser", "Barrier-repair moisturizer"]
        treatment = "Prescription-strength spot treatment"
    elif severity == "moderate":
        active_ingredients = ["Niacinamide", "BHA", "Retinol", "Tea tree oil"]
        base_products = ["Gentle cleanser", "Ceramide moisturizer"]
        treatment = "Targeted spot treatment"
    else:
        active_ingredients = ["Gentle BHA", "Niacinamide", "Peptide serum"]
        base_products = ["Gentle cleanser", "Lightweight moisturizer"]
        treatment = "Preventive spot treatment"

    if skin_type.lower() == "oily":
        base_products = ["Oil-free cleanser", "Mattifying gel moisturizer"]
    elif skin_type.lower() == "dry":
        base_products = ["Cream cleanser", "Rich barrier cream"]
    elif skin_type.lower() == "sensitive":
        active_ingredients = ["Azelaic acid", "Centella asiatica", "Green tea extract"]

    return {
        "morning": base_products + ["Vitamin C serum", "SPF 50+"],
        "evening": base_products + active_ingredients[:3] + [treatment],
        "weekly": ["Professional-strength chemical peel", "Clay mask", "Gentle exfoliation"],
    }

def get_evening_basic(age, skin_type):
    """Evening routine for basic skincare"""
    if skin_type.lower() == "oily":
        return ["Oil-control cleanser", "Lightweight moisturizer"]
    elif skin_type.lower() == "dry":
        return ["Cream cleanser", "Nourishing cream"]
    else:
        return ["Gentle cleanser", "Moisturizer"]

def get_weekly_basic(severity):
    """Weekly treatment based on severity"""
    if severity == "severe":
        return ["Calming mask", "Gentle exfoliation"]
    elif severity == "moderate":
        return ["Hydrating mask", "Light exfoliation"]
    else:
        return ["Face mask", "Exfoliation"]

def get_enhanced_routine(user, routine_class, result, class_scores, age, skin_type):
    """Hybrid Random Forest + enhanced hardcoded rules.
    routine_class must be one of: 'basic', 'advanced', 'premium'."""
    severity = result.get("severity", "mild")

    if routine_class == "premium":
        return get_enhanced_premium_routine(age, skin_type, severity, class_scores)
    elif routine_class == "advanced":
        return get_enhanced_active_routine(age, skin_type, severity, class_scores)
    else:
        return get_enhanced_basic_routine(age, skin_type, severity, class_scores)

prediction_bp = Blueprint("prediction_bp", __name__)

YOLO_CLASSES   = ['Acne']
YOLO_MODEL     = "yolov8"
YOLO_WEIGHTS   = "models/best_acne_yolov8s_single_class.pt"
# Detections are already filtered at the model level before they reach here.
# Use the same confidence threshold for any additional route-level filtering.
CONF_THRESHOLD = 0.15

# Load Random Forest model for acne detection (acne_detection_rf.pkl)
# Load Random Forest model for acne detection (acne_detection_rf.pkl) with robust path handling and custom class import
# Ensure the custom RandomForest implementation is importable before unpickling
try:
    import random_forest_from_scratch  # noqa: F401
except Exception as e:
    # If the module is missing, log but continue – loading will still fail gracefully
    print(f"[RF] Warning: could not import custom RandomForest module: {e}")

RF_MODEL = None
RF_SKIN_MAP = {}
RF_FEATURE_COLS = []

def _load_random_forest():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "acne_detection_rf.pkl"))
    if not os.path.exists(model_path):
        print(f"[RF] Model file not found at {model_path}")
        return None, None, None
    try:
        # The pickle may contain a custom RandomForest class; importing the module first resolves the attribute error
        rf_data = joblib.load(model_path)
        model = rf_data.get("model")
        if model is None:
            raise ValueError("Missing 'model' key in pickle")
        skin_map = rf_data.get("skin_map", {})
        feature_cols = rf_data.get("feature_cols", [])
        print("[RF] Random Forest model loaded successfully!")
        return model, skin_map, feature_cols
    except Exception as e:
        print(f"[RF] Failed to load model: {e}")
        return None, None, None

RF_MODEL, RF_SKIN_MAP, RF_FEATURE_COLS = _load_random_forest()
print(f"[DEBUG] RF_MODEL loaded: {RF_MODEL is not None}, feature cols count: {len(RF_FEATURE_COLS) if RF_FEATURE_COLS else 0}")
# Duplicate RandomForest loading block removed - original loading already defined above




def _display(yolo_type: str) -> str:
    return "Acne"


def _safe_float(v, default=0.0):
    try:    return float(v)
    except: return default


# ── face verification (quick pre-check before running YOLO) ──────────────────
_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
_EYE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)

def verify_human_face(image_path: str):
 
    img = cv2.imread(image_path)
    if img is None:
        return []

    ih, iw = img.shape[:2]
    image_area = ih * iw

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    candidate_faces = []
    for scale, neighbors, min_size in [
        (1.1, 6, (80, 80)),
        (1.1, 4, (60, 60)),
        (1.05, 4, (50, 50)),
        (1.05, 3, (40, 40)),
    ]:
        faces = _FACE_CASCADE.detectMultiScale(
            gray, scaleFactor=scale, minNeighbors=neighbors, minSize=min_size
        )
        if len(faces) > 0:
            candidate_faces = faces
            break

    if len(candidate_faces) == 0:
        return []

    valid_faces = []
    for (fx, fy, fw, fh) in candidate_faces:
        # 2a. Aspect ratio: width/height should be 0.65 – 1.45 for a frontal face
        aspect = fw / fh
        if not (0.65 <= aspect <= 1.45):
            continue

        # 2b. Minimum relative size: face must be >= 4% of image area
        face_area = fw * fh
        if face_area / image_area < 0.04:
            continue

        # 2c. Eye check inside the face ROI (Relaxed)
        #     Use upper 60% of face height where eyes are always located
        eye_roi_h = int(fh * 0.60)
        face_roi  = gray[fy: fy + eye_roi_h, fx: fx + fw]
        eyes = _EYE_CASCADE.detectMultiScale(
            face_roi, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
        )
        if len(eyes) < 1:
            # Retry with more permissive settings
            eyes = _EYE_CASCADE.detectMultiScale(
                face_roi, scaleFactor=1.05, minNeighbors=3, minSize=(15, 15)
            )
            
        # We no longer strictly reject faces based on eye detection since Haar cascades 
        # frequently miss eyes due to glasses, uneven lighting, or slight angles.
        # As long as the face bounding box passes the aspect ratio and size checks, we accept it.

        valid_faces.append((fx, fy, fw, fh))

    if not valid_faces:
        return []

    # Return the largest valid face
    best = max(valid_faces, key=lambda f: f[2] * f[3])
    import numpy as np
    return np.array([best])


# ── routine recommender (simplified using Random Forest) ────────────────────


# ── main endpoint ─────────────────────────────────────────────────────────────
@prediction_bp.route("/api/predict", methods=["POST"])
@login_required
def predict_api():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        age       = current_user.age
        skin_type = current_user.skin_type
        if not age or not skin_type:
            return jsonify({"error": "Your profile is missing age or skin type."}), 400

        # save file
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        image_file = request.files["image"]
        ext        = (os.path.splitext(image_file.filename or "")[1].lower()) or ".jpg"
        filename   = f"user_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
        save_path  = os.path.join(upload_folder, filename)
        
        try:
            from PIL import Image, ImageOps
            img = Image.open(image_file)
            img = ImageOps.exif_transpose(img)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(save_path)
        except Exception as e:
            current_app.logger.warning(f"PIL EXIF correction failed: {e}")
            image_file.seek(0)
            image_file.save(save_path)

        # quick face check
        faces = verify_human_face(save_path)
        if len(faces) == 0:
            os.remove(save_path)
            return jsonify({"status": "No face detected", "message": "No face detected. Please upload a clear, full-face photo with good lighting and your face fully visible."}), 400
        face_bbox = [int(faces[0][0]), int(faces[0][1]), int(faces[0][2]), int(faces[0][3])] if len(faces) > 0 else None

        # Ensure the Random Forest model is available
        if RF_MODEL is None:
            os.remove(save_path)
            return jsonify({"status": "Model unavailable", "message": "Skin analysis service is currently unavailable. Please try again later."}), 503

        # ensemble prediction (YOLO detection)
        result = predict_acne_from_image(save_path)
        print("[DEBUG] predict_acne_from_image result:", result)

        if "error" in result:
            if os.path.exists(save_path):
                os.remove(save_path)
            return jsonify({"error": result["error"]}), 500

        # extract results
        severity = result.get("severity", "mild")
        detection_engine = result.get("engine", "unknown")
        if detection_engine == "fallback_color_heuristic":
            current_app.logger.warning(
                "Prediction served by fallback color-heuristic detector, not YOLO — "
                "quality is significantly lower for this request."
            )

        # confidence from ensemble_web_integration is 0-1 – do NOT ×100
        raw_conf = result.get("confidence", 0.0)
        print("[DEBUG] Raw confidence value:", raw_conf, type(raw_conf))
        overall_conf = round(min(max(_safe_float(raw_conf), 0.0), 1.0), 4)

        # filter low-confidence detections
        filtered = [
            {
                "type":       d.get("type", "unknown"),
                "confidence": _safe_float(d.get("confidence", 0.0)),
                "bbox":       d.get("bbox"),
            }
            for d in (result.get("detections") or [])
            if isinstance(d, dict) and _safe_float(d.get("confidence", 0.0)) >= CONF_THRESHOLD
        ]
        count = len(filtered)

        # create annotated image with bounding boxes
        try:
            annotated_filename = f"annotated_{filename}"
            annotated_save_path = os.path.join(upload_folder, annotated_filename)
            img = cv2.imread(save_path)
            if img is not None:
                # ── 1. Green ellipse around the detected face ──────────────────
                if face_bbox:
                    fx, fy, fw, fh = face_bbox
                    cx_f = fx + fw // 2
                    cy_f = fy + fh // 2
                    axes  = (fw // 2, fh // 2)
                    cv2.ellipse(img, (cx_f, cy_f), axes, 0, 0, 360, (0, 255, 0), 3)
                    face_label = "Face"
                    (fw_t, fh_t), _ = cv2.getTextSize(face_label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                    cv2.rectangle(img, (fx, fy - fh_t - 8), (fx + fw_t + 4, fy), (0, 255, 0), -1)
                    cv2.putText(img, face_label, (fx + 2, fy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)

                # ── 2. Red rectangles around each acne lesion ──────────────────
                acne_color = (0, 0, 255)   # BGR red
                for d in filtered:
                    bx1, by1, bx2, by2 = d.get("bbox")
                    x1, y1, x2, y2 = int(bx1), int(by1), int(bx2), int(by2)
                    cv2.rectangle(img, (x1, y1), (x2, y2), acne_color, 2)
                    label = f"{d.get('type', 'Acne')} {round(d.get('confidence', 0.0) * 100)}%"
                    (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(img, (x1, y1 - lh - 6), (x1 + lw + 4, y1), acne_color, -1)
                    cv2.putText(img, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

                os.makedirs(upload_folder, exist_ok=True)
                cv2.imwrite(annotated_save_path, img)
                # URL path served by /uploads/<filename> route
                annotated_rel_path = f"uploads/{annotated_filename}"
            else:
                annotated_rel_path = None
        except Exception as e:
            current_app.logger.warning(f"Failed to create annotated image: {e}")
            annotated_rel_path = None

        # class scores – avg confidence per YOLO class (0-100 %)
        class_sum   = {c: 0.0 for c in YOLO_CLASSES}
        class_count = {c: 0   for c in YOLO_CLASSES}
        for d in filtered:
            t = d["type"]
            if t in class_sum:
                class_sum[t]   += d["confidence"]
                class_count[t] += 1

        class_scores = {
            _display(yc): round((class_sum[yc] / class_count[yc] * 100) if class_count[yc] > 0 else 0.0, 2)
            for yc in YOLO_CLASSES
        }

        # Use YOLO severity as the primary skin condition label
        severity_label_map = {
            "clear": "Clear Skin",
            "mild": "Mild Acne",
            "moderate": "Moderate Acne",
            "severe": "Severe Acne",
        }
        primary_insight = severity_label_map.get(severity, severity.capitalize() + " Acne")
        
        if severity == "clear":
            # If no lesions are found, we are highly confident in the "Clear Skin" diagnosis
            # Defaulting to 95-99% confidence instead of 0% acne probability
            overall_conf = 0.98
            
        primary_conf = round(overall_conf, 4)

        # Use RF model to recommend routine from tabular features (must match training schema)
        # Training columns (after dropping 'routine'): lesion_count, avg_confidence,
        # location_cluster, skin_type (encoded), patient_id, device_temp
        # le_target classes: ['advanced', 'basic', 'premium']  (indices 0, 1, 2)
        # le_skin classes:   ['combination'=0, 'dry'=1, 'normal'=2, 'oily'=3, 'sensitive'=4]
        try:
            if RF_MODEL is None:
                raise RuntimeError("Random Forest model not loaded")
            skin_type_enc_map = {"combination": 0, "dry": 1, "normal": 2, "oily": 3, "sensitive": 4}
            skin_enc = float(skin_type_enc_map.get(str(skin_type).lower(), 0))
            avg_conf = overall_conf                 # avg_confidence (0-1)
            location_cluster = 0.0                  # no cluster info at inference
            patient_id_val = float(current_user.id) # proxy for patient_id
            device_temp = 22.0                       # neutral default
            tabular_features = np.array([[
                float(count),     # lesion_count
                avg_conf,         # avg_confidence
                location_cluster, # location_cluster
                skin_enc,         # skin_type (encoded)
                patient_id_val,   # patient_id
                device_temp,      # device_temp
            ]])
            rf_pred_raw = RF_MODEL.predict(tabular_features)[0]
            rf_class_idx = int(rf_pred_raw)
            # Map le_target encoding: 0=advanced, 1=basic, 2=premium
            routine_class_map = {0: "advanced", 1: "basic", 2: "premium"}
            routine_class = routine_class_map.get(rf_class_idx, "basic")
        except Exception as e:
            current_app.logger.warning(f"Random Forest routine prediction failed: {e}; falling back to severity-based routing")
            routine_class = "advanced" if severity in ["moderate", "severe"] else "basic"

        # Severity can override the RF's tier for clear skin only.
        # Mild acne is allowed to follow the RF's predicted routine class.
        if severity == "clear":
            routine_class = "basic"
            rf_prediction_label = "Basic"
        else:
            rf_prediction_label = {
                "basic": "Basic Routine",
                "advanced": "Active Treatment",
                "premium": "Premium Treatment",
            }[routine_class]

        # Kept for any existing client code that still reads the old binary field
        rf_prediction = 0 if routine_class == "basic" else 1

        # Generate all three routine tiers
        basic_routine = get_enhanced_basic_routine(age, skin_type, severity, class_scores)
        advanced_routine = get_enhanced_active_routine(age, skin_type, severity, class_scores)
        premium_routine = get_enhanced_premium_routine(age, skin_type, severity, class_scores)

        # Use the RF/severity-selected tier as the main routine
        routine_data = {
            "basic": basic_routine,
            "advanced": advanced_routine,
            "premium": premium_routine,
        }[routine_class]

        # persist
        # Store as "uploads/filename" — served by the /uploads/<filename> route
        rel_path = f"uploads/{filename}"
        Prediction.create(
            user_id=current_user.id,
            image_path=rel_path,
            acne_type=primary_insight,
            confidence=overall_conf,
            severity=count,
        )
        routine_text = "\n\n".join(
            f"{k.capitalize()}:\n" + "\n".join(v)
            for k, v in (routine_data or {}).items() if v
        )
        Routine.create(
            user_id=current_user.id,
            acne_type=primary_insight,
            age=age,
            skin_type=skin_type,
            steps=routine_text,
        )

        return jsonify({
            "status": primary_insight,
            "primary_insight": primary_insight,
            "primary_confidence": primary_conf,
            "confidence": f"{round(primary_conf * 100, 1)}%",
            "class_scores": class_scores,
            "detections": filtered,
            "count": count,
            "severity": severity,
            "routine": routine_data,
            "basic_routine": basic_routine,
            "advanced_routine": advanced_routine,
            "premium_routine": premium_routine,
            "routine_class": routine_class,
            "image_path": rel_path,
            "annotated_image": annotated_rel_path,
            "model": {"name": YOLO_MODEL, "weights": YOLO_WEIGHTS, "classes": YOLO_CLASSES},
            "random_forest_prediction": rf_prediction_label,
            "random_forest_prediction_raw": rf_prediction,
            "clear_skin_threshold": CONF_THRESHOLD,
            "detection_engine": detection_engine,
            "face_bbox": face_bbox
        })

    except Exception:
        current_app.logger.exception("Unhandled error in /api/predict")
        return jsonify({"error": "Server error.", "detail": traceback.format_exc()}), 500