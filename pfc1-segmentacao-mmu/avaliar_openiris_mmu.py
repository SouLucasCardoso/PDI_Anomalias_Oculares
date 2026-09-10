#!/usr/bin/env python3
"""Avalia o segmentador semantico publico OpenIRIS no protocolo MMU local.

O modelo gera quatro mapas (globo ocular, iris, pupila e cilios). Limiar e
composicao da mascara sao escolhidos apenas na validacao. Como o model card
informa que MMU fez parte do treinamento original, o resultado e descritivo e
nao uma estimativa independente de generalizacao.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import time
from typing import Any

import numpy as np
from PIL import Image

from avaliar_sam2_mmu import (
    aggregate,
    compute_metrics,
    load_truth,
    save_crop,
    useful_selection_score,
)


REPO_ID = "Worldcoin/iris-semantic-segmentation"
MODEL_REVISION = "e6c8fbb8e2e7e024a58818530a6e3ae5c005f47a"
MODEL_FILE = "iris_semseg_upp_scse_mobilenetv2.onnx"
VARIANTS = ("iris_only", "iris_minus_pupil", "usable_iris")
MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark OpenIRIS no MMU.")
    parser.add_argument(
        "--cnn-output-dir",
        type=Path,
        default=Path("outputs/cnn/pareamento_corrigido_50ep"),
    )
    parser.add_argument(
        "--sam-output-dir",
        type=Path,
        default=Path("outputs/modelos_modernos/sam2_1_hiera_tiny"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/modelos_modernos/openiris"),
    )
    parser.add_argument("--repo-id", default=REPO_ID)
    parser.add_argument("--revision", default=MODEL_REVISION)
    parser.add_argument("--model-file", default=MODEL_FILE)
    parser.add_argument(
        "--thresholds", nargs="+", type=float, default=[0.3, 0.5, 0.7]
    )
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=list(VARIANTS))
    parser.add_argument("--validation-limit", type=int, default=None)
    parser.add_argument("--test-limit", type=int, default=None)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--no-save-recortes", action="store_true")
    return parser.parse_args()


def preprocess(image: Image.Image) -> np.ndarray:
    resized = image.convert("RGB").resize((640, 480), Image.Resampling.BILINEAR)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    normalized = (array - MEAN) / STD
    return normalized.transpose(2, 0, 1)[None].astype(np.float32)


def resize_probabilities(probabilities: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return np.stack(
        [
            np.asarray(
                Image.fromarray(channel.astype(np.float32)).resize(
                    size, Image.Resampling.BILINEAR
                ),
                dtype=np.float32,
            )
            for channel in probabilities
        ]
    )


def compose_mask(probabilities: np.ndarray, threshold: float, variant: str) -> np.ndarray:
    iris = probabilities[1] >= threshold
    if variant == "iris_only":
        return iris
    without_pupil = iris & ~(probabilities[2] >= threshold)
    if variant == "iris_minus_pupil":
        return without_pupil
    if variant == "usable_iris":
        return without_pupil & ~(probabilities[3] >= threshold)
    raise ValueError(f"Variante desconhecida: {variant}")


def sample_identity(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject": int(sample["subject"]),
        "side": sample["side"],
        "image_index": int(sample["index"]),
        "mask_index": int(sample["mask_index"]),
    }


def run_model(session, image: Image.Image) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    output = session.run(None, {session.get_inputs()[0].name: preprocess(image)})[0][0]
    elapsed = time.perf_counter() - start
    return resize_probabilities(output, image.size), elapsed


def evaluate_validation(
    session,
    samples: list[dict[str, Any]],
    variants: list[str],
    thresholds: list[float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, sample in enumerate(samples, 1):
        with Image.open(sample["image"]) as source:
            image = source.convert("RGB")
        truth = load_truth(sample["mask"])
        probabilities, elapsed = run_model(session, image)
        for variant in variants:
            for threshold in thresholds:
                prediction = compose_mask(probabilities, threshold, variant)
                row = sample_identity(sample)
                row.update({"variant": variant, "threshold": threshold})
                row.update(compute_metrics(prediction, truth))
                row["inference_seconds"] = elapsed
                rows.append(row)
        print(f"Validacao OpenIRIS: {number:3d}/{len(samples)}")
    return rows


def select_configuration(
    rows: list[dict[str, Any]], variants: list[str], thresholds: list[float]
) -> tuple[dict[str, Any], dict[str, Any]]:
    summaries: dict[str, Any] = {}
    candidates: list[tuple[float, str, float]] = []
    for variant in variants:
        summaries[variant] = {}
        for threshold in thresholds:
            group = [
                row for row in rows
                if row["variant"] == variant and row["threshold"] == threshold
            ]
            result = aggregate(group)
            result["indice_selecao_util"] = useful_selection_score(result)
            summaries[variant][str(threshold)] = result
            candidates.append((result["indice_selecao_util"], variant, threshold))
    _, variant, threshold = max(candidates)
    return {"variant": variant, "threshold": threshold}, summaries


def artifact_name(sample: dict[str, Any]) -> str:
    return (
        f"s{int(sample['subject']):02d}_{sample['side']}_"
        f"img{int(sample['index'])}_mask{int(sample['mask_index'])}"
    )


def evaluate_test(
    session,
    samples: list[dict[str, Any]],
    selected: dict[str, Any],
    output_dir: Path,
    save_recortes: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for number, sample in enumerate(samples, 1):
        with Image.open(sample["image"]) as source:
            image = source.convert("RGB")
        truth = load_truth(sample["mask"])
        probabilities, elapsed = run_model(session, image)
        prediction = compose_mask(
            probabilities, float(selected["threshold"]), selected["variant"]
        )
        row = sample_identity(sample)
        row.update(selected)
        row.update(compute_metrics(prediction, truth))
        row["inference_seconds"] = elapsed
        rows.append(row)
        if save_recortes:
            save_crop(image, prediction, output_dir / "recortes_teste", artifact_name(sample))
        records.append(
            {
                "sample": sample,
                "image": np.asarray(image, dtype=np.uint8),
                "truth": truth,
                "prediction": prediction,
                "pupil": probabilities[2] >= float(selected["threshold"]),
                "eyelashes": probabilities[3] >= float(selected["threshold"]),
            }
        )
        print(f"Teste OpenIRIS:     {number:3d}/{len(samples)}")
    return rows, records


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_examples(records: list[dict[str, Any]], rows: list[dict[str, Any]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ordered = sorted(enumerate(rows), key=lambda pair: float(pair[1]["dice"]))
    chosen = [ordered[i][0] for i in np.linspace(0, len(ordered) - 1, 6, dtype=int)]
    fig, axes = plt.subplots(len(chosen), 6, figsize=(15, 2.35 * len(chosen)))
    for row_index, record_index in enumerate(chosen):
        record = records[record_index]
        row = rows[record_index]
        image = record["image"]
        prediction = record["prediction"]
        panels = (
            image,
            record["truth"],
            prediction,
            image * prediction[:, :, None],
            record["pupil"],
            record["eyelashes"],
        )
        titles = (
            f"Imagem: pessoa {row['subject']}",
            "Mascara real",
            f"OpenIRIS (Dice={row['dice']:.3f})",
            "Recorte aplicado",
            "Pupila OpenIRIS",
            "Cilios OpenIRIS",
        )
        for column, (panel, title) in enumerate(zip(panels, titles, strict=True)):
            axes[row_index, column].imshow(panel, cmap="gray" if panel.ndim == 2 else None)
            axes[row_index, column].set_title(title, fontsize=8)
            axes[row_index, column].axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def mean_comparison_from_sam(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    automatic = data["test"]["automatic"]
    pupil = automatic["preenchimento_pupila_percentual"]
    return {
        "dice": automatic["dice"]["mean"],
        "iou": automatic["iou"]["mean"],
        "aproveitamento": automatic["aproveitamento_percentual"]["mean"],
        "pureza": automatic["pureza_percentual"]["mean"],
        "contaminacao": automatic["contaminacao_percentual"]["mean"],
        "pupila": None if pupil is None else pupil["mean"],
    }


def mean_comparison_from_cnn(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    metrics = data["test_detailed"]["metrics"]
    return {
        "dice": metrics["dice"]["mean"],
        "iou": metrics["iou"]["mean"],
        "aproveitamento": 100.0 * metrics["recall"]["mean"],
        "pureza": 100.0 * metrics["precision"]["mean"],
        "contaminacao": 100.0 * (1.0 - metrics["precision"]["mean"]),
        "pupila": 100.0 * data["test_detailed"]["pupil_fill_fraction"]["mean"],
    }


def save_report(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Comparação de segmentação no MMU",
        "",
        "| Método | Dice | IoU | Aproveitamento | Pureza | Contaminação | Pupila preenchida | Índice útil |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in summary["comparison"].items():
        pupil = "—" if values["pupila"] is None else f"{values['pupila']:.2f}%"
        useful = values["dice"] * (
            1.0 if values["pupila"] is None else 1.0 - values["pupila"] / 100.0
        )
        lines.append(
            f"| {name} | {values['dice']:.4f} | {values['iou']:.4f} | "
            f"{values['aproveitamento']:.2f}% | {values['pureza']:.2f}% | "
            f"{values['contaminacao']:.2f}% | {pupil} | {useful:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Advertência metodológica",
            "",
            "O model card do OpenIRIS declara o MMU entre as bases usadas no treinamento. "
            "Não é possível garantir que as 70 imagens locais de teste sejam inéditas para "
            "o modelo. Portanto, o resultado OpenIRIS nesta base é uma verificação técnica "
            "e não deve ser apresentado como estimativa independente de generalização.",
            "",
            "O SAM 2.1 automático foi executado zero-shot. O prompt que preserva melhor a "
            "abertura pupilar perde Dice e aproveitamento em relação à CNN, mas melhora "
            "pureza, contaminação e preenchimento da pupila. Não há superioridade absoluta.",
            "",
            "Aproveitamento corresponde à revocação da máscara. Ele deve sempre ser "
            "apresentado junto de pureza, contaminação e preenchimento da pupila.",
            "O índice útil é `Dice × (1 − preenchimento da pupila)` e foi usado somente "
            "para selecionar limiar e composição na validação.",
            "",
            "Fontes: [SAM 2](https://github.com/facebookresearch/sam2) e "
            "[OpenIRIS model card](https://github.com/worldcoin/open-iris/blob/main/SEMSEG_MODEL_CARD.md).",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if any(not 0.0 < threshold < 1.0 for threshold in args.thresholds):
        raise ValueError("Todos os limiares devem estar entre zero e um")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.cnn_output_dir / "manifesto.json"
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    validation_samples = manifest["split"]["val"]["samples"][: args.validation_limit]
    test_samples = manifest["split"]["test"]["samples"][: args.test_limit]

    import onnxruntime as ort
    from huggingface_hub import hf_hub_download

    model_path = hf_hub_download(
        args.repo_id,
        args.model_file,
        revision=args.revision,
        local_files_only=args.local_files_only,
    )
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    start = time.perf_counter()
    validation_rows = evaluate_validation(
        session, validation_samples, args.variants, args.thresholds
    )
    selected, validation_summary = select_configuration(
        validation_rows, args.variants, args.thresholds
    )
    print(f"Configuracao escolhida na validacao: {selected}")
    test_rows, records = evaluate_test(
        session, test_samples, selected, args.output_dir, not args.no_save_recortes
    )
    test_summary = aggregate(test_rows)

    comparison: dict[str, Any] = {}
    cnn = mean_comparison_from_cnn(args.cnn_output_dir / "metricas.json")
    sam = mean_comparison_from_sam(args.sam_output_dir / "metricas.json")
    if cnn is not None:
        comparison["CNN Small U-Net"] = cnn
    if sam is not None:
        comparison["SAM 2.1 automático (zero-shot)"] = sam
    pupil = test_summary["preenchimento_pupila_percentual"]
    comparison["OpenIRIS pré-treinado"] = {
        "dice": test_summary["dice"]["mean"],
        "iou": test_summary["iou"]["mean"],
        "aproveitamento": test_summary["aproveitamento_percentual"]["mean"],
        "pureza": test_summary["pureza_percentual"]["mean"],
        "contaminacao": test_summary["contaminacao_percentual"]["mean"],
        "pupila": None if pupil is None else pupil["mean"],
    }
    complete = args.validation_limit is None and args.test_limit is None
    summary = {
        "status": "benchmark_completo" if complete else "execucao_limitada_nao_comparavel",
        "dataset": "MMU Iris Database + mascaras manuais",
        "model": args.repo_id,
        "model_revision": args.revision,
        "model_file": args.model_file,
        "classes": {"0": "eyeball", "1": "iris", "2": "pupil", "3": "eyelashes"},
        "dataset_overlap_warning": (
            "O model card declara MMU no treinamento; possivel sobreposicao com este teste."
        ),
        "validation_image_count": len(validation_samples),
        "test_image_count": len(test_samples),
        "selected_configuration": selected,
        "validation": validation_summary,
        "test": test_summary,
        "comparison": comparison,
        "elapsed_seconds": time.perf_counter() - start,
    }
    write_csv(args.output_dir / "metricas_validacao_por_imagem.csv", validation_rows)
    write_csv(args.output_dir / "metricas_teste_por_imagem.csv", test_rows)
    with (args.output_dir / "metricas.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    save_examples(records, test_rows, args.output_dir / "exemplos_openiris_teste.png")
    save_report(summary, args.output_dir / "RELATORIO_COMPARATIVO_GERAL.md")
    print(f"Benchmark OpenIRIS concluido: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
