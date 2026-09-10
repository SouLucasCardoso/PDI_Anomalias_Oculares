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
from collections import deque
import csv
import itertools
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
from typing import Callable

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
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
    mask_index: int
    pairing_distance: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/cnn/baseline"))
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--height", type=int, default=120)
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--base-channels", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--threads", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument(
        "--loss",
        choices=("bce_dice", "boundary_tversky"),
        default="bce_dice",
        help="Funcao de perda. boundary_tversky enfatiza contornos e falsos positivos.",
    )
    parser.add_argument("--tversky-alpha", type=float, default=0.70)
    parser.add_argument("--tversky-beta", type=float, default=0.30)
    parser.add_argument("--tversky-gamma", type=float, default=0.75)
    parser.add_argument("--boundary-weight", type=float, default=4.0)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--min-learning-rate", type=float, default=1e-5)
    parser.add_argument(
        "--max-subject-pairing-distance",
        type=float,
        default=None,
        help=(
            "Exclui sujeitos cuja distancia media do pareamento geometrico, "
            "na resolucao original, ultrapasse este valor em pixels."
        ),
    )
    parser.add_argument(
        "--augmentation",
        choices=("light", "strong"),
        default="light",
        help="Aumento forte inclui rotacao, translacao, ruido e desfoque leves.",
    )
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument(
        "--no-test",
        action="store_true",
        help="Treina e seleciona pela validacao sem consultar o conjunto de teste.",
    )
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


def estimate_image_iris_center(path: Path) -> np.ndarray:
    """Estima o centro pupilar para auditar a correspondencia imagem-mascara."""
    with Image.open(path) as source:
        image = source.convert("L").filter(ImageFilter.GaussianBlur(4.0))
        array = np.asarray(image, dtype=np.float32)
    height, width = array.shape
    y0, y1 = round(0.28 * height), round(0.72 * height)
    x0, x1 = round(0.16 * width), round(0.84 * width)
    central = array[y0:y1, x0:x1]
    minimum_y, minimum_x = np.unravel_index(np.argmin(central), central.shape)
    center_y = y0 + int(minimum_y)
    center_x = x0 + int(minimum_x)

    radius = max(12, round(min(height, width) * 0.117))
    patch_y0, patch_y1 = max(0, center_y - radius), min(height, center_y + radius + 1)
    patch_x0, patch_x1 = max(0, center_x - radius), min(width, center_x + radius + 1)
    patch = array[patch_y0:patch_y1, patch_x0:patch_x1]
    dark_limit = float(np.quantile(patch, 0.35))
    weights = np.clip(dark_limit - patch, 0.0, None) ** 2
    if float(weights.sum()) <= 0.0:
        return np.asarray((center_x, center_y), dtype=np.float32)
    grid_y, grid_x = np.indices(patch.shape)
    refined_x = float((grid_x * weights).sum() / weights.sum()) + patch_x0
    refined_y = float((grid_y * weights).sum() / weights.sum()) + patch_y0
    return np.asarray((refined_x, refined_y), dtype=np.float32)


def estimate_mask_iris_center(path: Path) -> np.ndarray:
    with Image.open(path) as source:
        foreground = np.asarray(source.convert("L"), dtype=np.uint8) > 127
    rows, columns = np.where(foreground)
    if len(columns) == 0:
        raise ValueError(f"Mascara vazia: {path}")
    return np.asarray(
        (
            (float(columns.min()) + float(columns.max())) / 2.0,
            (float(rows.min()) + float(rows.max())) / 2.0,
        ),
        dtype=np.float32,
    )


