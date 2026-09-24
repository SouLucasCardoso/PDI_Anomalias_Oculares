#!/usr/bin/env python3
"""Compara U-Net e SAM no UBIPr com a mesma metrica macro por imagem."""

import csv
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from treinar_segmentacao_ubipr import MulticlassUNet, Sample, UBIPrDataset

CNN_DIR = Path("outputs/cnn/ubipr_multiclasse_30ep_batch32")
SAM_DIR = Path("outputs/modelos_modernos/sam2_1_hiera_tiny_ubipr")
SAM3_DIR = Path("outputs/modelos_modernos/sam3_1_ubipr")
OUTPUT = Path("outputs/comparacao_ubipr.json")


def metric(tp, fp, fn):
    return {
        "dice": 2*tp/max(2*tp+fp+fn, 1),
        "iou": tp/max(tp+fp+fn, 1),
        "recall": tp/max(tp+fn, 1),
        "precision": tp/max(tp+fp, 1),
        "predicted_pixels": tp+fp,
    }


def describe(rows):
    return {name: {"mean": float(np.mean([row[name] for row in rows])), "std": float(np.std([row[name] for row in rows]))} for name in ("dice", "iou", "recall", "precision")}


def main():
    manifest = json.loads((CNN_DIR/"manifesto.json").read_text(encoding="utf-8"))
    sample_dicts = manifest["test"]
    samples = [Sample(**record) for record in sample_dicts]
    dataset = UBIPrDataset(samples, 240, 320, False)
    loader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=4)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(CNN_DIR/"melhor_modelo.pt", map_location=device, weights_only=True)
    model = MulticlassUNet(8).to(device); model.load_state_dict(checkpoint["model"]); model.eval()
    cnn_rows, nonempty_flags = [], []
    with torch.inference_mode():
        for images, masks in loader:
            predicted = model(images.to(device)).argmax(1).cpu() == 1
            truths = masks == 1
            for prediction, truth in zip(predicted.numpy(), truths.numpy()):
                tp = int((prediction & truth).sum()); fp = int((prediction & ~truth).sum()); fn = int((~prediction & truth).sum())
                cnn_rows.append(metric(tp, fp, fn)); nonempty_flags.append(bool(truth.any()))

    with (SAM_DIR/"metricas_teste_por_imagem.csv").open(encoding="utf-8") as stream:
        raw_sam = list(csv.DictReader(stream))
    sam_rows = [{"dice": float(row["dice"]), "iou": float(row["iou"]), "recall": float(row["aproveitamento_percentual"])/100, "precision": float(row["pureza_percentual"])/100, "predicted_pixels_when_empty": float(row["razao_area_prevista_referencia"])} for row in raw_sam]
    if len(sam_rows) != len(cnn_rows):
        raise ValueError("CNN e SAM nao possuem o mesmo numero de imagens de teste")
    nonempty_cnn = [row for row, flag in zip(cnn_rows, nonempty_flags) if flag]
    nonempty_sam = [row for row, flag in zip(sam_rows, nonempty_flags) if flag]
    sam3_rows = None
    if (SAM3_DIR/"metricas_por_imagem.csv").exists():
        with (SAM3_DIR/"metricas_por_imagem.csv").open(encoding="utf-8") as stream:
            raw_sam3 = list(csv.DictReader(stream))
        if len(raw_sam3) != len(cnn_rows):
            raise ValueError("CNN e SAM 3.1 nao possuem o mesmo numero de imagens de teste")
        sam3_rows = [{name: float(row[name]) for name in ("dice", "iou", "recall", "precision")} |
                     {"predicted_nonempty": row["predicted_nonempty"].lower() == "true"} for row in raw_sam3]
    empty_positions = [index for index, flag in enumerate(nonempty_flags) if not flag]
    result = {
        "dataset": "UBIPr Single Eyes Segmented Version",
        "test_images": len(samples),
        "images_with_iris": len(nonempty_cnn),
        "images_without_iris": len(empty_positions),
        "primary_metric": "macro mean over test images with non-empty iris reference",
        "small_unet": describe(nonempty_cnn),
        "sam2_1_tiny_zero_shot": describe(nonempty_sam),
        "empty_reference_analysis": {
            "small_unet_images_with_false_positive_iris": sum(cnn_rows[i]["predicted_pixels"] > 0 for i in empty_positions),
            "sam_images_with_false_positive_iris": sum(sam_rows[i]["predicted_pixels_when_empty"] > 0 for i in empty_positions),
            "note": "Amostras vazias sao relatadas separadamente e nao entram no Dice primario.",
        },
        "interpretation_limit": "SAM e zero-shot; a U-Net foi treinada no UBIPr. Isto mede adaptacao ao dominio, nao superioridade geral de arquitetura.",
    }
    if sam3_rows is not None:
        result["sam3_1_zero_shot_text_prompt"] = describe(
            [row for row, flag in zip(sam3_rows, nonempty_flags) if flag]
        )
        result["empty_reference_analysis"]["sam3_1_images_with_false_positive_iris"] = sum(
            sam3_rows[i]["predicted_nonempty"] for i in empty_positions
        )
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
