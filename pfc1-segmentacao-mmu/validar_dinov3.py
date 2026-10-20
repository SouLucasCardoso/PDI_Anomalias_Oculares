"""Teste de inferencia DINOv3 em imagens reais; nao mede reconhecimento."""
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from huggingface_hub import hf_hub_download
from transformers import AutoImageProcessor, AutoModel

ROOT = Path(__file__).resolve().parent
MODEL = 'facebook/dinov3-vitl16-pretrain-lvd1689m'
REVISION = 'ea8dc2863c51be0a264bab82070e3e8836b02d51'


def main():
    model_dir = Path(hf_hub_download(MODEL, 'config.json', revision=REVISION,
                                   local_files_only=True)).parent
    processor = AutoImageProcessor.from_pretrained(model_dir, local_files_only=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = AutoModel.from_pretrained(model_dir, local_files_only=True,
        dtype=torch.bfloat16 if device.type == 'cuda' else torch.float32).to(device).eval()
    rows = json.loads((ROOT / 'data/manifesto_ubipr.json').read_text(encoding='utf-8'))['val'][:2]
    features = []
    for row in rows:
        with Image.open(row['image']) as image:
            inputs = processor(images=image.convert('RGB'), return_tensors='pt').to(device)
        with torch.inference_mode(), torch.autocast(device_type=device.type,
                dtype=torch.bfloat16, enabled=device.type == 'cuda'):
            output = model(**inputs)
            vector = output.pooler_output if output.pooler_output is not None else output.last_hidden_state[:, 0]
            vector = torch.nn.functional.normalize(vector.float(), dim=1).cpu().numpy()
        if not np.isfinite(vector).all():
            raise FloatingPointError('Embedding nao finito')
        features.append(vector[0])
    features = np.stack(features)
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'model': MODEL,
              'revision': REVISION, 'device': str(device), 'images': len(rows),
              'embedding_shape': list(features.shape), 'finite': bool(np.isfinite(features).all()),
              'norms': np.linalg.norm(features, axis=1).tolist(),
              'scientific_result': False, 'status': 'inference_ok'}
    out = ROOT / 'outputs/instalacao_2026-10-20/dinov3_smoke'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'validacao.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
