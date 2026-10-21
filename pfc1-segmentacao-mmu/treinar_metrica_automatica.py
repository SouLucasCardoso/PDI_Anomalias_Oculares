"""CE angular + triplet hard, lotes balanceados; desenvolvimento val apenas."""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,json,random,time
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader,Sampler
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/identidade_metrica_automatica_2026-10-20'

def batch_hard(features,labels,margin=.2):
    features=nn.functional.normalize(features.float(),dim=1)
    distance=1-features@features.T
    same=labels[:,None]==labels[None,:];positive=same&~torch.eye(len(labels),device=labels.device,dtype=torch.bool)
    valid=positive.any(1)&(~same).any(1)
    if not valid.all():raise ValueError('Triplet batch requires repeated identities and negatives for each anchor')
    hard_positive=distance.masked_fill(~positive,-torch.inf).max(1).values
    hard_negative=distance.masked_fill(same,torch.inf).min(1).values
    return torch.relu(hard_positive-hard_negative+margin).mean()

class BalancedBatches(Sampler):
    def __init__(self,labels,people_per_batch=16,captures_per_eye=4,rounds=5,seed=44):
        self.groups={int(k):np.flatnonzero(labels==k) for k in np.unique(labels)}
        self.eyes=np.array(sorted(self.groups));self.p=people_per_batch;self.k=captures_per_eye;self.rounds=rounds;self.seed=seed;self.epoch=0
        if len(self.eyes)<self.p:raise ValueError('Too few training eye classes for balanced batch')
    def __len__(self):return self.rounds*(len(self.eyes)//self.p)
    def __iter__(self):
        rng=np.random.default_rng(self.seed+self.epoch);self.epoch+=1
        for _ in range(self.rounds):
            order=rng.permutation(self.eyes)
            for start in range(0,len(order)-self.p+1,self.p):
                yield [int(i) for eye in order[start:start+self.p] for i in rng.choice(self.groups[int(eye)],self.k,replace=len(self.groups[int(eye)])<self.k)]

def main():
    from treinar_identidade_automatica import AutomaticCrops,evaluate
    from treinar_identidade_iris import IdentityEncoder,AngularHead
    from treinar_segmentacao_ubipr import Sample
    from avaliar_robustez_reconhecimento import load_splits,identity
    random.seed(44);np.random.seed(44);torch.manual_seed(44);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    previous=ROOT/'outputs/identidade_automatica_2026-10-20'
    assert (previous/'CONCLUIDO.json').exists()
    cache=ROOT/'data/cache_identidade_automatica_2026-10-20';manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    manifest=json.loads(manifest_path.read_text());train=[Sample(**r) for r in manifest['train']];val=load_splits(manifest)['val']
    labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in train}))};assert not {r.subject for r in train}&{r.subject for r in val}
    checkpoint=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20/melhor_modelo.pt'
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cache.glob('*.npy')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory development after simple adaptation failed; train identities only; no test/occlusion inference',
        'initialization':'Original identity checkpoint including training head, not failed fine-tuning epoch',
        'loss':'Angular cross entropy + 0.5*batch-hard triplet, cosine distance, triplet margin0.2',
        'batch':'16 distinct eye classes x4 captures, five shuffled rounds per epoch, sampling replacement only when fewer than4 valid captures',
        'optimizer':'AdamW encoder1e-5 head5e-5, wd1e-4, clipping5, cosine20epochs',
        'max_epochs':20,'patience':6,'seed':44,
        'preprocessing':'Reuse frozen U-Net automatic128 crops; rotation10 degrees, brightness/contrast15% train only',
        'selection':'Baseline epoch0 included; max validation TAR, ties Rank1; validation top3 gallery with empirical FMR<=1% each epoch',
        'caveat':'Repeated validation development; no independent confirmation or minimum-area claim',
        'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'cache_sha256':hashes,'source_preparation_protocol_sha256':hashlib.sha256((previous/'protocolo.json').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['treinar_identidade_automatica.py','treinar_identidade_iris.py','comparador_hdbif_lote.py','avaliar_robustez_reconhecimento.py']}}
    OUT.mkdir(exist_ok=True)
    if (OUT/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    (OUT/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    tx=np.load(cache/'train_crops.npy',mmap_mode='r+');tv=np.load(cache/'train_valid.npy');vx=np.load(cache/'val_crops.npy',mmap_mode='r+');vv=np.load(cache/'val_valid.npy')
    dataset=AutomaticCrops(tx,tv,train,labels,True)
    targets=np.array([labels[identity(train[i])] for i in dataset.positions]);sampler=BalancedBatches(targets)
    loader=DataLoader(dataset,batch_sampler=sampler,num_workers=0)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    model=IdentityEncoder().to(device);model.load_state_dict(state['model']);head=AngularHead(len(labels)).to(device);head.load_state_dict(state['training_head']);del state
    optimizer=torch.optim.AdamW([{'params':model.parameters(),'lr':1e-5},{'params':head.parameters(),'lr':5e-5}],weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=20)
    best=(-1.,-1.);stale=0;best_epoch=0;history=[];started=time.monotonic()
    for epoch in range(21):
        ce_sum=0.;triplet_sum=0.;batches=0
        if epoch:
            model.train();head.train()
            for x,y in loader:
                y=y.to(device);optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'): features=model(x.to(device))
                ce=nn.functional.cross_entropy(head(features,y),y);triplet=batch_hard(features,y);loss=ce+.5*triplet
                if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
                loss.backward();nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5.);optimizer.step()
                ce_sum+=float(ce.detach());triplet_sum+=float(triplet.detach());batches+=1
            scheduler.step()
        measured,scores=evaluate(model,vx,vv,val,device)
        history.append({'epoch':epoch,'angular_ce':ce_sum/batches if batches else None,'triplet_loss':triplet_sum/batches if batches else None,**measured})
        temporary=OUT/'historico.csv.part'
        with temporary.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
        temporary.replace(OUT/'historico.csv')
        if epoch==0:np.savez_compressed(OUT/'scores_baseline.npz',**scores)
        score=(measured['tar'],measured['rank1'])
        if score>best:
            best=score;best_epoch=epoch;stale=0;temporary=OUT/'melhor_modelo.pt.part'
            torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'validation':measured,'configuration':protocol},temporary);temporary.replace(OUT/'melhor_modelo.pt');np.savez_compressed(OUT/'scores_melhor.npz',**scores)
        elif epoch:stale+=1
        print(f'Epoch{epoch:02d} CE={ce_sum/batches if batches else 0:.4f} triplet={triplet_sum/batches if batches else 0:.4f} Rank1={measured["rank1"]:.4f} TAR={measured["tar"]:.4f} elapsed={time.monotonic()-started:.0f}s',flush=True)
        if stale>=6:break
    result={'status':'metric_adaptation_completed_validation_selected','best_epoch':best_epoch,'epochs_completed':len(history)-1,'best_validation_tar':best[0],'best_validation_rank1':best[1],
        'baseline':history[0],'test_inference':False,'checkpoint_sha256':hashlib.sha256((OUT/'melhor_modelo.pt').read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-started}
    (OUT/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
