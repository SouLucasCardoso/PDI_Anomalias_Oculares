"""Adaptacao do encoder a mascaras U-Net congeladas; somente treino/validacao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,random,time
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import Dataset,DataLoader
from torchvision import transforms
ROOT=Path(__file__).resolve().parent

class AutomaticCrops(Dataset):
    def __init__(self,images,valid,rows,labels,augment=False):
        self.images=images; self.valid=valid; self.rows=rows; self.labels=labels
        self.positions=[i for i in range(len(rows)) if valid[i] or not augment]
        steps=[transforms.ToTensor()]
        if augment:steps += [transforms.RandomRotation(10),transforms.ColorJitter(brightness=.15,contrast=.15)]
        self.transform=transforms.Compose(steps+[transforms.Normalize((.485,.456,.406),(.229,.224,.225))])
    def __len__(self):return len(self.positions)
    def __getitem__(self,index):
        from avaliar_robustez_reconhecimento import identity
        i=self.positions[index]
        return self.transform(self.images[i]),self.labels.get(identity(self.rows[i]),0)

def evaluate(model,images,valid,rows,device):
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold
    from comparador_hdbif_lote import aggregate
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None]; std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    model.eval(); features=[]
    for start in range(0,len(images),128):
        x=torch.from_numpy(np.asarray(images[start:start+128]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'): vector=model((x-mean)/std)
        features.append(nn.functional.normalize(vector.float(),dim=1).cpu().numpy())
    features=np.concatenate(features)
    if not np.isfinite(features).all():raise ValueError('Nonfinite embeddings')
    ids=sorted({identity(r) for r in rows}); gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name)); qi=[i for i,r in enumerate(rows) if r.session==2]
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids]
    labels=np.array([ids.index(identity(rows[i])) for i in qi]); raw=(features[qi]@features[gi].T).astype(np.float64); raw[:,~valid[gi]]=-2
    scores=aggregate(raw,groups,'top3'); qvalid=valid[qi]&(scores>-2).any(1)
    imp=np.ones_like(scores,dtype=bool);imp[np.arange(len(labels)),labels]=False; usable=imp&qvalid[:,None]&(scores>-2)
    threshold=operating_threshold(scores[usable]) if usable.any() else 2.
    result,correct,accepted=metrics(scores,labels,threshold,qvalid)
    result.update(threshold=threshold,joint_success=float((correct&accepted).mean()))
    return result,dict(scores=scores,labels=labels,valid=qvalid,correct=correct,accepted=accepted)

def prepare_crops(rows,segmenter,device,name,folder):
    from avaliar_dinov3_ubipr import masked_crop
    folder.mkdir(exist_ok=True,parents=True)
    images=np.lib.format.open_memmap(folder/(name+'_crops.npy'),mode='w+',dtype=np.uint8,shape=(len(rows),128,128,3)); valid=np.zeros(len(rows),dtype=bool)
    for start in range(0,len(rows),32):
        originals=[]; small=[]
        for row in rows[start:start+32]:
            with Image.open(row.image) as im: image=im.convert('RGB')
            originals.append(image); small.append(np.asarray(image.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255)
        x=torch.from_numpy(np.stack(small).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode(): masks=segmenter(x).argmax(1).cpu().numpy()==1
        for offset,(image,mask) in enumerate(zip(originals,masks)):
            mask=np.asarray(Image.fromarray(mask).resize(image.size,Image.Resampling.NEAREST),dtype=bool)
            i=start+offset;valid[i]=bool(mask.any()); images[i]=np.asarray(masked_crop(image,mask).resize((128,128),Image.Resampling.BILINEAR))
        if (start//32)%10==0:print(f'{name} automatic crops {min(start+32,len(rows))}/{len(rows)}',flush=True)
    images.flush();np.save(folder/(name+'_valid.npy'),valid)
    return images,valid

def main():
    from treinar_identidade_iris import IdentityEncoder,AngularHead
    from treinar_segmentacao_ubipr import MulticlassUNet,Sample
    from avaliar_robustez_reconhecimento import load_splits,identity
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    name='identidade_automatica_smoke_2026-10-20' if args.smoke else 'identidade_automatica_2026-10-20'
    out=ROOT/'outputs'/name;out.mkdir(exist_ok=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve existing experiment; do not overwrite')
    random.seed(43);np.random.seed(43);torch.manual_seed(43);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'; manifest=json.loads(manifest_path.read_text())
    train=[Sample(**r) for r in manifest['train']];val=load_splits(manifest)['val']
    labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in train}))}
    assert not {r.subject for r in train}&{r.subject for r in val}
    if args.smoke:
        train=train[:64];eyes=sorted({identity(r) for r in val})[:4]
        val=[next(r for r in val if identity(r)==eye and r.session==session) for eye in eyes for session in (1,2)]
    old=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20/melhor_modelo.pt';unet=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Training identities only, automatic validation top3 selection; no test or occlusion inference; exploratory after repeated validation development',
        'technical_smoke':args.smoke,'seed':43,'initialization':'Previous identity checkpoint, including classification head; train class ordering unchanged',
        'masks':'Frozen U-Net original RGB320x240/255; iris class1 nearest resize original; no reference mask in crop preparation',
        'crop':'Predicted iris black exterior, bbox margin25%, bilinear128x128, ImageNet normalization',
        'augmentation':'Train-only rotation +/-10 degrees, brightness/contrast +/-15%; no synthetic occlusion',
        'optimizer':'AdamW encoder lr3e-5, angular head lr1e-4, weight_decay1e-4; cosine schedule20epochs; clip5',
        'max_epochs':1 if args.smoke else 20,'patience':6,'batch_size':64,'margin':.3,'scale':30,
        'validation':'All eligible session1 captures; mean top3 valid similarities per eye; all session2 queries; validation empirical FMR<=1% recalibrated every checkpoint',
        'selection':'Baseline epoch0 included; maximum validation TAR, ties Rank1; keep baseline if adaptation never improves; no fresh independent confirmation',
        'failure_handling':'Exclude empty predicted crops in train only; retain every validation query/eye',
        'counts':{'train_images':len(train),'train_classes':len(labels),'train_people':len({r.subject for r in train}),'val_images':len(val),'val_queries':sum(r.session==2 for r in val),'val_people':len({r.subject for r in val})},
        'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (old,unet,manifest_path)},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['treinar_identidade_iris.py','treinar_segmentacao_ubipr.py','avaliar_robustez_reconhecimento.py','avaliar_dinov3_ubipr.py','comparador_hdbif_lote.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');segmenter=MulticlassUNet(8).to(device).eval()
    segmenter.load_state_dict(torch.load(unet,map_location='cpu',weights_only=True)['model'])
    cache=ROOT/'data'/('cache_'+name)
    tx,tv=prepare_crops(train,segmenter,device,'train',cache);vx,vv=prepare_crops(val,segmenter,device,'val',cache)
    del segmenter
    if device.type=='cuda':torch.cuda.empty_cache()
    dataset=AutomaticCrops(tx,tv,train,labels,True)
    (out/'auditoria.json').write_text(json.dumps({'excluded_empty_training':int((~tv).sum()),'retained_empty_validation':int((~vv).sum()),'cache':str(cache),'training_identity_order':labels},indent=2),encoding='utf-8')
    state=torch.load(old,map_location='cpu',weights_only=True)
    model=IdentityEncoder().to(device);model.load_state_dict(state['model'])
    head=AngularHead(len(labels)).to(device);head.load_state_dict(state['training_head']);del state
    optimizer=torch.optim.AdamW([{'params':model.parameters(),'lr':3e-5},{'params':head.parameters(),'lr':1e-4}],weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=20)
    loader=DataLoader(dataset,batch_size=64,shuffle=True,num_workers=0,drop_last=True)
    if not len(loader):raise ValueError('Training batch incomplete')
    history=[];best=(-1.,-1.);best_epoch=0;stale=0;started=time.monotonic()
    for epoch in range(protocol['max_epochs']+1):
        loss_total=0.;batches=0
        if epoch:
            model.train();head.train()
            for x,y in loader:
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'): features=model(x.to(device))
                loss=nn.functional.cross_entropy(head(features,y.to(device)),y.to(device))
                if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
                loss.backward();nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5.);optimizer.step();loss_total+=float(loss.detach());batches+=1
            scheduler.step()
        measured,scores=evaluate(model,vx,vv,val,device)
        history.append({'epoch':epoch,'train_loss':loss_total/batches if batches else None,**measured})
        temporary=out/'historico.csv.part'
        with temporary.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
        temporary.replace(out/'historico.csv')
        if epoch==0:np.savez_compressed(out/'scores_baseline.npz',**scores)
        score=(measured['tar'],measured['rank1'])
        if score>best:
            best=score;best_epoch=epoch;stale=0
            temporary=out/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'validation':measured,'configuration':protocol},temporary);temporary.replace(out/'melhor_modelo.pt')
            np.savez_compressed(out/'scores_melhor.npz',**scores)
        elif epoch:stale+=1
        print(f'Epoch{epoch:02d} loss={loss_total/batches if batches else 0:.4f} Rank1={measured["rank1"]:.4f} TAR={measured["tar"]:.4f} FMR={measured["far"]:.4f} {time.monotonic()-started:.0f}s',flush=True)
        if stale>=protocol['patience']:break
    result={'status':'automatic_finetuning_completed_validation_selected','technical_smoke':args.smoke,'best_epoch':best_epoch,'best_validation_tar':best[0],'best_validation_rank1':best[1],'epochs_completed':len(history)-1,'baseline':history[0],
        'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'elapsed_training_seconds':time.monotonic()-started,'test_inference':False}
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
