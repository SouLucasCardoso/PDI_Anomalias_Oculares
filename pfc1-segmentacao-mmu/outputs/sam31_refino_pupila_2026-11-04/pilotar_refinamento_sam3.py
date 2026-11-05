"""Piloto pareado de refino SAM3: somente treino, sem treino novo ou identificacao."""
from datetime import datetime, timezone
import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import time
import traceback

import numpy as np
from PIL import Image

from refinamento_sam3_pupila import GUARDS, Sam3PupilRefiner, local_box, guard_roi

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
DEFAULT=ROOT/'outputs/sam31_refino_pupila_2026-11-04'
METHODS=('global','global_pupil','roi','roi_pupil')
SOURCES=('pilotar_refinamento_sam3.py','refinamento_sam3_pupila.py',
         'segmentador_sam3_iris.py','avaliar_sam31_diverso.py')


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path,value):
    temporary=path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');temporary.replace(path)


def binding(args):
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    data=read(manifest_file);training=read(BASE/'protocolo.json');final=read(BASE/'CONCLUIDO.json')
    if sha(manifest_file)!=training['frozen']['manifest_sha256']:raise ValueError('Manifesto mudou')
    if not (BASE/'identidade/CONCLUIDO.json').exists():raise ValueError('Concluir comparacao anterior antes do novo piloto')
    groups={s:{r['subject'] for r in data[s]} for s in ('train','val','test')}
    if groups['train'] & (groups['val'] | groups['test']):raise ValueError('Pessoas sobrepostas')
    if not 1<=args.count<=len(groups['train']):raise ValueError('Quantidade invalida')
    cache=Path(training['frozen']['configuration']['cache'])
    index_file=cache/'index.jsonl'
    if sha(index_file)!=read(cache/'CONCLUIDO.json')['index_sha256']:raise ValueError('Indice de cache mudou')
    index={r['key']:r for r in (json.loads(line) for line in index_file.read_text().splitlines())}
    rng=np.random.default_rng(args.seed);people=rng.permutation(sorted(groups['train']))[:args.count]
    cases=[]
    for person in people:
        eligible=sorted([r for r in data['train'] if r['subject']==int(person)],key=lambda r:r['image'])
        row=eligible[int(rng.integers(len(eligible)))];key='train/bank0/'+Path(row['image']).stem
        file=cache/(key+'.npz');photo=ROOT/'data/ubipr/single_eye'/Path(row['image']).name
        if sha(file)!=index[key]['sha256'] or sha(photo)!=index[key]['image_sha256']:raise ValueError('Dados de treino alterados')
        cases.append({'image':photo.name,'subject':int(person),'photo':str(photo),'photo_sha256':sha(photo),
                      'cache_file':str(file),'cache_sha256':index[key]['sha256']})
    checkpoint=BASE/f'candidato_epoca_{final["best_epoch"]:02}.pt'
    if sha(checkpoint)!=final['checkpoint_sha256']:raise ValueError('Candidato alterado')
    sam=read(ROOT/'outputs/sam31_atual_prompts_2026-11-03/protocolo.json')
    if sha(Path(sam['checkpoint']))!=sam['checkpoint_sha256']:raise ValueError('Pesos oficiais SAM3 alterados')
    origin=json.loads(importlib.metadata.distribution('sam3').read_text('direct_url.json'))
    if 'f1647e8d0c1d280991f4d1b7d974c2704537fe66' not in json.dumps(origin):raise ValueError('Revisao SAM3 diferente')
    return {'count':args.count,'seed':args.seed,'sources':{n:sha(ROOT/n) for n in SOURCES},
            'manifest_sha256':sha(manifest_file),'cache_index_sha256':sha(index_file),'cases':cases,
            'iris_checkpoint':str(checkpoint),'iris_checkpoint_sha256':sha(checkpoint),
            'semantic_checkpoint':sam['checkpoint'],'semantic_checkpoint_sha256':sam['checkpoint_sha256'],
            'sam_origin':origin,'sam_code_revision':'f1647e8d0c1d280991f4d1b7d974c2704537fe66',
            'versions':{n:importlib.metadata.version(n) for n in ('torch','torchvision','sam3','numpy','pillow')},
            'previous_identity_result_sha256':sha(BASE/'identidade/CONCLUIDO.json')}


