from pathlib import Path
import shutil
from ultralytics import YOLO


def main():
    project_root = Path(__file__).parent

    model_path = project_root / "models" / "best_acne_yolov8s_single_class.pt"
    data_yaml = project_root / "dataset" / "data-2" / "data.yaml"

    model = YOLO(str(model_path))

    # Run official YOLO validation
    metrics = model.val(
        data=str(data_yaml),
        split="test",
        imgsz=640,
        batch=8,
        workers=0,      # Windows-safe
        plots=True,     # Generate confusion matrix and curves
        save_json=False,
        verbose=True,
        project=str(project_root / "results"),
        name="evaluation",
        exist_ok=True,
    )

    print("\n===== Evaluation Results =====")
    print(f"Precision      : {metrics.box.mp:.4f}")
    print(f"Recall         : {metrics.box.mr:.4f}")
    print(f"mAP@0.5        : {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95   : {metrics.box.map:.4f}")

    metrics_file = project_root / "results" / "evaluation" / "metrics.txt"

    with open(metrics_file, "w") as f:
        f.write(f"Precision      : {metrics.box.mp:.4f}\n")
        f.write(f"Recall         : {metrics.box.mr:.4f}\n")
        f.write(f"mAP@0.5        : {metrics.box.map50:.4f}\n")
        f.write(f"mAP@0.5:0.95   : {metrics.box.map:.4f}\n")

    print("\nResults saved to:")
    print(project_root / "results" / "evaluation")


if __name__ == "__main__":
    main()
    