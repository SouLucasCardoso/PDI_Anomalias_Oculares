#!/usr/bin/env python3
"""Avalia SAM 2.1 Tiny zero-shot na mesma particao UBIPr da Small U-Net."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
import torch

from avaliar_sam2_mmu import (
    MODEL_ID,
    MODEL_REVISION,
    VARIANTS,
    clamp_box,
    compute_metrics,
    inference_context,
    mask_geometry,
    processor_prompt,
)
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnn-output-dir", type=Path, default=Path("outputs/cnn/ubipr_multiclasse_30ep_batch32"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modelos_modernos/sam2_1_hiera_tiny_ubipr"))
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--revision", default=MODEL_REVISION)
    parser.add_argument("--cache-dir", type=Path, default=Path("data/modelos/huggingface/hub"))
    parser.add_argument("--validation-limit", type=int, default=None)
    parser.add_argument("--test-limit", type=int, default=None)
    parser.add_argument("--image-batch-size", type=int, default=8)
    parser.add_argument("--local-files-only", action="store_true")
    return parser.parse_args()


def load_iris(path: str | Path) -> np.ndarray:
    with Image.open(path) as source:
        return np.asarray(source.convert("L"), dtype=np.uint8) == 85


def estimate_center(path: str | Path, maximum_side: int = 320) -> np.ndarray:
    with Image.open(path) as source:
        original_width, original_height = source.size
        scale = min(1.0, maximum_side / max(source.size))
        size = (max(1, round(original_width*scale)), max(1, round(original_height*scale)))
        image = source.convert("L").resize(size, Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(max(1.0, 4.0*scale)))
        array = np.asarray(image, dtype=np.float32)
    height, width = array.shape
    y0, y1 = round(0.28*height), round(0.72*height); x0, x1 = round(0.16*width), round(0.84*width)
    central = array[y0:y1, x0:x1]
    minimum_y, minimum_x = np.unravel_index(np.argmin(central), central.shape)
    center_y, center_x = y0+int(minimum_y), x0+int(minimum_x)
    radius = max(4, round(min(height, width)*0.117))
    py0, py1 = max(0, center_y-radius), min(height, center_y+radius+1); px0, px1 = max(0, center_x-radius), min(width, center_x+radius+1)
    patch = array[py0:py1, px0:px1]; dark_limit = float(np.quantile(patch, 0.35)); weights = np.clip(dark_limit-patch, 0, None)**2
    if float(weights.sum()) > 0:
        grid_y, grid_x = np.indices(patch.shape)
        center_x = float((grid_x*weights).sum()/weights.sum())+px0; center_y = float((grid_y*weights).sum()/weights.sum())+py0
    return np.asarray((center_x/scale, center_y/scale), dtype=np.float32)


def calibrate(samples: list[dict]) -> dict[str, float]:
    values = {"dx": [], "dy": [], "width": [], "height": []}
    for sample in samples:
        truth = load_iris(sample["mask"])
        if not truth.any():
            continue
        height, width = truth.shape
        geometry = mask_geometry(truth)
        center_x, center_y = estimate_center(sample["image"])
        sample["_center"] = [float(center_x), float(center_y)]
        values["dx"].append((geometry["cx"] - center_x) / width)
        values["dy"].append((geometry["cy"] - center_y) / height)
        values["width"].append(geometry["width"] / width)
        values["height"].append(geometry["height"] / height)
    if not values["width"]:
        raise ValueError("A validacao nao contem mascaras de iris nao vazias")
    return {name: float(np.median(numbers)) for name, numbers in values.items()}


def automatic_geometry(sample: dict, image_size: tuple[int, int], calibration: dict[str, float]) -> dict:
    width, height = image_size
    center = sample.get("_center")
    if center is None:
        center = estimate_center(sample["image"])
        sample["_center"] = [float(center[0]), float(center[1])]
    pupil_x, pupil_y = center
    cx = pupil_x + calibration["dx"] * width
    cy = pupil_y + calibration["dy"] * height
    box_width = calibration["width"] * width
    box_height = calibration["height"] * height
    box = clamp_box(cx, cy, box_width * 1.08, box_height * 1.08, width, height)
    points = [[cx - 0.34*box_width, cy], [cx + 0.34*box_width, cy], [cx, cy - 0.34*box_height], [cx, cy + 0.34*box_height]]
    points = [[float(min(max(x, 0), width-1)), float(min(max(y, 0), height-1))] for x, y in points]
    return {"box": box, "ring_points": points, "negative_center": [float(pupil_x), float(pupil_y)]}


@torch.inference_mode()
def predict_from_embeddings(model, processor, image_embeddings, original_sizes, geometry, variant, device):
    prompts = processor_prompt(geometry, variant)
    inputs = processor(original_sizes=original_sizes, return_tensors="pt", **prompts)
    model_inputs = {name: inputs[name].to(device) for name in ("input_boxes", "input_points", "input_labels") if name in inputs}
    if device.type == "cuda": torch.cuda.synchronize()
    started = time.perf_counter()
    with inference_context(device):
        outputs = model(image_embeddings=image_embeddings, multimask_output=True, **model_inputs)
    if device.type == "cuda": torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    masks = processor.post_process_masks(outputs.pred_masks.cpu(), original_sizes.cpu(), binarize=False)[0]
    scores = outputs.iou_scores[0, 0].detach().float().cpu()
    selected = int(torch.argmax(scores))
    return masks[0, selected].numpy() > 0.0, float(scores[selected]), elapsed


def evaluate(model, processor, samples: list[dict], variants: list[str], calibration: dict[str, float], device: torch.device, stage: str, image_batch_size: int) -> list[dict]:
    rows = []
    for start in range(0, len(samples), image_batch_size):
        batch = samples[start:start+image_batch_size]
        images, truths, geometries = [], [], []
        for sample in batch:
            with Image.open(sample["image"]) as source:
                image = source.convert("RGB")
            images.append(image)
            truths.append(load_iris(sample["mask"]))
            geometries.append(automatic_geometry(sample, image.size, calibration))
        inputs = processor(images=images, return_tensors="pt")
        with torch.inference_mode(), inference_context(device):
            embeddings = model.get_image_embeddings(inputs["pixel_values"].to(device))
        for variant in variants:
            boxes = [[geometry["box"]] for geometry in geometries]
            prompt_kwargs = {"input_boxes": boxes}
            if variant == "box_negative":
                prompt_kwargs.update({"input_points": [[[geometry["negative_center"]]] for geometry in geometries], "input_labels": [[[0]] for _ in geometries]})
            elif variant == "box_ring_points":
                prompt_kwargs.update({"input_points": [[geometry["ring_points"] + [geometry["negative_center"]]] for geometry in geometries], "input_labels": [[[1, 1, 1, 1, 0]] for _ in geometries]})
            elif variant != "box":
                raise ValueError(f"Variante desconhecida: {variant}")
            prompt_inputs = processor(original_sizes=inputs["original_sizes"], return_tensors="pt", **prompt_kwargs)
            model_inputs = {name: prompt_inputs[name].to(device) for name in ("input_boxes", "input_points", "input_labels") if name in prompt_inputs}
            if device.type == "cuda": torch.cuda.synchronize()
            decoder_started = time.perf_counter()
            with torch.inference_mode(), inference_context(device):
                outputs = model(image_embeddings=embeddings, multimask_output=True, **model_inputs)
            if device.type == "cuda": torch.cuda.synchronize()
            elapsed = (time.perf_counter() - decoder_started) / len(batch)
            masks_by_image = processor.post_process_masks(outputs.pred_masks.cpu(), inputs["original_sizes"].cpu(), binarize=False)
            scores = outputs.iou_scores[:, 0].detach().float().cpu()
            for offset, (sample, truth) in enumerate(zip(batch, truths)):
                selected = int(torch.argmax(scores[offset]))
                prediction = masks_by_image[offset][0, selected].numpy() > 0.0
                predicted_iou = float(scores[offset, selected])
                metrics = compute_metrics(prediction, truth)
                rows.append({"subject": sample["subject"], "session": sample["session"], "side": sample["side"], "index": sample["index"], "variant": variant, **metrics, "sam_predicted_iou": predicted_iou, "decoder_seconds": elapsed})
        number = min(start + image_batch_size, len(samples))
        if number % 40 == 0 or number == len(samples):
            print(f"{stage}: {number}/{len(samples)}", flush=True)
    return rows


def summarize(rows: list[dict]) -> dict:
    fields = ("dice", "iou", "aproveitamento_percentual", "pureza_percentual", "contaminacao_percentual", "razao_area_prevista_referencia")
    return {field: {"mean": float(np.mean([r[field] for r in rows])), "std": float(np.std([r[field] for r in rows]))} for field in fields}


def save_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)


def balanced_limit(samples: list[dict], limit: int | None) -> list[dict]:
    if limit is None or limit >= len(samples):
        return samples
    by_subject: dict[int, list[dict]] = {}
    for sample in samples:
        by_subject.setdefault(int(sample["subject"]), []).append(sample)
    selected = []
    depth = 0
    while len(selected) < limit:
        added = False
        for subject in sorted(by_subject):
            if depth < len(by_subject[subject]):
                selected.append(by_subject[subject][depth]); added = True
                if len(selected) == limit:
                    break
        if not added:
            break
        depth += 1
    return selected


def main() -> None:
    args = parse_args()
    with (args.cnn_output_dir/"manifesto.json").open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    validation = balanced_limit(manifest["val"], args.validation_limit)
    test = balanced_limit(manifest["test"], args.test_limit)
    calibration = calibrate(validation)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from transformers import Sam2Model, Sam2Processor
    processor = Sam2Processor.from_pretrained(args.model_id, revision=args.revision, cache_dir=args.cache_dir, local_files_only=args.local_files_only)
    model = Sam2Model.from_pretrained(args.model_id, revision=args.revision, cache_dir=args.cache_dir, local_files_only=args.local_files_only).to(device).eval()
    started = time.time()
    validation_rows = evaluate(model, processor, validation, list(VARIANTS), calibration, device, "validacao", args.image_batch_size)
    validation_by_variant = {variant: summarize([row for row in validation_rows if row["variant"] == variant]) for variant in VARIANTS}
    selected = max(VARIANTS, key=lambda variant: validation_by_variant[variant]["dice"]["mean"])
    print(f"Prompt selecionado exclusivamente na validacao: {selected}", flush=True)
    test_rows = evaluate(model, processor, test, [selected], calibration, device, "teste", args.image_batch_size)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_csv(args.output_dir/"metricas_validacao_por_imagem.csv", validation_rows)
    save_csv(args.output_dir/"metricas_teste_por_imagem.csv", test_rows)
    status = "completo" if args.validation_limit is None and args.test_limit is None else ("validacao_amostrada_teste_completo" if args.test_limit is None else "limitado")
    result = {"status": status, "dataset": "UBIPr Single Eyes Segmented Version", "target": "iris (native value 85)", "model": args.model_id, "revision": args.revision, "mode": "zero-shot; no fine-tuning", "device": str(device), "image_batch_size": args.image_batch_size, "validation_sampling": "round-robin by subject", "validation_images": len(validation), "test_images": len(test), "calibration": calibration, "validation": validation_by_variant, "selected_variant": selected, "test": summarize(test_rows), "elapsed_seconds": time.time()-started, "comparison_warning": "Comparacao com a U-Net usa a mesma particao e alvo iris, mas o SAM permanece zero-shot."}
    (args.output_dir/"metricas.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
