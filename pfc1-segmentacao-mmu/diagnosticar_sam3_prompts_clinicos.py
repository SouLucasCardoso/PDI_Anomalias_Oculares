"""SAM3.1 atual: texto e caixas automaticas nos quatro casos clinicos fixos."""
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/sam31_atual_prompts_2026-11-03'
LATEST = 'f1647e8d0c1d280991f4d1b7d974c2704537fe66'
OLD = ROOT / 'outputs/segmentacao_area_2026-10-27/diagnostico_sam2_prompts_2026-11-03'
NAMES = ('P0005_OD20241206.JPG', 'P0007_OS20250306.JPG', 'P0114_OS20250417.JPG', 'P0803_OD20250112.JPG')
METHODS = ('text_only', 'text_box_original', 'text_box_diverse')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def normalized_box(mask):
    """Caixa automatica CXCYWH normalizada, com margem fixa de5%."""
    y, x = np.where(mask)
    if len(x) < 16:
        return None
    h, w = mask.shape
    margin = max(2, round(.05 * max(int(x.max()-x.min()+1), int(y.max()-y.min()+1))))
    x0, y0 = max(0, int(x.min())-margin), max(0, int(y.min())-margin)
    x1, y1 = min(w, int(x.max())+1+margin), min(h, int(y.max())+1+margin)
    return [(x0+x1)/(2*w), (y0+y1)/(2*h), (x1-x0)/w, (y1-y0)/h]


