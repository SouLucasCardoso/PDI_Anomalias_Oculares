#!/usr/bin/env python3
"""Avalia reconhecimento por embeddings DINOv3 em condições de recorte UBIPr."""

from __future__ import annotations

import argparse
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
from transformers import AutoImageProcessor, AutoModel

from treinar_segmentacao_ubipr import MulticlassUNet, Sample, UBIPrDataset, decode_mask


MODEL_ID = "facebook/dinov3-vitl16-pretrain-lvd1689m"
CNN_DIR = Path("outputs/cnn/ubipr_multiclasse_30ep_batch32")
OUTPUT_DIR = Path("outputs/modelos_modernos/dinov3_vitl16_ubipr")
CONDITIONS = ("imagem_inteira", "recorte_referencia", "recorte_unet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnn-dir", type=Path, default=CNN_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=6)
    parser.add_argument("--limit-subjects", type=int, default=None, help="Pessoas por partição no smoke test; não usar cientificamente.")
    return parser.parse_args()


def masked_crop(image: Image.Image, mask: np.ndarray, margin: float = 0.25) -> Image.Image:
    """Aplica a máscara e recorta sua caixa envolvente com margem proporcional."""
    rgb = np.asarray(image.convert("RGB"))
    if not mask.any():
        return Image.fromarray(np.zeros_like(rgb))
    ys, xs = np.where(mask)
    height, width = mask.shape
    pad_x = max(2, round((xs.max() - xs.min() + 1) * margin))
    pad_y = max(2, round((ys.max() - ys.min() + 1) * margin))
    x0, x1 = max(0, xs.min() - pad_x), min(width, xs.max() + pad_x + 1)
    y0, y1 = max(0, ys.min() - pad_y), min(height, ys.max() + pad_y + 1)
    cut = rgb.copy()
    cut[~mask] = 0
    return Image.fromarray(cut[y0:y1, x0:x1])


def eer(genuine: np.ndarray, impostor: np.ndarray) -> tuple[float, float]:
    """Retorna EER e limiar aproximados percorrendo todos os escores observados."""
    thresholds = np.unique(np.concatenate((genuine, impostor)))
    fnr = np.asarray([(genuine < threshold).mean() for threshold in thresholds])
    fpr = np.asarray([(impostor >= threshold).mean() for threshold in thresholds])
    index = int(np.argmin(np.abs(fnr - fpr)))
    return float((fnr[index] + fpr[index]) / 2), float(thresholds[index])


def threshold_for_far(impostor: np.ndarray, far: float) -> float:
    return float(np.quantile(impostor, 1.0 - far, method="higher"))


def score_embeddings(embeddings: np.ndarray, samples: list[Sample], thresholds: dict[str, float] | None = None) -> tuple[dict[str, float], dict[str, float]]:
    gallery_subjects = sorted({sample.subject for sample in samples if sample.session == 1})
    gallery = []
    usable_subjects = []
    for subject in gallery_subjects:
        positions = [i for i, sample in enumerate(samples) if sample.subject == subject and sample.session == 1]
        if positions and any(sample.subject == subject and sample.session == 2 for sample in samples):
            centroid = embeddings[positions].mean(axis=0)
            centroid /= max(float(np.linalg.norm(centroid)), 1e-12)
            gallery.append(centroid); usable_subjects.append(subject)
    gallery_matrix = np.stack(gallery)
    query_positions = [i for i, sample in enumerate(samples) if sample.session == 2 and sample.subject in usable_subjects]
    similarities = embeddings[query_positions] @ gallery_matrix.T
    labels = np.asarray([usable_subjects.index(samples[i].subject) for i in query_positions])
    genuine = similarities[np.arange(len(labels)), labels]
    impostor_mask = np.ones_like(similarities, dtype=bool)
    impostor_mask[np.arange(len(labels)), labels] = False
    impostor = similarities[impostor_mask]
    measured_eer, measured_threshold = eer(genuine, impostor)
    if thresholds is None:
        thresholds = {"far_1_percent": threshold_for_far(impostor, 0.01), "far_0_1_percent": threshold_for_far(impostor, 0.001)}
    result = {
        "subjects": len(usable_subjects), "queries": len(query_positions),
        "top1_accuracy": float((similarities.argmax(axis=1) == labels).mean()),
        "eer": measured_eer, "eer_threshold_descriptive": measured_threshold,
        "genuine_similarity_mean": float(genuine.mean()), "impostor_similarity_mean": float(impostor.mean()),
        "tar_at_far_1_percent": float((genuine >= thresholds["far_1_percent"]).mean()),
        "tar_at_far_0_1_percent": float((genuine >= thresholds["far_0_1_percent"]).mean()),
    }
    return result, thresholds


def predict_unet_masks(samples: list[Sample], cnn_dir: Path, device: torch.device) -> list[np.ndarray]:
    dataset = UBIPrDataset(samples, 240, 320, False)
    checkpoint = torch.load(cnn_dir / "melhor_modelo.pt", map_location=device, weights_only=True)
    model = MulticlassUNet(8).to(device); model.load_state_dict(checkpoint["model"]); model.eval()
    masks = []
    with torch.inference_mode():
        for position in range(len(dataset)):
            image_tensor, _ = dataset[position]
            masks.append((model(image_tensor[None].to(device)).argmax(1)[0].cpu().numpy() == 1))
    del model
    if device.type == "cuda": torch.cuda.empty_cache()
    return masks


