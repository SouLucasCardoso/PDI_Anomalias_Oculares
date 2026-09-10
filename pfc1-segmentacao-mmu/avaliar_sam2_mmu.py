#!/usr/bin/env python3
"""Avalia o SAM 2.1 no mesmo protocolo por pessoa usado pela CNN.

O programa calibra um prompt geometrico automatico apenas na validacao, escolhe
a variante de prompt pelo Dice de validacao e consulta o teste uma unica vez.
Tambem executa um protocolo ``oracle_bbox``: a caixa vem da mascara real e serve
somente como limite superior assistido, nao como pipeline autonomo.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import csv
import json
from pathlib import Path
import time
from typing import Any

import numpy as np
from PIL import Image
import torch

from treinar_segmentacao_mmu import (
    describe_values,
    enclosed_background,
    estimate_image_iris_center,
)


MODEL_ID = "facebook/sam2.1-hiera-tiny"
MODEL_REVISION = "de431c4043854a71d8101e17995dfe596bf101a5"
VARIANTS = ("box", "box_negative", "box_ring_points")
PROTOCOLS = ("automatic", "oracle_bbox")
METRIC_FIELDS = (
    "dice",
    "iou",
    "aproveitamento_percentual",
    "pureza_percentual",
    "contaminacao_percentual",
    "perda_iris_percentual",
    "razao_area_prevista_referencia",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark do SAM 2.1 Tiny nas imagens MMU."
    )
    parser.add_argument(
        "--cnn-output-dir",
        type=Path,
        default=Path("outputs/cnn/pareamento_corrigido_50ep"),
        help="Execucao oficial da CNN, que fornece manifesto e comparacao.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/modelos_modernos/sam2_1_hiera_tiny"),
    )
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--revision", default=MODEL_REVISION)
    parser.add_argument(
        "--device", choices=("auto", "cuda", "cpu"), default="auto"
    )
    parser.add_argument(
        "--protocols", nargs="+", choices=PROTOCOLS, default=list(PROTOCOLS)
    )
    parser.add_argument(
        "--variants", nargs="+", choices=VARIANTS, default=list(VARIANTS)
    )
    parser.add_argument("--validation-limit", type=int, default=None)
    parser.add_argument("--test-limit", type=int, default=None)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--no-save-recortes", action="store_true")
    return parser.parse_args()


def mask_geometry(mask: np.ndarray) -> dict[str, float]:
    rows, columns = np.where(mask)
    if not len(columns):
        raise ValueError("Mascara de referencia vazia")
    x0, x1 = float(columns.min()), float(columns.max())
    y0, y1 = float(rows.min()), float(rows.max())
    return {
        "cx": (x0 + x1) / 2.0,
        "cy": (y0 + y1) / 2.0,
        "width": x1 - x0 + 1.0,
        "height": y1 - y0 + 1.0,
    }


def clamp_box(
    cx: float, cy: float, width: float, height: float, image_width: int, image_height: int
) -> list[float]:
    x0 = max(0.0, cx - width / 2.0)
    y0 = max(0.0, cy - height / 2.0)
    x1 = min(float(image_width - 1), cx + width / 2.0)
    y1 = min(float(image_height - 1), cy + height / 2.0)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Caixa de prompt degenerada")
    return [float(x0), float(y0), float(x1), float(y1)]


def load_truth(path: str | Path) -> np.ndarray:
    with Image.open(path) as source:
        return np.asarray(source.convert("L"), dtype=np.uint8) > 127


def calibrate_automatic_geometry(samples: list[dict[str, Any]]) -> dict[str, float]:
    """Aprende apenas estatisticas globais da validacao; nao usa o teste."""
    values: dict[str, list[float]] = {
        "center_offset_x_ratio": [],
        "center_offset_y_ratio": [],
        "box_width_ratio": [],
        "box_height_ratio": [],
    }
    for sample in samples:
        truth = load_truth(sample["mask"])
        height, width = truth.shape
        geometry = mask_geometry(truth)
        pupil_x, pupil_y = estimate_image_iris_center(Path(sample["image"]))
        values["center_offset_x_ratio"].append((geometry["cx"] - pupil_x) / width)
        values["center_offset_y_ratio"].append((geometry["cy"] - pupil_y) / height)
        values["box_width_ratio"].append(geometry["width"] / width)
        values["box_height_ratio"].append(geometry["height"] / height)
    return {name: float(np.median(numbers)) for name, numbers in values.items()}


def prompt_geometry(
    sample: dict[str, Any],
    image_size: tuple[int, int],
    truth: np.ndarray,
    protocol: str,
    calibration: dict[str, float],
) -> dict[str, Any]:
    width, height = image_size
    pupil_x, pupil_y = estimate_image_iris_center(Path(sample["image"]))
    if protocol == "automatic":
        cx = float(pupil_x + calibration["center_offset_x_ratio"] * width)
        cy = float(pupil_y + calibration["center_offset_y_ratio"] * height)
        box_width = calibration["box_width_ratio"] * width
        box_height = calibration["box_height_ratio"] * height
    elif protocol == "oracle_bbox":
        geometry = mask_geometry(truth)
        cx, cy = geometry["cx"], geometry["cy"]
        box_width, box_height = geometry["width"], geometry["height"]
    else:
        raise ValueError(f"Protocolo desconhecido: {protocol}")

    # Uma margem pequena evita cortar o limite externo da iris.
    box = clamp_box(cx, cy, box_width * 1.08, box_height * 1.08, width, height)
    ring_points = [
        [cx - 0.34 * box_width, cy],
        [cx + 0.34 * box_width, cy],
        [cx, cy - 0.34 * box_height],
        [cx, cy + 0.34 * box_height],
    ]
    ring_points = [
        [
            float(min(max(x, 0.0), width - 1.0)),
            float(min(max(y, 0.0), height - 1.0)),
        ]
        for x, y in ring_points
    ]
    return {
        "box": box,
        "ring_points": ring_points,
        "negative_center": [float(pupil_x), float(pupil_y)],
    }


def processor_prompt(geometry: dict[str, Any], variant: str) -> dict[str, Any]:
    result: dict[str, Any] = {"input_boxes": [[geometry["box"]]]}
    if variant == "box":
        return result
    if variant == "box_negative":
        points = [geometry["negative_center"]]
        labels = [0]
    elif variant == "box_ring_points":
        points = geometry["ring_points"] + [geometry["negative_center"]]
        labels = [1, 1, 1, 1, 0]
    else:
        raise ValueError(f"Variante desconhecida: {variant}")
    result["input_points"] = [[points]]
    result["input_labels"] = [[labels]]
    return result


def compute_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | None]:
    prediction = prediction.astype(bool)
    truth = truth.astype(bool)
    true_positive = int((prediction & truth).sum())
    false_positive = int((prediction & ~truth).sum())
    false_negative = int((~prediction & truth).sum())
    union = true_positive + false_positive + false_negative
    predicted_area = true_positive + false_positive
    reference_area = true_positive + false_negative
    dice = (2.0 * true_positive) / max(2 * true_positive + false_positive + false_negative, 1)
    precision = true_positive / max(predicted_area, 1)
    recall = true_positive / max(reference_area, 1)
    pupil = enclosed_background(truth)
    pupil_fill = None
    if int(pupil.sum()) >= 30:
        pupil_fill = 100.0 * float(prediction[pupil].mean())
    return {
        "dice": dice,
        "iou": true_positive / max(union, 1),
        "aproveitamento_percentual": 100.0 * recall,
        "pureza_percentual": 100.0 * precision,
        "contaminacao_percentual": 100.0 * (1.0 - precision),
        "perda_iris_percentual": 100.0 * (1.0 - recall),
        "razao_area_prevista_referencia": predicted_area / max(reference_area, 1),
        "preenchimento_pupila_percentual": pupil_fill,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = {
        name: describe_values([float(row[name]) for row in rows])
        for name in METRIC_FIELDS
    }
    pupil_values = [
        float(row["preenchimento_pupila_percentual"])
        for row in rows
        if row["preenchimento_pupila_percentual"] is not None
    ]
    result["preenchimento_pupila_percentual"] = (
        describe_values(pupil_values) if pupil_values else None
    )
    if "sam_predicted_iou" in rows[0]:
        result["sam_predicted_iou"] = describe_values(
            [float(row["sam_predicted_iou"]) for row in rows]
        )
    return result


def useful_selection_score(metrics: dict[str, Any]) -> float:
    """Penaliza a selecao de discos que apagam a abertura pupilar."""
    pupil = metrics["preenchimento_pupila_percentual"]
    pupil_factor = 1.0 if pupil is None else 1.0 - pupil["mean"] / 100.0
    return float(metrics["dice"]["mean"] * pupil_factor)


def inference_context(device: torch.device):
    if device.type == "cuda":
        return torch.autocast("cuda", dtype=torch.float16)
    return nullcontext()


@torch.inference_mode()
def encode_image(model, processor, image: Image.Image, device: torch.device):
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)
    with inference_context(device):
        embeddings = model.get_image_embeddings(pixel_values)
    return embeddings, inputs["original_sizes"]


@torch.inference_mode()
def predict_mask(
    model,
    processor,
    image: Image.Image,
    image_embeddings,
    original_sizes: torch.Tensor,
    geometry: dict[str, Any],
    variant: str,
    device: torch.device,
) -> tuple[np.ndarray, float, float]:
    kwargs = processor_prompt(geometry, variant)
    inputs = processor(images=image, return_tensors="pt", **kwargs)
    model_inputs = {
        name: inputs[name].to(device)
        for name in ("input_boxes", "input_points", "input_labels")
        if name in inputs
    }
    if device.type == "cuda":
        torch.cuda.synchronize()
    start = time.perf_counter()
    with inference_context(device):
        outputs = model(
            image_embeddings=image_embeddings,
            multimask_output=True,
            **model_inputs,
        )
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    masks = processor.post_process_masks(
        outputs.pred_masks.cpu(), original_sizes.cpu(), binarize=False
    )[0]
    scores = outputs.iou_scores[0, 0].detach().float().cpu()
    selected = int(torch.argmax(scores))
    prediction = masks[0, selected].numpy() > 0.0
    return prediction, float(scores[selected]), elapsed


def base_row(sample: dict[str, Any], protocol: str, variant: str) -> dict[str, Any]:
    return {
        "subject": int(sample["subject"]),
        "side": sample["side"],
        "image_index": int(sample["index"]),
        "mask_index": int(sample["mask_index"]),
        "protocol": protocol,
        "variant": variant,
    }


def evaluate_validation(
    model,
    processor,
    samples: list[dict[str, Any]],
    protocols: list[str],
    variants: list[str],
    calibration: dict[str, float],
    device: torch.device,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, sample in enumerate(samples, 1):
        with Image.open(sample["image"]) as source:
            image = source.convert("RGB")
        truth = load_truth(sample["mask"])
        embeddings, original_sizes = encode_image(model, processor, image, device)
        for protocol in protocols:
            geometry = prompt_geometry(sample, image.size, truth, protocol, calibration)
            for variant in variants:
                prediction, score, elapsed = predict_mask(
                    model, processor, image, embeddings, original_sizes,
                    geometry, variant, device,
                )
                row = base_row(sample, protocol, variant)
                row.update(compute_metrics(prediction, truth))
                row["sam_predicted_iou"] = score
                row["prompt_decoder_seconds"] = elapsed
                rows.append(row)
        print(f"Validacao SAM 2.1: {number:3d}/{len(samples)}")
    return rows


def select_variants(
    rows: list[dict[str, Any]], protocols: list[str], variants: list[str]
) -> tuple[dict[str, str], dict[str, Any]]:
    selected: dict[str, str] = {}
    summaries: dict[str, Any] = {}
    for protocol in protocols:
        summaries[protocol] = {}
        for variant in variants:
            group = [
                row for row in rows
                if row["protocol"] == protocol and row["variant"] == variant
            ]
            summaries[protocol][variant] = aggregate(group)
            summaries[protocol][variant]["indice_selecao_util"] = useful_selection_score(
                summaries[protocol][variant]
            )
        selected[protocol] = max(
            variants,
            key=lambda variant: summaries[protocol][variant]["indice_selecao_util"],
        )
    return selected, summaries


def artifact_name(sample: dict[str, Any]) -> str:
    return (
        f"s{int(sample['subject']):02d}_{sample['side']}_"
        f"img{int(sample['index'])}_mask{int(sample['mask_index'])}"
    )


def save_crop(image: Image.Image, prediction: np.ndarray, directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    image_array = np.asarray(image, dtype=np.uint8)
    crop = image_array * prediction[:, :, None].astype(np.uint8)
    Image.fromarray(prediction.astype(np.uint8) * 255).save(directory / f"{name}_mascara.png")
    Image.fromarray(crop).save(directory / f"{name}_recorte.png")


def evaluate_test(
    model,
    processor,
    samples: list[dict[str, Any]],
    selected: dict[str, str],
    calibration: dict[str, float],
    device: torch.device,
    output_dir: Path,
    save_recortes: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    visual_records: list[dict[str, Any]] = []
    for number, sample in enumerate(samples, 1):
        with Image.open(sample["image"]) as source:
            image = source.convert("RGB")
        truth = load_truth(sample["mask"])
        embeddings, original_sizes = encode_image(model, processor, image, device)
        predictions: dict[str, np.ndarray] = {}
        for protocol, variant in selected.items():
            geometry = prompt_geometry(sample, image.size, truth, protocol, calibration)
            prediction, score, elapsed = predict_mask(
                model, processor, image, embeddings, original_sizes,
                geometry, variant, device,
            )
            predictions[protocol] = prediction
            row = base_row(sample, protocol, variant)
            row.update(compute_metrics(prediction, truth))
            row["sam_predicted_iou"] = score
            row["prompt_decoder_seconds"] = elapsed
            rows.append(row)
            if save_recortes:
                save_crop(
                    image,
                    prediction,
                    output_dir / "recortes_teste" / protocol,
                    artifact_name(sample),
                )
        visual_records.append(
            {
                "sample": sample,
                "image": np.asarray(image, dtype=np.uint8),
                "truth": truth,
                "predictions": predictions,
            }
        )
        print(f"Teste SAM 2.1:     {number:3d}/{len(samples)}")
    return rows, visual_records


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_examples(records: list[dict[str, Any]], rows: list[dict[str, Any]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    automatic_rows = {
        (row["subject"], row["side"], row["image_index"]): row
        for row in rows if row["protocol"] == "automatic"
    }
    score_pairs = []
    for index, record in enumerate(records):
        sample = record["sample"]
        key = (int(sample["subject"]), sample["side"], int(sample["index"]))
        score = automatic_rows.get(key, {"dice": 0.0})["dice"]
        score_pairs.append((float(score), index))
    score_pairs.sort()
    chosen = [score_pairs[i][1] for i in np.linspace(0, len(score_pairs) - 1, 6, dtype=int)]
    fig, axes = plt.subplots(len(chosen), 6, figsize=(15, 2.35 * len(chosen)))
    for row_index, record_index in enumerate(chosen):
        record = records[record_index]
        sample = record["sample"]
        image = record["image"]
        truth = record["truth"]
        automatic = record["predictions"].get("automatic", np.zeros_like(truth))
        oracle = record["predictions"].get("oracle_bbox", np.zeros_like(truth))
        key = (int(sample["subject"]), sample["side"], int(sample["index"]))
        auto_dice = automatic_rows.get(key, {"dice": float("nan")})["dice"]
        panels = (
            image,
            truth,
            automatic,
            image * automatic[:, :, None],
            oracle,
            image * oracle[:, :, None],
        )
        titles = (
            f"Imagem: pessoa {sample['subject']}",
            "Mascara real",
            f"SAM automatico (Dice={auto_dice:.3f})",
            "Recorte automatico",
            "SAM com caixa real",
            "Recorte assistido",
        )
        for column, (panel, title) in enumerate(zip(panels, titles, strict=True)):
            axes[row_index, column].imshow(panel, cmap="gray" if panel.ndim == 2 else None)
            axes[row_index, column].set_title(title, fontsize=8)
            axes[row_index, column].axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def cnn_comparison(cnn_output_dir: Path) -> dict[str, Any] | None:
    metrics_path = cnn_output_dir / "metricas.json"
    if not metrics_path.exists():
        return None
    with metrics_path.open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    detailed = metrics["test_detailed"]["metrics"]
    return {
        "model": metrics["model"],
        "dice_mean": detailed["dice"]["mean"],
        "iou_mean": detailed["iou"]["mean"],
        "aproveitamento_percentual_mean": 100.0 * detailed["recall"]["mean"],
        "pureza_percentual_mean": 100.0 * detailed["precision"]["mean"],
        "contaminacao_percentual_mean": 100.0 * (1.0 - detailed["precision"]["mean"]),
        "preenchimento_pupila_percentual_mean": (
            100.0 * metrics["test_detailed"]["pupil_fill_fraction"]["mean"]
        ),
        "source": str(metrics_path),
    }


def save_report(summary: dict[str, Any], path: Path) -> None:
    comparison = summary["comparison"]
    lines = [
        "# Benchmark inicial: CNN e SAM 2.1 Hiera Tiny",
        "",
        "## Resultado no teste MMU",
        "",
        "| Método | Dice | IoU | Aproveitamento | Pureza | Contaminação | Pupila preenchida | Índice útil |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in comparison.items():
        pupil = values.get("preenchimento_pupila_percentual_mean")
        pupil_text = "—" if pupil is None else f"{pupil:.2f}%"
        useful = values["dice_mean"] * (1.0 if pupil is None else 1.0 - pupil / 100.0)
        lines.append(
            f"| {name} | {values['dice_mean']:.4f} | {values['iou_mean']:.4f} | "
            f"{values['aproveitamento_percentual_mean']:.2f}% | "
            f"{values['pureza_percentual_mean']:.2f}% | "
            f"{values['contaminacao_percentual_mean']:.2f}% | {pupil_text} | {useful:.4f} |"
        )
    lines.extend(
        [
            "",
            "Aproveitamento é a revocação da máscara: porcentagem da íris de referência "
            "preservada. Deve ser interpretado junto com pureza e contaminação.",
            "O índice útil é `Dice × (1 − preenchimento da pupila)` e serve apenas para "
            "selecionar, na validação, máscaras que preservam a abertura pupilar.",
            "",
            "## Protocolo",
            "",
            "- `automatic`: centro estimado exclusivamente pela imagem e geometria global "
            "calibrada na validação; é o resultado utilizável como pipeline.",
            "- `oracle_bbox`: caixa delimitadora obtida da máscara real; é um limite superior "
            "assistido e não constitui segmentação autônoma.",
            "- A variante de prompt foi escolhida pelo índice útil de validação. O conjunto "
            "de teste não foi usado para calibrar geometria ou escolher prompt.",
            "- Para cada prompt, a máscara foi escolhida pela qualidade prevista pelo próprio SAM.",
            "",
            "## Interpretação",
            "",
            "O SAM 2.1 é um modelo de segmentação geral e foi avaliado sem fine-tuning em "
            "íris. Dice e aproveitamento precisam ser interpretados junto do preenchimento "
            "da pupila: encontrar o disco ocular não garante preservar o anel útil. O próximo "
            "experimento deve ajustar o modelo ao domínio ou usar um segmentador multiclasse.",
            "",
            "Referências: [SAM 2 oficial](https://github.com/facebookresearch/sam2) e "
            "[checkpoint oficial](https://huggingface.co/facebook/sam2.1-hiera-tiny).",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.validation_limit is not None and args.validation_limit <= 0:
        raise ValueError("validation-limit deve ser positivo")
    if args.test_limit is not None and args.test_limit <= 0:
        raise ValueError("test-limit deve ser positivo")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.cnn_output_dir / "manifesto.json"
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    validation_samples = manifest["split"]["val"]["samples"][: args.validation_limit]
    test_samples = manifest["split"]["test"]["samples"][: args.test_limit]
    calibration = calibrate_automatic_geometry(validation_samples)

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA solicitada, mas nao esta disponivel")

    from transformers import Sam2Model, Sam2Processor

    print(f"Carregando {args.model_id} em {device}...")
    processor = Sam2Processor.from_pretrained(
        args.model_id, revision=args.revision, local_files_only=args.local_files_only
    )
    model = Sam2Model.from_pretrained(
        args.model_id, revision=args.revision, local_files_only=args.local_files_only
    ).to(device).eval()
    parameter_count = sum(parameter.numel() for parameter in model.parameters())

    start = time.perf_counter()
    validation_rows = evaluate_validation(
        model, processor, validation_samples, args.protocols, args.variants,
        calibration, device,
    )
    selected, validation_summary = select_variants(
        validation_rows, args.protocols, args.variants
    )
    print(f"Prompts selecionados na validacao: {selected}")
    test_rows, visual_records = evaluate_test(
        model, processor, test_samples, selected, calibration, device,
        args.output_dir, not args.no_save_recortes,
    )
    test_summary = {
        protocol: aggregate([row for row in test_rows if row["protocol"] == protocol])
        for protocol in args.protocols
    }
    elapsed = time.perf_counter() - start

    cnn = cnn_comparison(args.cnn_output_dir)
    comparison: dict[str, Any] = {}
    if cnn is not None:
        comparison["CNN Small U-Net"] = cnn
    for protocol in args.protocols:
        metrics = test_summary[protocol]
        label = "SAM 2.1 automático" if protocol == "automatic" else "SAM 2.1 caixa real (assistido)"
        comparison[label] = {
            "dice_mean": metrics["dice"]["mean"],
            "iou_mean": metrics["iou"]["mean"],
            "aproveitamento_percentual_mean": metrics["aproveitamento_percentual"]["mean"],
            "pureza_percentual_mean": metrics["pureza_percentual"]["mean"],
            "contaminacao_percentual_mean": metrics["contaminacao_percentual"]["mean"],
            "preenchimento_pupila_percentual_mean": (
                None if metrics["preenchimento_pupila_percentual"] is None
                else metrics["preenchimento_pupila_percentual"]["mean"]
            ),
        }
    complete_run = args.validation_limit is None and args.test_limit is None
    summary = {
        "status": "benchmark_completo" if complete_run else "execucao_limitada_nao_comparavel",
        "dataset": "MMU Iris Database + mascaras manuais",
        "model": args.model_id,
        "model_revision": args.revision,
        "model_parameters": parameter_count,
        "device": str(device),
        "protocol_notes": {
            "automatic": "Sem uso da mascara da imagem avaliada; geometria calibrada apenas na validacao.",
            "oracle_bbox": "Usa a caixa da mascara real; somente limite superior assistido.",
        },
        "validation_image_count": len(validation_samples),
        "test_image_count": len(test_samples),
        "automatic_geometry_calibration": calibration,
        "selected_prompt_variant": selected,
        "validation": validation_summary,
        "test": test_summary,
        "comparison": comparison,
        "elapsed_seconds": elapsed,
    }
    write_csv(args.output_dir / "metricas_validacao_por_imagem.csv", validation_rows)
    write_csv(args.output_dir / "metricas_teste_por_imagem.csv", test_rows)
    with (args.output_dir / "metricas.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    if visual_records:
        save_examples(
            visual_records, test_rows, args.output_dir / "exemplos_sam2_teste.png"
        )
    save_report(summary, args.output_dir / "RELATORIO_COMPARATIVO.md")
    print(f"Benchmark concluido em {elapsed:.1f}s: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
