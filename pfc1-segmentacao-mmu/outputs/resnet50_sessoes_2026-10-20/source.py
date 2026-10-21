"""Treino novo ImageNet->UBIPr, sessoes balanceadas e contraste supervisionado."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,random,time
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

ROOT=Path(__file__).resolve().parent

def main():
    from reconhecedor_resnet50 import Encoder,SessionBatches,supervised_contrastive
    from treinar_identidade_iris import AngularHead
    from treinar_identidade_automatica import AutomaticCrops,evaluate
    from treinar_segmentacao_ubipr import Sample
    from avaliar_robustez_reconhecimento import identity,load_splits
    parser=argparse.ArgumentParser();parser.add_argument('--weights',type=Path,required=True);parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'resnet50_sessoes_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    random.seed(46);np.random.seed(46);torch.manual_seed(46);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    weight_hash=hashlib.sha256(args.weights.read_bytes()).hexdigest()
    assert weight_hash=='11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca'
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_path.read_text())
    train=[Sample(**r) for r in manifest['train']];val=load_splits(manifest)['val'];assert not {r.subject for r in train}&{r.subject for r in val}
    labels={e:i for i,e in enumerate(sorted({identity(r) for r in train}))};cache=ROOT/'data/cache_identidade_automatica_2026-10-20'
    tx=np.load(cache/'train_crops.npy',mmap_mode='r');tv=np.load(cache/'train_valid.npy');vx=np.load(cache/'val_crops.npy',mmap_mode='r');vv=np.load(cache/'val_valid.npy')
    assert len(tx)==len(train) and len(vx)==len(val)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'UBIPr primary; one query photo; development validation only, no test or occlusion inference',
        'architecture':'resnet50_gem3_256','initialization':'Official torchvision ImageNet1K_V2 backbone, fresh projection and training head; no UBIRIS weights',
        'preprocessing':'Frozen automatic U-Net crops from previous audited cache;128x128, ImageNet normalization; train-only rotation10 degrees brightness/contrast15%',
        'sampling':'16 eyes x4 captures, 4 shuffled rounds per epoch;2session1+2session2 if both present, otherwise4same-eye captures; replacement only if needed',
        'loss':'Angular CE +0.2 supervised contrastive temperature0.1; margin warmup0 epochs1-2,0.1 epochs3-4,0.2 epochs5-6,0.3 thereafter; scale30',
        'optimizer':'AdamW backbone1e-4, projection/head5e-4, wd1e-4, cosine40epochs, clip5; BF16 encoder FP32 losses',
        'seed':46,'max_epochs':40,'patience':10,'batch_size':64,
        'selection':'Max validation TAR at empirical FMR<=1%, tie Rank1; all session1 enrollment top3, every session2 query retained; stop patience only after epoch10',
        'counts':{'train_images':len(train),'valid_train_images':int(tv.sum()),'train_people':len({r.subject for r in train}),'train_eye_classes':len(labels),'val_queries':sum(r.session==2 for r in val)},
        'caveat':'Repeated development validation; cannot certify target90 or minimum area without independent confirmation',
        'weights_sha256':weight_hash,'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'cache_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cache.glob('*.npy')},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['reconhecedor_resnet50.py','treinar_identidade_automatica.py','treinar_identidade_iris.py','comparador_hdbif_lote.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    dataset=AutomaticCrops(tx,tv,train,labels,True);targets=np.array([labels[identity(train[i])] for i in dataset.positions]);sessions=np.array([train[i].session for i in dataset.positions])
    sampler=SessionBatches(targets,sessions);loader=DataLoader(dataset,batch_sampler=sampler,num_workers=0)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=Encoder();state=torch.load(args.weights,map_location='cpu',weights_only=True);state.pop('fc.weight');state.pop('fc.bias');model.backbone.load_state_dict(state);model.to(device)
    head=AngularHead(len(labels)).to(device)
    optimizer=torch.optim.AdamW([{'params':model.backbone.parameters(),'lr':1e-4},{'params':list(model.projection.parameters())+list(head.parameters()),'lr':5e-4}],weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=40);history=[];best=(-1.,-1.);best_epoch=0;stale=0;started=time.monotonic()
    for epoch in range(1,41):
        model.train();head.train();head.margin=min(.3,((epoch-1)//2)*.1);ce_total=0.;con_total=0.;batches=0
        for x,y in loader:
            y=y.to(device);optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):features=model(x.to(device))
            ce=nn.functional.cross_entropy(head(features,y),y);con=supervised_contrastive(features,y);loss=ce+.2*con
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5.);optimizer.step();ce_total+=float(ce.detach());con_total+=float(con.detach());batches+=1
        measured,scores=evaluate(model,vx,vv,val,device);scheduler.step();history.append({'epoch':epoch,'angular_ce':ce_total/batches,'contrastive_loss':con_total/batches,'margin':head.margin,**measured})
        temporary=out/'historico.csv.part'
        with temporary.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
        temporary.replace(out/'historico.csv');key=(measured['tar'],measured['rank1'])
        if key>best:
            best=key;best_epoch=epoch;stale=0;temporary=out/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'validation':measured,'configuration':protocol},temporary);temporary.replace(out/'melhor_modelo.pt');np.savez_compressed(out/'scores_melhor.npz',**scores)
        else:stale+=1
        print(f'Epoch{epoch:02d} CE={ce_total/batches:.4f} SupCon={con_total/batches:.4f} Rank1={measured["rank1"]:.4f} TAR={measured["tar"]:.4f} FMR={measured["far"]:.4f} elapsed={time.monotonic()-started:.0f}s',flush=True)
        if epoch>=10 and stale>=10:break
    result={'status':'resnet50_session_training_completed','best_epoch':best_epoch,'epochs_completed':len(history),'best_validation_tar':best[0],'best_validation_rank1':best[1],'test_inference':False,'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'elapsed_training_seconds':time.monotonic()-started}
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