def match_masks_by_geometry(
    images: list[Path], masks: list[Path]
) -> list[tuple[Path, Path, float]]:
    """Associa 5 imagens e 5 mascaras cuja numeracao interna nao e equivalente."""
    if len(images) != len(masks):
        raise ValueError("Quantidades diferentes de imagens e mascaras")
    image_centers = np.stack([estimate_image_iris_center(path) for path in images])
    mask_centers = np.stack([estimate_mask_iris_center(path) for path in masks])
    costs = np.linalg.norm(image_centers[:, None, :] - mask_centers[None, :, :], axis=2)
    permutation = min(
        itertools.permutations(range(len(masks))),
        key=lambda candidate: sum(costs[row, column] for row, column in enumerate(candidate)),
    )
    matches = [
        (image, masks[mask_position], float(costs[image_position, mask_position]))
        for image_position, (image, mask_position) in enumerate(zip(images, permutation))
    ]
    mean_distance = float(np.mean([distance for _, _, distance in matches]))
    if mean_distance > 120.0:
        raise RuntimeError(
            f"Pareamento geometrico suspeito (distancia media={mean_distance:.1f}px): {images[0].parent}"
        )
    return matches


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
    # renumeradas de forma contigua (1..45). Por isso os sujeitos sao associados
    # pela ordem numerica das pastas. Dentro de cada sujeito/lado, a numeracao
    # dos cinco arquivos tambem nao e equivalente: a atribuicao de menor custo
    # entre os centros estimados corrige essa segunda fonte de desalinhamento.
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
            for image_path, mask_path, pairing_distance in match_masks_by_geometry(images, masks):
                image_index = numeric_suffix(image_path)
                mask_index = numeric_suffix(mask_path)
                samples.append(
                    Sample(
                        image=str(image_path.resolve()),
                        mask=str(mask_path.resolve()),
                        subject=int(image_subject.name),
                        mask_subject=int(mask_subject.name),
                        side=side,
                        index=image_index,
                        mask_index=mask_index,
                        pairing_distance=pairing_distance,
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
    def __init__(
        self,
        samples: list[Sample],
        height: int,
        width: int,
        augment: bool,
        augmentation: str = "light",
    ):
        self.samples = samples
        self.height = height
        self.width = width
        self.augment = augment
        self.augmentation = augmentation

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
            if self.augmentation == "strong":
                angle = random.uniform(-6.0, 6.0)
                translation = (
                    round(random.uniform(-0.04, 0.04) * image.width),
                    round(random.uniform(-0.04, 0.04) * image.height),
                )
                fill = int(np.asarray(image, dtype=np.uint8).mean())
                image = image.rotate(
                    angle,
                    resample=Image.Resampling.BILINEAR,
                    translate=translation,
                    fillcolor=fill,
                )
                mask = mask.rotate(
                    angle,
                    resample=Image.Resampling.NEAREST,
                    translate=translation,
                    fillcolor=0,
                )
                image = ImageEnhance.Brightness(image).enhance(random.uniform(0.80, 1.20))
                image = ImageEnhance.Contrast(image).enhance(random.uniform(0.80, 1.20))
                if random.random() < 0.25:
                    image = image.filter(ImageFilter.GaussianBlur(random.uniform(0.2, 0.8)))
            else:
                image = ImageEnhance.Brightness(image).enhance(random.uniform(0.9, 1.1))
                image = ImageEnhance.Contrast(image).enhance(random.uniform(0.9, 1.1))

        image = image.resize((self.width, self.height), Image.Resampling.BILINEAR)
        mask = mask.resize((self.width, self.height), Image.Resampling.NEAREST)
        image_array = np.asarray(image, dtype=np.float32) / 255.0
        if self.augment and self.augmentation == "strong" and random.random() < 0.5:
            noise = np.random.normal(0.0, 0.015, size=image_array.shape).astype(np.float32)
            image_array = np.clip(image_array + noise, 0.0, 1.0)
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


def focal_tversky_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    alpha: float = 0.70,
    beta: float = 0.30,
    gamma: float = 0.75,
    eps: float = 1e-6,
) -> torch.Tensor:
    """Penaliza falsos positivos com mais peso para evitar preencher a pupila."""
    probabilities = torch.sigmoid(logits)
    dims = (1, 2, 3)
    true_positive = (probabilities * targets).sum(dims)
    false_positive = (probabilities * (1.0 - targets)).sum(dims)
    false_negative = ((1.0 - probabilities) * targets).sum(dims)
    index = (true_positive + eps) / (
        true_positive + alpha * false_positive + beta * false_negative + eps
    )
    return ((1.0 - index).clamp_min(0.0) ** gamma).mean()


def boundary_tversky_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    alpha: float = 0.70,
    beta: float = 0.30,
    gamma: float = 0.75,
    boundary_weight: float = 4.0,
) -> torch.Tensor:
    """Combina Tversky focal com BCE ponderada nas bordas externa e pupilar."""
    dilated = nn.functional.max_pool2d(targets, kernel_size=3, stride=1, padding=1)
    eroded = 1.0 - nn.functional.max_pool2d(
        1.0 - targets, kernel_size=3, stride=1, padding=1
    )
    boundary = (dilated - eroded).clamp(0.0, 1.0)
    weights = 1.0 + boundary_weight * boundary
    pixel_bce = nn.functional.binary_cross_entropy_with_logits(
        logits, targets, reduction="none"
    )
    weighted_bce = (pixel_bce * weights).sum() / weights.sum().clamp_min(1.0)
    return weighted_bce + focal_tversky_loss(logits, targets, alpha, beta, gamma)


