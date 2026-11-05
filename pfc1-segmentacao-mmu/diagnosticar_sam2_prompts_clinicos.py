"""Diagnostico qualitativo de prompts automaticos, CPU; nao altera a rodada ativa."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/segmentacao_area_2026-10-27/diagnostico_sam2_prompts_2026-11-03'
CHECKPOINT = ROOT / 'outputs/segmentacao_area_2026-10-27/treino/candidato_epoca_15.pt'
REFERENCE = ROOT / 'outputs/sam31_diverso_2026-10-27/mascaras.npz'
NAMES = ('P0005_OD20241206.JPG', 'P0007_OS20250306.JPG',
         'P0114_OS20250417.JPG', 'P0803_OD20250112.JPG')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def protocol():
    models = json.loads((ROOT / 'data/modelos/status.json').read_text(encoding='utf-8-sig'))['models']
    sam = models['sam2']
    directory = Path(sam['path'])
    weight = directory / 'model.safetensors'
    if digest(weight) != sam['weights'][0]['sha256']:
        raise ValueError('Pesos SAM2 divergentes')
    rows = json.loads((ROOT / 'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    images = [next(r for r in rows if Path(r['image']).name == name) for name in NAMES]
    return {'registered_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'Four previously fixed SLPVLD cases; qualitative only, NO ground-truth masks, Dice, identity inference, training, checkpoint selection or production replacement',
            'model': 'Generic SAM2.1 Hiera Tiny, NOT Iris-SAM and NOT SAM3.1',
            'sam_directory': str(directory), 'sam_revision': sam['revision'],
            'sam_weight_sha256': digest(weight), 'checkpoint_sha256': digest(CHECKPOINT),
            'initial_masks_sha256': digest(REFERENCE), 'unet_epoch': 15,
            'precision_device': 'CPU FP32, two threads, no CUDA use or downloads',
            'prompt_rule': 'Reuse automatic_prompts: bbox with5%padding, up to4positive distance maxima by quadrant, predicted-hole negative center if present and2outside corners; no reference/manual prompts. Highest SAM predicted IoU among multimasks; threshold logits0; missing prompt yields empty mask, no fallback.',
            'image_rule': 'RGB thumbnail1200 preserving aspect ratio; U-Net416x320 bilinear then native nearest mask; original U-Net masks reused from preserved clinical benchmark',
            'sources': {name: digest(ROOT / name) for name in
                        ('diagnosticar_sam2_prompts_clinicos.py', 'piloto_sam_guiado.py', 'treinar_segmentacao_ubipr.py')},
            'images': [{'path': r['image'], 'sha256': digest(Path(r['image']))} for r in images]}


def draw(examples):
    os.environ.setdefault('MPLCONFIGDIR', str(Path(os.environ['TEMP']) / 'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig, axes = plt.subplots(4, 5, figsize=(18, 11), layout='constrained')
    titles = ('Imagem original', 'U-Net diversa, época15', 'SAM2.1: prompt U-Net antiga',
              'SAM2.1: prompt U-Net diversa', 'Recorte: SAM2.1 + diversa')
    for row, (name, photo, unet, old, new) in enumerate(examples):
        rgb = np.asarray(photo)
        views = [rgb]
        for mask in (unet, old, new):
            overlay = rgb.copy()
            overlay[mask] = (.45 * rgb[mask] + .55 * np.array([0, 230, 0])).astype(np.uint8)
            views.append(overlay)
        views.append(np.where(new[..., None], rgb, 0))
        for col, view in enumerate(views):
            axes[row, col].imshow(view)
            axes[row, col].axis('off')
            axes[row, col].set_title(titles[col] if row == 0 else '', fontsize=9)
        axes[row, 0].text(0, -.06, name, transform=axes[row, 0].transAxes, fontsize=8)
    fig.suptitle('SAM2.1 genérico: diagnóstico de prompts automáticos\nQuatro casos fixos, sem máscaras clínicas de referência; nenhuma seleção de modelo', fontsize=12)
    fig.savefig(OUT / 'comparacao_prompts_clinicos.png', dpi=120)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registrar', action='store_true')
    args = parser.parse_args()
    current = protocol()
    if args.registrar:
        OUT.mkdir(parents=True, exist_ok=False)
        (OUT / 'protocolo.json').write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding='utf-8')
        (OUT / 'source.py').write_bytes(Path(__file__).read_bytes())
        print('Diagnostic protocol registered before inference', flush=True)
        return
    registered = json.loads((OUT / 'protocolo.json').read_text(encoding='utf-8'))
    for key in current:
        if key != 'registered_utc' and current[key] != registered[key]:
            raise ValueError('Protocolo divergente: ' + key)
    if (OUT / 'CONCLUIDO.json').exists():
        raise FileExistsError('Preservar ensaio concluido')
    import torch
    from transformers import Sam2Model, Sam2Processor
    from piloto_sam_guiado import automatic_prompts
    from treinar_segmentacao_ubipr import MulticlassUNet
    torch.set_num_threads(2)
    unet = MulticlassUNet(8).eval()
    state = torch.load(CHECKPOINT, map_location='cpu', weights_only=True)
    unet.load_state_dict(state['model'], strict=True)
    processor = Sam2Processor.from_pretrained(registered['sam_directory'], local_files_only=True)
    sam = Sam2Model.from_pretrained(registered['sam_directory'], local_files_only=True).eval()
    masks, examples, records = {}, [], []
    started = time.monotonic()
    with np.load(REFERENCE, allow_pickle=False) as cached:
        for item in registered['images']:
            name = Path(item['path']).name
            with Image.open(item['path']) as image:
                photo = image.convert('RGB')
                photo.thumbnail((1200, 1200))
            shape = (photo.height, photo.width)
            np.testing.assert_array_equal(cached[name + '_shape'], shape)
            original = np.unpackbits(cached[name + '_unet'], count=int(np.prod(shape))).reshape(shape).astype(bool)
            x = np.asarray(photo.resize((416, 320), Image.Resampling.BILINEAR), dtype=np.float32) / 255
            with torch.inference_mode():
                small = unet(torch.from_numpy(x.transpose(2, 0, 1).copy())[None]).argmax(1)[0].numpy() == 1
            diverse = np.asarray(Image.fromarray(small).resize(photo.size, Image.Resampling.NEAREST), dtype=bool)
            predictions = []
            for label, support in (('original', original), ('diverse', diverse)):
                predicted = np.zeros(shape, dtype=bool)
                prompt, score = None, None
                try:
                    prompt = automatic_prompts(support)
                except ValueError:
                    pass
                if prompt is not None:
                    inputs = processor(images=photo, input_boxes=[[prompt['box']]],
                                       input_points=[[prompt['points']]], input_labels=[[prompt['labels']]], return_tensors='pt')
                    native = inputs['original_sizes']
                    with torch.inference_mode():
                        output = sam(**{k: v for k, v in inputs.items() if k not in ('original_sizes', 'reshaped_input_sizes')}, multimask_output=True)
                    decoded = processor.post_process_masks(output.pred_masks, native, binarize=False)[0]
                    choice = int(output.iou_scores[0, 0].argmax())
                    score = float(output.iou_scores[0, 0, choice])
                    predicted = decoded[0, choice].numpy() > 0
                predictions.append(predicted)
                records.append({'image': name, 'support': label, 'prompt': prompt,
                                'prompt_failed': prompt is None, 'predicted_iou_score_not_measured_iou': score,
                                'support_pixels': int(support.sum()), 'predicted_pixels': int(predicted.sum())})
                masks[name + '_' + label + '_support'] = np.packbits(support)
                masks[name + '_' + label + '_sam2'] = np.packbits(predicted)
            masks[name + '_shape'] = np.array(shape)
            examples.append((name, photo, diverse, *predictions))
            print(json.dumps({'images': len(examples), 'seconds': time.monotonic() - started}), flush=True)
    np.savez_compressed(OUT / 'mascaras.npz', **masks)
    draw(examples)
    result = {'status': 'completed', 'qualitative_only': True, 'images': 4,
              'prompt_cases': records, 'cuda_used': False, 'reference_masks_available': False,
              'recognition_measured': False, 'production_replaced': False,
              'masks_sha256': digest(OUT / 'mascaras.npz'), 'figure_sha256': digest(OUT / 'comparacao_prompts_clinicos.png'),
              'seconds_excluding_model_load': time.monotonic() - started}
    (OUT / 'CONCLUIDO.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Qualitative diagnostic completed; no measured Dice or clinical percentage', flush=True)


if __name__ == '__main__':
    main()
