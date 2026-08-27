#!/usr/bin/env python3
"""Prova de conceito de segmentacao da iris no MMU.

Baixa as imagens MMU e as mascaras manuais, cria uma divisao sem pessoas
compartilhadas entre treino/validacao/teste, treina uma U-Net pequena e salva
metricas, curvas e exemplos de previsao.

Uso:
    python treinar_segmentacao_mmu.py --epochs 20
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import shutil
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


MMU_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/"
    "naureenmohammad/mmu-iris-dataset"
)
MASKS_URL = (
    "https://github.com/jkozlova/Masks-for-MMU-Iris-dataset/"
    "archive/refs/heads/main.zip"
)


@dataclass(frozen=True)
class Sample:
    image: str
    mask: str
    subject: int
    mask_subject: int
    side: str
    index: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/baseline"))
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--height", type=int, default=120)
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--base-channels", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--threads", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--no-download", action="store_true")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def download(url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    print(f"Baixando {destination.name}...")
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as out:
        shutil.copyfileobj(response, out)
    temporary.replace(destination)


def extract(zip_path: Path, destination: Path) -> None:
    marker = destination / ".extracted"
    if marker.exists():
        return
    destination.mkdir(parents=True, exist_ok=True)
    print(f"Extraindo {zip_path.name}...")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)
    marker.touch()


def find_unique_dir(root: Path, name: str) -> Path:
    candidates = [p for p in root.rglob(name) if p.is_dir()]
    if len(candidates) != 1:
        raise RuntimeError(f"Esperado 1 diretorio '{name}' em {root}; encontrados {candidates}")
    return candidates[0]


def prepare_data(data_dir: Path, allow_download: bool) -> tuple[Path, Path]:
    archives = data_dir / "archives"
    extracted = data_dir / "raw"
    mmu_zip = archives / "mmu-iris-dataset.zip"
    masks_zip = archives / "mmu-masks-main.zip"

    if allow_download:
        download(MMU_URL, mmu_zip)
        download(MASKS_URL, masks_zip)
    elif not (mmu_zip.exists() and masks_zip.exists()):
        raise FileNotFoundError(
            "Arquivos ausentes. Remova --no-download ou coloque os ZIPs em data/archives."
        )

    extract(mmu_zip, extracted / "mmu")
    extract(masks_zip, extracted / "masks")
    image_root = find_unique_dir(extracted / "mmu", "MMU-Iris-Database")
    mask_root = find_unique_dir(extracted / "masks", "mask")
    return image_root, mask_root


def numeric_suffix(path: Path) -> int:
    match = re.search(r"(\d+)$", path.stem)
    if not match:
        raise ValueError(f"Nome sem indice numerico: {path}")
    return int(match.group(1))


def build_manifest(image_root: Path, mask_root: Path) -> list[Sample]:
    image_subjects = sorted(
        (p for p in image_root.iterdir() if p.is_dir() and p.name.isdigit()),
        key=lambda p: int(p.name),
    )
    mask_subjects = sorted(
        (p for p in mask_root.iterdir() if p.is_dir() and p.name.isdigit()),
        key=lambda p: int(p.name),
    )
    if len(image_subjects) != 45 or len(mask_subjects) != 45:
        raise RuntimeError(
            f"Esperados 45 sujeitos; imagens={len(image_subjects)}, mascaras={len(mask_subjects)}"
        )

    # A copia do Kaggle usa pastas 1..46 sem a pasta 4. As mascaras foram
    # renumeradas de forma contigua (1..45). Por isso o pareamento correto e
    # feito pela ordem numerica das pastas, e nao pela igualdade do ID.
    samples: list[Sample] = []
    for image_subject, mask_subject in zip(image_subjects, mask_subjects, strict=True):
        for side in ("left", "right"):
            images = sorted((image_subject / side).glob("*.bmp"), key=numeric_suffix)
            masks = sorted((mask_subject / side).glob("*.bmp"), key=numeric_suffix)
            if len(images) != 5 or len(masks) != 5:
                raise RuntimeError(
                    f"Esperadas 5 imagens: {image_subject.name}/{side} tem {len(images)}; "
                    f"mascara {mask_subject.name}/{side} tem {len(masks)}"
                )
            for image_path, mask_path in zip(images, masks, strict=True):
                image_index = numeric_suffix(image_path)
                mask_index = numeric_suffix(mask_path)
                if image_index != mask_index:
                    raise RuntimeError(f"Indices incompativeis: {image_path} e {mask_path}")
                samples.append(
                    Sample(
                        image=str(image_path.resolve()),
                        mask=str(mask_path.resolve()),
                        subject=int(image_subject.name),
                        mask_subject=int(mask_subject.name),
                        side=side,
                        index=image_index,
                    )
                )
    if len(samples) != 450:
        raise RuntimeError(f"Esperadas 450 amostras; encontradas {len(samples)}")
    return samples


def split_by_subject(samples: list[Sample], seed: int) -> dict[str, list[Sample]]:
    subjects = sorted({sample.subject for sample in samples})
    rng = random.Random(seed)
    rng.shuffle(subjects)
    split_subjects = {
        "train": set(subjects[:32]),
        "val": set(subjects[32:38]),
        "test": set(subjects[38:]),
    }
    splits = {
        name: [sample for sample in samples if sample.subject in ids]
        for name, ids in split_subjects.items()
    }
    if any(split_subjects[a] & split_subjects[b] for a, b in (("train", "val"), ("train", "test"), ("val", "test"))):
        raise AssertionError("Vazamento de sujeitos entre as particoes")
    return splits


class IrisDataset(Dataset):
    def __init__(self, samples: list[Sample], height: int, width: int, augment: bool):
        self.samples = samples
        self.height = height
        self.width = width
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, int]:
        sample = self.samples[index]
        with Image.open(sample.image) as source:
            image = source.convert("L")
        with Image.open(sample.mask) as source:
            mask = source.convert("L")

        if self.augment:
            if random.random() < 0.5:
                image = ImageOps.mirror(image)
                mask = ImageOps.mirror(mask)
            image = ImageEnhance.Brightness(image).enhance(random.uniform(0.9, 1.1))
            image = ImageEnhance.Contrast(image).enhance(random.uniform(0.9, 1.1))

        image = image.resize((self.width, self.height), Image.Resampling.BILINEAR)
        mask = mask.resize((self.width, self.height), Image.Resampling.NEAREST)
        image_array = np.asarray(image, dtype=np.float32) / 255.0
        mask_array = (np.asarray(mask, dtype=np.uint8) > 127).astype(np.float32)
        return (
            torch.from_numpy(image_array).unsqueeze(0),
            torch.from_numpy(mask_array).unsqueeze(0),
            index,
        )


class DoubleConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class SmallUNet(nn.Module):
    def __init__(self, base: int = 16):
        super().__init__()
        self.enc1 = DoubleConv(1, base)
        self.enc2 = DoubleConv(base, base * 2)
        self.enc3 = DoubleConv(base * 2, base * 4)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = DoubleConv(base * 4, base * 8)
        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.dec3 = DoubleConv(base * 8, base * 4)
        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.dec2 = DoubleConv(base * 4, base * 2)
        self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.dec1 = DoubleConv(base * 2, base)
        self.output = nn.Conv2d(base, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        x = self.bottleneck(self.pool(e3))
        x = self.dec3(torch.cat((self.up3(x), e3), dim=1))
        x = self.dec2(torch.cat((self.up2(x), e2), dim=1))
        x = self.dec1(torch.cat((self.up1(x), e1), dim=1))
        return self.output(x)


def dice_loss(logits: torch.Tensor, targets: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    probabilities = torch.sigmoid(logits)
    dims = (1, 2, 3)
    intersection = (probabilities * targets).sum(dims)
    denominator = probabilities.sum(dims) + targets.sum(dims)
    return 1.0 - ((2.0 * intersection + eps) / (denominator + eps)).mean()


def combined_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    return nn.functional.binary_cross_entropy_with_logits(logits, targets) + dice_loss(logits, targets)


@torch.no_grad()
def batch_metrics(logits: torch.Tensor, targets: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    predictions = torch.sigmoid(logits) >= 0.5
    truth = targets >= 0.5
    dims = (1, 2, 3)
    intersection = (predictions & truth).sum(dims).float()
    pred_sum = predictions.sum(dims).float()
    truth_sum = truth.sum(dims).float()
    union = (predictions | truth).sum(dims).float()
    dice = (2.0 * intersection + 1e-6) / (pred_sum + truth_sum + 1e-6)
    iou = (intersection + 1e-6) / (union + 1e-6)
    return dice, iou


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None,
) -> dict[str, float]:
    training = optimizer is not None
    model.train(training)
    totals = {"loss": 0.0, "dice": 0.0, "iou": 0.0, "n": 0}
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for images, masks, _ in loader:
            images = images.to(device)
            masks = masks.to(device)
            if training:
                optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = combined_loss(logits, masks)
            if training:
                loss.backward()
                optimizer.step()
            dice, iou = batch_metrics(logits.detach(), masks)
            batch_size = images.shape[0]
            totals["loss"] += float(loss.detach()) * batch_size
            totals["dice"] += float(dice.sum())
            totals["iou"] += float(iou.sum())
            totals["n"] += batch_size
    return {key: totals[key] / totals["n"] for key in ("loss", "dice", "iou")}


def save_history(history: list[dict[str, float]], output_dir: Path) -> None:
    with (output_dir / "historico.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=history[0].keys())
        writer.writeheader()
        writer.writerows(history)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    epochs = [row["epoch"] for row in history]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(epochs, [row["train_loss"] for row in history], label="Treino")
    axes[0].plot(epochs, [row["val_loss"] for row in history], label="Validacao")
    axes[0].set(title="Perda", xlabel="Epoca", ylabel="BCE + Dice")
    axes[0].legend()
    axes[1].plot(epochs, [row["train_dice"] for row in history], label="Treino")
    axes[1].plot(epochs, [row["val_dice"] for row in history], label="Validacao")
    axes[1].set(title="Coeficiente Dice", xlabel="Epoca", ylabel="Dice", ylim=(0, 1))
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(output_dir / "curvas_treinamento.png", dpi=180)
    plt.close(fig)


@torch.no_grad()
def save_predictions(
    model: nn.Module,
    dataset: IrisDataset,
    samples: list[Sample],
    device: torch.device,
    output_dir: Path,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    chosen = np.linspace(0, len(dataset) - 1, 6, dtype=int)
    fig, axes = plt.subplots(len(chosen), 4, figsize=(10, 2.25 * len(chosen)))
    model.eval()
    for row, dataset_index in enumerate(chosen):
        image, mask, _ = dataset[int(dataset_index)]
        logits = model(image.unsqueeze(0).to(device))
        probability = torch.sigmoid(logits)[0, 0].cpu().numpy()
        prediction = probability >= 0.5
        dice, _ = batch_metrics(logits.cpu(), mask.unsqueeze(0))
        source = samples[int(dataset_index)]
        panels = (image[0].numpy(), mask[0].numpy(), probability, prediction)
        titles = (
            f"Imagem: pessoa {source.subject}",
            "Mascara real",
            "Probabilidade",
            f"Predicao (Dice={float(dice[0]):.3f})",
        )
        for col, (panel, title) in enumerate(zip(panels, titles, strict=True)):
            axes[row, col].imshow(panel, cmap="gray", vmin=0, vmax=1)
            axes[row, col].set_title(title, fontsize=9)
            axes[row, col].axis("off")
    fig.tight_layout()
    fig.savefig(output_dir / "exemplos_teste.png", dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    if args.height % 8 or args.width % 8:
        raise ValueError("Altura e largura devem ser divisiveis por 8")
    torch.set_num_threads(args.threads)
    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    image_root, mask_root = prepare_data(args.data_dir, not args.no_download)
    samples = build_manifest(image_root, mask_root)
    splits = split_by_subject(samples, args.seed)
    for name, records in splits.items():
        subjects = sorted({record.subject for record in records})
        print(f"{name:>5}: {len(records):3d} imagens, {len(subjects):2d} pessoas: {subjects}")

    with (args.output_dir / "manifesto.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "split": {
                    name: {
                        "subjects": sorted({record.subject for record in records}),
                        "samples": [asdict(record) for record in records],
                    }
                    for name, records in splits.items()
                }
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    datasets = {
        name: IrisDataset(records, args.height, args.width, augment=(name == "train"))
        for name, records in splits.items()
    }
    loaders = {
        name: DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=(name == "train"),
            num_workers=args.workers,
            pin_memory=torch.cuda.is_available(),
        )
        for name, dataset in datasets.items()
    }

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SmallUNet(args.base_channels).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    print(f"Dispositivo: {device}; parametros treinaveis: {parameter_count:,}")

    history: list[dict[str, float]] = []
    best_dice = -1.0
    best_epoch = 0
    start = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        train = run_epoch(model, loaders["train"], device, optimizer)
        val = run_epoch(model, loaders["val"], device, None)
        row = {
            "epoch": epoch,
            "train_loss": train["loss"],
            "train_dice": train["dice"],
            "train_iou": train["iou"],
            "val_loss": val["loss"],
            "val_dice": val["dice"],
            "val_iou": val["iou"],
        }
        history.append(row)
        print(
            f"Epoca {epoch:02d}/{args.epochs}: "
            f"loss treino={train['loss']:.4f}, val={val['loss']:.4f}; "
            f"Dice treino={train['dice']:.4f}, val={val['dice']:.4f}"
        )
        if val["dice"] > best_dice:
            best_dice = val["dice"]
            best_epoch = epoch
            torch.save(model.state_dict(), args.output_dir / "melhor_modelo.pt")

    model.load_state_dict(torch.load(args.output_dir / "melhor_modelo.pt", map_location=device, weights_only=True))
    test = run_epoch(model, loaders["test"], device, None)
    elapsed = time.perf_counter() - start
    metrics = {
        "status": "prova_de_conceito",
        "dataset": "MMU Iris Database + mascaras manuais associadas a Ganeeva e Myasnikov (2022)",
        "image_count": len(samples),
        "subject_count": len({sample.subject for sample in samples}),
        "split": {name: len(records) for name, records in splits.items()},
        "split_subjects": {
            name: sorted({record.subject for record in records})
            for name, records in splits.items()
        },
        "model": "Small U-Net",
        "parameters": parameter_count,
        "resolution": [args.height, args.width],
        "seed": args.seed,
        "best_epoch": best_epoch,
        "best_validation_dice": best_dice,
        "test": test,
        "device": str(device),
        "elapsed_seconds": elapsed,
        "caveat": (
            "Base biometrica sem rotulos de doencas; valida apenas a etapa de segmentacao. "
            "O repositorio de mascaras nao declara licenca explicita e a copia do Kaggle "
            "informa licenca Unknown."
        ),
    }
    with (args.output_dir / "metricas.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)
    save_history(history, args.output_dir)
    save_predictions(model, datasets["test"], splits["test"], device, args.output_dir)
    print(
        f"Teste: loss={test['loss']:.4f}; Dice={test['dice']:.4f}; IoU={test['iou']:.4f}. "
        f"Resultados em {args.output_dir.resolve()}"
    )


if __name__ == "__main__":
    main()