def make_loss(
    name: str,
    alpha: float = 0.70,
    beta: float = 0.30,
    gamma: float = 0.75,
    boundary_weight: float = 4.0,
) -> Callable[[torch.Tensor, torch.Tensor], torch.Tensor]:
    if name == "bce_dice":
        return combined_loss
    if name == "boundary_tversky":
        return lambda logits, targets: boundary_tversky_loss(
            logits,
            targets,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            boundary_weight=boundary_weight,
        )
    raise ValueError(f"Funcao de perda desconhecida: {name}")


@torch.no_grad()
def batch_metrics(
    logits: torch.Tensor,
    targets: torch.Tensor,
    threshold: float = 0.5,
) -> tuple[torch.Tensor, torch.Tensor]:
    predictions = torch.sigmoid(logits) >= threshold
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
    loss_function: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] = combined_loss,
    threshold: float = 0.5,
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
            loss = loss_function(logits, masks)
            if training:
                loss.backward()
                optimizer.step()
            dice, iou = batch_metrics(logits.detach(), masks, threshold)
            batch_size = images.shape[0]
            totals["loss"] += float(loss.detach()) * batch_size
            totals["dice"] += float(dice.sum())
            totals["iou"] += float(iou.sum())
            totals["n"] += batch_size
    return {key: totals[key] / totals["n"] for key in ("loss", "dice", "iou")}


@torch.no_grad()
def select_threshold(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    minimum: float = 0.20,
    maximum: float = 0.80,
    steps: int = 61,
) -> tuple[float, float]:
    """Seleciona o limiar apenas na validacao, sem consultar o teste."""
    model.eval()
    probabilities: list[torch.Tensor] = []
    truths: list[torch.Tensor] = []
    for images, masks, _ in loader:
        logits = model(images.to(device))
        probabilities.append(torch.sigmoid(logits).cpu())
        truths.append((masks >= 0.5).cpu())
    probability = torch.cat(probabilities)
    truth = torch.cat(truths)
    dims = (1, 2, 3)
    best_threshold = 0.5
    best_dice = -1.0
    for threshold in torch.linspace(minimum, maximum, steps):
        prediction = probability >= float(threshold)
        intersection = (prediction & truth).sum(dims).float()
        dice = (
            (2.0 * intersection + 1e-6)
            / (prediction.sum(dims) + truth.sum(dims) + 1e-6)
        ).mean()
        if float(dice) > best_dice:
            best_threshold = float(threshold)
            best_dice = float(dice)
    return best_threshold, best_dice


