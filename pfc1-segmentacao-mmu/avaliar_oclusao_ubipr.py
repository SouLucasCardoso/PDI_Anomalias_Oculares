#!/usr/bin/env python3
"""Mede o limite de segmentacao da iris sob oclusao sintetica controlada.

O ensaio usa somente a particao de teste ja congelada. Barras opacas entram
pelas margens superior e inferior, aproximando oclusoes palpebrais, ate cobrir
uma fracao conhecida dos pixels de iris anotados. A referencia avaliada e a
parte da iris que continua visivel; a cobertura em relacao a iris original e
relatada separadamente.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from treinar_segmentacao_ubipr import MulticlassUNet, Sample, UBIPrDataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=Path("outputs/cnn/ubipr_multiclasse_30ep_batch32"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/robustez_oclusao_ubipr"))
    parser.add_argument("--levels", default="0,10,20,30,40,50,60,70,80,90")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--success-dice", type=float, default=0.70)
    parser.add_argument("--success-rate", type=float, default=0.95)
    parser.add_argument("--limit", type=int, default=None, help="Somente para smoke test; nao usar como resultado cientifico.")
    return parser.parse_args()


def occlusion_rows(iris: np.ndarray, fraction: float, direction: str) -> tuple[np.ndarray, float]:
    """Retorna uma faixa horizontal que cobre aproximadamente a fracao pedida."""
    if direction not in {"top", "bottom"}:
        raise ValueError("direction deve ser 'top' ou 'bottom'")
    if not 0 <= fraction <= 1:
        raise ValueError("fraction deve estar entre 0 e 1")
    occlusion = np.zeros_like(iris, dtype=bool)
    total = int(iris.sum())
    if total == 0 or fraction == 0:
        return occlusion, 0.0
    per_row = iris.sum(axis=1)
    order = range(iris.shape[0]) if direction == "top" else range(iris.shape[0] - 1, -1, -1)
    target = fraction * total
    covered = 0
    boundary = None
    for row in order:
        covered += int(per_row[row])
        boundary = row
        if covered >= target:
            break
    if direction == "top":
        occlusion[: boundary + 1] = True
    else:
        occlusion[boundary:] = True
    return occlusion, float((occlusion & iris).sum() / total)


def binary_metrics(prediction: np.ndarray, visible_truth: np.ndarray, original_truth: np.ndarray) -> dict[str, float]:
    tp = int((prediction & visible_truth).sum())
    fp = int((prediction & ~visible_truth).sum())
    fn = int((~prediction & visible_truth).sum())
    return {
        "dice_visible": 2 * tp / max(2 * tp + fp + fn, 1),
        "iou_visible": tp / max(tp + fp + fn, 1),
        "recall_visible": tp / max(tp + fn, 1),
        "precision_visible": tp / max(tp + fp, 1),
        "iris_original_preserved": tp / max(int(original_truth.sum()), 1),
    }


def summarize(rows: list[dict[str, object]], success_dice: float, success_rate: float) -> dict[str, object]:
    by_level: list[dict[str, object]] = []
    for level in sorted({int(row["target_occlusion_percent"]) for row in rows}):
        selected = [row for row in rows if int(row["target_occlusion_percent"]) == level]
        dice = np.asarray([float(row["dice_visible"]) for row in selected])
        success = float((dice >= success_dice).mean())
        by_level.append({
            "target_occlusion_percent": level,
            "actual_occlusion_percent_mean": float(np.mean([float(row["actual_occlusion_percent"]) for row in selected])),
            "images_directions": len(selected),
            "dice_visible_mean": float(dice.mean()),
            "dice_visible_median": float(np.median(dice)),
            "success_rate_dice_ge_threshold": success,
            "iris_original_preserved_mean": float(np.mean([float(row["iris_original_preserved"]) for row in selected])),
        })
    valid = [row for row in by_level if float(row["success_rate_dice_ge_threshold"]) >= success_rate]
    limiting = max((int(row["target_occlusion_percent"]) for row in valid), default=None)
    direction_limits = {}
    for direction in sorted({str(row["direction"]) for row in rows}):
        direction_rows = [row for row in rows if row["direction"] == direction]
        valid_levels = []
        for level in sorted({int(row["target_occlusion_percent"]) for row in direction_rows}):
            selected = [row for row in direction_rows if int(row["target_occlusion_percent"]) == level]
            rate = np.mean([float(row["dice_visible"]) >= success_dice for row in selected])
            if rate >= success_rate:
                valid_levels.append(level)
        direction_limits[direction] = max(valid_levels, default=None)
    return {
        "operational_definition": f"maior oclusao com pelo menos {success_rate:.0%} dos casos-direcoes atingindo Dice visivel >= {success_dice:.2f}",
        "limiting_occlusion_percent": limiting,
        "minimum_visible_iris_percent": None if limiting is None else 100 - limiting,
        "limiting_occlusion_percent_by_direction": direction_limits,
        "by_level": by_level,
    }


def main() -> None:
    args = parse_args()
    levels = sorted({int(value) for value in args.levels.split(",")})
    if not levels or levels[0] < 0 or levels[-1] > 99:
        raise ValueError("levels deve conter inteiros entre 0 e 99")
    manifest = json.loads((args.model_dir / "manifesto.json").read_text(encoding="utf-8"))
    samples = [Sample(**record) for record in manifest["test"]]
    if args.limit is not None:
        samples = samples[: args.limit]
        print("AVISO: limite de desenvolvimento ativo; resultado nao e cientifico.")
    dataset = UBIPrDataset(samples, 240, 320, False)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.model_dir / "melhor_modelo.pt", map_location=device, weights_only=True)
    model = MulticlassUNet(8).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()

    rows: list[dict[str, object]] = []
    offset = 0
    with torch.inference_mode():
        for images, masks in loader:
            images_np = images.numpy()
            masks_np = masks.numpy()
            for local_index, (image, mask) in enumerate(zip(images_np, masks_np)):
                truth = mask == 1
                if not truth.any():
                    continue
                sample = samples[offset + local_index]
                variants = []
                metadata = []
                for level in levels:
                    for direction in ("top", "bottom"):
                        blocked, actual = occlusion_rows(truth, level / 100, direction)
                        altered = image.copy()
                        altered[:, blocked] = 0.0
                        variants.append(altered)
                        metadata.append((level, direction, blocked, actual))
                predictions = model(torch.from_numpy(np.stack(variants)).to(device)).argmax(1).cpu().numpy() == 1
                for prediction, (level, direction, blocked, actual) in zip(predictions, metadata):
                        visible = truth & ~blocked
                        row = {
                            "subject": sample.subject, "session": sample.session, "index": sample.index, "side": sample.side,
                            "target_occlusion_percent": level, "direction": direction,
                            "actual_occlusion_percent": 100 * actual,
                            **binary_metrics(prediction, visible, truth),
                        }
                        rows.append(row)
            offset += len(images)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "metricas_por_imagem.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "dataset": "UBIPr Single Eyes Segmented Version",
        "split": "test (frozen, subject-disjoint)",
        "model": "Small U-Net multiclasse, checkpoint epoch 25",
        "test_images_with_iris": len({(r["subject"], r["session"], r["index"], r["side"]) for r in rows}),
        "directions": ["top", "bottom"],
        "occluder": "black horizontal band",
        "success_dice_threshold": args.success_dice,
        "required_success_rate": args.success_rate,
        "development_limit": args.limit,
        **summarize(rows, args.success_dice, args.success_rate),
        "interpretation_limit": "Mede robustez da segmentacao a oclusao sintetica, nao desempenho de reconhecimento biometrico nem diagnostico clinico.",
    }
    (args.output_dir / "metricas.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
