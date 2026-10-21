"""Treino de Transformer polar por identidade, pessoas de treino apenas."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,random,time
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
ROOT=Path(__file__).resolve().parent

def main():
    from transformers import AutoModel
    from huggingface_hub import hf_hub_download
    from reconhecedor_transformer_polar import Encoder
    from reconhecedor_resnet50 import SessionBatches,supervised_contrastive
    from treinar_identidade_iris import AngularHead
    from treinar_encoder_polar import PolarDataset
    from treinar_identidade_automatica import evaluate
    from treinar_segmentacao_ubipr import Sample
    from avaliar_robustez_reconhecimento import load_splits,identity,MODEL_REVISION
    from avaliar_dinov3_ubipr import MODEL_ID
    from validar_lateralidade_informada import subset
    from validar_metrica_intra_classe import measure
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'transformer_polar_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    random.seed(49);np.random.seed(49);torch.manual_seed(49);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    folder=Path(hf_hub_download(MODEL_ID,'config.json',revision=MODEL_REVISION,local_files_only=True)).parent
    configuration=json.loads((folder/'config.json').read_text());configuration['num_hidden_layers']=6
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_path.read_text());train=[Sample(**r) for r in manifest['train']];val=load_splits(manifest)['val']
    assert not {r.subject for r in train}&{r.subject for r in val}
    labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in train}))};cache=ROOT/'data/cache_encoder_polar_2026-10-20'
    tx=np.load(cache/'train_polar.npy',mmap_mode='r');tv=np.load(cache/'train_valid.npy');vx=np.load(cache/'val_polar.npy',mmap_mode='r');vv=np.load(cache/'val_valid.npy')
    assert len(tx)==len(train) and len(vx)==len(val)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'architecture':'dino6_polar_spatial256','backbone_config':configuration,
        'scope':'UBIPr primary, single query photo, authorized correct side input. Train identities only; repeated development validation, no test or occlusion inference',
        'initialization':f'First6 layers of cached{MODEL_ID}@{MODEL_REVISION}; original final norm Identity; fresh tokenLayerNorm1024/Linear64/GELU and spatial flatten8192/Dropout0.2/Linear256/BN/L2. CLS and4registers excluded from output.',
        'preprocessing':'Previously audited automatic polar cache64x512, ImageNet normalization; train-only cyclic angular roll +/-32 and brightness/contrast15%; no square resize or generated texture',
        'sampling':'16 training eyes x4 captures,4rounds/epoch;2S1+2S2 if possible; all valid training eyes, no validation identity during fitting',
        'loss':'Angular CE+0.2 supervised contrastive temperature0.1; margin warmup0,0.1,0.2 per2epochs then0.3, scale30',
        'optimizer':'AdamW backbone2e-5, new token/projection2e-4, angularhead5e-4, wd1e-4, cosine30, clip5, BF16 forward FP32 losses and parameters',
        'seed':49,'max_epochs':30,'patience':8,'batch_size':64,
        'selection':'Side-informed16-eye TAR at validation empirical FMR<=1% over15same-side impostors, tie Rank1; keep full32 scores as control',
        'counts':{'train_images':len(train),'valid_train':int(tv.sum()),'train_people':len({r.subject for r in train}),'train_classes':len(labels),'val_queries':sum(r.session==2 for r in val)},
        'limitations':'Custom6-layer prefix, not official final DINOv3; pretraining web identities not individually audited. Repeated development not independent confirmation.',
        'model_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()},
        'cache_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cache.glob('*.npy')},
        'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['reconhecedor_transformer_polar.py','reconhecedor_resnet50.py','treinar_encoder_polar.py','validar_lateralidade_informada.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    backbone=AutoModel.from_pretrained(folder,dtype=torch.float32,local_files_only=True);assert len(backbone.model.layer)==24
    backbone.model.layer=nn.ModuleList(list(backbone.model.layer)[:6]);backbone.norm=nn.Identity()
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=Encoder(backbone).to(device);head=AngularHead(len(labels)).to(device)
    dataset=PolarDataset(tx,tv,train,labels,True);targets=np.array([labels[identity(train[i])] for i in dataset.positions]);sessions=np.array([train[i].session for i in dataset.positions]);sampler=SessionBatches(targets,sessions,seed=49);loader=DataLoader(dataset,batch_sampler=sampler,num_workers=0)
    optimizer=torch.optim.AdamW([{'params':model.backbone.parameters(),'lr':2e-5},{'params':list(model.token_projection.parameters())+list(model.projection.parameters()),'lr':2e-4},{'params':head.parameters(),'lr':5e-4}],weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=30);history=[];best=(-1.,-1.);best_epoch=0;stale=0;started=time.monotonic()
    for epoch in range(1,31):
        model.train();head.train();head.margin=min(.3,((epoch-1)//2)*.1);total=0.;batches=0
        for x,y in loader:
            y=y.to(device);optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):features=model(x.to(device))
            loss=nn.functional.cross_entropy(head(features,y),y)+.2*supervised_contrastive(features,y)
            if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
            loss.backward();nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5.);optimizer.step();total+=float(loss.detach());batches+=1
        full_metrics,scores=evaluate(model,vx,vv,val,device);side_scores,side_labels,_=subset(scores['scores'],val,sorted({identity(r) for r in val}));side=dict(scores=side_scores,labels=side_labels,valid=scores['valid']);measured=measure(side);scheduler.step()
        history.append({'epoch':epoch,'train_loss':total/batches,**measured,'rank1_full32':full_metrics['rank1'],'tar_full32':full_metrics['tar']})
        temporary=out/'historico.csv.part'
        with temporary.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
        temporary.replace(out/'historico.csv');key=(measured['tar'],measured['rank1'])
        if key>best:
            best=key;best_epoch=epoch;stale=0;temporary=out/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'validation':measured,'configuration':protocol},temporary);temporary.replace(out/'melhor_modelo.pt');np.savez_compressed(out/'scores_melhor.npz',**scores);np.savez_compressed(out/'scores_lateral_melhor.npz',**side)
        else:stale+=1
        print(f'Transformer epoch{epoch:02d} loss={total/batches:.4f} Rank1={measured["rank1"]:.4f} TAR={measured["tar"]:.4f} FMR={measured["far"]:.4f} elapsed={time.monotonic()-started:.0f}s',flush=True)
        if epoch>=8 and stale>=8:break
    final={'status':'polar_transformer_training_completed','best_epoch':best_epoch,'epochs_completed':len(history),'best_validation_tar':best[0],'best_validation_rank1':best[1],'test_inference':False,'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'elapsed_training_seconds':time.monotonic()-started}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
