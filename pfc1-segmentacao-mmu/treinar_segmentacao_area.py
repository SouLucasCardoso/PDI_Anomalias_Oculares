"""Rodada retomavel de segmentacao diversa, com salvamento dentro da epoca.

Nao usa identidade para escolher checkpoint. A retomada repete a mesma ordem e
aumentacao por foto/epoca. Mantem o ultimo lote salvo, AdamW e scheduler.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from torch.utils.data import DataLoader
import cv2

from treinar_segmentacao_ubipr import MulticlassUNet, set_seed, sha256
from treinar_segmentacao_diversa import DiverseEyes, MODES, diverse_loss, epoch, transform, preview, save_json

ROOT=Path(__file__).resolve().parent


class EpochEyes(DiverseEyes):
    epoch_index=0

    def __getitem__(self,index):
        image,mask=self.raw(index)
        rng=np.random.default_rng(np.random.SeedSequence([self.seed,self.epoch_index,index]))
        image,mask=transform(image,mask,self.width,self.height,self.mode,rng)
        return torch.from_numpy(image.transpose(2,0,1).copy()),torch.from_numpy(mask.astype(np.int64))


def order_for_epoch(size,seed,index):
    return torch.randperm(size,generator=torch.Generator().manual_seed(seed+index)).tolist()


def save_checkpoint(path,state):
    temporary=path.with_suffix(path.suffix+'.part');torch.save(state,temporary);temporary.replace(path)


def immutable_copy(source,target):
    if target.exists():
        if sha256(source)!=sha256(target):raise FileExistsError(f'Copia divergente: {target}')
        return
    temporary=target.with_suffix(target.suffix+'.part')
    shutil.copy2(source,temporary);temporary.replace(target)


def baseline_from(folder,manifest_hash,initial_hash,width,height,seed,limit):
    protocol=json.loads((folder/'protocolo.json').read_text(encoding='utf-8-sig'))
    config=protocol['configuration']
    if protocol['manifest_sha256']!=manifest_hash or protocol['initial_checkpoint_sha256']!=initial_hash:
        raise ValueError('Baseline pertence a dados/pesos diferentes')
    if (config['width'],config['height'],config['seed'],config.get('limit'))!=(width,height,seed,limit):
        raise ValueError('Baseline possui resolucao, semente ou populacao diferente')
    # Reciclar somente inferencia identica, com fontes preservadas.
    source=(folder/'source.py').read_text(encoding='utf-8-sig')
    current=(ROOT/'treinar_segmentacao_diversa.py').read_text(encoding='utf-8-sig')
    def bodies(text):
        return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(text).body if isinstance(node,ast.FunctionDef)}
    old,new=bodies(source),bodies(current)
    for name in ('geometry','add_glasses','transform','boundary_weights','diverse_loss'):
        if old[name]!=new[name]:raise ValueError('Transformacao/perda diferente do baseline: '+name)
    return json.loads((folder/'validacao_epoca_00.json').read_text(encoding='utf-8'))


def train_pass(model,dataset,device,optimizer,batch_size,index,seed,completed,totals,save_every,on_save,out):
    dataset.epoch_index=index;order=order_for_epoch(len(dataset),seed,index)
    loader=DataLoader(dataset,batch_size=batch_size,sampler=order[completed*batch_size:],num_workers=0,
                      generator=torch.Generator().manual_seed(seed+index))
    total_batches=math.ceil(len(dataset)/batch_size);model.train()
    for step,(images,target) in enumerate(loader,completed+1):
        images,target=images.to(device),target.to(device);optimizer.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=torch.bfloat16,enabled=device.type=='cuda'):
            loss=diverse_loss(model(images),target)
        if not bool(torch.isfinite(loss)):raise FloatingPointError('Perda nao finita')
        loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
        totals['loss_sum']+=float(loss.detach())*len(images);totals['samples']+=len(images)
        if step==completed+1 or step%save_every==0 or step==total_batches:
            on_save(step,totals)
            progress={'utc':datetime.now(timezone.utc).isoformat(),'phase':'training','epoch':index,'batch':step,
                      'batches':total_batches,'samples':totals['samples'],'loss':totals['loss_sum']/totals['samples']}
            save_json(out/'progresso.json',progress);print(json.dumps(progress),flush=True)
    return {'loss':totals['loss_sum']/max(totals['samples'],1),'samples':totals['samples']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--mirror-dir',type=Path,required=True)
    p.add_argument('--baseline-dir',type=Path,required=True)
    p.add_argument('--epochs',type=int,default=30);p.add_argument('--batch-size',type=int,default=16)
    p.add_argument('--save-every',type=int,default=25);p.add_argument('--patience',type=int,default=8)
    p.add_argument('--learning-rate',type=float,default=1e-4);p.add_argument('--width',type=int,default=416)
    p.add_argument('--height',type=int,default=320);p.add_argument('--seed',type=int,default=127)
    p.add_argument('--limit',type=int);p.add_argument('--resume',action='store_true')
    a=p.parse_args();out=a.output_dir;mirror=a.mirror_dir
    if min(a.width,a.height)<8 or a.width%8 or a.height%8 or min(a.batch_size,a.save_every,a.epochs)<1:raise ValueError('Parametros invalidos')
    cv2.setNumThreads(1);torch.set_num_threads(4);set_seed(a.seed);torch.backends.cudnn.benchmark=False
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    initial=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    groups={s:{r['subject'] for r in manifest[s]} for s in ('train','val','test')}
    assert all(not groups[x]&groups[y] for x,y in [('train','val'),('train','test'),('val','test')])
    config={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items() if k!='resume'}
    provenance={'manifest_sha256':sha256(manifest_path),'initial_checkpoint_sha256':sha256(initial),
                'script_sha256':sha256(Path(__file__)),'preprocessing_sha256':sha256(ROOT/'treinar_segmentacao_diversa.py')}
    if a.resume:
        protocol=json.loads((out/'protocolo.json').read_text(encoding='utf-8'))
        if protocol['configuration']!=config or protocol['provenance']!=provenance:raise ValueError('Retomada requer mesmos dados, fontes e parametros')
        state=torch.load(out/'retomada.pt',map_location='cpu',weights_only=True)
    else:
        out.mkdir(parents=True,exist_ok=False);mirror.mkdir(parents=True,exist_ok=False)
        protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'configuration':config,'provenance':provenance,
                  'scope':'Train/validation only. Test images and recognition scores never choose checkpoint.',
                  'selection':'Same minimum Dice over4 validation conditions; clean guard baseline-0.01; epoch0 included; patience8',
                  'augmentation':'Same geometry/photometry as diverse v1; deterministic seed per image and epoch for resume',
                  'baseline_reused_from':str(a.baseline_dir),'counts':{s:{'images':len(manifest[s]),'people':len(groups[s])} for s in groups},
                  'checkpoint_policy':'Save before training, every25batches and after epoch; model+AdamW+scheduler+order progress. Mirror latest recovery at50batches and immutable selected candidates.',
                  'interrupted_v1_note':'Previous process absent; only epoch0 survived. Partial epoch1 updates unavailable, not counted as completed training.',
                  'clinical_masks_available':False,'recognition_gain_measured':False}
        save_json(out/'protocolo.json',protocol);immutable_copy(out/'protocolo.json',mirror/'protocolo.json')
        for name in ('treinar_segmentacao_area.py','treinar_segmentacao_diversa.py'):
            immutable_copy(ROOT/name,out/name);immutable_copy(ROOT/name,mirror/name)
        evaluated=baseline_from(a.baseline_dir,provenance['manifest_sha256'],provenance['initial_checkpoint_sha256'],a.width,a.height,a.seed,a.limit)
        dice={mode:evaluated[mode]['macro_dice_all'] for mode in MODES}
        history=[{'epoch':0,'train_loss':None,'dice':dice,'eligible':True,'score':min(dice.values()),'reused_baseline':True}]
        state={'model':torch.load(initial,map_location='cpu',weights_only=True)['model'],'configuration':config,
               'next_epoch':1,'completed_batches':0,'totals':{'loss_sum':0.,'samples':0},'history':history,
               'best_epoch':0,'best_score':min(dice.values()),'baseline_clean':dice['clean'],'stale':0,
               'epoch':0,'validation':evaluated,'optimizer':None,'scheduler':None}
        save_checkpoint(out/'melhor_modelo.pt',state);save_checkpoint(out/'retomada.pt',state)
        immutable_copy(out/'melhor_modelo.pt',mirror/'candidato_epoca_00.pt')
        save_json(out/'historico.json',history);immutable_copy(out/'historico.json',mirror/'historico_ate_epoca_00.json')
    rows={s:manifest[s][:a.limit] if a.limit else manifest[s] for s in ('train','val')}
    train=EpochEyes(rows['train'],'train',a.width,a.height,a.seed)
    validation={mode:DataLoader(DiverseEyes(rows['val'],mode,a.width,a.height,a.seed),batch_size=a.batch_size,num_workers=0) for mode in MODES}
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=MulticlassUNet(8).to(device)
    model.load_state_dict(state['model'],strict=True)
    optimizer=torch.optim.AdamW(model.parameters(),lr=a.learning_rate,weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,a.epochs,eta_min=a.learning_rate*.1)
    if state['optimizer'] is not None:optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
    history=state['history'];best_epoch=state['best_epoch'];best=state['best_score'];stale=state['stale'];baseline=state['baseline_clean']
    next_epoch=state['next_epoch'];completed=state['completed_batches'];totals=state['totals']
    def snapshot(index,step,accum):
        payload={'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),
                 'configuration':config,'epoch':index,'next_epoch':index,'completed_batches':step,'totals':dict(accum),
                 'history':history,'best_epoch':best_epoch,'best_score':best,'baseline_clean':baseline,'stale':stale}
        save_checkpoint(out/'retomada.pt',payload)
        if step and (step%50==0 or step==math.ceil(len(train)/a.batch_size)):
            immutable_copy(out/'retomada.pt',mirror/f'retomada_epoca_{index:02}_lote_{step:04}.pt')
        return payload
    try:
        for index in range(next_epoch,a.epochs+1):
            save_json(out/'status.json',{'status':'running','pid':os.getpid(),'epoch':index,'best_epoch':best_epoch,'utc':datetime.now(timezone.utc).isoformat()})
            trained=train_pass(model,train,device,optimizer,a.batch_size,index,a.seed,completed,totals,a.save_every,
                               lambda step,accum:snapshot(index,step,accum),out)
            evaluated={mode:epoch(model,loader,device,progress=out/'progresso.json') for mode,loader in validation.items()}
            dice={m:r['macro_dice_all'] for m,r in evaluated.items()};score=min(dice.values());eligible=dice['clean']>=baseline-.01
            history.append({'epoch':index,'train_loss':trained['loss'],'dice':dice,'eligible':eligible,'score':score})
            scheduler.step()
            if eligible and score>best:best=score;best_epoch=index;stale=0
            else:stale+=1
            completed=0;totals={'loss_sum':0.,'samples':0}
            payload=snapshot(index+1,0,totals);payload.update(epoch=index,validation=evaluated)
            save_checkpoint(out/'retomada.pt',payload)
            if best_epoch==index:
                save_checkpoint(out/'melhor_modelo.pt',payload);immutable_copy(out/'melhor_modelo.pt',mirror/f'candidato_epoca_{index:02}.pt')
            save_json(out/'historico.json',history);save_json(out/f'validacao_epoca_{index:02}.json',evaluated)
            immutable_copy(out/'historico.json',mirror/f'historico_ate_epoca_{index:02}.json')
            immutable_copy(out/f'validacao_epoca_{index:02}.json',mirror/f'validacao_epoca_{index:02}.json')
            print(json.dumps(history[-1]),flush=True)
            if stale>=a.patience:break
        final={'status':'completed','best_epoch':best_epoch,'epochs_trained':history[-1]['epoch'],'best_score':best,
               'checkpoint_sha256':sha256(out/'melhor_modelo.pt'),'test_inference':False,'recognition_gain_measured':False}
        save_json(out/'CONCLUIDO.json',final);immutable_copy(out/'CONCLUIDO.json',mirror/'CONCLUIDO.json')
        save_json(out/'status.json',{'status':'completed','pid':os.getpid(),'best_epoch':best_epoch})
    except BaseException as error:
        save_json(out/'status.json',{'status':'failed','pid':os.getpid(),'error':repr(error)})
        raise


if __name__=='__main__':main()
