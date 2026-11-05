"""Preflight CPU dos nove componentes congelados; sem medir taxa de identificacao."""
from __future__ import annotations

import os
# Este ensaio nao disputa a GPU com a construcao de mapas SAM3.
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import time
import traceback

import numpy as np
import torch

import avaliar_candidato_congelado as frozen

ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT/'outputs/tecnologias_atuais_2026-11-03/identidade_smoke_cpu'
SOURCES = ('verificar_identidade_ambiente_sam3.py', 'avaliar_candidato_congelado.py',
           'treinar_identidade_iris.py', 'reconhecedor_resnet50.py', 'reconhecedor_convnext.py',
           'reconhecedor_transformer_polar.py', 'validar_correspondencia_espacial.py',
           'avaliar_robustez_reconhecimento.py', 'textura_polar.py', 'preparar_polar_vermelho.py')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    temp = path.with_suffix(path.suffix+'.part')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def run(out, work):
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import Sample
    from avaliar_robustez_reconhecimento import identity
    import reconhecedor_resnet50, reconhecedor_convnext, reconhecedor_transformer_polar

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(20261103)
    device = torch.device('cpu')
    manifest_file = ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
    rows = []
    for raw in manifest['val']:
        raw = dict(raw)
        for name in ('image', 'mask'):
            raw[name] = str(ROOT/'data/ubipr/single_eye'/Path(raw[name]).name)
        rows.append(Sample(**raw))
    eligible = {identity(r) for r in rows if r.session == 1} & {identity(r) for r in rows if r.session == 2}
    eye = sorted(eligible)[0]
    selected = [min((r for r in rows if identity(r) == eye and r.session == session),
                    key=lambda r: Path(r.image).name) for session in (1, 2)]
    frozen_file = ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    if sha(frozen_file) != 'd933686f045eab5d6578cfe4701578d9ca1eeaaff4069bcff8427a602546dbda':
        raise ValueError('Configuracao congelada alterada')
    checkpoints = {n: ROOT/'outputs'/folder/'melhor_modelo.pt' for n, (folder, _) in frozen.WEIGHTS.items()}
    for name, path in checkpoints.items():
        if sha(path) != frozen.WEIGHTS[name][1]:
            raise ValueError('Pesos de identidade alterados: '+name)
    arc_dir = ROOT/'data/modelos/cvrl_arciris'
    arc_weights = next(arc_dir.rglob('ResNet100_154000.pt'))
    arc_source = arc_dir/'modules/network.py'
    if sha(arc_weights) != '466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f':
        raise ValueError('Pesos ArcIris alterados')
    if sha(arc_source) != 'de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327':
        raise ValueError('Codigo ArcIris alterado')
    protocol = {
        'registered_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'CPU compatibility smoke only, two predetermined validation photographs; not performance or candidate selection',
        'selection': 'Lexically first eligible eye, lexically first photo in each session, no quality or score filtering',
        'samples': [{'image': Path(r.image).name, 'session': r.session, 'image_sha256': sha(Path(r.image))} for r in selected],
        'manifest_sha256': sha(manifest_file), 'frozen_configuration_sha256': sha(frozen_file),
        'sources': {name: sha(ROOT/name) for name in SOURCES},
        'checkpoints': {name: sha(path) for name, path in checkpoints.items()},
        'arc_weights_sha256': sha(arc_weights), 'arc_source_sha256': sha(arc_source),
        'versions': {n: importlib.metadata.version(n) for n in ('torch', 'torchvision', 'transformers', 'numpy', 'pillow')},
        'device': 'cpu', 'precision': 'FP32; ArcIris output normalized in FP64 as in frozen extractor',
        'cuda_visible_devices': os.environ['CUDA_VISIBLE_DEVICES'], 'network_offline': True,
        'test_inference': False, 'new_sam3_decoder_evaluated': False,
        'does_not_replace_full_cuda_evaluation': True,
    }
    if (out/'protocolo.json').exists():
        raise ValueError('Preservar ensaio existente; usar outro diretorio de saida')
    write(out/'protocolo.json', protocol)
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    arrays, rv, pv = frozen.prepare(selected, device, work/'prepared')
    features, components = {}, []

    def record(name, value, expected_shape, started):
        if value.shape != expected_shape or not np.isfinite(value).all():
            raise ValueError('Saida invalida em '+name)
        features[name] = value
        item = {'component': name, 'shape': list(value.shape), 'finite': True,
                'output_sha256': hashlib.sha256(value.tobytes()).hexdigest(),
                'elapsed_seconds': time.monotonic()-started}
        components.append(item)
        write(out/'progresso.json', {'completed_components': len(components), 'total': 9, 'last_component': item})
        print(json.dumps(item), flush=True)

    for name in ('rgb', 'polar', 'r50', 'convnext', 'native', 'transformer'):
        started = time.monotonic()
        if name in ('rgb', 'polar'):
            model = IdentityEncoder().eval()
            model.load_state_dict(torch.load(checkpoints[name], map_location='cpu', weights_only=True)['model'], strict=True)
        else:
            module = {'r50': reconhecedor_resnet50, 'convnext': reconhecedor_convnext,
                      'native': reconhecedor_resnet50, 'transformer': reconhecedor_transformer_polar}[name]
            model, _ = module.load(checkpoints[name], device)
        images = arrays['polar'] if name in ('polar', 'transformer') else arrays['native'] if name == 'native' else arrays['rgb']
        if name == 'convnext':
            images = np.stack([reconhecedor_convnext.contrast(image) for image in images])
        value = frozen.extract(model, images, device, batch=2)
        record(name, value, (2, 256), started)
        if name == 'polar':
            started = time.monotonic()
            scores, valid = frozen.spatial(model, images, pv, selected, device)
            if valid.shape != (1,):
                raise ValueError('Validade espacial com dimensoes incorretas')
            record('spatial', scores, (1, 1), started)
        del model
        gc.collect()

    spec = importlib.util.spec_from_file_location('arciris_cpu_compatibility', arc_source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.iresnet100().eval()
    model.load_state_dict(torch.load(arc_weights, map_location='cpu', weights_only=True), strict=True)
    for name, images in (('arc_clahe', arrays['polar']), ('arc_red', arrays['red'])):
        started = time.monotonic()
        record(name, frozen.extract(model, images, device, batch=2, arc=True), (2, 512), started)
    del model
    np.savez_compressed(out/'saidas_compatibilidade.npz', **features)
    for array in arrays.values():
        array.flush()
        array._mmap.close()
    if len(components) != 9 or torch.cuda.is_initialized():
        raise ValueError('Ensaio incompleto ou CUDA inicializado indevidamente')
    write(out/'CONCLUIDO.json', {
        'status': 'compatibility_smoke_passed', 'components': components,
        'rgb_valid': rv.tolist(), 'polar_valid': pv.tolist(),
        'protocol_sha256': sha(out/'protocolo.json'),
        'outputs_sha256': sha(out/'saidas_compatibilidade.npz'),
        'cpu_only': True, 'cuda_initialized': False, 'test_inference': False,
        'performance_metrics_computed': False, 'minimum_area_assigned': False,
        'new_sam3_decoder_evaluated': False,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()) or any(args.work.iterdir()):
        raise ValueError('Usar diretorios vazios; preservar resultados anteriores')
    from contextlib import redirect_stdout, redirect_stderr
    with (args.out/'execucao.log').open('w', encoding='utf-8', buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                run(args.out, args.work)
            except BaseException as error:
                traceback.print_exc()
                write(args.out/'FALHA.json', {'error': repr(error), 'utc': datetime.now(timezone.utc).isoformat()})
                raise


if __name__ == '__main__':
    main()