def extract_embeddings(samples: list[Sample], unet_masks: list[np.ndarray], processor, model, device: torch.device, batch_size: int) -> dict[str, np.ndarray]:
    vectors = {condition: [] for condition in CONDITIONS}
    pending_images, pending_conditions = [], []

    def flush() -> None:
        if not pending_images: return
        inputs = processor(images=pending_images, return_tensors="pt").to(device)
        with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            output = model(**inputs)
            features = output.pooler_output if output.pooler_output is not None else output.last_hidden_state[:, 0]
        features = torch.nn.functional.normalize(features.float(), dim=1).cpu().numpy()
        if not np.isfinite(features).all():
            raise FloatingPointError("DINOv3 produziu embedding não finito; reduza o lote ou use float32.")
        for condition, feature in zip(pending_conditions, features): vectors[condition].append(feature)
        pending_images.clear(); pending_conditions.clear()

    for index, (sample, predicted_small) in enumerate(zip(samples, unet_masks), 1):
        image = Image.open(sample.image).convert("RGB")
        native = Image.open(sample.mask).convert("L")
        reference = decode_mask(native) == 1
        predicted = np.asarray(Image.fromarray(predicted_small).resize(image.size, Image.Resampling.NEAREST), dtype=bool)
        variants = {"imagem_inteira": image, "recorte_referencia": masked_crop(image, reference), "recorte_unet": masked_crop(image, predicted)}
        for condition in CONDITIONS:
            pending_images.append(variants[condition]); pending_conditions.append(condition)
            if len(pending_images) >= batch_size: flush()
        if index % 100 == 0: print(f"embeddings: {index}/{len(samples)}")
    flush()
    return {condition: np.stack(rows) for condition, rows in vectors.items()}


def save_chart(results: dict[str, dict[str, float]], destination: Path) -> None:
    labels = ["Imagem inteira", "Referência", "U-Net"]
    top1 = [100 * results[c]["top1_accuracy"] for c in CONDITIONS]
    tar = [100 * results[c]["tar_at_far_1_percent"] for c in CONDITIONS]
    eer_values = [100 * results[c]["eer"] for c in CONDITIONS]
    x = np.arange(len(labels)); width = 0.24
    fig, axis = plt.subplots(figsize=(10, 5.5))
    axis.bar(x - width, top1, width, label="Top-1 ↑")
    axis.bar(x, tar, width, label="TAR @ FAR 1% ↑")
    axis.bar(x + width, eer_values, width, label="EER ↓")
    axis.set_ylabel("Percentual (%)"); axis.set_xticks(x, labels); axis.set_ylim(0, 100)
    axis.set_title("DINOv3 ViT-L/16 — reconhecimento entre sessões do UBIPr")
    axis.legend(); axis.grid(axis="y", alpha=0.25)
    for container in axis.containers: axis.bar_label(container, fmt="%.1f", padding=2, fontsize=8)
    fig.tight_layout(); fig.savefig(destination, dpi=180); plt.close(fig)


def main() -> None:
    args = parse_args(); device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    manifest = json.loads((args.cnn_dir / "manifesto.json").read_text(encoding="utf-8"))
    splits = {name: [Sample(**row) for row in manifest[name]] for name in ("val", "test")}
    original_counts = {name: len(rows) for name, rows in splits.items()}
    common_subjects = {
        name: sorted({row.subject for row in rows if {item.session for item in rows if item.subject == row.subject} == {1, 2}})
        for name, rows in splits.items()
    }
    splits = {name: [row for row in rows if row.subject in common_subjects[name]] for name, rows in splits.items()}
    if args.limit_subjects is not None:
        limited = {}
        for name, rows in splits.items():
            subjects = common_subjects[name][:args.limit_subjects]
            limited[name] = [row for row in rows if row.subject in subjects]
        splits = limited
        print("AVISO: limite de desenvolvimento ativo; resultado não é científico.")
    all_samples = splits["val"] + splits["test"]
    unet_masks = predict_unet_masks(all_samples, args.cnn_dir, device)
    print(f"Carregando {MODEL_ID}...")
    processor = AutoImageProcessor.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.bfloat16 if device.type == "cuda" else torch.float32).to(device).eval()
    embeddings = extract_embeddings(all_samples, unet_masks, processor, model, device, args.batch_size)
    val_count = len(splits["val"]); validation, test, selected_thresholds = {}, {}, {}
    for condition in CONDITIONS:
        validation[condition], thresholds = score_embeddings(embeddings[condition][:val_count], splits["val"])
        test[condition], _ = score_embeddings(embeddings[condition][val_count:], splits["test"], thresholds)
        selected_thresholds[condition] = thresholds
    report = {"dataset": "UBIPr Single Eyes Segmented Version", "model": MODEL_ID,
              "protocol": "session 1 gallery centroid; session 2 queries; FAR thresholds selected only on validation subjects",
              "eligible_subjects_with_both_sessions": {name: len(subjects) for name, subjects in common_subjects.items()},
              "original_split_images": original_counts,
              "device": str(device), "development_limit_subjects": args.limit_subjects,
              "validation": validation, "selected_thresholds": selected_thresholds, "test": test,
              "interpretation_limit": "Reconhecimento de identidade na base biométrica UBIPr; não mede diagnóstico de alterações oculares."}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metricas.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    save_chart(test, args.output_dir / "comparacao_reconhecimento.png")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
