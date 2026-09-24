#!/usr/bin/env python3
"""Avalia o detector de imagem do checkpoint SAM 3.1 no teste congelado UBIPr."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
os.environ.setdefault("HF_HOME", str(ROOT / "data/modelos/huggingface"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import torch
from huggingface_hub import hf_hub_download

from treinar_segmentacao_ubipr import Sample, decode_mask


DEFAULT_MODEL_DIR = Path("outputs/cnn/ubipr_multiclasse_30ep_batch32")
DEFAULT_OUTPUT_DIR = Path("outputs/modelos_modernos/sam3_1_ubipr")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prompt", default="iris of the eye")
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--limit", type=int, default=None, help="Smoke test; não usar como resultado científico.")
    return parser.parse_args()


def collapse_masks(masks: object, shape: tuple[int, int]) -> np.ndarray:
    """Combina todas as instâncias retornadas pelo prompt em uma máscara binária."""
    if isinstance(masks, torch.Tensor):
        values = masks.detach().cpu().numpy()
    else:
        values = np.asarray(masks)
    if values.size == 0:
        return np.zeros(shape, dtype=bool)
    values = np.squeeze(values)
    if values.ndim == 2:
        return values.astype(bool)
    if values.ndim != 3:
        raise ValueError(f"Formato inesperado de máscaras: {values.shape}")
    return values.astype(bool).any(axis=0)


def metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    tp = int((prediction & truth).sum())
    fp = int((prediction & ~truth).sum())
    fn = int((~prediction & truth).sum())
    return {
        "dice": 2 * tp / max(2 * tp + fp + fn, 1),
        "iou": tp / max(tp + fp + fn, 1),
        "recall": tp / max(tp + fn, 1),
        "precision": tp / max(tp + fp, 1),
    }


def overlay(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    result = image.astype(np.float32).copy()
    tint = np.asarray(color, dtype=np.float32)
    result[mask] = 0.55 * result[mask] + 0.45 * tint
    return result.astype(np.uint8)


def save_visual_board(records: list[dict[str, object]], destination: Path) -> None:
    if not records:
        return
    ordered = sorted(records, key=lambda row: float(row["dice"]))
    picks = [ordered[0], ordered[len(ordered) // 2], ordered[-1]]
    fig, axes = plt.subplots(len(picks), 4, figsize=(14, 3.5 * len(picks)), squeeze=False)
    for row_index, row in enumerate(picks):
        image = np.asarray(Image.open(str(row["image"])).convert("RGB"))
        truth = np.asarray(row["truth"], dtype=bool)
        prediction = np.asarray(row["prediction"], dtype=bool)
        cut = image.copy(); cut[~prediction] = 0
        panels = (image, overlay(image, truth, (0, 255, 0)), overlay(image, prediction, (255, 0, 0)), cut)
        titles = ("Original", "Referência (verde)", f"SAM 3.1 (vermelho)\nDice={row['dice']:.3f}", "Recorte real")
        for column, (panel, title) in enumerate(zip(panels, titles)):
            axes[row_index, column].imshow(panel)
            axes[row_index, column].set_title(title)
            axes[row_index, column].axis("off")
    fig.suptitle("UBIPr — SAM 3.1: pior, mediano e melhor caso", fontsize=14)
    fig.tight_layout()
    fig.savefig(destination, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    checkpoint = hf_hub_download("facebook/sam3.1", "sam3.1_multiplex.pt")
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    model = build_sam3_image_model(checkpoint_path=checkpoint, load_from_HF=False, device=device, eval_mode=True)
    processor = Sam3Processor(model, device=device, confidence_threshold=args.confidence)
    manifest = json.loads((args.model_dir / "manifesto.json").read_text(encoding="utf-8"))
    samples = [Sample(**record) for record in manifest["test"]]
    if args.limit is not None:
        samples = samples[: args.limit]
        print("AVISO: limite de desenvolvimento ativo; resultado não é científico.")

    rows: list[dict[str, object]] = []
    visual_records: list[dict[str, object]] = []
    for position, sample in enumerate(samples, 1):
        image = Image.open(sample.image).convert("RGB")
        native_mask = Image.open(sample.mask).convert("L")
        truth = decode_mask(native_mask) == 1
        amp = torch.autocast(device_type="cuda", dtype=torch.bfloat16) if device == "cuda" else nullcontext()
        with amp:
            state = processor.set_image(image)
            output = processor.set_text_prompt(prompt=args.prompt, state=state)
        prediction = collapse_masks(output["masks"], truth.shape)
        row = {"subject": sample.subject, "session": sample.session, "index": sample.index, "side": sample.side,
               "iris_reference_nonempty": bool(truth.any()), "predicted_nonempty": bool(prediction.any()), **metrics(prediction, truth)}
        rows.append(row)
        if truth.any():
            visual_records.append({**row, "image": sample.image, "truth": truth, "prediction": prediction})
        print(f"[{position}/{len(samples)}] C{sample.subject}: Dice={row['dice']:.4f}")

    nonempty = [row for row in rows if row["iris_reference_nonempty"]]
    report = {
        "dataset": "UBIPr Single Eyes Segmented Version", "split": "test (frozen, subject-disjoint)",
        "model": "facebook/sam3.1, detector de imagem extraído do checkpoint multiplex",
        "prompt": args.prompt, "confidence": args.confidence, "device": device, "development_limit": args.limit,
        "images": len(rows), "images_with_iris": len(nonempty),
        "metrics_macro_nonempty": {key: float(np.mean([row[key] for row in nonempty])) for key in ("dice", "iou", "recall", "precision")},
        "empty_references_with_false_positive": sum(row["predicted_nonempty"] for row in rows if not row["iris_reference_nonempty"]),
        "warning": "Zero-shot com prompt textual; comparar como adaptação ao domínio, não como superioridade geral de arquitetura.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "metricas_por_imagem.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    (args.output_dir / "metricas.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    save_visual_board(visual_records, args.output_dir / "amostras_visuais.png")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
