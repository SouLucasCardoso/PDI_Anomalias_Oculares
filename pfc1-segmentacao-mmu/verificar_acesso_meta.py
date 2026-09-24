#!/usr/bin/env python3
"""Verifica autenticação e aceite dos repositórios gated sem baixar checkpoints."""

from pathlib import Path
import os

os.environ.setdefault("HF_HOME", str((Path(__file__).parent / "data/modelos/huggingface").resolve()))

from huggingface_hub import hf_hub_download


FILES = (
    ("facebook/dinov3-vitl16-pretrain-lvd1689m", "config.json"),
    ("facebook/sam3.1", "config.json"),
)


def main() -> None:
    failed = False
    for model, filename in FILES:
        try:
            path = hf_hub_download(model, filename)
            print(f"ACESSO OK: {model} ({path})")
        except Exception as error:
            failed = True
            print(f"ACESSO BLOQUEADO: {model}: {type(error).__name__}: {error}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
