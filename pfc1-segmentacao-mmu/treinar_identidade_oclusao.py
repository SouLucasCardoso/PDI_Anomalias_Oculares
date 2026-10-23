"""Adapta identidade ao novo segmentador com oclusao e professor limpo de treino."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,random,time
import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset,DataLoader
from torchvision import transforms
ROOT=Path(__file__).resolve().parent

def occlude_crop(image,level,lower):
    output=np.array(image,copy=True);support=cv2.erode((output>0).any(2).astype(np.uint8),np.ones((3,3),np.uint8))>0;y,x=np.where(support)
    if len(x):
        order=np.lexsort((x,-y if lower else y));take=order[:round(len(x)*level/100)];output[y[take],x[take]]=128
    return output

class AdaptationInputs(Dataset):
    def __init__(self,images,valid,rows,labels,teacher):
        self.images=images;self.positions=np.flatnonzero(valid);self.rows=rows;self.labels=labels;self.teacher=teacher
        self.transform=transforms.Compose([transforms.ToTensor(),transforms.RandomRotation(10),transforms.ColorJitter(brightness=.1,contrast=.1),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    def __len__(self):return len(self.positions)
    def __getitem__(self,index):
        from avaliar_robustez_reconhecimento import identity
        i=int(self.positions[index]);image=np.array(self.images[i],copy=True)
        if random.random()<.5:image=occlude_crop(image,random.uniform(1,40),random.random()<.5)
        return self.transform(image),self.labels[identity(self.rows[i])],torch.from_numpy(self.teacher[i].copy())

def evaluate_conditions(model,conditions,rows,device):
    from avaliar_candidato_congelado import extract,global_scores
    from avaliar_robustez_reconhecimento import identity,operating_threshold,metrics
    from validar_lateralidade_informada import subset
    ids=sorted({identity(r) for r in rows});data={}
    for name,(images,valid) in conditions.items():
        full,qvalid=global_scores(extract(model,images,device),valid,rows);scores,labels,_=subset(full,rows,ids);data[name]=dict(scores=scores,labels=labels,valid=qvalid)
    clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(len(clean['labels'])),clean['labels']]=False;usable=imp&clean['valid'][:,None]&(clean['scores']>-2);threshold=operating_threshold(clean['scores'][usable]);results={}
    for name,c in data.items():
        r,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);r.update(threshold=threshold,joint_success=float((correct&accepted).mean()));c.update(correct=correct,accepted=accepted);results[name]=r
    return results,data

def main():
    from treinar_segmentacao_ubipr import Sample,MulticlassUNet,set_seed
    from treinar_identidade_iris import IdentityEncoder,AngularHead
    from treinar_identidade_automatica import prepare_crops
    from avaliar_candidato_congelado import extract
    from avaliar_robustez_reconhecimento import identity
    from reconhecedor_resnet50 import SessionBatches,supervised_contrastive
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'identidade_oclusao_segmentacao_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());manifest_hash=hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    def relocate(r):
        r=r.copy()
        for field in ['image','mask']:r[field]=str(ROOT/'data/ubipr/single_eye'/Path(r[field]).name)
        return Sample(**r)
    train=[relocate(r) for r in manifest['train']];val=[relocate(r) for r in manifest['val']];eligible={identity(r) for r in val if r.session==1}&{identity(r) for r in val if r.session==2};val=[r for r in val if identity(r) in eligible]
    assert not {r.subject for r in train}&{r.subject for r in val};labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in train}))}
    original=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20/melhor_modelo.pt';assert hashlib.sha256(original.read_bytes()).hexdigest()=='6060c164eada674712127830b2d188a9e6b4ed210f7b8d595e58fdfeb10387fc'
    segmenter=ROOT/'outputs/segmentacao_oclusao_2026-10-21/melhor_modelo.pt';seg_hash=hashlib.sha256(segmenter.read_bytes()).hexdigest();assert seg_hash=='8f126141f4dd7fc31352e9135b69e901454449dc5e4493ab5e973d4c8643035c'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Train/validation ONLY, no test images or identity labels used; new model never automatically replaces frozen candidate',
      'architecture':'ResNet18 identity256 initialized from frozen original, reuse original366-class angular head; all BatchNorm running statistics frozen, affine parameters learnable',
      'preprocessing':'New fixed robust U-Net predicts native-image iris masks; masked bbox25% resized128. Validation caches clean/native upper/lower10% have same robust segmenter and all482 queries.',
      'augmentation':'50% clean,50% gray128 loss uniform1..40% upper/lower equal within eroded3x3 nonblack predicted crop support; resized-grid training proxy, no anatomical percentage claim. Rotation+/-10degrees,color brightness/contrast10%. No generated/restored texture.',
      'teacher':'Frozen original encoder, original automatic segmentation clean training crops, paired same image. Teacher is used only for training, not validation/inference. Exclude invalid teacher/student training pairs only.',
      'loss':'Angular CE margin0.3 scale30 +0.2 supervised contrastive temperature0.1 +0.5 mean(1-cosine(student,clean teacher))',
      'optimizer':'AdamW backbone2e-5 projection/head1e-4 wd1e-4,cosine6epochs,clip5,BF16 student/FP32 head,seed52,16eyesx4images balanced sessions,4rounds/epoch',
      'selection':'Include epoch0; maximize worst-condition TAR then worst Rank1 then mean TAR across clean/upper10/lower10 validation. Each checkpoint threshold calibrated once on CLEAN validation empirical FMR<=1%, used unchanged for both occlusions. Clean Rank1/TAR each must remain >= epoch0 minus0.02. Report occluded FMR; this optimization is NOT release acceptance.',
      'limits':'Repeated development validation, single-encoder metrics not full fusion. No minimum area, no test inference, no weight/augmentation search.',
      'max_epochs':6,'patience':3,'counts':{'train':len(train),'train_people':len({r.subject for r in train}),'train_eyes':len(labels),'val_images':len(val),'val_queries':sum(r.session==2 for r in val)},
      'manifest_sha256':manifest_hash,'original_encoder_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'segmenter_sha256':seg_hash,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['treinar_identidade_automatica.py','treinar_identidade_iris.py','reconhecedor_resnet50.py','avaliar_candidato_congelado.py','validar_lateralidade_informada.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());set_seed(52);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    state=torch.load(original,map_location='cpu',weights_only=True);assert state['configuration']['manifest_sha256']==manifest_hash and state['training_head']['weight'].shape==(len(labels),256)
    cache=a.output_root.parent/'cache_identidade_oclusao_segmentacao_2026-10-21';cache.mkdir(parents=True,exist_ok=False);unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(segmenter,map_location='cpu',weights_only=True)['model']);tx,tv=prepare_crops(train,unet,device,'train',cache);del unet
    old_cache=ROOT/'data/cache_identidade_automatica_2026-10-20';old_images=np.load(old_cache/'train_crops.npy',mmap_mode='r');old_valid=np.load(old_cache/'train_valid.npy');assert len(old_images)==len(train)
    teacher=IdentityEncoder().to(device).eval();teacher.load_state_dict(state['model']);teacher_features=extract(teacher,old_images,device);np.save(cache/'teacher.npy',teacher_features);del teacher
    valid=tv&old_valid;dataset=AdaptationInputs(tx,valid,train,labels,teacher_features);targets=np.array([labels[identity(train[i])] for i in dataset.positions]);sessions=np.array([train[i].session for i in dataset.positions]);sampler=SessionBatches(targets,sessions,seed=52);loader=DataLoader(dataset,batch_sampler=sampler,num_workers=0)
    conditions={}
    for name,prefix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
        tag=prefix+'_segmentador_'+seg_hash[:12];folder=a.output_root.parent/f'cache_confirmacao_val{tag}_2026-10-21'
        validation_protocol=json.loads((ROOT/'outputs'/f'confirmacao_congelada_val{tag}_2026-10-21/protocolo.json').read_text());assert validation_protocol['unet_sha256']==seg_hash and validation_protocol['queries']==482
        with np.load(folder/'valid.npz') as z:conditions[name]=(np.load(folder/'rgb.npy',mmap_mode='r'),z['rgb'])
    (out/'auditoria.json').write_text(json.dumps({'excluded_training_pairs':int((~valid).sum()),'student_invalid':int((~tv).sum()),'teacher_invalid':int((~old_valid).sum()),'training_class_order':labels,'teacher_cache_sha256':hashlib.sha256((cache/'teacher.npy').read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    model=IdentityEncoder().to(device);model.load_state_dict(state['model']);head=AngularHead(len(labels)).to(device);head.load_state_dict(state['training_head']);optimizer=torch.optim.AdamW([{'params':model.backbone.parameters(),'lr':2e-5},{'params':model.projection.parameters(),'lr':1e-4},{'params':head.parameters(),'lr':1e-4}],weight_decay=1e-4);scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,6)
    best=(-1.,-1.,-1.);best_epoch=0;stale=0;history=[];baseline=None;started=time.monotonic()
    for epoch in range(7):
        losses=[]
        if epoch:
            model.train();head.train()
            for layer in model.modules():
                if isinstance(layer,nn.modules.batchnorm._BatchNorm):layer.eval()
            for images,targets,reference in loader:
                images=images.to(device);targets=targets.to(device,dtype=torch.long);reference=reference.to(device);optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):features=model(images)
                ce=nn.functional.cross_entropy(head(features.float(),targets),targets);contrast=supervised_contrastive(features,targets);retention=(1-nn.functional.cosine_similarity(features.float(),reference.float(),dim=1)).mean();loss=ce+.2*contrast+.5*retention
                if not torch.isfinite(loss):raise ValueError('Nonfinite adaptation loss')
                loss.backward();nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5);optimizer.step();losses.append(float(loss.detach()))
            scheduler.step()
        model.eval();evaluated,scores=evaluate_conditions(model,conditions,val,device)
        if baseline is None:baseline=evaluated['clean']
        allowed=all(evaluated['clean'][m]>=baseline[m]-.02 for m in ['rank1','tar']);key=(min(r['tar'] for r in evaluated.values()),min(r['rank1'] for r in evaluated.values()),float(np.mean([r['tar'] for r in evaluated.values()])))
        row={'epoch':epoch,'train_loss':float(np.mean(losses)) if losses else None,'clean_guard':allowed}
        for name,r in evaluated.items():row.update({f'{name}_{metric}':r[metric] for metric in ['rank1','tar','far']})
        history.append(row)
        with (out/'historico.csv').open('w',newline='',encoding='utf-8') as stream:writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerows(history)
        if epoch==0:
            for name,data in scores.items():np.savez_compressed(out/f'scores_baseline_{name}.npz',**data)
        if allowed and key>best:
            best=key;best_epoch=epoch;stale=0;temporary=out/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'configuration':protocol,'validation':evaluated},temporary);temporary.replace(out/'melhor_modelo.pt')
            for name,data in scores.items():np.savez_compressed(out/f'scores_melhor_{name}.npz',**data)
        elif epoch:stale+=1
        print(json.dumps(row|{'seconds':time.monotonic()-started}),flush=True)
        if stale>=3:break
    final={'status':'identity_occlusion_adaptation_completed','best_epoch':best_epoch,'epochs_trained':history[-1]['epoch'],'history':history,'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'test_inference':False,'frozen_candidate_replaced':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
