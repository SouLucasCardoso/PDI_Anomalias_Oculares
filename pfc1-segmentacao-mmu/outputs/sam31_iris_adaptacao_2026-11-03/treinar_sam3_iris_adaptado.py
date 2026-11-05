"""Cache SAM3.1 e treino retomavel de cabeca de iris, somente treino/validacao."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gc
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import time
import traceback

import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset,DataLoader
import cv2
from segmentador_sam3_iris import IrisSam3Adapter,Sam3VisualFeatures,iris_loss,binary_metrics,SAM_REVISION
from treinar_segmentacao_diversa import decode_native_fast,transform,MODES,save_json
from treinar_segmentacao_ubipr import set_seed

ROOT=Path(__file__).resolve().parent
SOURCES=('treinar_sam3_iris_adaptado.py','segmentador_sam3_iris.py','treinar_segmentacao_diversa.py',
         'treinar_segmentacao_ubipr.py','avaliar_sam31_diverso.py')


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def checkpoint(path,state):
    temp=path.with_suffix('.pt.part');torch.save(state,temp);temp.replace(path)


def manifest():
    file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    data=json.loads(file.read_text(encoding='utf-8-sig'))
    groups={k:{r['subject'] for r in data[k]} for k in ('train','val','test')}
    if any(groups[a]&groups[b] for a,b in (('train','val'),('train','test'),('val','test'))):
        raise ValueError('Pessoas sobrepostas nas particoes')
    return file,data


def specifications(data,limit=None):
    result=[]
    for split in ('train','val'):
        rows=data[split][:limit] if limit else data[split]
        for i,row in enumerate(rows):
            for mode in (('bank0','bank1') if split=='train' else MODES):
                result.append({'key':f'{split}/{mode}/{Path(row["image"]).stem}',
                               'split':split,'mode':mode,'index':i,'image':Path(row['image']).name,
                               'subject':row['subject']})
    return result


def read_index(path):
    if not path.exists():return {}
    lines=path.read_text(encoding='utf-8').splitlines();values={}
    for i,line in enumerate(lines):
        try:row=json.loads(line)
        except json.JSONDecodeError:
            if i!=len(lines)-1:raise
            path.write_text('\n'.join(lines[:i])+'\n',encoding='utf-8');break
        if row['key'] in values and values[row['key']]!=row:raise ValueError('Indice duplicado divergente')
        values[row['key']]=row
    return values


def build_cache(data,a,out):
    cache=a.cache;cache.mkdir(parents=True,exist_ok=True)
    binding={'sources':{n:sha(ROOT/n) for n in SOURCES},'manifest_sha256':sha(manifest()[0]),
             'seed':a.seed,'limit':a.limit,'shape':[416,320],'sam_revision':SAM_REVISION}
    cache_protocol=cache/'protocolo.json'
    if cache_protocol.exists():
        if json.loads(cache_protocol.read_text())!=binding:raise ValueError('Cache pertence a outra configuracao')
    else:save_json(cache_protocol,binding)
    index_file=cache/'index.jsonl';ready=cache/'CONCLUIDO.json';specs=specifications(data,a.limit)
    if ready.exists():
        meta=json.loads(ready.read_text())
        if meta['index_sha256']!=sha(index_file) or meta['count']!=len(specs):raise ValueError('Cache divergente')
        return read_index(index_file)
    index=read_index(index_file);extractor=None
    with index_file.open('a',encoding='utf-8',buffering=1) as stream:
        for number,spec in enumerate(specs,1):
            file=cache/(spec['key']+'.npz');file.parent.mkdir(parents=True,exist_ok=True)
            if spec['key'] in index:
                if not file.exists() or sha(file)!=index[spec['key']]['sha256']:raise ValueError('Arquivo de cache alterado')
                continue
            if file.exists():
                with np.load(file,allow_pickle=False) as saved:
                    if str(saved['key'])!=spec['key'] or saved['features'].shape!=(256,72,72):raise ValueError('Cache incompleto')
                    image_sha,mask_sha=str(saved['image_sha256']),str(saved['annotation_sha256'])
            else:
                if extractor is None:
                    extractor=Sam3VisualFeatures('cuda')
                    save_json(out/'carregamento_sam3.json',extractor.audit)
                source=data[spec['split']][spec['index']]
                image_bytes=(ROOT/'data/ubipr/single_eye'/Path(source['image']).name).read_bytes()
                mask_bytes=(ROOT/'data/ubipr/single_eye'/Path(source['mask']).name).read_bytes()
                image_sha,mask_sha=hashlib.sha256(image_bytes).hexdigest(),hashlib.sha256(mask_bytes).hexdigest()
                with Image.open(io.BytesIO(image_bytes)) as photo:image=np.asarray(photo.convert('RGB'))
                with Image.open(io.BytesIO(mask_bytes)) as annotation:target=decode_native_fast(annotation)
                mode={'bank0':'clean','bank1':'train'}.get(spec['mode'],spec['mode'])
                rgb,target=transform(image,target,416,320,mode,np.random.default_rng(a.seed+spec['index']))
                rgb=np.clip(rgb*255,0,255).astype(np.uint8)
                features=extractor(rgb)
                temp=file.with_suffix('.npz.part')
                with temp.open('wb') as dest:
                    np.savez(dest,key=spec['key'],rgb=rgb,target=target.astype(np.uint8),features=features,
                             image_sha256=image_sha,annotation_sha256=mask_sha)
                temp.replace(file)
            row={**spec,'sha256':sha(file),'bytes':file.stat().st_size,'image_sha256':image_sha,'annotation_sha256':mask_sha}
            stream.write(json.dumps(row)+'\n');index[spec['key']]=row
            if number==1 or number%25==0 or number==len(specs):
                progress={'stage':'sam3_cache','completed':number,'total':len(specs),'utc':datetime.now(timezone.utc).isoformat()}
                save_json(out/'progresso.json',progress);print(json.dumps(progress),flush=True)
    del extractor;gc.collect();torch.cuda.empty_cache()
    save_json(ready,{'count':len(index),'index_sha256':sha(index_file)})
    return index


class CachedEyes(Dataset):
    def __init__(self,rows,split,mode,cache,index,seed):
        self.rows,self.split,self.mode,self.cache,self.index,self.seed=rows,split,mode,cache,index,seed
        self.epoch_index=0
    def __len__(self):return len(self.rows)
    def __getitem__(self,i):
        mode=self.mode
        if self.split=='train':
            bank=int(np.random.default_rng(np.random.SeedSequence([self.seed,self.epoch_index,i])).integers(2))
            mode=f'bank{bank}'
        key=f'{self.split}/{mode}/{Path(self.rows[i]["image"]).stem}'
        file=self.cache/(key+'.npz')
        if sha(file)!=self.index[key]['sha256']:raise ValueError('Cache alterado durante treino')
        with np.load(file,allow_pickle=False) as data:
            rgb=torch.from_numpy(data['rgb'].astype(np.float32).transpose(2,0,1).copy()/255)
            target=torch.from_numpy(data['target'].astype(np.int64))
            feature=torch.from_numpy(data['features'].astype(np.float32))
        return rgb,target,feature,i


def evaluate(model,dataset,device,batch_size,out):
    loader=DataLoader(dataset,batch_size=batch_size,num_workers=0);model.eval();records=[]
    with torch.inference_mode():
        for batch,(rgb,target,features,indices) in enumerate(loader,1):
            with torch.autocast('cuda',dtype=torch.bfloat16,enabled=device.type=='cuda'):
                pred=model(rgb.to(device),features.to(device)).argmax(1).cpu().numpy()
            for p,t,i in zip(pred,target.numpy(),indices.tolist()):
                row=dataset.rows[i]
                records.append({'image':Path(row['image']).name,'subject':row['subject'],**binary_metrics(p,t)})
            if batch==1 or batch%50==0 or batch==len(loader):
                save_json(out/'progresso.json',{'stage':'validation','mode':dataset.mode,'batch':batch,'batches':len(loader)})
    return {'macro_dice':float(np.mean([r['dice'] for r in records])),
            'macro_iou':float(np.mean([r['iou'] for r in records])),
            'p10_dice':float(np.quantile([r['dice'] for r in records],.1)),
            'catastrophic_cases':sum(r['dice']<.5 for r in records),'samples':len(records),'records':records}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--mirror',type=Path,required=True);p.add_argument('--prepare',action='store_true')
    p.add_argument('--wait-reference',action='store_true');p.add_argument('--limit',type=int)
    p.add_argument('--epochs',type=int,default=20);p.add_argument('--seed',type=int,default=20261103)
    p.add_argument('--batch-size',type=int,default=16);p.add_argument('--init',type=Path)
    a=p.parse_args();out=a.run;mirror=a.mirror
    if min(a.epochs,a.batch_size)<1 or (a.limit is not None and a.limit<1):raise ValueError('Parametros invalidos')
    out.mkdir(parents=True,exist_ok=True);mirror.mkdir(parents=True,exist_ok=True)
    file,data=manifest()
    configuration={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items() if k!='prepare'}
    origin=json.loads(importlib.metadata.distribution('sam3').read_text('direct_url.json'))
    if SAM_REVISION not in json.dumps(origin):raise ValueError('Ambiente SAM3 incorreto')
    metadata={'configuration':configuration,'manifest_sha256':sha(file),
              'sources':{n:sha(ROOT/n) for n in SOURCES},
              'versions':{n:importlib.metadata.version(n) for n in ('torch','torchvision','sam3','numpy','pillow')},
              'sam_origin':origin}
    sam_protocol=json.loads((ROOT/'outputs/sam31_atual_prompts_2026-11-03/protocolo.json').read_text())
    if sha(Path(sam_protocol['checkpoint']))!=sam_protocol['checkpoint_sha256']:raise ValueError('Pesos SAM3 alterados')
    metadata['sam_checkpoint_sha256']=sam_protocol['checkpoint_sha256']
    protocol_file=mirror/'protocolo.json'
    if protocol_file.exists():
        protocol=json.loads(protocol_file.read_text())
        if protocol['frozen']!=metadata:raise ValueError('Fontes, dados ou parametros mudaram; registrar outra rodada')
    else:
        if not a.prepare:raise ValueError('Registrar com --prepare antes de executar')
        protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'frozen':metadata,
                  'architecture':'Frozen official SAM3.1 vision features256x72x72 (1008/patch14), supervised RGB+SAM3 decoder; not full SAM3 finetuning nor original text predictor',
                  'augmentation':'Two fixed train banks: native and diverse, chosen deterministically per image/epoch. Four fixed validation conditions. Float16 feature cache, uint8 RGB and targets; unknown255 ignored.',
                  'selection':'Epoch0 included. Maximize minimum macroDice across4conditions; clean >= epoch0clean-0.005; patience6. No identity/clinical labels select weights.',
                  'loss':'BoundaryCE+irisDice+0.25TverskyLoss, FPweight0.7,FN0.3. Native class0 includes pupil/background; NO invented pupil reference.',
                  'initialization':'Final checkpoint selected by segmentation in prior registered round, after its complete identity/area pipeline finishes; explicit init for smoke only',
                  'scope':'Train/validation only, ALLcases retained; no TEST inference or clinical masks used; recognition not measured by this trainer',
                  'engineering_target_not_clinical_standard':{'all4_validation_macroDice':.90,'clinical_review_still_required':True},
                  'development_smoke_only':a.limit is not None}
        save_json(protocol_file,protocol)
        for n in SOURCES:(mirror/n).write_bytes((ROOT/n).read_bytes())
    if a.prepare:print('SAM3 adapter protocol prepared',flush=True);return
    if (out/'CONCLUIDO.json').exists():return
    log=(mirror/'execucao.log').open('a',encoding='utf-8',buffering=1)
    from contextlib import redirect_stdout,redirect_stderr
    with log,redirect_stdout(log),redirect_stderr(log):
        try:
            save_json(out/'status.json',{'stage':'starting','pid':os.getpid()})
            initial=a.init
            if initial is None:
                reference=ROOT/'outputs/segmentacao_area_2026-10-27'
                while not (reference/'CONCLUIDO_RODADA.json').exists():
                    if not a.wait_reference:raise RuntimeError('Rodada de referencia ainda ativa')
                    save_json(out/'status.json',{'stage':'waiting_reference_pipeline','pid':os.getpid()});time.sleep(30)
                final=json.loads((reference/'treino/CONCLUIDO.json').read_text())
                initial=reference/'treino'/f'candidato_epoca_{final["best_epoch"]:02}.pt'
                if sha(initial)!=final['checkpoint_sha256']:raise ValueError('Controle final alterado')
            initial_info={'path':str(initial),'sha256':sha(initial)}
            binding=mirror/'inicializacao.json'
            if binding.exists() and json.loads(binding.read_text())!=initial_info:raise ValueError('Inicializacao alterada')
            save_json(binding,initial_info)
            cv2.setNumThreads(1);torch.set_num_threads(2);set_seed(a.seed);torch.backends.cudnn.benchmark=False
            if not torch.cuda.is_available():raise RuntimeError('Rodada exige GPU')
            save_json(out/'status.json',{'stage':'sam3_cache','pid':os.getpid()})
            index=build_cache(data,a,out)
            if a.limit:data={k:v[:a.limit] for k,v in data.items()}
            device=torch.device('cuda');model=IrisSam3Adapter().to(device)
            optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4)
            scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,a.epochs,eta_min=1e-5)
            datasets={m:CachedEyes(data['val'],'val',m,a.cache,index,a.seed) for m in MODES}
            train=CachedEyes(data['train'],'train','bank0',a.cache,index,a.seed)
            recovery=out/'retomada.pt'
            if recovery.exists():
                state=torch.load(recovery,map_location='cpu',weights_only=True)
                model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
                history=state['history'];best=state['best'];best_epoch=state['best_epoch'];stale=state['stale']
                epoch_index=state['next_epoch'];completed=state['completed_batches'];totals=state['totals'];baseline=state['baseline']
            else:
                model.load_rgb_control(torch.load(initial,map_location='cpu',weights_only=True)['model'])
                measured={m:evaluate(model,d,device,a.batch_size,out) for m,d in datasets.items()}
                save_json(mirror/'validacao_epoca_00.json',measured)
                measured={m:{k:v for k,v in r.items() if k!='records'} for m,r in measured.items()}
                baseline=measured['clean']['macro_dice'];best=min(r['macro_dice'] for r in measured.values())
                best_epoch=0;stale=0;epoch_index=1;completed=0;totals=[0.,0]
                history=[{'epoch':0,'validation':measured,'score':best}]
            def snapshot(next_epoch,batches,totals,persist=True):
                state={'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),
                       'history':history,'best':best,'best_epoch':best_epoch,'stale':stale,'baseline':baseline,
                       'next_epoch':next_epoch,'completed_batches':batches,'totals':list(totals),
                       'model_type':'sam3_visual_iris_adapter','configuration':{'width':416,'height':320},
                       'sam_revision':SAM_REVISION,'cache_index_sha256':sha(a.cache/'index.jsonl')}
                if persist:checkpoint(recovery,state)
                return state
            if not recovery.exists():
                state=snapshot(1,0,totals,False);checkpoint(out/'melhor_modelo.pt',state);checkpoint(mirror/'candidato_epoca_00.pt',state)
                checkpoint(recovery,state)
            for epoch_index in range(epoch_index,a.epochs+1):
                train.epoch_index=epoch_index
                order=torch.randperm(len(train),generator=torch.Generator().manual_seed(a.seed+epoch_index)).tolist()
                loader=DataLoader(train,batch_size=a.batch_size,sampler=order[completed*a.batch_size:],num_workers=0,
                                  generator=torch.Generator().manual_seed(a.seed+epoch_index))
                save_json(out/'status.json',{'stage':'training','pid':os.getpid(),'epoch':epoch_index,'best_epoch':best_epoch})
                model.train();batches=math.ceil(len(train)/a.batch_size)
                for step,(rgb,target,features,_) in enumerate(loader,completed+1):
                    optimizer.zero_grad(set_to_none=True)
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        loss=iris_loss(model(rgb.to(device),features.to(device)),target.to(device))
                    if not torch.isfinite(loss):raise FloatingPointError('Perda nao finita')
                    loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step()
                    totals[0]+=float(loss.detach())*len(rgb);totals[1]+=len(rgb)
                    if step==completed+1 or step%25==0 or step==batches:
                        snapshot(epoch_index,step,totals)
                        save_json(out/'progresso.json',{'stage':'training','epoch':epoch_index,'batch':step,'batches':batches,'loss':totals[0]/totals[1]})
                measured={m:evaluate(model,d,device,a.batch_size,out) for m,d in datasets.items()}
                save_json(mirror/f'validacao_epoca_{epoch_index:02}.json',measured)
                measured={m:{k:v for k,v in r.items() if k!='records'} for m,r in measured.items()}
                score=min(r['macro_dice'] for r in measured.values());eligible=measured['clean']['macro_dice']>=baseline-.005
                history.append({'epoch':epoch_index,'validation':measured,'score':score,'eligible':eligible,'train_loss':totals[0]/totals[1]})
                if eligible and score>best:best=score;best_epoch=epoch_index;stale=0
                else:stale+=1
                scheduler.step();completed=0;totals=[0.,0]
                state=snapshot(epoch_index+1,0,totals,False)
                if best_epoch==epoch_index:
                    checkpoint(out/'melhor_modelo.pt',state);checkpoint(mirror/f'candidato_epoca_{epoch_index:02}.pt',state)
                checkpoint(recovery,state)
                save_json(out/'historico.json',history)
                print(json.dumps({'epoch':epoch_index,'score':score,'best_epoch':best_epoch}),flush=True)
                if stale>=6:break
            selected=history[best_epoch]
            final={'status':'completed','best_epoch':best_epoch,'checkpoint_sha256':sha(out/'melhor_modelo.pt'),
                   'best_score':best,'validation':selected['validation'],
                   'segmentation_engineering_target_passed':all(v['macro_dice']>=.9 for v in selected['validation'].values()),
                   'clinical_masks_reviewed':False,'recognition_measured':False,'test_inference':False,
                   'development_smoke_only':a.limit is not None}
            save_json(out/'CONCLUIDO.json',final);save_json(mirror/'CONCLUIDO.json',final)
            save_json(out/'status.json',{'stage':'completed','pid':os.getpid(),'best_epoch':best_epoch})
        except BaseException as error:
            traceback.print_exc();save_json(out/'status.json',{'stage':'failed','pid':os.getpid(),'error':repr(error)});raise


if __name__=='__main__':main()
