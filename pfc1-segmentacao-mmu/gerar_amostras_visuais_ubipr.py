#!/usr/bin/env python3
"""Gera uma prancha honesta de amostras visuais do teste UBIPr."""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import torch
from torch.utils.data import DataLoader

from avaliar_sam2_ubipr import automatic_geometry, load_iris, predict_from_embeddings
from avaliar_sam2_mmu import encode_image
from treinar_segmentacao_ubipr import MulticlassUNet, Sample, UBIPrDataset

CNN_DIR = Path("outputs/cnn/ubipr_multiclasse_30ep_batch32")
SAM_DIR = Path("outputs/modelos_modernos/sam2_1_hiera_tiny_ubipr")
OUTPUT = Path("outputs/amostras_visuais_ubipr.png")


def dice(prediction, truth):
    intersection = int((prediction & truth).sum())
    return 2*intersection/max(int(prediction.sum())+int(truth.sum()), 1)


def infer_cnn_scores(model, samples, device):
    dataset = UBIPrDataset(samples, 240, 320, False)
    loader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=4)
    scores = []
    with torch.inference_mode():
        for images, masks in loader:
            predictions = model(images.to(device)).argmax(1).cpu() == 1
            truths = masks == 1
            scores.extend(dice(p.numpy(), t.numpy()) for p, t in zip(predictions, truths))
    return scores


def choose_examples(cnn_scores, sam_scores, samples):
    valid = [i for i, sample in enumerate(samples) if load_iris(sample.mask).any()]
    by_combined = sorted(valid, key=lambda i: (cnn_scores[i]+sam_scores[i])/2)
    choices = [
        (by_combined[0], "pior resultado conjunto"),
        (min(valid, key=lambda i: cnn_scores[i]), "pior U-Net"),
        (min(valid, key=lambda i: sam_scores[i]), "pior SAM"),
        (max(valid, key=lambda i: cnn_scores[i]-sam_scores[i]), "maior vantagem U-Net"),
        (by_combined[len(by_combined)//2], "caso mediano"),
        (by_combined[-1], "melhor resultado conjunto"),
    ]
    result, seen = [], set()
    for index, label in choices:
        if index not in seen:
            result.append((index, label)); seen.add(index)
    return result


def overlay(image, mask, color):
    result = image.astype(np.float32).copy()
    tint = np.zeros_like(result); tint[..., :] = color
    result[mask] = 0.55*result[mask]+0.45*tint[mask]
    return np.clip(result, 0, 255).astype(np.uint8)


def main():
    manifest = json.loads((CNN_DIR/"manifesto.json").read_text(encoding="utf-8"))
    samples = [Sample(**record) for record in manifest["test"]]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(CNN_DIR/"melhor_modelo.pt", map_location=device, weights_only=True)
    cnn = MulticlassUNet(8).to(device); cnn.load_state_dict(checkpoint["model"]); cnn.eval()
    cnn_scores = infer_cnn_scores(cnn, samples, device)
    with (SAM_DIR/"metricas_teste_por_imagem.csv").open(encoding="utf-8") as stream:
        sam_rows = list(csv.DictReader(stream))
    sam_scores = [float(row["dice"]) for row in sam_rows]
    chosen = choose_examples(cnn_scores, sam_scores, samples)

    summary = json.loads((SAM_DIR/"metricas.json").read_text(encoding="utf-8"))
    from transformers import Sam2Model, Sam2Processor
    cache = Path("data/modelos/huggingface/hub")
    processor = Sam2Processor.from_pretrained(summary["model"], revision=summary["revision"], cache_dir=cache, local_files_only=True)
    sam = Sam2Model.from_pretrained(summary["model"], revision=summary["revision"], cache_dir=cache, local_files_only=True).to(device).eval()

    figure, axes = plt.subplots(len(chosen), 5, figsize=(18, 3.4*len(chosen)), constrained_layout=True)
    titles = ("Imagem original", "Referência manual", "Small U-Net", "SAM 2.1 zero-shot", "Recortes U-Net | SAM")
    for column, title in enumerate(titles): axes[0, column].set_title(title, fontsize=13, weight="bold")
    records = []
    for row, (index, label) in enumerate(chosen):
        sample = samples[index]
        with Image.open(sample.image) as source: image = source.convert("RGB")
        image_array = np.asarray(image)
        truth = load_iris(sample.mask)
        dataset = UBIPrDataset([sample], 240, 320, False)
        tensor, _ = dataset[0]
        with torch.inference_mode(): prediction_small = cnn(tensor.unsqueeze(0).to(device)).argmax(1)[0].cpu().numpy() == 1
        prediction_cnn = np.asarray(Image.fromarray(prediction_small).resize(image.size, Image.Resampling.NEAREST), dtype=bool)
        embeddings, original_sizes = encode_image(sam, processor, image, device)
        geometry = automatic_geometry({"image": sample.image}, image.size, summary["calibration"])
        prediction_sam, _, _ = predict_from_embeddings(sam, processor, embeddings, original_sizes, geometry, summary["selected_variant"], device)
        crop_cnn = image_array*prediction_cnn[..., None]
        crop_sam = image_array*prediction_sam[..., None]
        combined_crop = np.concatenate((crop_cnn, crop_sam), axis=1)
        panels = (image_array, overlay(image_array, truth, (0,255,0)), overlay(image_array, prediction_cnn, (0,160,255)), overlay(image_array, prediction_sam, (255,80,40)), combined_crop)
        for column, panel in enumerate(panels):
            axes[row, column].imshow(panel); axes[row, column].axis("off")
        axes[row, 0].set_ylabel(f"{label}\nC{sample.subject} S{sample.session} I{sample.index} {sample.side}\nU-Net={cnn_scores[index]:.3f} | SAM={sam_scores[index]:.3f}", fontsize=10)
        records.append({"category": label, "subject": sample.subject, "session": sample.session, "index": sample.index, "side": sample.side, "unet_dice": cnn_scores[index], "sam_dice": sam_scores[index]})
    figure.suptitle("UBIPr — amostras reais da partição de teste (verde=referência, azul=U-Net, vermelho=SAM)", fontsize=16, weight="bold")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True); figure.savefig(OUTPUT, dpi=160); plt.close(figure)
    OUTPUT.with_suffix(".json").write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Prancha salva em {OUTPUT.resolve()} com {len(chosen)} casos")


if __name__ == "__main__":
    main()