def make_protocol():
    origin = json.loads(importlib.metadata.distribution('sam3').read_text('direct_url.json'))
    if LATEST not in json.dumps(origin):
        raise ValueError('Executar com o ambiente SAM3 atualizado, nao com o ambiente historico')
    latest = json.loads((ROOT / 'outputs/tecnologias_atuais_2026-11-03/checkpoint_oficial_sam31.json').read_text())
    original = json.loads((ROOT / 'outputs/sam31_diverso_2026-10-27/protocolo.json').read_text())
    checkpoint = Path(original['sam_checkpoint'])
    expected = latest['checkpoint'][0]['lfs']['sha256']
    if digest(checkpoint) != expected:
        raise ValueError('Checkpoint local diferente do oficial mais recente verificado')
    rows = json.loads((ROOT / 'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    images = [next(r for r in rows if Path(r['image']).name == name) for name in NAMES]
    return {'registered_utc': datetime.now(timezone.utc).isoformat(), 'sam_family': 'SAM3.1',
            'scope': 'Qualitative ONLY, same4SLPVLDcases, no clinical reference masks, no Dice, identity, training, checkpoint selection or production replacement',
            'sam_code_revision': LATEST, 'sam_origin': origin, 'checkpoint': str(checkpoint),
            'checkpoint_sha256': expected, 'checkpoint_hf_revision': latest['sha'],
            'python': sys.executable, 'versions': {n: importlib.metadata.version(n) for n in
                ('torch','torchvision','sam3','transformers','huggingface-hub','numpy','pillow')},
            'device': 'cuda', 'precision': 'BF16autocast, strictFP32checkpoint loading, processor1008',
            'text': 'iris of the eye', 'confidence_threshold': .5, 'methods': list(METHODS),
            'prompt_rule': 'Text only versus text plus positive normalized bbox from cached original/diverseUNet masks,5%margin. All masks above fixed confidence unioned. No points, manual/reference prompts, mask-score selection or fallback. Missingbbox yields empty candidate.',
            'support_rule': 'Reuse only preserved UNet support masks, diverse epoch15, from previous4case diagnostic; no SAM2 model imported or run',
            'supports_sha256': digest(OLD / 'mascaras.npz'),
            'sources': {n: digest(ROOT / n) for n in ('diagnosticar_sam3_prompts_clinicos.py',
                        'avaliar_sam31_diverso.py','avaliar_sam3_1_ubipr.py')},
            'images': [{'path': r['image'], 'sha256': digest(Path(r['image']))} for r in images]}


def draw(examples):
    os.environ.setdefault('MPLCONFIGDIR', str(Path(os.environ['TEMP']) / 'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig, axes = plt.subplots(4, 5, figsize=(18, 11), layout='constrained')
    titles = ('Imagem original', 'SAM3.1: texto', 'SAM3.1: texto + caixa antiga',
              'SAM3.1: texto + caixa diversa', 'Recorte: texto + caixa diversa')
    for row, (name, photo, predictions) in enumerate(examples):
        rgb = np.asarray(photo)
        views = [rgb]
        for mask in predictions:
            overlay = rgb.copy()
            overlay[mask] = (.45 * rgb[mask] + .55 * np.array([0,230,0])).astype(np.uint8)
            views.append(overlay)
        views.append(np.where(predictions[-1][...,None], rgb, 0))
        for col, view in enumerate(views):
            axes[row,col].imshow(view)
            axes[row,col].axis('off')
            axes[row,col].set_title(titles[col] if row == 0 else '', fontsize=9)
        axes[row,0].text(0,-.06,name,transform=axes[row,0].transAxes,fontsize=8)
    fig.suptitle('SAM3.1: código oficial atual, texto e caixas automáticas\nQuatro casos fixos, sem referência clínica anotada ou seleção de modelo',fontsize=12)
    fig.savefig(OUT / 'comparacao_sam31_atual.png',dpi=120)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registrar',action='store_true')
    args = parser.parse_args()
    current = make_protocol()
    if args.registrar:
        OUT.mkdir(parents=True,exist_ok=False)
        (OUT/'protocolo.json').write_text(json.dumps(current,indent=2,ensure_ascii=False),encoding='utf-8')
        (OUT/'source.py').write_bytes(Path(__file__).read_bytes())
        print('SAM3.1 protocol registered before inference',flush=True)
        return
    protocol = json.loads((OUT/'protocolo.json').read_text(encoding='utf-8'))
    for key in current:
        if key != 'registered_utc' and current[key] != protocol[key]:
            raise ValueError('Protocolo divergente: '+key)
    if (OUT/'CONCLUIDO.json').exists():
        raise FileExistsError('Preservar ensaio concluido')
    import torch
    from sam3.model.sam3_image_processor import Sam3Processor
    from avaliar_sam31_diverso import load_detector
    from avaliar_sam3_1_ubipr import collapse_masks
    torch.set_num_threads(2)
    if not torch.cuda.is_available():
        raise RuntimeError('Este ensaio foi registrado para CUDA')
    free, _ = torch.cuda.mem_get_info()
    if free < 4.3 * 2**30:
        raise RuntimeError('Aguardar pelo menos4.3GiB livres sem interromper a outra rodada')
    torch.cuda.reset_peak_memory_stats()
    model, audit = load_detector(Path(protocol['checkpoint']),'cuda')
    (OUT/'carregamento_estrito.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    processor = Sam3Processor(model,device='cuda',confidence_threshold=.5)
    records, saved, examples = [], {}, []
    started = time.monotonic()
    with np.load(OLD/'mascaras.npz',allow_pickle=False) as supports:
        for item in protocol['images']:
            name = Path(item['path']).name
            with Image.open(item['path']) as image:
                photo = image.convert('RGB');photo.thumbnail((1200,1200))
            shape = (photo.height,photo.width)
            np.testing.assert_array_equal(supports[name+'_shape'],shape)
            boxes = {}
            for label in ('original','diverse'):
                mask = np.unpackbits(supports[name+'_'+label+'_support'],count=int(np.prod(shape))).reshape(shape).astype(bool)
                boxes[label] = normalized_box(mask)
            predictions = []
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                state = processor.set_image(photo)
                for method in METHODS:
                    processor.reset_all_prompts(state)
                    box = None if method == 'text_only' else boxes['original' if method.endswith('original') else 'diverse']
                    failed = method != 'text_only' and box is None
                    scores = []
                    if failed:
                        prediction = np.zeros(shape,dtype=bool)
                    else:
                        if box is not None:
                            processor.add_geometric_prompt(box=box,label=True,state=state)
                        output = processor.set_text_prompt(prompt=protocol['text'],state=state)
                        prediction = collapse_masks(output['masks'],shape).copy()
                        scores = output['scores'].float().cpu().tolist()
                    predictions.append(prediction)
                    saved[name+'_'+method] = np.packbits(prediction)
                    records.append({'image':name,'method':method,'automatic_box_cxcywh':box,
                                    'prompt_failed':failed,'prediction_pixels':int(prediction.sum()),
                                    'model_scores_not_measured_iou':scores})
            saved[name+'_shape'] = np.array(shape)
            examples.append((name,photo,predictions))
            print(json.dumps({'images':len(examples),'seconds':time.monotonic()-started}),flush=True)
    peak = torch.cuda.max_memory_allocated()
    np.savez_compressed(OUT/'mascaras.npz',**saved)
    del processor,model
    torch.cuda.empty_cache()
    draw(examples)
    result = {'status':'completed','sam_family':'SAM3.1','sam_code_revision':LATEST,
              'strict_load':audit,'records':records,'clinical_reference_masks_available':False,
              'measured_dice_or_iou':None,'identity_evaluated':False,'production_replaced':False,
              'peak_cuda_bytes':peak,'seconds_excluding_load':time.monotonic()-started,
              'masks_sha256':digest(OUT/'mascaras.npz'),'figure_sha256':digest(OUT/'comparacao_sam31_atual.png')}
    (OUT/'CONCLUIDO.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('SAM3.1 updated diagnostic completed',flush=True)


if __name__ == '__main__':
    main()
