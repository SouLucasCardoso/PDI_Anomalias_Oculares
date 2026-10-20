"""Baixa pesos oficiais da CNN clinica e verifica integridade, sem treinar."""
import hashlib
import json
from pathlib import Path

import torch
from torchvision.models import ResNet18_Weights

ROOT = Path(__file__).resolve().parent


def main():
    weights = ResNet18_Weights.IMAGENET1K_V1
    state = weights.get_state_dict(progress=True, check_hash=True)
    if 'fc.weight' not in state or tuple(state['fc.weight'].shape) != (1000, 512):
        raise ValueError('Checkpoint ImageNet inesperado')
    path = Path(torch.hub.get_dir()) / 'checkpoints/resnet18-f37072fd.pth'
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = {'model': 'torchvision ResNet18', 'weights': 'IMAGENET1K_V1',
              'sha256': digest, 'bytes': path.stat().st_size,
              'status': 'downloaded_not_clinically_trained'}
    out = ROOT / 'data/modelos/resnet18_status.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
