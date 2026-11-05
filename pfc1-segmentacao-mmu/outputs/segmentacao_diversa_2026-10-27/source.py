"""Ajuste de segmentacao com escala, vistas obliquas e oculos sinteticos.

Usa apenas treino/validacao do manifesto original. Nao rotula fotos clinicas
automaticamente nem substitui a referencia de reconhecimento congelada.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from treinar_segmentacao_ubipr import MulticlassUNet, decode_mask, set_seed, sha256

ROOT = Path(__file__).resolve().parent
IGNORE = 255
MODES = ("clean", "zoom3", "oblique", "glasses")


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 9: raise
            time.sleep(.15)


def geometry(image, mask, width, height, scale=1., angle=0., squeeze=1., dx=0., dy=0.):
    """Mesma transformacao para RGB/alvo; borda desconhecida fica ignorada."""
    source_h, source_w = mask.shape
    theta = math.radians(angle)
    rotation = np.array([[math.cos(theta), -math.sin(theta)],
                         [math.sin(theta), math.cos(theta)]], np.float32)
    linear = rotation @ np.diag([width/source_w*scale*squeeze, height/source_h*scale])
    offset = np.array([width*(.5+dx), height*(.5+dy)]) - linear @ np.array([source_w/2, source_h/2])
    matrix = np.column_stack((linear, offset)).astype(np.float32)
    rgb = cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(128, 128, 128))
    target = cv2.warpAffine(mask, matrix, (width, height), flags=cv2.INTER_NEAREST,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=IGNORE)
    return rgb, target


def add_glasses(image, mask, rng):
    """Armacoes opacas/reflexos saturados nao viram iris nos alvos."""
    h, w = mask.shape
    artifact = np.zeros((h, w), np.uint8)
    cy = round(h*rng.uniform(.30, .70))
    thickness = max(2, round(h*rng.uniform(.012, .035)))
    cv2.ellipse(artifact, (w//2, cy), (round(w*.43), round(h*.32)),
                rng.uniform(-18, 18), 0, 360, 1, thickness)
    reflection = np.zeros_like(artifact)
    x = round(w*rng.uniform(.25, .75))
    cv2.line(reflection, (x, round(h*.18)), (min(w-1, x+round(w*.13)), round(h*.83)),
             1, max(2, thickness//2))
    output = image.copy()
    output[artifact.astype(bool)] = rng.integers(8, 45, size=3, dtype=np.uint8)
    output[reflection.astype(bool)] = 245
    target = mask.copy()
    target[(artifact | reflection).astype(bool)] = 0
    # Pixels criados fora da foto continuam desconhecidos, mesmo sob a armacao.
    target[mask == IGNORE] = IGNORE
    return output, target


def transform(image, mask, width, height, mode, rng):
    if mode == "train":
        # 35% quase nativo protege o desempenho original. Zoom cobre dominio clinico.
        scale = rng.uniform(.8, 1.25) if rng.random() < .35 else rng.uniform(1.25, 4.0)
        image, mask = geometry(image, mask, width, height, scale, rng.uniform(-25, 25),
                               rng.uniform(.60, 1.10), rng.uniform(-.13, .13), rng.uniform(-.12, .12))
        if rng.random() < .5:
            image, mask = image[:, ::-1].copy(), mask[:, ::-1].copy()
        if rng.random() < .35:
            image, mask = add_glasses(image, mask, rng)
        image = image.astype(np.float32)/255.
        image = np.clip(image*rng.uniform(.7, 1.35), 0, 1)**rng.uniform(.7, 1.4)
        if rng.random() < .20:
            image = cv2.GaussianBlur(image, (3, 3), rng.uniform(.3, 1.2))
        image = np.clip(image+rng.normal(0, rng.uniform(0, .015), image.shape), 0, 1)
        return image.astype(np.float32), mask
    settings = {"clean": (1., 0., 1.), "zoom3": (3., 0., 1.),
                "oblique": (1.5, 20., .65), "glasses": (1., 0., 1.)}
    image, mask = geometry(image, mask, width, height, *settings[mode])
    if mode == "glasses":
        image, mask = add_glasses(image, mask, rng)
    return image.astype(np.float32)/255., mask


class DiverseEyes(Dataset):
    def __init__(self, rows, mode, width=416, height=320, seed=127):
        self.rows, self.mode, self.width, self.height, self.seed = rows, mode, width, height, seed

    def __len__(self):
        return len(self.rows)

    def raw(self, i):
        row = self.rows[i]
        # Manifestos de outras maquinas sao resolvidos pela fonte local auditada.
        image_path = ROOT / "data/ubipr/single_eye" / Path(row["image"]).name
        mask_path = ROOT / "data/ubipr/single_eye" / Path(row["mask"]).name
        with Image.open(image_path) as im:
            image = np.asarray(im.convert("RGB"))
        with Image.open(mask_path) as im:
            mask = decode_mask(im).astype(np.uint8)
        return image, mask

    def __getitem__(self, i):
        image, mask = self.raw(i)
        rng = np.random.default_rng(np.random.randint(2**31) if self.mode == "train" else self.seed+i)
        image, mask = transform(image, mask, self.width, self.height, self.mode, rng)
        return torch.from_numpy(image.transpose(2, 0, 1).copy()), torch.from_numpy(mask.astype(np.int64))


def boundary_weights(target):
    iris = (target == 1).float()[:, None]
    high = nn.functional.max_pool2d(iris, 5, 1, 2)
    low = -nn.functional.max_pool2d(-iris, 5, 1, 2)
    return 1.+2.*(high-low)[:, 0]


def diverse_loss(logits, target):
    valid = target != IGNORE
    # Ignorar preenchimento; nao aprender uma borda de iris falsa na moldura.
    ce = nn.functional.cross_entropy(logits.float(), target, ignore_index=IGNORE, reduction="none")
    weights = boundary_weights(target)*valid
    ce = (ce*weights).sum()/weights.sum().clamp_min(1)
    probability = logits.float().softmax(1)[:, 1]*valid
    truth = (target == 1).float()
    intersection = (probability*truth).sum((1, 2))
    dice = (2*intersection+1.)/(probability.sum((1, 2))+truth.sum((1, 2))+1.)
    return ce + 1.-dice.mean()


def epoch(model, loader, device, optimizer=None, progress=None):
    model.train(optimizer is not None)
    total_loss, seen, count = 0., 0, 0
    total_dice, total_iou, empty_fp = 0., 0., 0
    tp_total = pred_total = truth_total = 0
    with torch.set_grad_enabled(optimizer is not None):
        for step, (image, target) in enumerate(loader, 1):
            image, target = image.to(device), target.to(device)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                logits = model(image)
                loss = diverse_loss(logits, target)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("Perda nao finita; treino interrompido sem promover pesos")
            if optimizer is not None:
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.)
                optimizer.step()
            with torch.no_grad():
                valid = target != IGNORE
                pred, truth = (logits.argmax(1) == 1)&valid, target == 1
                tp = (pred&truth).sum((1, 2)); pp = pred.sum((1, 2)); tt = truth.sum((1, 2))
                total_dice += float(((2*tp+1e-6)/(pp+tt+1e-6)).sum())
                total_iou += float(((tp+1e-6)/(pp+tt-tp+1e-6)).sum())
                empty_fp += int(((tt == 0)&(pp > 0)).sum())
                tp_total += int(tp.sum()); pred_total += int(pp.sum()); truth_total += int(tt.sum())
            seen += len(image); count += 1; total_loss += float(loss.detach())*len(image)
            if progress and (step == 1 or step % 50 == 0 or step == len(loader)):
                save_json(progress, {"utc": datetime.now(timezone.utc).isoformat(),
                                    "phase": "training" if optimizer else loader.dataset.mode,
                                    "batch": step, "batches": len(loader), "samples": seen,
                                    "loss": total_loss/seen})
                print(f"{loader.dataset.mode} lote {step}/{len(loader)} perda={total_loss/seen:.4f}", flush=True)
    return {"loss": total_loss/max(seen, 1), "macro_dice_all": total_dice/max(seen, 1),
            "macro_iou_all": total_iou/max(seen, 1), "samples": seen,
            "micro_dice": (2*tp_total+1e-6)/(pred_total+truth_total+1e-6),
            "empty_reference_false_positives": empty_fp}


def preview(dataset, destination):
    picks = np.linspace(0, len(dataset)-1, 4, dtype=int)
    modes = ("clean", "zoom3", "oblique", "glasses", "train")
    w, h = 256, 208
    board = Image.new("RGB", (len(modes)*w, len(picks)*(h+24)), "white")
    draw = ImageDraw.Draw(board)
    for y, index in enumerate(picks):
        image, mask = dataset.raw(int(index))
        for x, mode in enumerate(modes):
            rgb, target = transform(image, mask, w, h, mode, np.random.default_rng(127+int(index)))
            rgb = (rgb*255).astype(np.uint8)
            rgb[target == 1] = (rgb[target == 1]*.55+np.array([0, 255, 0])*.45).astype(np.uint8)
            board.paste(Image.fromarray(rgb), (x*w, y*(h+24)+24))
            draw.text((x*w+5, y*(h+24)+5), f"{mode} | treino #{index}", fill="black")
    board.save(destination)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--mirror-dir", type=Path, help="Copia imutavel por epoca, apropriada ao OneDrive")
    p.add_argument("--manifest", type=Path, default=ROOT/"outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json")
    p.add_argument("--init", type=Path, default=ROOT/"outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--patience", type=int, default=8)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--width", type=int, default=416)
    p.add_argument("--height", type=int, default=320)
    p.add_argument("--seed", type=int, default=127)
    p.add_argument("--limit", type=int, help="Somente verificacao; nao treino completo")
    p.add_argument("--preview-only", action="store_true")
    a = p.parse_args()
    if a.width % 8 or a.height % 8:
        raise ValueError("Dimensoes devem ser multiplas de 8")
    a.output_dir.mkdir(parents=True, exist_ok=False)
    set_seed(a.seed); torch.set_num_threads(4)
    manifest = json.loads(a.manifest.read_text(encoding="utf-8-sig"))
    groups = {k: {r["subject"] for r in manifest[k]} for k in ("train", "val", "test")}
    if any(groups[x]&groups[y] for x,y in (("train","val"),("train","test"),("val","test"))):
        raise ValueError("Vazamento de pessoas no manifesto")
    config = {k: str(v) if isinstance(v, Path) else v for k,v in vars(a).items()}
    protocol = {"registered_utc": datetime.now(timezone.utc).isoformat(), "configuration": config,
                "script_sha256": sha256(Path(__file__)), "manifest_sha256": sha256(a.manifest),
                "initial_checkpoint_sha256": sha256(a.init),
                "counts": {k: {"images":len(manifest[k]), "people":len(groups[k])} for k in ("train","val","test")},
                "model": "MulticlassUNet8, ajuste dos pesos originais, resolucao416x320; nao e SAM",
                "augmentation": "35% escala0.8..1.25;65% escala1.25..4;rotacao+-25;compressao horizontal0.60..1.10;translacao;espelho;35%armacao/reflexo sintetico;brilho/gamma/ruido/desfoque",
                "labels": "UBIPr humano nativo85=iris;geometria identica;INTER_NEAREST;moldura255 ignorada;artefatos opacos classe0;nenhuma pseudoanotacao clinica",
                "selection": "epoca0 incluida; maximizar minimo Dice macro de clean/zoom3/oblique/glasses na validacao completa; clean nao pode cair mais0.01 do baseline; sem selecao por teste/reconhecimento",
                "limitations": "UBIPr nao fornece diagnosticos nem rotulos auditados de oculos/direcao;simulacao2D nao equivale a novas vistas3D ou oculos reais;validacao ja explorada;fotosSLPVLD sem mascaras nao entram no treino",
                "test_inference": False, "recognition_inference": False, "frozen_model_replaced": False,
                "development_limit": a.limit, "torch": torch.__version__,
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    save_json(a.output_dir/"protocolo.json", protocol)
    (a.output_dir/"source.py").write_bytes(Path(__file__).read_bytes())
    rows = {k: manifest[k][:a.limit] if a.limit else manifest[k] for k in ("train", "val")}
    train = DiverseEyes(rows["train"], "train", a.width, a.height, a.seed)
    preview(train, a.output_dir/"aumentacoes.png")
    if a.mirror_dir:
        a.mirror_dir.mkdir(parents=True, exist_ok=False)
        for name in ("protocolo.json", "source.py", "aumentacoes.png"):
            shutil.copy2(a.output_dir/name, a.mirror_dir/name)
    if a.preview_only:
        save_json(a.output_dir/"status.json", {"status":"preview_only"}); return
    train_loader = DataLoader(train, batch_size=a.batch_size, shuffle=True, num_workers=a.workers)
    validation = {mode: DataLoader(DiverseEyes(rows["val"], mode, a.width, a.height, a.seed),
                                  batch_size=a.batch_size, num_workers=a.workers) for mode in MODES}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MulticlassUNet(8).to(device)
    model.load_state_dict(torch.load(a.init, map_location="cpu", weights_only=True)["model"], strict=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=a.learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, a.epochs, eta_min=a.learning_rate*.1)
    best, stale, best_epoch, baseline, history, started = -1., 0, 0, None, [], time.monotonic()
    try:
        for index in range(a.epochs+1):
            save_json(a.output_dir/"status.json", {"status":"running", "pid":os.getpid(), "epoch":index,
                                                 "best_epoch":best_epoch, "utc":datetime.now(timezone.utc).isoformat()})
            trained = epoch(model, train_loader, device, optimizer, a.output_dir/"progresso.json") if index else None
            evaluated = {mode: epoch(model, loader, device, progress=a.output_dir/"progresso.json")
                         for mode, loader in validation.items()}
            dice = {mode: r["macro_dice_all"] for mode, r in evaluated.items()}
            if baseline is None: baseline = dice["clean"]
            eligible = dice["clean"] >= baseline-.01
            score = min(dice.values())
            row = {"epoch":index, "train_loss": trained["loss"] if trained else None,
                   **{f"dice_{k}":v for k,v in dice.items()}, "eligible_clean_guard":eligible,
                   "minimum_dice":score, "seconds":time.monotonic()-started}
            history.append(row)
            with (a.output_dir/"historico.csv").open("w", newline="", encoding="utf-8") as f:
                writer=csv.DictWriter(f, fieldnames=list(row));writer.writeheader();writer.writerows(history)
            save_json(a.output_dir/f"validacao_epoca_{index:02}.json", evaluated)
            state = {"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                     "scheduler": scheduler.state_dict(), "epoch":index, "configuration":config,
                     "validation":evaluated, "classes": ("background_or_pupil","iris","sclera","eyebrow")}
            if eligible and score > best:
                best, best_epoch, stale = score, index, 0
                part=a.output_dir/"melhor_modelo.pt.part";torch.save(state, part);part.replace(a.output_dir/"melhor_modelo.pt")
                if a.mirror_dir:
                    shutil.copy2(a.output_dir/"melhor_modelo.pt", a.mirror_dir/f"candidato_epoca_{index:02}.pt")
            elif index: stale += 1
            part=a.output_dir/"ultimo_modelo.pt.part";torch.save(state,part);part.replace(a.output_dir/"ultimo_modelo.pt")
            if a.mirror_dir:
                shutil.copy2(a.output_dir/f"validacao_epoca_{index:02}.json", a.mirror_dir/f"validacao_epoca_{index:02}.json")
                shutil.copy2(a.output_dir/"historico.csv", a.mirror_dir/f"historico_ate_epoca_{index:02}.csv")
            print(json.dumps(row), flush=True)
            if index: scheduler.step()
            if stale >= a.patience: break
        save_json(a.output_dir/"CONCLUIDO.json", {"status":"completed", "best_epoch":best_epoch,
                  "epochs_trained":history[-1]["epoch"], "best_minimum_dice":best,
                  "checkpoint_sha256":sha256(a.output_dir/"melhor_modelo.pt"),
                  "test_inference":False, "recognition_improvement_measured":False})
        save_json(a.output_dir/"status.json", {"status":"completed", "pid":os.getpid(), "best_epoch":best_epoch})
        if a.mirror_dir:
            shutil.copy2(a.output_dir/"CONCLUIDO.json", a.mirror_dir/"CONCLUIDO.json")
    except BaseException as error:
        save_json(a.output_dir/"status.json", {"status":"failed", "error":repr(error), "pid":os.getpid()})
        raise


if __name__ == "__main__":
    main()
