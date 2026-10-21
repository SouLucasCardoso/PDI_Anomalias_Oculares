"""Novo encoder de textura polar, treino UBIPr, sem tocar reconhecimento de teste."""
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

class PolarDataset(Dataset):
    def __init__(self,images,valid,rows,labels,augment):
        self.images=images;self.positions=np.flatnonzero(valid).tolist();self.rows=rows;self.labels=labels;self.augment=augment
        self.color=transforms.ColorJitter(brightness=.15,contrast=.15)
    def __len__(self):return len(self.positions)
    def __getitem__(self,index):
        from avaliar_robustez_reconhecimento import identity
        from textura_polar import cyclic_roll
        i=self.positions[index];image=self.images[i]
        if self.augment:image=cyclic_roll(image,random.randint(-32,32))
        value=transforms.functional.to_tensor(image)
        if self.augment:value=self.color(value)
        value=transforms.functional.normalize(value,[.485,.456,.406],[.229,.224,.225])
        return value,self.labels[identity(self.rows[i])]

def prepare(rows,segmenter,device,folder,split):
    from textura_polar import prepare_texture
    folder.mkdir(exist_ok=True,parents=True)
    images=np.lib.format.open_memmap(folder/(split+'_polar.npy'),mode='w+',dtype=np.uint8,shape=(len(rows),64,512,3));valid=np.zeros(len(rows),bool);audits=[]
    for start in range(0,len(rows),32):
        originals=[];inputs=[]
        for row in rows[start:start+32]:
            with Image.open(row.image) as im:rgb=im.convert('RGB')
            originals.append(rgb);inputs.append(np.asarray(rgb.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255)
        tensor=torch.from_numpy(np.stack(inputs).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=segmenter(tensor).argmax(1).cpu().numpy()==1
        for offset,(image,mask) in enumerate(zip(originals,masks)):
            i=start+offset;mask=np.asarray(Image.fromarray(mask).resize(image.size,Image.Resampling.NEAREST),dtype=bool)
            reason=None;metadata=None
            try:polar,metadata=prepare_texture(np.asarray(image),mask);valid[i]=True
            except ValueError as error:polar=np.full((64,512,3),127,np.uint8);reason=str(error)
            images[i]=polar;audits.append({'image':Path(rows[i].image).name,'valid':bool(valid[i]),'reason':reason,'geometry':metadata})
        if (start//32)%10==0:print(f'{split} polar {min(start+32,len(rows))}/{len(rows)}',flush=True)
    images.flush();np.save(folder/(split+'_valid.npy'),valid)
    (folder/(split+'_auditoria.json')).write_text(json.dumps(audits,indent=2),encoding='utf-8')
    return images,valid

def main():
    from treinar_identidade_iris import IdentityEncoder,AngularHead
    from treinar_identidade_automatica import evaluate
    from treinar_segmentacao_ubipr import MulticlassUNet,Sample
    from avaliar_robustez_reconhecimento import load_splits,identity
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    name='encoder_polar_smoke_2026-10-20' if args.smoke else 'encoder_polar_2026-10-20';out=ROOT/'outputs'/name;out.mkdir(exist_ok=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve existing experiment')
    random.seed(45);np.random.seed(45);torch.manual_seed(45);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_path.read_text())
    train=[Sample(**r) for r in manifest['train']];val=load_splits(manifest)['val'];assert not {r.subject for r in train}&{r.subject for r in val}
    labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in train}))}
    if args.smoke:
        train=train[:128];eyes=sorted({identity(r) for r in val})[:4];val=[next(r for r in val if identity(r)==eye and r.session==session) for eye in eyes for session in (1,2)]
    weights=ROOT/'data/modelos/torch/hub/checkpoints/resnet18-f37072fd.pth';unet=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    if hashlib.sha256(weights.read_bytes()).hexdigest()!='f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec':raise ValueError('ImageNet weights changed')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'technical_smoke':args.smoke,'scope':'New polar-domain identity training; train people only, repeated development validation; no test or occlusion inference',
        'model':'ImageNet ResNet18 + Linear512to256 + BatchNorm + L2, angular classification head; input3x64x512',
        'preprocessing':'Frozen U-Net320x240 FP32, iris class1 nearest to original; bbox50% ROI native resolution; grayscale CLAHEclip2 grid8x8; ellipse approximation of predicted mask, largest enclosed pupil hole or concentric fallback; polar64x512; invalid pixels127; grayscale repeated3 channels; ImageNet normalization',
        'fallback':'When no pupil hole: mask-bbox center and radius min(mask-bbox width,height)/8, geometric approximation only; no reference-mask correction',
        'augmentation':'Train only cyclic horizontal roll +/-32 columns, brightness/contrast +/-15%; no synthetic occlusion or arbitrary spatial rotation',
        'optimizer':'AdamW lr3e-4 wd1e-4, cosine30epochs, clip5, BF16 encoder/FP32 angular head',
        'margin':.3,'scale':30,'seed':45,'max_epochs':1 if args.smoke else 30,'patience':8,'batch_size':64,
        'selection':'Maximum validation TAR at separately calibrated empirical FMR<=1%, tie Rank1; all session1 enrollment, top3 similarities per eye, session2 queries; no automatic replacement of existing model',
        'failures':'Empty predicted masks or unusable geometry excluded only in training; all validation eyes/queries retained as failures',
        'counts':{'train_images':len(train),'train_people':len({r.subject for r in train}),'classes':len(labels),'val_images':len(val),'val_queries':sum(r.session==2 for r in val),'val_people':len({r.subject for r in val})},
        'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (weights,unet,manifest_path)},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['textura_polar.py','normalizacao_eliptica.py','treinar_identidade_iris.py','treinar_identidade_automatica.py','comparador_hdbif_lote.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');segmenter=MulticlassUNet(8).to(device).eval();segmenter.load_state_dict(torch.load(unet,map_location='cpu',weights_only=True)['model'])
    cache=ROOT/'data'/('cache_'+name);tx,tv=prepare(train,segmenter,device,cache,'train');vx,vv=prepare(val,segmenter,device,cache,'val');del segmenter
    if device.type=='cuda':torch.cuda.empty_cache()
    dataset=PolarDataset(tx,tv,train,labels,True);loader=DataLoader(dataset,batch_size=64,shuffle=True,num_workers=0,drop_last=True)
    if not len(loader):raise ValueError('Insufficient valid training images')
    (out/'auditoria.json').write_text(json.dumps({'excluded_train':int((~tv).sum()),'retained_validation_failures':int((~vv).sum()),'cache':str(cache),'class_order':labels},indent=2),encoding='utf-8')
    model=IdentityEncoder();state=torch.load(weights,map_location='cpu',weights_only=True);state.pop('fc.weight');state.pop('fc.bias');model.backbone.load_state_dict(state);model.to(device);head=AngularHead(len(labels)).to(device)
    optimizer=torch.optim.AdamW(list(model.parameters())+list(head.parameters()),lr=3e-4,weight_decay=1e-4);scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=30)
    history=[];best=(-1.,-1.);best_epoch=0;stale=0;started=time.monotonic()
    for epoch in range(1,protocol['max_epochs']+1):
        model.train();head.train();total=0.;batches=0
        for x,y in loader:
            optimizer.zero_grad(set_to_none=True);y=y.to(device)
            with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):features=model(x.to(device))
            loss=nn.functional.cross_entropy(head(features,y),y)
            if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
            loss.backward();nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5.);optimizer.step();total+=float(loss.detach());batches+=1
        measured,scores=evaluate(model,vx,vv,val,device);scheduler.step();history.append({'epoch':epoch,'train_loss':total/batches,**measured})
        temporary=out/'historico.csv.part'
        with temporary.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
        temporary.replace(out/'historico.csv')
        key=(measured['tar'],measured['rank1'])
        if key>best:
            best=key;best_epoch=epoch;stale=0;temporary=out/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'validation':measured,'configuration':protocol},temporary);temporary.replace(out/'melhor_modelo.pt');np.savez_compressed(out/'scores_melhor.npz',**scores)
        else:stale+=1
        print(f'Epoch{epoch:02d} loss={total/batches:.4f} Rank1={measured["rank1"]:.4f} TAR={measured["tar"]:.4f} FMR={measured["far"]:.4f} elapsed={time.monotonic()-started:.0f}s',flush=True)
        if stale>=8:break
    result={'status':'polar_training_completed_validation_selected','technical_smoke':args.smoke,'best_epoch':best_epoch,'epochs_completed':len(history),'best_validation_tar':best[0],'best_validation_rank1':best[1],'test_inference':False,'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'elapsed_training_seconds':time.monotonic()-started}
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