def run(args,registered):
    import torch
    from segmentador_sam3_iris import binary_metrics
    out=args.out;b=registered['binding']
    torch.set_num_threads(2);torch.manual_seed(args.seed);torch.backends.cudnn.benchmark=False
    if not torch.cuda.is_available():raise ValueError('GPU indisponivel')
    free,_=torch.cuda.mem_get_info()
    if free<4.3*2**30:raise ValueError('Aguardar GPU livre: pelo menos4.3GiB')
    torch.cuda.reset_peak_memory_stats()
    write(out/'estado.json',{'phase':'loading_model','completed':0,'total':args.count})
    engine=Sam3PupilRefiner(Path(b['semantic_checkpoint']),Path(b['iris_checkpoint']))
    write(out/'carregamento_estrito.json',engine.audit)
    rows=[];started=time.monotonic()
    for number,case in enumerate(b['cases'],1):
        if sha(Path(case['cache_file']))!=case['cache_sha256']:raise ValueError('Cache mudou')
        with np.load(case['cache_file'],allow_pickle=False) as cached:
            rgb=cached['rgb'];target=cached['target'];features=cached['features']
        global_result=engine.infer(rgb)
        masks={'global':global_result['iris'],'global_pupil':global_result['corrected']}
        with torch.inference_mode():
            x=torch.from_numpy(rgb.astype(np.float32).transpose(2,0,1).copy()/255)[None].cuda()
            old_feature=torch.from_numpy(features.astype(np.float32))[None].cuda()
            cached_prediction=engine.head(x,old_feature).argmax(1)[0].cpu().numpy()==1
            del x,old_feature
        disagreement=float((cached_prediction!=masks['global']).mean())
        if disagreement>.01:raise ValueError('Backbone completo nao reproduz controle visual; auditar antes de continuar')
        box=local_box(masks['global']);roi_meta={'box_cached_xyxy':box};roi_result=None
        if box is not None:
            x0,y0,x1,y1=box
            if sha(Path(case['photo']))!=case['photo_sha256']:raise ValueError('Foto de treino mudou')
            with Image.open(case['photo']) as original:
                photo=original.convert('RGB')
                native_box=(max(0,math.floor(x0/416*photo.width)),max(0,math.floor(y0/320*photo.height)),
                            min(photo.width,math.ceil(x1/416*photo.width)),min(photo.height,math.ceil(y1/320*photo.height)))
                roi_rgb=np.asarray(photo.crop(native_box).resize((416,320),Image.Resampling.BILINEAR))
            roi_result=engine.infer(roi_rgb);roi_meta['box_native_xyxy']=native_box
            for method,key in (('roi','iris'),('roi_pupil','corrected')):
                proposal=np.zeros((320,416),bool)
                proposal[y0:y1,x0:x1]=np.asarray(Image.fromarray(roi_result[key]).resize((x1-x0,y1-y0),Image.Resampling.NEAREST),bool)
                masks[method],roi_meta[method]=guard_roi(masks['global'],proposal)
        else:
            masks['roi']=masks['global'].copy();masks['roi_pupil']=masks['global'].copy()
        # A referencia so entra depois de todas as previsoes e escolhas geometricas.
        measured={m:binary_metrics(masks[m].astype(np.uint8),target) for m in METHODS}
        row={'image':case['image'],'subject':case['subject'],'methods':measured,
             'global_pupil_selection':global_result['selection'],'roi':roi_meta,
             'roi_pupil_selection':roi_result['selection'] if roi_result else None,
             'cached_global_prediction_disagreement_fraction':disagreement}
        file=out/(Path(case['image']).stem+'.npz')
        with file.with_suffix('.npz.part').open('wb') as stream:
            saved={'rgb':rgb,'target':target,'global_pupil':np.packbits(global_result['pupil']),
                   'global_semantic_candidates':np.packbits(global_result['semantic_masks'],axis=-1),
                   'global_semantic_candidates_shape':np.array(global_result['semantic_masks'].shape),
                   **{m+'_iris':np.packbits(masks[m]) for m in METHODS}}
            np.savez_compressed(stream,**saved)
        file.with_suffix('.npz.part').replace(file)
        row['saved_masks_sha256']=sha(file);rows.append(row)
        write(out/'parcial.json',rows)
        progress={'phase':'train_feasibility','completed':number,'total':args.count,
                  'last_image':case['image'],'seconds_excluding_model_load':time.monotonic()-started}
        write(out/'estado.json',progress);print(json.dumps(progress),flush=True)
    summary={m:{'macro_dice':float(np.mean([r['methods'][m]['dice'] for r in rows])),
                'macro_iou':float(np.mean([r['methods'][m]['iou'] for r in rows])),
                'dice_below_0_5':sum(r['methods'][m]['dice']<.5 for r in rows),
                'empty_reference_false_positives':sum(r['methods'][m]['empty_reference_false_positive'] for r in rows)} for m in METHODS}
    acceptable=[m for m in METHODS[1:] if summary[m]['macro_dice']>=summary['global']['macro_dice']+.005 and
                summary[m]['dice_below_0_5']<=summary['global']['dice_below_0_5'] and
                summary[m]['empty_reference_false_positives']<=summary['global']['empty_reference_false_positives']]
    selected=max(acceptable,key=lambda m:summary[m]['macro_dice']) if acceptable and args.count>=32 else None
    result={'completed_utc':datetime.now(timezone.utc).isoformat(),'count':args.count,'methods':summary,
            'suggested_for_full_segmentation_validation':selected,'training_feasibility_only':True,
            'development_smoke_only':args.count<32,'validation_or_clinical_or_test_images_read':False,
            'identity_evaluated':False,'minimum_area_assigned':False,'production_replaced':False,
            'strict_load':engine.audit,'peak_cuda_bytes':torch.cuda.max_memory_allocated(),
            'pupil_candidates_selected_global':sum(r['global_pupil_selection']['chosen_index'] is not None for r in rows),
            'pupil_candidates_selected_roi':sum(r['roi_pupil_selection'] is not None and r['roi_pupil_selection']['chosen_index'] is not None for r in rows),
            'protocol_sha256':sha(out/'protocolo.json'),'case_results_sha256':sha(out/'parcial.json')}
    write(out/'CONCLUIDO.json',result);write(out/'estado.json',{'phase':'completed','completed':args.count,'total':args.count})
    lines=['# Piloto de refinamento SAM3', '',
           '**Somente viabilidade em treino; sem novo minimo de area ou validacao clinica.**', '',
           f"{args.count} imagens de pessoas distintas do treino; todas preservadas.", '',
           '| Metodo | Dice macro | IoU macro | Casos Dice<50% |', '|---|---:|---:|---:|']
    for m,v in summary.items():lines.append(f"| {m} | {100*v['macro_dice']:.2f}% | {100*v['macro_iou']:.2f}% | {v['dice_below_0_5']} |")
    lines+=['',f"Variante sugerida para validacao completa: **{selected or 'nenhuma'}**.", '',
            'A regra previa exige ganho de pelo menos0,5pp no treino, sem aumento de falhas graves ou falsos positivos em referencias vazias. Essa regra nao substitui validacao nas quatro condicoes, reconhecimento ou os criterios clinicos.', '',
            'O SAM3 recebe texto pupil of the eye, sem cliques ou caixas de referencia. A selecao usa apenas escores previstos e restricoes geometricas. A ROI parte da previsao global, usa pixels nativos e retorna ao sistema de coordenadas comum. Todas as variantes usam os mesmos pesos congelados.', '',
            'Apenas a mascara anotada de iris e usada na medicao de Dice. Nao foi inventada uma referencia independente de pupila. Os candidatos sem confianca ou plausibilidade mantem a previsao global.']
    (out/'RELATORIO.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'completed':args.count,'summary':summary,'selected':selected}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    p.add_argument('--out',type=Path,default=DEFAULT);p.add_argument('--count',type=int,default=32)
    p.add_argument('--seed',type=int,default=20261104);a=p.parse_args();current=binding(a)
    if a.prepare:
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/'protocolo.json',{'registered_utc':datetime.now(timezone.utc).isoformat(),'binding':current,
            'methods':METHODS,'guards':GUARDS,'text':'pupil of the eye','confidence_threshold':.5,
            'selection':'Seed20261104, distinct TRAIN people, random image per person; no score or quality filtering',
            'scope':'Training feasibility only; ground truth never enters prompts or geometry; no validation/clinical/test inference',
            'precision':'SAM3 BF16, featureFP16roundtrip, decoderFP32','promotion_rule':'Train Dice+0.5pp, no increase catastrophic or empty-reference FP; then full validation required',
            'official_sources_checked_2026_11_04':{'code':'https://github.com/facebookresearch/sam3/commits/main/',
                'release':'https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md',
                'checkpoint':'https://huggingface.co/api/models/facebook/sam3.1',
                'hf_snapshot':'daa63191845a41281374e725f4c9e51c7a824460'}})
        for name in SOURCES:(a.out/name).write_bytes((ROOT/name).read_bytes())
        print('Protocolo registrado antes da inferencia',flush=True);return
    registered=read(a.out/'protocolo.json')
    if registered['binding']!=current:raise ValueError('Protocolo divergiu; preservar ensaio anterior')
    if (a.out/'CONCLUIDO.json').exists():raise ValueError('Preservar piloto concluido')
    requested=False;kernel=None
    if os.name=='nt':
        kernel=ctypes.WinDLL('kernel32');kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint32]
        kernel.SetThreadExecutionState.restype=ctypes.c_uint32;requested=bool(kernel.SetThreadExecutionState(0x80000001))
    from contextlib import redirect_stdout,redirect_stderr
    with (a.out/'execucao.log').open('a',encoding='utf-8',buffering=1) as log,redirect_stdout(log),redirect_stderr(log):
        try:run(a,registered)
        except BaseException as error:
            traceback.print_exc();write(a.out/'FALHA.json',{'error':repr(error),'utc':datetime.now(timezone.utc).isoformat()});raise
        finally:
            if requested:kernel.SetThreadExecutionState(0x80000000)


if __name__=='__main__':main()
