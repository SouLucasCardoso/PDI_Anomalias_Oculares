"""Diagnostico local e inferencia OpenIRIS; nao altera resultados historicos."""
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform

import numpy as np
import torch
from PIL import Image
from huggingface_hub import hf_hub_download
import onnxruntime as ort

from avaliar_openiris_mmu import REPO_ID, MODEL_REVISION, MODEL_FILE, run_model

ROOT = Path(__file__).resolve().parent


def main():
    report = {
        'utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
        'versions': {p: version(p) for p in ('torch', 'torchvision', 'numpy', 'Pillow',
                     'transformers', 'onnxruntime', 'matplotlib', 'sam3', 'triton-windows')},
        'cuda': torch.cuda.is_available(), 'cuda_runtime': torch.version.cuda,
    }
    if report['cuda']:
        report['gpu'] = torch.cuda.get_device_name(0)
        a = torch.ones((2, 2), device='cuda')
        report['gpu_operation_ok'] = bool(torch.equal((a @ a).cpu(), torch.full((2, 2), 2.)))
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor
    report['sam3_import_ok'] = callable(build_sam3_image_model) and callable(Sam3Processor)
    model = hf_hub_download(REPO_ID, MODEL_FILE, revision=MODEL_REVISION, local_files_only=True)
    session = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
    sample = json.loads((ROOT / 'data/manifesto_ubipr.json').read_text(encoding='utf-8'))['val'][0]
    with Image.open(sample['image']) as im:
        output, seconds = run_model(session, im)
    report['openiris_inference'] = {'shape': list(output.shape),
                                   'finite': bool(np.isfinite(output).all()), 'seconds': seconds}
    report['historical_checkpoints'] = {
        name: (ROOT / 'outputs/cnn' / name / 'melhor_modelo.pt').exists()
        for name in ('pareamento_corrigido_50ep', 'ubipr_multiclasse_30ep_batch32')}
    target = ROOT / 'data/diagnostico_ambiente.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['openiris_inference']['finite']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
