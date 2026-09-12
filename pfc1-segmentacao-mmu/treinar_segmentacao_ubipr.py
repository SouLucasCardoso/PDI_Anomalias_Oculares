#!/usr/bin/env python3
"""Audita e treina uma U-Net multiclasse no UBIPr Single Eyes Segmented."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import tarfile
import time
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

UBIPR_URL = "https://iris.di.ubi.pt/ubipr1.tar"
FILENAME = re.compile(r"^C(?P<subject>\d+)_S(?P<session>\d+)_I(?P<index>\d+)_(?P<side>[LR])$")
NATIVE_TO_CLASS = {0: 0, 85: 1, 170: 2, 255: 3}
CLASS_NAMES = ("background_or_pupil", "iris", "sclera", "eyebrow")


@dataclass(frozen=True)
class Sample:
    image: str
    mask: str
    subject: int
    session: int
    index: int
    side: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/cnn/ubipr_multiclasse"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--base-channels", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--threads", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--limit-per-split", type=int, default=None, help="Limite apenas para testes rapidos; nao usar em resultados.")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    urllib.request.urlretrieve(url, temporary)
    temporary.replace(destination)


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Caminho inseguro no TAR: {member.name}")
        bundle.extractall(destination, filter="data")


def prepare_data(data_dir: Path, allow_download: bool = True) -> tuple[Path, Path]:
    archive = data_dir / "ubipr1.tar"
    extracted = data_dir / "ubipr"
    root = extracted / "single_eye"
    if root.exists() and any(root.glob("*.jpg")):
        return root, archive
    if not archive.exists():
        if not allow_download:
            raise FileNotFoundError(f"Arquivo ausente: {archive}")
        download(UBIPR_URL, archive)
    safe_extract(archive, extracted)
    if not root.exists():
        raise FileNotFoundError("Diretorio single_eye nao encontrado no arquivo UBIPr")
    return root, archive


def parse_stem(stem: str) -> tuple[int, int, int, str]:
    match = FILENAME.fullmatch(stem)
    if match is None:
        raise ValueError(f"Nome UBIPr inesperado: {stem}")
    return int(match["subject"]), int(match["session"]), int(match["index"]), match["side"]


def build_manifest(root: Path) -> list[Sample]:
    images = {path.stem: path for path in root.glob("*.jpg")}
    masks = {path.stem: path for path in root.glob("*.png")}
    if images.keys() != masks.keys():
        raise ValueError(f"Pareamento incompleto: sem mascara={len(images.keys()-masks.keys())}, sem imagem={len(masks.keys()-images.keys())}")
    samples = []
    for stem in sorted(images):
        subject, session, index, side = parse_stem(stem)
        samples.append(Sample(str(images[stem].resolve()), str(masks[stem].resolve()), subject, session, index, side))
    if not samples:
        raise ValueError(f"Nenhum par JPG/PNG encontrado em {root}")
    return samples


def split_by_subject(samples: list[Sample], seed: int) -> dict[str, list[Sample]]:
    subjects = sorted({sample.subject for sample in samples})
    random.Random(seed).shuffle(subjects)
    train_end = round(0.70 * len(subjects))
    val_end = train_end + round(0.15 * len(subjects))
    groups = {"train": set(subjects[:train_end]), "val": set(subjects[train_end:val_end]), "test": set(subjects[val_end:])}
    if any(groups[a] & groups[b] for a, b in (("train", "val"), ("train", "test"), ("val", "test"))):
        raise AssertionError("Vazamento de pessoas entre particoes")
    return {name: [sample for sample in samples if sample.subject in members] for name, members in groups.items()}


def decode_mask(mask: Image.Image) -> np.ndarray:
    values = np.asarray(mask.convert("L"), dtype=np.uint8)
    unexpected = sorted(set(np.unique(values).tolist()) - set(NATIVE_TO_CLASS))
    if unexpected:
        raise ValueError(f"Valores inesperados na mascara: {unexpected[:20]}")
    output = np.zeros(values.shape, dtype=np.int64)
    for native, class_id in NATIVE_TO_CLASS.items():
        output[values == native] = class_id
    return output


def audit(samples: list[Sample]) -> dict[str, object]:
    native_pixels: Counter[int] = Counter()
    sizes: Counter[str] = Counter()
    for sample in samples:
        with Image.open(sample.image) as image, Image.open(sample.mask) as mask:
            if image.size != mask.size:
                raise ValueError(f"Dimensoes divergentes: {sample.image} / {sample.mask}")
            sizes[f"{image.width}x{image.height}"] += 1
            values, counts = np.unique(np.asarray(mask.convert("L")), return_counts=True)
            native_pixels.update({int(value): int(count) for value, count in zip(values, counts)})
    unexpected = sorted(set(native_pixels) - set(NATIVE_TO_CLASS))
    if unexpected:
        raise ValueError(f"Niveis de mascara nao documentados: {unexpected}")
    return {"samples": len(samples), "subjects": len({s.subject for s in samples}), "sessions": sorted({s.session for s in samples}), "sides": sorted({s.side for s in samples}), "image_sizes": dict(sizes), "native_mask_pixels": {str(k): native_pixels[k] for k in sorted(native_pixels)}, "native_to_class": {str(k): {"id": v, "name": CLASS_NAMES[v]} for k, v in NATIVE_TO_CLASS.items()}, "pupil_warning": "A pupila usa o mesmo nivel 0 do fundo; nao e uma classe separada."}


class UBIPrDataset(Dataset):
    def __init__(self, samples: list[Sample], height: int, width: int, augment: bool):
        self.samples, self.height, self.width, self.augment = samples, height, width, augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, position: int) -> tuple[torch.Tensor, torch.Tensor]:
        sample = self.samples[position]
        with Image.open(sample.image) as source:
            image = source.convert("RGB")
        with Image.open(sample.mask) as source:
            mask = source.convert("L")
        if self.augment and random.random() < 0.5:
            image, mask = ImageOps.mirror(image), ImageOps.mirror(mask)
        if self.augment:
            image = ImageEnhance.Brightness(image).enhance(random.uniform(0.9, 1.1))
            image = ImageEnhance.Contrast(image).enhance(random.uniform(0.9, 1.1))
        image = image.resize((self.width, self.height), Image.Resampling.BILINEAR)
        mask = mask.resize((self.width, self.height), Image.Resampling.NEAREST)
        image_array = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0
        return torch.from_numpy(image_array), torch.from_numpy(decode_mask(mask))


class DoubleConv(nn.Module):
    def __init__(self, inputs: int, outputs: int):
        super().__init__()
        self.block = nn.Sequential(nn.Conv2d(inputs, outputs, 3, padding=1, bias=False), nn.BatchNorm2d(outputs), nn.ReLU(inplace=True), nn.Conv2d(outputs, outputs, 3, padding=1, bias=False), nn.BatchNorm2d(outputs), nn.ReLU(inplace=True))

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.block(value)


class MulticlassUNet(nn.Module):
    def __init__(self, base: int = 8, classes: int = 4):
        super().__init__()
        self.enc1, self.enc2, self.enc3 = DoubleConv(3, base), DoubleConv(base, base*2), DoubleConv(base*2, base*4)
        self.pool, self.middle = nn.MaxPool2d(2), DoubleConv(base*4, base*8)
        self.up3, self.dec3 = nn.ConvTranspose2d(base*8, base*4, 2, 2), DoubleConv(base*8, base*4)
        self.up2, self.dec2 = nn.ConvTranspose2d(base*4, base*2, 2, 2), DoubleConv(base*4, base*2)
        self.up1, self.dec1 = nn.ConvTranspose2d(base*2, base, 2, 2), DoubleConv(base*2, base)
        self.output = nn.Conv2d(base, classes, 1)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(value); e2 = self.enc2(self.pool(e1)); e3 = self.enc3(self.pool(e2))
        value = self.dec3(torch.cat((self.up3(self.middle(self.pool(e3))), e3), 1))
        value = self.dec2(torch.cat((self.up2(value), e2), 1))
        return self.output(self.dec1(torch.cat((self.up1(value), e1), 1)))


def loss_function(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    probabilities = torch.softmax(logits, 1)
    truth = nn.functional.one_hot(targets, len(CLASS_NAMES)).permute(0, 3, 1, 2).float()
    intersection = (probabilities * truth).sum((0, 2, 3))
    dice = (2*intersection+1e-6)/(probabilities.sum((0,2,3))+truth.sum((0,2,3))+1e-6)
    return nn.functional.cross_entropy(logits, targets) + 1.0 - dice[1:].mean()


def run_epoch(model: nn.Module, loader: DataLoader, device: torch.device, optimizer=None) -> dict[str, object]:
    training = optimizer is not None
    model.train(training)
    total, batches = 0.0, 0
    intersections = torch.zeros(4, dtype=torch.float64); predictions = torch.zeros(4, dtype=torch.float64); truths = torch.zeros(4, dtype=torch.float64)
    with (torch.enable_grad() if training else torch.no_grad()):
        for images, masks in loader:
            images, masks = images.to(device), masks.to(device)
            if training: optimizer.zero_grad(set_to_none=True)
            logits = model(images); loss = loss_function(logits, masks)
            if training: loss.backward(); optimizer.step()
            predicted = logits.argmax(1)
            for class_id in range(4):
                pred_class, true_class = predicted == class_id, masks == class_id
                intersections[class_id] += (pred_class & true_class).sum().cpu(); predictions[class_id] += pred_class.sum().cpu(); truths[class_id] += true_class.sum().cpu()
            total += float(loss.detach()); batches += 1
    dice = (2*intersections+1e-6)/(predictions+truths+1e-6)
    return {"loss": total/max(batches, 1), "dice": {name: float(dice[i]) for i, name in enumerate(CLASS_NAMES)}, "mean_foreground_dice": float(dice[1:].mean())}


def main() -> None:
    args = parse_args(); set_seed(args.seed); torch.set_num_threads(args.threads)
    root, archive = prepare_data(args.data_dir, not args.no_download)
    samples = build_manifest(root); splits = split_by_subject(samples, args.seed)
    report = audit(samples)
    report.update({"source_url": UBIPR_URL, "archive": archive.name, "archive_sha256": sha256(archive), "split": {name: {"samples": len(rows), "subjects": sorted({r.subject for r in rows})} for name, rows in splits.items()}})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/"auditoria.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.output_dir/"manifesto.json").write_text(json.dumps({name: [asdict(r) for r in rows] for name, rows in splits.items()}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.audit_only: return
    if args.limit_per_split is not None:
        splits = {name: rows[:args.limit_per_split] for name, rows in splits.items()}
        print("AVISO: limite de desenvolvimento ativo; esta execucao nao produz resultado cientifico.")
    datasets = {name: UBIPrDataset(rows, args.height, args.width, name == "train") for name, rows in splits.items()}
    loaders = {name: DataLoader(data, batch_size=args.batch_size, shuffle=name == "train", num_workers=args.workers) for name, data in datasets.items()}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MulticlassUNet(args.base_channels).to(device); optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    best, best_epoch, stale, history, started = -1.0, 0, 0, [], time.time()
    for epoch in range(1, args.epochs+1):
        train = run_epoch(model, loaders["train"], device, optimizer); val = run_epoch(model, loaders["val"], device)
        row = {"epoch": epoch, "train_loss": train["loss"], "val_loss": val["loss"], "val_mean_foreground_dice": val["mean_foreground_dice"], **{f"val_dice_{k}": v for k, v in val["dice"].items()}}
        history.append(row); print(f"epoca {epoch:02d}: perda={val['loss']:.4f}, Dice multiclasse={val['mean_foreground_dice']:.4f}")
        if val["mean_foreground_dice"] > best:
            best, best_epoch, stale = val["mean_foreground_dice"], epoch, 0
            torch.save({"model": model.state_dict(), "classes": CLASS_NAMES, "native_to_class": NATIVE_TO_CLASS, "epoch": epoch}, args.output_dir/"melhor_modelo.pt")
        else:
            stale += 1
            if stale >= args.patience: break
    checkpoint = torch.load(args.output_dir/"melhor_modelo.pt", map_location=device, weights_only=True); model.load_state_dict(checkpoint["model"])
    test = run_epoch(model, loaders["test"], device)
    with (args.output_dir/"historico.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=history[0].keys()); writer.writeheader(); writer.writerows(history)
    metrics = {"dataset": "UBIPr Single Eyes Segmented Version", "license": "CC BY-NC-SA 4.0", "device": str(device), "configuration": {"epochs_requested": args.epochs, "epochs_completed": len(history), "batch_size": args.batch_size, "workers": args.workers, "height": args.height, "width": args.width, "base_channels": args.base_channels, "learning_rate": args.learning_rate, "patience": args.patience, "seed": args.seed}, "best_epoch": best_epoch, "validation_mean_foreground_dice": best, "test": test, "elapsed_seconds": time.time()-started, "warning": "Resultados de segmentacao; a base nao fornece rotulos clinicos."}
    (args.output_dir/"metricas.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"); print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
