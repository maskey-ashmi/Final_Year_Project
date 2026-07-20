#!/usr/bin/env python3
"""
YOLOv8 Acne Detection Training Script - Extended Refinement
Resumes from: best_acne_yolov8s_4class.pt
"""
import torch
import sys
import shutil
from pathlib import Path

# ─────────────────────────────────────────────
#  1. GLOBAL CONFIG & DEPENDENCIES
# ─────────────────────────────────────────────
def check_dependencies():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    print(f"[OK] PyTorch version : {torch.__version__}")
    if torch.cuda.is_available():
        print(f"[OK] GPU detected     : {torch.cuda.get_device_name(0)}")
        print(f"[OK] VRAM             : {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        return '0'
    else:
        print("[WARNING] No GPU found — training will be very slow on CPU!")
        return 'cpu'

# ─────────────────────────────────────────────
#  2. MAIN EXECUTION BLOCK
# ─────────────────────────────────────────────
def main():
    # Setup Paths
    PROJECT_ROOT = Path(__file__).parent
    RUNS_DIR     = PROJECT_ROOT / "runs" / "train"
    MODELS_DIR   = PROJECT_ROOT / "models"
    
    DEVICE = check_dependencies()
    # MODIFIED: Pointing specifically to data-2/data.yaml
    yaml_path = PROJECT_ROOT / "data-2" / "data.yaml"
    
    # ── WEIGHT SELECTION ──
    # Specifically pointing to your previously saved custom weights
    prev_best = MODELS_DIR / 'best_acne_yolov8s_4class.pt'
    
    if prev_best.exists():
        print(f"\n[OK] FOUND CUSTOM WEIGHTS: {prev_best.name}")
        print(f"[INFO] Resuming training from this state...")
        model_to_load = str(prev_best)
    else:
        print(f"\n[WARNING] {prev_best.name} not found in {MODELS_DIR}!")
        print("[INFO] Starting from generic yolov8s.pt instead.")
        model_to_load = 'yolov8s.pt'

    if not yaml_path.exists():
        print(f"[ERROR] data.yaml not found at: {yaml_path}")
        sys.exit(1)

    # Clear cache
    if DEVICE != 'cpu':
        torch.cuda.empty_cache()

    print("\n" + "=" * 55)
    print("  EXTENDED REFINEMENT: 100 EPOCHS")
    print("  Target: Higher mAP for Acne Detection (data-2)")
    print("=" * 55)

    from ultralytics import YOLO
    model = YOLO(model_to_load) 

    try:
        results = model.train(
            data         = str(yaml_path),
            epochs       = 100,        
            imgsz        = 640,
            batch        = 4,           
            device       = DEVICE,
            workers      = 4,           
            
            # ── Optimization ──
            # Using a smaller lr0 (0.001) for fine-tuning existing weights
            lr0          = 0.001,       
            lrf          = 0.01,
            cos_lr       = True,
            amp          = True,        
            
            # ── Regularization & Augmentation ──
            weight_decay = 0.0005,
            augment      = True,
            hsv_s        = 0.9,         
            mosaic       = 1.0,
            mixup        = 0.15,
            
            # ── Output ──
            project      = str(RUNS_DIR),
            name         = 'acne_yolov8s_refinement', 
            exist_ok     = True,
            save         = True,
            patience     = 30,          # Stop if no improvement for 30 epochs
        )

        # ── Update the Best Model ──
        exp_dir = RUNS_DIR / 'acne_yolov8s_refinement'
        new_best_pt = exp_dir / 'weights' / 'best.pt'

        if new_best_pt.exists():
            # Copy new best weights to your central models folder
            MODELS_DIR.mkdir(exist_ok=True)
            shutil.copy(new_best_pt, prev_best)
            print(f"\n[OK] BEST WEIGHTS UPDATED: {prev_best}")

            # ── Final Evaluation ──
            print("\n[INFO] Evaluating refined model on test set...")
            best_model = YOLO(str(prev_best))
            metrics = best_model.val(
                data   = str(yaml_path),
                split  = 'test',
                imgsz  = 640,
                device = DEVICE,
            )

            print("\n" + "=" * 55)
            print("  REFINED TEST RESULTS")
            print("=" * 55)
            print(f"  mAP@0.5      : {metrics.box.map50:.4f}")
            print(f"  mAP@0.5:0.95 : {metrics.box.map:.4f}")
            print("=" * 55)

    except torch.cuda.OutOfMemoryError:
        print("\n[ERROR] GPU out of memory! Lower batch to 2.")
    except Exception as e:
        import traceback
        print(f"\n[ERROR] Training failed: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()
