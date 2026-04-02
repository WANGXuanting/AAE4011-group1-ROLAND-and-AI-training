#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO Trainer + Exporter

- Trains an Ultralytics YOLO model (e.g., 'yolo12m.pt' or 'yolov11m.pt') on your dataset YAML.
- Clear "Training Settings" and "Augmentation Settings" blocks for quick tweaking.
- Saves best weights (.pt) to runs/detect/train*/weights/best.pt

Requirements:
  pip install ultralytics onnxruntime
  (TensorRT export requires NVIDIA TensorRT installed)

Example:
  python train.py --data datasets/curated_ppe_vehicle/auto.yaml --model best.pt
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any 

try:
    from ultralytics import YOLO
except Exception as e:
    print("Ultralytics not found. Install with: pip install ultralytics")
    raise

# --------------------------
# Training Settings (EDIT ME)
# --------------------------
TRAINING_SETTINGS: Dict[str, Any] = {
    # Core
    "epochs": 150,           # number of training epochs
    "imgsz": 1280,           # training image size (square). Common: 640/960/1280/1408/1536/1920 ()
    "batch": 10,           # batch size (auto if -1[60% vram], 0.8[80% vram] or integer)
    "workers": 18,            # dataloader workers
    "device": "cuda:0",          # e.g., "0", "0,1" or "cpu". None=auto
    "seed": 42,              # reproducibility
    "patience": 100,          # Early stop if no improvement (epochs) 
    "save_period": 0,        # Save checkpoint every N epochs (0=only best/last)
    "project": "runs/detect",   
    "name": "gazebo_car",       # run folder name
    "optimizer": "MuSGD",     # "auto", "SGD","MuSGD", "Adam", "AdamW"
    "rect": False,            # rect mode removes padding, if rect=false: images will be letterboxes
    "amp":True,
    "half":True,
    
    # LR & Regularization
    "lr0": 0.01,             # initial learning rate
    "lrf": 0.0005,             # Final learning rate as a fraction of the initial rate: final epoch rate = (lr0 * lrf)
    "momentum": 0.937,       # SGD momentum/Adam beta1
    "weight_decay": 0.0005,  # optimizer weight decay
    "warmup_epochs": 5.0,    # warmup epochs
    "warmup_bias_lr": 0.1,   # warmup bias lr

    # class specific
    "box": 7.5, # weight for bbox in loss function
    "cls": 0.5, # weight for class in loss function

    # Misc
    "dropout":0.25,
    "verbose": True,
    "cache": False,          # cache images for (slightly) faster epochs
    "close_mosaic": 30,      # disable mosaic last N epochs
    "cos_lr": True,         # cosine LR schedule
}

# ------------------------------
# Augmentation Settings (EDIT ME)
# (Ultralytics built-ins; all are per-image probabilities/intensities)
# ------------------------------
AUG_SETTINGS: Dict[str, Any] = {
    # Color space
    "hsv_h": 0,  # image HSV-Hue augmentation (fraction)
    "hsv_s": 0,    # image HSV-Saturation augmentation (fraction)
    "hsv_v": 0,    # image HSV-Value augmentation (fraction)

    # Geometric
    "degrees": 45.0,     # image rotation (+/- deg)
    "translate": 0.2,  # image translation (+/- fraction)
    "scale": 0.3,      # image scale (+/- gain)
    "shear": 0.0,       # image shear (+/- deg)
    "perspective": 0.0002, # perspective (+/- fraction)

    # Flips
    "flipud": 0.0,  # vertical flip prob
    "fliplr": 0.5,  # horizontal flip prob

    # Mosaics (set to 0.0 to disable)
    "mosaic": 1.0,     # mosaic prob (powerful but can be memory-hungry)
    "mixup": 0.25,      #mixup prob
    "cutmix":0.5,
}

# ---------------
# Export Settings
# ---------------
EXPORT_ONNX: Dict[str, Any] = {
    "format": "onnx",
    "dynamic": True,     # dynamic axes (batch, dims)
    "simplify": True,    # run onnx-simplifier
    "opset": 12          # opset version
}
EXPORT_TRT: Dict[str, Any] = {
    "format": "engine",  # TensorRT
    "half": True,        # FP16 if supported
    "dynamic": True,    # dynamic shapes off (safer on Jetsons)
    "workspace": 2       # TensorRT workspace (GB)
}


