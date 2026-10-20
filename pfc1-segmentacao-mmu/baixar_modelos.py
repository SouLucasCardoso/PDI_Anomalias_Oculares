"""Baixa pesos e configuracoes dos modelos usados no projeto, sem expor tokens."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
config = ROOT / 'data/hf-home.txt'
home = config.read_text(encoding='utf-8-sig').strip() if config.exists() else str(ROOT / 'data/modelos/huggingface')
os.environ.setdefault('HF_HOME', home)

from huggingface_hub import hf_hub_download, snapshot_download
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError


def main():
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'models': {}}
    jobs = (
        ('sam2', 'facebook/sam2.1-hiera-tiny', 'de431c4043854a71d8101e17995dfe596bf101a5', None),
        ('openiris', 'Worldcoin/iris-semantic-segmentation', 'e6c8fbb8e2e7e024a58818530a6e3ae5c005f47a', 'iris_semseg_upp_scse_mobilenetv2.onnx'),
        ('dinov3', 'facebook/dinov3-vitl16-pretrain-lvd1689m', 'ea8dc2863c51be0a264bab82070e3e8836b02d51', None),
        ('sam3.1', 'facebook/sam3.1', 'daa63191845a41281374e725f4c9e51c7a824460', 'sam3.1_multiplex.pt'),
    )
    for name, repo, revision, filename in jobs:
        try:
            if filename:
                path = hf_hub_download(repo, filename, revision=revision)
            else:
                path = snapshot_download(repo, revision=revision,
                    allow_patterns=['*.json', '*.safetensors'])
            status = 'downloaded'
            result['models'][name] = {'repo': repo, 'revision': revision, 'status': status, 'path': path}
            location = Path(path)
            weights = [location] if location.is_file() else sorted(location.glob('*.safetensors'))
            if not weights:
                raise FileNotFoundError('Download sem arquivo de pesos')
            weight_records = []
            for weight in weights:
                with weight.open('rb') as stream:
                    checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
                weight_records.append({'name': weight.name, 'bytes': weight.stat().st_size, 'sha256': checksum})
            result['models'][name]['weights'] = weight_records
        except GatedRepoError:
            result['models'][name] = {'repo': repo, 'status': 'gated_access_required'}
        except HfHubHTTPError as exc:
            response = getattr(exc, 'response', None)
            result['models'][name] = {'repo': repo, 'status': 'http_error',
                                     'http_status': getattr(response, 'status_code', None)}
        except Exception as exc:
            result['models'][name] = {'repo': repo, 'status': 'error', 'type': type(exc).__name__}
        print(name, result['models'][name]['status'], flush=True)
    target = ROOT / 'data/modelos/status.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if any(r['status'] != 'downloaded' for r in result['models'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
