"""Diagnostico pontual de um snapshot intermediario; nunca escolhe o modelo.

Usa as16pessoas ja sorteadas no ensaioSAM3.1 e quatro condicoes predefinidas.
Original320x240 e candidato na resolucao registrada, ambos FP32/BILINEAR/CPU.
Resultados nao alteram o treino, a regra de elegibilidade ou o reconhecedor.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
from PIL import Image
import torch

from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask,sha256
from treinar_segmentacao_diversa import transform,MODES,IGNORE
from avaliar_sam31_diverso import metrics
from avaliar_candidato_congelado import segmenter_input_size

ROOT=Path(__file__).resolve().parent


def predict(model,photo,size):
    x=torch.from_numpy(np.asarray(photo.resize(size,Image.Resampling.BILINEAR),np.float32).transpose(2,0,1).copy()/255)[None]
    with torch.inference_mode():pred=model(x).argmax(1)[0].numpy()==1
    return np.asarray(Image.fromarray(pred).resize(photo.size,Image.Resampling.NEAREST),bool)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2)
    source=ROOT/'outputs/sam31_diverso_2026-10-27/protocolo.json'
    selection=json.loads(source.read_text(encoding='utf-8-sig'));samples=selection['samples']
    state=torch.load(a.snapshot,map_location='cpu',weights_only=True)
    original_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    if sha256(original_path)!='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d':raise ValueError('Controle alterado')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Intermediate diagnostic only; not checkpoint selection, not full-validation result, not recognition or minimum area',
              'selection':'All16people in existing SAM3.1 seed127 sample; no filtering or subsequent choice by score',
              'snapshot':str(a.snapshot),'snapshot_sha256':sha256(a.snapshot),'epoch':state['epoch'],'batches':state['completed_batches'],
              'original_sha256':sha256(original_path),'sample_protocol_sha256':sha256(source),'script_sha256':sha256(Path(__file__)),
              'samples':samples,'modes':MODES,'input_original':[320,240],'input_candidate':list(segmenter_input_size(state,True)),
              'precision':'CPU FP32 both; BILINEAR resize for both. Operational model input dimensions retained.',
              'new_training_parameters_chosen_from_result':False,'clinical_segmentation_reference_available':False}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    candidate=MulticlassUNet(8).eval();candidate.load_state_dict(state['model'],strict=True)
    original=MulticlassUNet(8).eval();original.load_state_dict(torch.load(original_path,map_location='cpu',weights_only=True)['model'],strict=True)
    records=[];packed={}
    for index,row in enumerate(samples):
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['image']).name) as im:rgb=np.asarray(im.convert('RGB'))
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['mask']).name) as im:mask=decode_mask(im).astype(np.uint8)
        for mode in MODES:
            image,target=transform(rgb,mask,640,480,mode,np.random.default_rng(selection['seed']+index))
            photo=Image.fromarray((image*255).astype(np.uint8))
            packed[f'{index}_{mode}_target']=target
            for method,model,size in [('original',original,(320,240)),('snapshot',candidate,segmenter_input_size(state,True))]:
                pred=predict(model,photo,size);record={'subject':row['subject'],'image':Path(row['image']).name,'condition':mode,'method':method,
                                                      **metrics(pred,target==1,target!=IGNORE)}
                records.append(record);packed[f'{index}_{mode}_{method}']=np.packbits(pred)
        print(f'Diagnostico intermediario {index+1}/{len(samples)} pessoas',flush=True)
    summary={mode:{method:{name:float(np.mean([r[name] for r in records if r['condition']==mode and r['method']==method])) for name in ('dice','iou')}
                         for method in ('original','snapshot')} for mode in MODES}
    np.savez_compressed(out/'mascaras.npz',**packed)
    (out/'metricas_por_imagem.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    # Conferir os bytes efetivamente preservados, incluindo todos os casos vazios.
    with np.load(out/'mascaras.npz',allow_pickle=False) as saved:
        for index,row in enumerate(samples):
            for mode in MODES:
                target=saved[f'{index}_{mode}_target']
                for method in ('original','snapshot'):
                    pred=np.unpackbits(saved[f'{index}_{mode}_{method}'],count=target.size).reshape(target.shape).astype(bool)
                    record=next(r for r in records if r['subject']==row['subject'] and r['condition']==mode and r['method']==method)
                    recalc=metrics(pred,target==1,target!=IGNORE)
                    for key in ('dice','iou','prediction_pixels','reference_pixels'):
                        if abs(recalc[key]-record[key])>1e-12:raise ValueError('Mascara preservada nao reproduz metrica')
    env=os.environ.copy();env['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    subprocess.run([sys.executable,str(ROOT/'comparar_recortes_diversos.py'),'--checkpoint',str(a.snapshot),'--output-dir',str(out/'clinicos')],cwd=ROOT,env=env,check=True)
    final={'status':'completed_diagnostic_only','summary':summary,'people':len(samples),'records_recalculated':len(records),
           'checkpoint_selected':False,'full_validation_completed':False,'recognition_gain_measured':False,
           'minimum_visible_iris_area':None,'training_changed':False,
           'masks_sha256':sha256(out/'mascaras.npz'),'clinical_qualitative_only':True}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)


if __name__=='__main__':main()