def enclosed_background(mask: np.ndarray) -> np.ndarray:
    """Retorna cavidades fechadas no fundo; na mascara da iris, representam a pupila."""
    background = ~mask
    height, width = background.shape
    exterior = np.zeros_like(background, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for column in range(width):
        for row in (0, height - 1):
            if background[row, column] and not exterior[row, column]:
                exterior[row, column] = True
                queue.append((row, column))
    for row in range(height):
        for column in (0, width - 1):
            if background[row, column] and not exterior[row, column]:
                exterior[row, column] = True
                queue.append((row, column))
    while queue:
        row, column = queue.popleft()
        for next_row, next_column in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            if (
                0 <= next_row < height
                and 0 <= next_column < width
                and background[next_row, next_column]
                and not exterior[next_row, next_column]
            ):
                exterior[next_row, next_column] = True
                queue.append((next_row, next_column))
    return background & ~exterior


def describe_values(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "standard_deviation": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        "minimum": float(array.min()),
        "first_quartile": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "third_quartile": float(np.quantile(array, 0.75)),
        "maximum": float(array.max()),
    }


@torch.no_grad()
def detailed_evaluation(
    model: nn.Module,
    dataset: IrisDataset,
    samples: list[Sample],
    device: torch.device,
    threshold: float,
    batch_size: int,
    output_dir: Path,
) -> dict[str, object]:
    model.eval()
    rows: list[dict[str, object]] = []
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    for images, masks, indices in loader:
        probabilities = torch.sigmoid(model(images.to(device))).cpu().numpy()[:, 0]
        truths = masks.numpy()[:, 0] >= 0.5
        predictions = probabilities >= threshold
        for probability, truth, prediction, raw_index in zip(
            probabilities, truths, predictions, indices.tolist(), strict=True
        ):
            sample = samples[int(raw_index)]
            true_positive = int((prediction & truth).sum())
            false_positive = int((prediction & ~truth).sum())
            false_negative = int((~prediction & truth).sum())
            true_negative = int((~prediction & ~truth).sum())
            dice = (2.0 * true_positive) / max(
                2 * true_positive + false_positive + false_negative, 1
            )
            iou = true_positive / max(true_positive + false_positive + false_negative, 1)
            precision = true_positive / max(true_positive + false_positive, 1)
            recall = true_positive / max(true_positive + false_negative, 1)
            specificity = true_negative / max(true_negative + false_positive, 1)
            area_ratio = prediction.sum() / max(truth.sum(), 1)
            pupil = enclosed_background(truth)
            pupil_fill = None
            if int(pupil.sum()) >= 30:
                pupil_fill = float(prediction[pupil].mean())
            rows.append(
                {
                    "subject": sample.subject,
                    "side": sample.side,
                    "image_index": sample.index,
                    "mask_index": sample.mask_index,
                    "pairing_distance_pixels": sample.pairing_distance,
                    "dice": dice,
                    "iou": iou,
                    "precision": precision,
                    "recall": recall,
                    "specificity": specificity,
                    "predicted_to_true_area_ratio": float(area_ratio),
                    "pupil_fill_fraction": pupil_fill,
                    "mean_probability": float(probability.mean()),
                }
            )

    fields = list(rows[0].keys())
    with (output_dir / "metricas_por_imagem.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    metric_names = (
        "dice",
        "iou",
        "precision",
        "recall",
        "specificity",
        "predicted_to_true_area_ratio",
    )
    per_subject = {}
    for subject in sorted({int(row["subject"]) for row in rows}):
        subject_rows = [row for row in rows if row["subject"] == subject]
        per_subject[str(subject)] = {
            name: float(np.mean([float(row[name]) for row in subject_rows]))
            for name in metric_names
        }
    pupil_values = [
        float(row["pupil_fill_fraction"])
        for row in rows
        if row["pupil_fill_fraction"] is not None
    ]
    dice_values = [float(row["dice"]) for row in rows]
    summary: dict[str, object] = {
        "threshold": threshold,
        "image_count": len(rows),
        "metrics": {
            name: describe_values([float(row[name]) for row in rows])
            for name in metric_names
        },
        "dice_counts": {
            "below_0_4": sum(value < 0.4 for value in dice_values),
            "below_0_5": sum(value < 0.5 for value in dice_values),
            "at_least_0_7": sum(value >= 0.7 for value in dice_values),
            "at_least_0_8": sum(value >= 0.8 for value in dice_values),
        },
        "closed_pupil_images": len(pupil_values),
        "pupil_fill_fraction": describe_values(pupil_values) if pupil_values else None,
        "per_subject": per_subject,
    }

    # Sensibilidade de controle de qualidade: preserva a metrica principal com
    # todas as imagens e tambem informa o resultado sem sujeitos cuja anotacao
    # apresenta grande desalinhamento geometrico medio. Esse numero secundario
    # nao deve substituir o teste completo nem ser usado para selecionar modelo.
    quality_cutoff = 45.0
    subject_pairing_distance = {
        subject: float(
            np.mean(
                [
                    sample.pairing_distance
                    for sample in samples
                    if sample.subject == subject
                ]
            )
        )
        for subject in sorted({sample.subject for sample in samples})
    }
    included_subjects = [
        subject
        for subject, distance in subject_pairing_distance.items()
        if distance <= quality_cutoff
    ]
    excluded_subjects = [
        subject
        for subject, distance in subject_pairing_distance.items()
        if distance > quality_cutoff
    ]
    quality_rows = [row for row in rows if int(row["subject"]) in included_subjects]
    quality_dice = [float(row["dice"]) for row in quality_rows]
    summary["pairing_quality_sensitivity"] = {
        "purpose": (
            "Secondary quality-control analysis only; the full test set remains "
            "the primary result."
        ),
        "maximum_subject_mean_distance_pixels": quality_cutoff,
        "included_subjects": included_subjects,
        "excluded_subjects": excluded_subjects,
        "image_count": len(quality_rows),
        "metrics": {
            name: describe_values([float(row[name]) for row in quality_rows])
            for name in metric_names
        },
        "dice_counts": {
            "below_0_4": sum(value < 0.4 for value in quality_dice),
            "below_0_5": sum(value < 0.5 for value in quality_dice),
            "at_least_0_7": sum(value >= 0.7 for value in quality_dice),
            "at_least_0_8": sum(value >= 0.8 for value in quality_dice),
        },
    }
    with (output_dir / "resumo_detalhado.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return summary


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
    threshold: float = 0.5,
    filename: str = "exemplos_teste.png",
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    model.eval()
    scores = []
    for dataset_index in range(len(dataset)):
        image, mask, _ = dataset[dataset_index]
        logits = model(image.unsqueeze(0).to(device))
        dice, _ = batch_metrics(logits.cpu(), mask.unsqueeze(0), threshold)
        scores.append(float(dice[0]))
    order = np.argsort(scores)
    chosen = order[np.linspace(0, len(order) - 1, 6, dtype=int)]
    fig, axes = plt.subplots(len(chosen), 5, figsize=(12.5, 2.25 * len(chosen)))
    for row, dataset_index in enumerate(chosen):
        image, mask, _ = dataset[int(dataset_index)]
        logits = model(image.unsqueeze(0).to(device))
        probability = torch.sigmoid(logits)[0, 0].cpu().numpy()
        prediction = probability >= threshold
        dice, _ = batch_metrics(logits.cpu(), mask.unsqueeze(0), threshold)
        source = samples[int(dataset_index)]
        crop = image[0].numpy() * prediction
        panels = (image[0].numpy(), mask[0].numpy(), probability, prediction, crop)
        titles = (
            f"Imagem: pessoa {source.subject}",
            "Mascara real",
            "Probabilidade",
            f"Predicao (Dice={float(dice[0]):.3f}; limiar={threshold:.2f})",
            "Recorte aplicado",
        )
        for col, (panel, title) in enumerate(zip(panels, titles, strict=True)):
            axes[row, col].imshow(panel, cmap="gray", vmin=0, vmax=1)
            axes[row, col].set_title(title, fontsize=9)
            axes[row, col].axis("off")
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    if args.height % 8 or args.width % 8:
        raise ValueError("Altura e largura devem ser divisiveis por 8")
    if not (0.0 <= args.tversky_alpha <= 1.0 and 0.0 <= args.tversky_beta <= 1.0):
        raise ValueError("Alpha e beta de Tversky devem estar entre 0 e 1")
    if args.patience < 0:
        raise ValueError("Patience nao pode ser negativo")
    torch.set_num_threads(args.threads)
    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    image_root, mask_root = prepare_data(args.data_dir, not args.no_download)
    samples = build_manifest(image_root, mask_root)
    original_splits = split_by_subject(samples, args.seed)
    subject_pairing_distance = {
        subject: float(
            np.mean([sample.pairing_distance for sample in samples if sample.subject == subject])
        )
        for subject in sorted({sample.subject for sample in samples})
    }
    excluded_subjects: set[int] = set()
    if args.max_subject_pairing_distance is not None:
        excluded_subjects = {
            subject
            for subject, distance in subject_pairing_distance.items()
            if distance > args.max_subject_pairing_distance
        }
    splits = {
        name: [record for record in records if record.subject not in excluded_subjects]
        for name, records in original_splits.items()
    }
    if any(not records for records in splits.values()):
        raise RuntimeError("O filtro de qualidade esvaziou uma das particoes")
    for name, records in splits.items():
        subjects = sorted({record.subject for record in records})
        print(f"{name:>5}: {len(records):3d} imagens, {len(subjects):2d} pessoas: {subjects}")
    if excluded_subjects:
        print(f"Sujeitos excluidos pelo pareamento: {sorted(excluded_subjects)}")

    pairing_audit = {
        "method": "minimum_cost_assignment_by_iris_center_within_each_subject_and_side",
        "changed_index_pairs": sum(sample.index != sample.mask_index for sample in samples),
        "distance_pixels_original_resolution": {
            "mean": float(np.mean([sample.pairing_distance for sample in samples])),
            "median": float(np.median([sample.pairing_distance for sample in samples])),
            "maximum": float(np.max([sample.pairing_distance for sample in samples])),
        },
        "subject_mean_distance": subject_pairing_distance,
        "maximum_subject_mean_distance": args.max_subject_pairing_distance,
        "excluded_subjects": sorted(excluded_subjects),
    }

    with (args.output_dir / "manifesto.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "pairing_audit": pairing_audit,
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
        name: IrisDataset(
            records,
            args.height,
            args.width,
            augment=(name == "train"),
            augmentation=args.augmentation,
        )
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
    loss_function = make_loss(
        args.loss,
        alpha=args.tversky_alpha,
        beta=args.tversky_beta,
        gamma=args.tversky_gamma,
        boundary_weight=args.boundary_weight,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=max(2, args.patience // 3),
        min_lr=args.min_learning_rate,
    )
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    print(
        f"Dispositivo: {device}; parametros treinaveis: {parameter_count:,}; "
        f"perda={args.loss}; aumento={args.augmentation}"
    )

    history: list[dict[str, float]] = []
    best_dice = -1.0
    best_epoch = 0
    epochs_without_improvement = 0
    stopped_early = False
    start = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        train = run_epoch(
            model, loaders["train"], device, optimizer, loss_function=loss_function
        )
        val = run_epoch(
            model, loaders["val"], device, None, loss_function=loss_function
        )
        learning_rate = float(optimizer.param_groups[0]["lr"])
        row = {
            "epoch": epoch,
            "learning_rate": learning_rate,
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
            f"Dice treino={train['dice']:.4f}, val={val['dice']:.4f}; "
            f"lr={learning_rate:.2e}"
        )
        if val["dice"] > best_dice:
            best_dice = val["dice"]
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(model.state_dict(), args.output_dir / "melhor_modelo.pt")
        else:
            epochs_without_improvement += 1
        scheduler.step(val["dice"])
        if (
            args.patience
            and epochs_without_improvement >= args.patience
            and epoch < args.epochs
        ):
            stopped_early = True
            print(f"Parada antecipada: {args.patience} epocas sem melhorar a validacao.")
            break

    model.load_state_dict(
        torch.load(
            args.output_dir / "melhor_modelo.pt",
            map_location=device,
            weights_only=True,
        )
    )
    selected_threshold, selected_validation_dice = select_threshold(
        model, loaders["val"], device
    )
    validation = run_epoch(
        model,
        loaders["val"],
        device,
        None,
        loss_function=loss_function,
        threshold=selected_threshold,
    )
    test = None
    detailed_test = None
    if not args.no_test:
        test = run_epoch(
            model,
            loaders["test"],
            device,
            None,
            loss_function=loss_function,
            threshold=selected_threshold,
        )
        detailed_test = detailed_evaluation(
            model,
            datasets["test"],
            splits["test"],
            device,
            selected_threshold,
            args.batch_size,
            args.output_dir,
        )
    elapsed = time.perf_counter() - start
    metrics = {
        "status": "prova_de_conceito",
        "dataset": "MMU Iris Database + mascaras manuais associadas a Ganeeva e Myasnikov (2022)",
        "image_count": len(samples),
        "subject_count": len({sample.subject for sample in samples}),
        "split": {name: len(records) for name, records in splits.items()},
        "split_before_quality_filter": {
            name: len(records) for name, records in original_splits.items()
        },
        "split_subjects": {
            name: sorted({record.subject for record in records})
            for name, records in splits.items()
        },
        "model": "Small U-Net",
        "parameters": parameter_count,
        "resolution": [args.height, args.width],
        "seed": args.seed,
        "pairing_audit": pairing_audit,
        "training": {
            "requested_epochs": args.epochs,
            "trained_epochs": len(history),
            "stopped_early": stopped_early,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "minimum_learning_rate": args.min_learning_rate,
            "weight_decay": args.weight_decay,
            "loss": args.loss,
            "tversky_alpha": args.tversky_alpha,
            "tversky_beta": args.tversky_beta,
            "tversky_gamma": args.tversky_gamma,
            "boundary_weight": args.boundary_weight,
            "augmentation": args.augmentation,
            "patience": args.patience,
        },
        "best_epoch": best_epoch,
        "best_validation_dice": best_dice,
        "selected_threshold": selected_threshold,
        "validation_dice_at_selected_threshold": selected_validation_dice,
        "validation": validation,
        "test": test,
        "test_detailed": detailed_test,
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
    if test is None:
        save_predictions(
            model,
            datasets["val"],
            splits["val"],
            device,
            args.output_dir,
            selected_threshold,
            "exemplos_validacao.png",
        )
        print(
            f"Validacao: Dice={validation['dice']:.4f}; limiar={selected_threshold:.2f}. "
            f"Teste preservado. Resultados em {args.output_dir.resolve()}"
        )
    else:
        save_predictions(
            model,
            datasets["test"],
            splits["test"],
            device,
            args.output_dir,
            selected_threshold,
        )
        print(
            f"Teste: loss={test['loss']:.4f}; Dice={test['dice']:.4f}; "
            f"IoU={test['iou']:.4f}; limiar={selected_threshold:.2f}. "
            f"Resultados em {args.output_dir.resolve()}"
        )


if __name__ == "__main__":
    main()
