"""ResNet18 com margem angular para identidade ocular; treino UBIPr somente."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader,Dataset
from torchvision import models,transforms
from avaliar_dinov3_ubipr import masked_crop
from avaliar_robustez_reconhecimento import load_splits,identity,make_gallery,operating_threshold,metrics
from treinar_segmentacao_ubipr import Sample,decode_mask

ROOT=Path(__file__).resolve().parent

class IdentityEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone=models.resnet18(weights=None)
        self.backbone.fc=nn.Identity()
        self.projection=nn.Sequential(nn.Linear(512,256,bias=False),nn.BatchNorm1d(256))

    def forward(self,x):
        return nn.functional.normalize(self.projection(self.backbone(x)),dim=1)

class AngularHead(nn.Module):
    def __init__(self,classes,margin=.3,scale=30.):
        super().__init__(); self.weight=nn.Parameter(torch.empty(classes,256))
        nn.init.xavier_uniform_(self.weight); self.margin=margin; self.scale=scale

    def forward(self,features,labels):
        cosine=nn.functional.linear(nn.functional.normalize(features.float(),dim=1),
                                    nn.functional.normalize(self.weight.float(),dim=1)).clamp(-1+1e-6,1-1e-6)
        target=cosine.gather(1,labels[:,None])
        phi=target*math.cos(self.margin)-torch.sqrt((1-target.square()).clamp_min(1e-8))*math.sin(self.margin)
        phi=torch.where(target>math.cos(math.pi-self.margin),phi,target-math.sin(math.pi-self.margin)*self.margin)
        logits=cosine.scatter(1,labels[:,None],phi)
        return logits*self.scale

class Crops(Dataset):
    def __init__(self,rows,labels=None,augment=False):
        self.rows=rows; self.labels=labels; self.images=[]; self.valid=[]
        steps=[transforms.ToTensor()]
        if augment: steps += [transforms.RandomRotation(15),transforms.ColorJitter(brightness=.15,contrast=.15)]
        steps += [transforms.Normalize((.485,.456,.406),(.229,.224,.225))]
        self.transform=transforms.Compose(steps)
        for index,row in enumerate(rows):
            with Image.open(row.image) as im: image=im.convert('RGB')
            with Image.open(row.mask) as im: mask=decode_mask(im)==1
            self.valid.append(bool(mask.any()))
            self.images.append(np.asarray(masked_crop(image,mask).resize((128,128),Image.Resampling.BILINEAR)).copy())
            if (index+1)%1000==0: print(f'Preparo de recortes {index+1}/{len(rows)}',flush=True)
        self.positions=[i for i,valid in enumerate(self.valid) if valid or not augment]

    def __len__(self): return len(self.positions)

    def __getitem__(self,index):
        position=self.positions[index]
        label=self.labels[identity(self.rows[position])] if self.labels is not None else position
        return self.transform(self.images[position]),label

def evaluate(model,dataset,device,batch):
    model.eval(); vectors=[]
    with torch.inference_mode():
        for images,_ in DataLoader(dataset,batch_size=batch,shuffle=False,num_workers=0):
            with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):
                vector=model(images.to(device))
            vectors.append(nn.functional.normalize(vector.float(),dim=1).cpu().numpy())
    features=np.concatenate(vectors); valid=np.asarray(dataset.valid)
    if not np.isfinite(features).all(): raise FloatingPointError('Nonfinite embeddings')
    gallery,ids,failed=make_gallery(features,valid,dataset.rows)
    qi=[i for i,r in enumerate(dataset.rows) if r.session==2]
    labels=np.array([ids.index(identity(dataset.rows[i])) for i in qi])
    scores=(features[qi]@gallery.T).astype(np.float64)
    for eye in failed: scores[:,ids.index(eye)]=-2.
    impostor=np.ones_like(scores,dtype=bool); impostor[np.arange(len(qi)),labels]=False
    threshold=operating_threshold(scores[impostor & valid[qi,None] & (scores>-2)])
    measured,_,_=metrics(scores,labels,threshold,valid[qi])
    return dict(measured,threshold=threshold,failed_enrollments=len(failed))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20')
    parser.add_argument('--epochs',type=int,default=30)
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    if (out/'protocolo.json').exists(): raise ValueError('Experiment exists; preserve it and choose a new directory')
    random.seed(42); np.random.seed(42); torch.manual_seed(42); torch.set_num_threads(8)
    torch.backends.cudnn.benchmark=False
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    train=[Sample(**r) for r in manifest['train']]; val=load_splits(manifest)['val']
    if {r.subject for r in train}&{r.subject for r in val}: raise ValueError('Subject leakage')
    if args.smoke:
        train=train[:64]; eyes=sorted({identity(r) for r in val})[:4]
        val=[next(r for r in val if identity(r)==eye and r.session==session) for eye in eyes for session in (1,2)]
    identities=sorted({identity(r) for r in train}); labels={eye:i for i,eye in enumerate(identities)}
    weights=ROOT/'data/modelos/torch/hub/checkpoints/resnet18-f37072fd.pth'
    weight_hash=hashlib.sha256(weights.read_bytes()).hexdigest()
    if weight_hash!='f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec': raise ValueError('ImageNet weights changed')
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'technical_smoke':args.smoke,
        'round':'Exploratory follow-up after DINOv3 and HDBIF baselines; previously inspected tests are not fresh holdouts',
        'model':'ImageNet ResNet18 + Linear512to256 + BatchNorm + L2; angular margin classification head for training only',
        'margin_radians':.3,'scale':30,'seed':42,'max_epochs':args.epochs,'patience':8,
        'batch_size':64,'drop_last_training':True,'optimizer':'AdamW lr3e-4 weight_decay1e-4',
        'scheduler':'CosineAnnealingLR over requested epochs','crop':'Reference iris masked black, bbox margin25%, bilinear128x128, ImageNet normalization',
        'augmentation':'Training-only rotation +/-15 degrees, brightness and contrast +/-15%; no synthetic occlusion training',
        'missing_reference':'Exclude empty-mask samples from training only; retain failed validation queries',
        'selection':'Max validation TAR at empirical validation FMR<=1%, ties validation Rank1; no test features used in training',
        'validation_gallery':'Session1 centroid, session2 queries, identity subject+side, subject-disjoint from train',
        'device':str(device),'torch':str(torch.__version__),'imagenet_weights_sha256':weight_hash,
        'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'counts':{'train_images':len(train),'train_people':len({r.subject for r in train}),'train_eye_classes':len(labels),
                  'validation_images':len(val),'validation_people':len({r.subject for r in val}),'validation_eyes':len({identity(r) for r in val})},
        'fresh_domain_plan':'Nuclear Cataract separate subject-disjoint calibration/test, registered before recognition; acquisition dates unavailable, no longitudinal claims',
        'arcface_reference':'https://github.com/deepinsight/insightface/tree/master/recognition/arcface_torch'}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(protocol['counts']),flush=True)
    training=Crops(train,labels,augment=True); validation=Crops(val)
    (out/'auditoria.json').write_text(json.dumps({'train_empty_masks_excluded':len(train)-len(training),
        'validation_empty_masks_retained':sum(not v for v in validation.valid)},indent=2),encoding='utf-8')
    if len(training)<64: raise ValueError('Training batch incomplete')
    model=IdentityEncoder()
    state=torch.load(weights,map_location='cpu',weights_only=True)
    state.pop('fc.weight'); state.pop('fc.bias'); model.backbone.load_state_dict(state)
    model.to(device); head=AngularHead(len(labels)).to(device)
    optimizer=torch.optim.AdamW(list(model.parameters())+list(head.parameters()),lr=3e-4,weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=args.epochs)
    loader=DataLoader(training,batch_size=64,shuffle=True,num_workers=0,drop_last=True)
    history=[]; best=(-1.,-1.); stale=0; best_epoch=0; start=time.monotonic()
    for epoch in range(1,args.epochs+1):
        model.train(); head.train(); total=0.; batches=0
        for images,targets in loader:
            images=images.to(device); targets=targets.to(device); optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):
                features=model(images)
            loss=nn.functional.cross_entropy(head(features,targets),targets)
            if not torch.isfinite(loss): raise FloatingPointError('Nonfinite training loss')
            loss.backward(); nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5.)
            optimizer.step(); total+=float(loss.detach()); batches+=1
        measured=evaluate(model,validation,device,128); scheduler.step()
        history.append({'epoch':epoch,'train_loss':total/batches,**measured})
        temporary=out/'historico.csv.part'
        with temporary.open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(history[0])); writer.writeheader(); writer.writerows(history)
        temporary.replace(out/'historico.csv')
        score=(measured['tar'],measured['rank1'])
        if score>best:
            best=score; best_epoch=epoch; stale=0
            temporary=out/'melhor_modelo.pt.part'
            torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,
                        'validation':measured,'configuration':protocol},temporary)
            temporary.replace(out/'melhor_modelo.pt')
        else: stale+=1
        print(f"Epoch {epoch:02d}: loss={total/batches:.4f}, val_rank1={measured['rank1']:.4f}, val_TAR={measured['tar']:.4f}, elapsed={time.monotonic()-start:.0f}s",flush=True)
        if stale>=8: break
    result={'status':'training_completed_validation_selected_no_test_inference','best_epoch':best_epoch,
        'best_validation_tar':best[0],'best_validation_rank1':best[1],'epochs_completed':len(history),
        'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),
        'elapsed_seconds':time.monotonic()-start,'technical_smoke':args.smoke}
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()
