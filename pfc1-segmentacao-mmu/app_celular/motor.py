"""Inferencia local; pesos de pesquisa somente em leitura, cadastro independente."""
from __future__ import annotations
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ('rgb', 'polar', 'spatial', 'r50', 'convnext', 'native', 'transformer', 'arc_clahe', 'arc_red')
SCHEMA = 'iris_mobile_nine_components_v1'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unit(values, axis=-1):
    values = np.asarray(values, np.float64)
    return values / np.maximum(np.linalg.norm(values, axis=axis, keepdims=True), 1e-12)


def rank_candidates(query, groups, calibration):
    """Mesma ordem de fusao anterior a normalizacao por galeria; sem decisao binaria."""
    records = []
    for group in groups:
        samples = group['features']
        scores = {}
        for component in COMPONENTS:
            if component == 'spatial':
                prototype = unit(np.stack([x[component] for x in samples]).mean(0), axis=0)
                scores[component] = float((query[component] * prototype).sum(0).mean())
            else:
                similarities = np.array([float(unit(query[component]) @ unit(x[component])) for x in samples])
                if component.startswith('arc_'):
                    similarities = 1 - np.arccos(np.clip(similarities, -1, 1)) / np.pi
                scores[component] = float(np.sort(similarities)[-3:].mean())
        standardized = []
        for view in range(2):
            selected = COMPONENTS[:7] + (COMPONENTS[7 + view],)
            standardized.append(float(np.mean([(scores[c] - p['mean']) / p['std']
                                               for c, p in zip(selected, calibration[view])])))
        records.append({'person_id': group['person_id'], 'name': group['name'], 'side': group['side'],
                        'samples': len(samples), 'score': float(np.mean(standardized)), 'components': scores})
    records.sort(key=lambda x: (-x['score'], x['person_id']))
    return {'ranking': records, 'candidate_count': len(records), 'accepted': None,
            'decision': 'experimental_ranking_only', 'phone_threshold_validated': False,
            'benchmark_threshold_transferred': False,
            'margin': records[0]['score'] - records[1]['score'] if len(records) > 1 else None}