def train_and_export(
    data_yaml: str,
    model_name: str,
    epochs: int | None = None,
    imgsz: int | None = None,
    batch: int | None = None,
    device: str | None = None,
    export_onnx: bool = False,
    export_trt: bool = False,
) -> None:
    """
    Train a YOLO model on `data_yaml` and optionally export ONNX/TRT.

    data_yaml: path to dataset YAML (your classes.yaml)
    model_name: pretrained weights name/path (e.g. 'yolo12m.pt', 'yolov11m.pt', or path/to/custom.pt)
    """
    # Build overrides from defaults + user tweaks
    overrides = dict(TRAINING_SETTINGS)
    overrides.update(AUG_SETTINGS)

    # Apply CLI overrides (if provided)
    if epochs is not None: overrides["epochs"] = epochs
    if imgsz is not None: overrides["imgsz"] = imgsz
    if batch is not None: overrides["batch"] = batch
    if device is not None: overrides["device"] = device

    # Put required args
    overrides["data"] = str(data_yaml)
    overrides["task"] = "detect"   # ensure detect task

    # Instantiate model (will download if needed)
    print(f"[INFO] Loading model: {model_name}")
    model = YOLO(model_name)

    def save_params_txt(trainer):
        try:
            run_dir = Path(trainer.save_dir)
            run_dir.mkdir(parents=True, exist_ok=True)
            params_txt_path = run_dir / "training_parameters.txt"
            with open(params_txt_path, "w", encoding="utf-8") as f:
                f.write("=== TRAINING SETTINGS ===\n")
                for k in TRAINING_SETTINGS.keys():
                    f.write(f"{k}: {overrides.get(k, TRAINING_SETTINGS[k])}\n")
                
                f.write("\n=== AUGMENTATION SETTINGS ===\n")
                for k in AUG_SETTINGS.keys():
                    f.write(f"{k}: {overrides.get(k, AUG_SETTINGS[k])}\n")
                    
                f.write("\n=== EXTRA INFO ===\n")
                f.write(f"model: {model_name}\n")
                f.write(f"data: {data_yaml}\n")
            print(f"\n[INFO] Training parameters successfully saved to: {params_txt_path}\n")
        except Exception as e:
            print(f"\n[WARN] Failed to save training parameters txt: {e}\n")

    model.add_callback("on_train_start", save_params_txt)

    # Train
    print(f"[INFO] Training with overrides:\n{overrides}\n")
    results = model.train(**overrides)

    # Try to locate best.pt
    best_pt = None
    try:
        # Newer Ultralytics: model.trainer.save_dir points to run dir
        run_dir = Path(model.trainer.save_dir)
        best_pt = run_dir / "weights" / "best.pt"
    except Exception:
        # Fallback: scan default layout
        run_dir = Path(TRAINING_SETTINGS["project"]).joinpath(TRAINING_SETTINGS["name"])
        weights_dir = run_dir / "weights"
        candidates = list(weights_dir.glob("best.pt"))
        if candidates:
            best_pt = candidates[0]

    if best_pt and best_pt.exists():
        print(f"[OK] Best weights: {best_pt}")
    else:
        print("[WARN] Could not locate best.pt automatically. Check runs/ directory.")

    # Reload best for export (safer)
    export_model_path = str(best_pt) if (best_pt and best_pt.exists()) else model_name
    export_model = YOLO(export_model_path)

    # Export ONNX (optional)
    if export_onnx:
        try:
            print("[INFO] Exporting ONNX ...")
            onnx_path = export_model.export(**EXPORT_ONNX)
            print(f"[OK] ONNX exported to: {onnx_path}")
        except Exception as e:
            print(f"[ERROR] ONNX export failed: {e}")

    # Export TensorRT (optional; requires TensorRT installed)
    if export_trt:
        try:
            print("[INFO] Exporting TensorRT (engine) ...")
            engine_path = export_model.export(**EXPORT_TRT)
            print(f"[OK] TensorRT engine exported to: {engine_path}")
        except Exception as e:
            print(f"[ERROR] TensorRT export failed: {e}")

    print("[DONE] Training routine finished.")


def parse_args():
    p = argparse.ArgumentParser(description="YOLO trainer + exporter")
    p.add_argument("--data", type=str, default="dataset/classes.yaml",
                   help="Path to dataset YAML (your classes.yaml)")
    p.add_argument("--model", type=str, default="yolo26n.pt",
                   help="Pretrained model weights (e.g., yolo12m.pt / yolov11m.pt / custom.pt)")
    p.add_argument("--epochs", type=int, default=None, help="Override epochs (default in script)")
    p.add_argument("--imgsz", type=int, default=None, help="Override imgsz (default in script)")
    p.add_argument("--batch", type=int, default=None, help="Override batch size (default in script)")
    p.add_argument("--device", type=str, default=None, help='Override device, e.g. "0", "0,1", "cpu"')
    p.add_argument("--export-onnx", action="store_true", help="Export ONNX after training")
    p.add_argument("--export-trt", action="store_true", help="Export TensorRT engine after training")
    return p.parse_args()


def main():
    args = parse_args()
    train_and_export(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        export_onnx=args.export_onnx,
        export_trt=args.export_trt,
    )


if __name__ == "__main__":
    main()
