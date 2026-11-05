"""Predicoes clinicas do adaptador SAM3; referencias humanas nunca entram na inferencia."""
import argparse
import gc
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from segmentador_sam3_iris import IrisSam3Adapter,Sam3VisualFeatures
from treinar_sam3_iris_adaptado import sha
from treinar_segmentacao_diversa import save_json

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'


def selected_checkpoint():
    final=json.loads((BASE/'CONCLUIDO.json').read_text())
    if final.get('development_smoke_only'):raise ValueError('Nao usar pesos de smoke como candidato')
    file=BASE/f'candidato_epoca_{final["best_epoch"]:02}.pt'
    if sha(file)!=final['checkpoint_sha256']:raise ValueError('Checkpoint alterado')
    return file


def main():
    p=argparse.ArgumentParser();p.add_argument('--group',choices=['normal','iris_anomaly'],default='normal');a=p.parse_args()
    file=selected_checkpoint();out=BASE/'clinica'/a.group
    if a.group=='iris_anomaly':
        ready=json.loads((ROOT/'outputs/prontidao_anomalias_2026-11-03/estado.json').read_text())
        if not ready['segmentation_pilot_ready'] or ready['checkpoint_sha256']!=sha(file):
            raise ValueError('Aguardar os criterios registrados do piloto')
    manifest=json.loads((ROOT/'outputs/revisao_clinica_2026-11-03/manifesto.json').read_text(encoding='utf-8'))
    tasks=[t for t in manifest['tasks'] if t['group']==a.group]
    out.mkdir(parents=True,exist_ok=True)
    protocol={'checkpoint_sha256':sha(file),'sources':{n:sha(ROOT/n) for n in
              ('avaliar_clinica_sam3_adaptado.py','segmentador_sam3_iris.py')},
              'tasks':[{'id':t['id'],'image_sha256':t['image_sha256']} for t in tasks],
              'references_used_in_inference':False,'precision':'SAM3 BF16, decoder FP32; RGB original resized416x320, native NN mask'}
    if (out/'protocolo.json').exists():
        if json.loads((out/'protocolo.json').read_text())!=protocol:raise ValueError('Ensaio clinico mudou')
    else:save_json(out/'protocolo.json',protocol)
    if (out/'CONCLUIDO.json').exists():return
    torch.set_num_threads(2);extractor=Sam3VisualFeatures('cuda');model=IrisSam3Adapter().cuda().eval()
    model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model'],strict=True)
    for task in tasks:
        target=out/(task['id']+'.npz')
        if target.exists():continue
        if sha(Path(task['image']))!=task['image_sha256']:raise ValueError('Foto alterada')
        with Image.open(task['image']) as image:photo=image.convert('RGB')
        rgb=np.asarray(photo.resize((416,320),Image.Resampling.BILINEAR))
        features=extractor(rgb)
        x=torch.from_numpy(rgb.astype(np.float32).transpose(2,0,1).copy()/255)[None].cuda()
        with torch.inference_mode():small=model(x,torch.from_numpy(features.astype(np.float32))[None].cuda()).argmax(1)[0].cpu().numpy()==1
        predicted=np.asarray(Image.fromarray(small).resize(photo.size,Image.Resampling.NEAREST),bool)
        with target.with_suffix('.npz.part').open('wb') as stream:
            np.savez_compressed(stream,predicted=np.packbits(predicted),shape=np.array(predicted.shape),
                                image_sha256=task['image_sha256'],checkpoint_sha256=protocol['checkpoint_sha256'])
        target.with_suffix('.npz.part').replace(target)
    del model,extractor;gc.collect();torch.cuda.empty_cache()
    save_json(out/'CONCLUIDO.json',{'count':len(tasks),'checkpoint_sha256':protocol['checkpoint_sha256'],
                                  'prediction_hashes':{t['id']:sha(out/(t['id']+'.npz')) for t in tasks},
                                  'clinical_reference_used_in_inference':False})


if __name__=='__main__':main()