class IrisEngine:
    def __init__(self):
        self.initialized = False
        self.models = {}
        self.extractor = None
        self.head = None
        self.provenance = None

    def initialize(self, progress):
        if self.initialized:
            return
        import torch
        import cv2
        from avaliar_candidato_congelado import WEIGHTS
        from segmentador_sam3_residual import load_checkpoint
        from segmentador_sam3_iris import Sam3VisualFeatures
        torch.set_num_threads(2)
        cv2.setNumThreads(1)
        torch.backends.cudnn.benchmark = False
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        base = ROOT / 'outputs/sam31_residual_2026-11-05'
        final = json.loads((base / 'CONCLUIDO.json').read_text(encoding='utf-8-sig'))
        candidate = base / f'candidato_epoca_{final["best_epoch"]:02}.pt'
        if sha(candidate) != final['checkpoint_sha256']:
            raise ValueError('Checkpoint de segmentacao alterado')
        self.weights = {name: ROOT / 'outputs' / folder / 'melhor_modelo.pt' for name, (folder, _) in WEIGHTS.items()}
        progress('preparacao', 'Conferindo os modelos locais')
        for name, file in self.weights.items():
            if sha(file) != WEIGHTS[name][1]:
                raise ValueError('Pesos de identidade alterados: ' + name)
        self.arc_weights = next((ROOT / 'data/modelos/cvrl_arciris').rglob('ResNet100_154000.pt'))
        if sha(self.arc_weights) != '466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f':
            raise ValueError('Pesos ArcIris alterados')
        self.head = load_checkpoint(torch.load(candidate, map_location='cpu', weights_only=True), 'cpu')
        progress('segmentacao', 'Carregando o extrator SAM3.1 no PC')
        self.extractor = Sam3VisualFeatures('cpu')
        frozen = json.loads((ROOT / 'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text())
        self.calibration = frozen['component_calibration_red_and_clahe']
        sources = ('app_celular/motor.py', 'segmentador_sam3_residual.py', 'segmentador_sam3_iris.py',
                   'avaliar_candidato_congelado.py', 'textura_polar.py', 'preparar_polar_vermelho.py',
                   'normalizacao_eliptica.py', 'reconhecedor_resnet50.py', 'reconhecedor_convnext.py',
                   'reconhecedor_transformer_polar.py', 'treinar_identidade_iris.py')
        self.provenance = {'schema': SCHEMA, 'segmenter_sha256': final['checkpoint_sha256'],
                           'selected_epoch': final['best_epoch'], 'identity_weights': {k: sha(v) for k, v in self.weights.items()},
                           'arc_weights_sha256': sha(self.arc_weights), 'sources': {n: sha(ROOT / n) for n in sources},
                           'fusion': 'Original component standardization and relative weights, BEFORE per-query gallery normalization. Top3 per component; mean local spatial prototype. No mobile acceptance threshold.',
                           'benchmark_metrics_apply_to_phone': False, 'training_or_threshold_changes': False}
        self.engine_id = hashlib.sha256(json.dumps(self.provenance, sort_keys=True).encode()).hexdigest()
        self.initialized = True

    def _get_model(self, name):
        import torch
        if name in self.models:
            return self.models[name]
        if name in ('rgb', 'polar'):
            from treinar_identidade_iris import IdentityEncoder
            model = IdentityEncoder()
            model.load_state_dict(torch.load(self.weights[name], map_location='cpu', weights_only=True)['model'])
        elif name in ('r50', 'native'):
            import reconhecedor_resnet50
            model, _ = reconhecedor_resnet50.load(self.weights[name], 'cpu')
        elif name == 'convnext':
            import reconhecedor_convnext
            model, _ = reconhecedor_convnext.load(self.weights[name], 'cpu')
        elif name == 'transformer':
            import reconhecedor_transformer_polar
            model, _ = reconhecedor_transformer_polar.load(self.weights[name], 'cpu')
        elif name == 'arc':
            file = ROOT / 'data/modelos/cvrl_arciris/modules/network.py'
            if sha(file) != 'de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327':
                raise ValueError('Fonte ArcIris alterada')
            spec = importlib.util.spec_from_file_location('mobile_arciris_network', file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            model = module.iresnet100()
            model.load_state_dict(torch.load(self.arc_weights, map_location='cpu', weights_only=True))
        else:
            raise ValueError('Componente desconhecido')
        self.models[name] = model.requires_grad_(False).eval().cpu()
        return self.models[name]

    def analyze(self, image_path, output_dir, progress):
        start = time.monotonic()
        self.initialize(progress)
        import torch
        import cv2
        from avaliar_candidato_congelado import extract
        from avaliar_dinov3_ubipr import masked_crop
        from textura_polar import prepare_texture
        from preparar_polar_vermelho import red_texture
        with Image.open(image_path) as opened:
            photo = opened.convert('RGB')
        rgb = np.asarray(photo)
        small = np.asarray(photo.resize((416, 320), Image.Resampling.BILINEAR))
        progress('segmentacao', 'Localizando a iris com SAM3.1')
        self.extractor.device = self.device
        self.extractor.backbone.to(self.device)
        self.head.to(self.device).eval()
        try:
            feature = self.extractor(small)
            x = torch.from_numpy(small.transpose(2, 0, 1).copy()).float()[None].to(self.device) / 255
            with torch.inference_mode():
                logits = self.head(x, torch.from_numpy(feature.astype(np.float32))[None].to(self.device))
                small_mask = logits.argmax(1)[0].cpu().numpy() == 1
        finally:
            self.extractor.backbone.cpu()
            self.head.cpu()
            if self.device.type == 'cuda':
                torch.cuda.empty_cache()
        del x, logits
        mask = np.asarray(Image.fromarray(small_mask).resize(photo.size, Image.Resampling.NEAREST), bool)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        overlay = rgb.copy()
        overlay[mask] = (overlay[mask] * .56 + np.array([21, 211, 174]) * .44).astype(np.uint8)
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (21, 211, 174), max(1, round(photo.width / 500)))
        Image.fromarray(overlay).save(output_dir / 'overlay.jpg', quality=92)
        Image.fromarray(mask.astype(np.uint8) * 255).save(output_dir / 'mask.png')
        if int(mask.sum()) < 32:
            raise ValueError('A iris nao foi localizada. Tente outra foto, com um olho inteiro em foco.')
        y, xx = np.where(mask)
        width, height = int(xx.max() - xx.min() + 1), int(y.max() - y.min() + 1)
        focus = float(cv2.Laplacian(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), cv2.CV_64F)[mask].var())
        warnings = []
        if width < 100:
            warnings.append('A iris ficou pequena na foto. Aproxime o enquadramento mantendo o foco.')
        if focus < 35:
            warnings.append('A imagem pode estar desfocada. Toque na iris na camera e tente novamente.')
        if mask.mean() > .65:
            warnings.append('O recorte detectado e muito amplo. Confira a regiao verde antes de cadastrar.')
        progress('textura', 'Preparando a textura da iris')
        try:
            polar, geometry = prepare_texture(rgb, mask)
            red = red_texture(rgb, mask)
        except ValueError as error:
            raise ValueError('A regiao foi detectada, mas a textura nao pode ser normalizada. Refaça a foto.') from error
        Image.fromarray(polar).save(output_dir / 'polar.png')
        crop = masked_crop(photo, mask)
        inputs = {'rgb': np.asarray(crop.resize((128, 128), Image.Resampling.BILINEAR)),
                  'native': np.asarray(crop.resize((224, 224), Image.Resampling.BILINEAR)),
                  'polar': polar, 'red': red}
        features = {}
        for name in ('rgb', 'polar', 'r50', 'convnext', 'native', 'transformer', 'arc'):
            progress('descritores', 'Comparando textura no PC: ' + {'rgb': '1/7', 'polar': '2/7', 'r50': '3/7',
                      'convnext': '4/7', 'native': '5/7', 'transformer': '6/7', 'arc': '7/7'}[name])
            model = self._get_model(name).to(self.device).eval()
            try:
                if name == 'arc':
                    for key, view in (('arc_clahe', 'polar'), ('arc_red', 'red')):
                        features[key] = extract(model, inputs[view][None], self.device, batch=1, arc=True)[0]
                else:
                    view = 'polar' if name in ('polar', 'transformer') else 'native' if name == 'native' else 'rgb'
                    value = inputs[view]
                    if name == 'convnext':
                        from reconhecedor_convnext import contrast
                        value = contrast(value)
                    features[name] = extract(model, value[None], self.device, batch=1)[0]
                if name == 'polar':
                    from torch import nn
                    extractor = nn.Sequential(*list(model.backbone.children())[:7]).eval()
                    mean = torch.tensor([.485, .456, .406], device=self.device)[None, :, None, None]
                    std = torch.tensor([.229, .224, .225], device=self.device)[None, :, None, None]
                    value = torch.from_numpy(polar.transpose(2, 0, 1).copy()).float()[None].to(self.device) / 255
                    with torch.inference_mode():
                        background = extractor((torch.full_like(value, 127 / 255) - mean) / std)
                        spatial = nn.functional.normalize(extractor((value - mean) / std) - background, dim=1)
                    features['spatial'] = spatial[0].cpu().numpy()
                    del extractor, value, spatial, background
            finally:
                model.cpu()
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()
        if set(features) != set(COMPONENTS) or not all(np.isfinite(v).all() for v in features.values()):
            raise ValueError('Nao foi possivel produzir todos os descritores')
        np.savez_compressed(output_dir / 'features.npz', **features)
        return {'engine_id': self.engine_id, 'quality': {'iris_width_px': width, 'iris_height_px': height,
                'segmented_pixels': int(mask.sum()), 'focus_indicator': round(focus, 2)},
                'warnings': warnings, 'elapsed_seconds': round(time.monotonic() - start, 2),
                'device': str(self.device), 'representation_count': 9}

    def identify(self, query_features, groups):
        return rank_candidates(query_features, groups, self.calibration)
