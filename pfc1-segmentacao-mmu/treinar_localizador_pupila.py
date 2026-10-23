"""Treina somente geometria circular; proxy de supervisao, sem identidades de teste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,hashlib,random,time
import cv2
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import Dataset,DataLoader
from localizador_pupila import PupilLocator,pupil_target,encode_roi
ROOT=Path(__file__).resolve().parent


class PupilInputs(Dataset):
    def __init__(self,images,targets,augment=False):self.images=images;self.targets=targets;self.augment=augment
    def __len__(self):return len(self.images)
    def __getitem__(self,i):
        image=np.array(self.images[i],copy=True)
        if self.augment:
            image[:,:,:3]=np.clip((image[:,:,:3].astype(np.float32)-128)*random.uniform(.85,1.15)+128+random.uniform(-20,20),0,255).astype(np.uint8)
            if random.random()<.5:
                contours,_=cv2.findContours(image[:,:,3],cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);binary=np.zeros((64,64),np.uint8);cv2.drawContours(binary,contours,-1,255,cv2.FILLED);image[:,:,3]=binary
        return torch.from_numpy(image.transpose(2,0,1).copy()).float()/255,torch.from_numpy(self.targets[i].copy())


def main():
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'outputs');a=p.parse_args()
    out=a.output_root/'localizador_pupila_2026-10-22';out.mkdir(parents=True,exist_ok=False);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());rows=manifest['train'];key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in rows if r['session']==1}&{key(r) for r in rows if r['session']==2};paired=sorted({r['subject'] for r in rows if key(r) in eligible})
    monitor=sorted(np.random.default_rng(57).permutation(paired)[:16].tolist());fit=sorted({r['subject'] for r in rows}-set(monitor));assert not set(fit)&set(monitor)
    unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(unet_file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Train split only for fitting/selection. No validation identity or test inference in locator training. Frozen original U-Net saw all original train including internal monitor; not an end-to-end unseen-person pipeline.',
        architecture='4-channel RGB+predicted-mask native ROI at64x64; Conv16/32/64, GroupNorm,2maxpool,spatial8x8,Linear128->3 sigmoid predicts centerXY and circle radius<=0.4ROI short side. Random initialization; no identity labels.',
        targets='Largest plausible enclosed hole in TRAIN iris annotation fitted ellipse -> area-equivalent circle. Proxy derived from annotations, NOT independently annotated anatomical pupil. Exclude samples with no closed plausible annotation hole or unusable predicted ROI from locator loss only. Native RGB remains unmasked for localization, NOT for identity features.',
        augmentation='RGB brightness/contrast15%,50% fill ALL holes of predicted mask channel using external contours; simulate lost pupil hole without modifying RGB or labels. No geometric augmentation, no generative restoration.',
        training='Seed57;167 fit people,16 disjoint monitor people from original train selected by seeded session eligibility. AdamW1e-3 wd1e-4,B64,FP32,15max epochs,patience4 after5. Weighted SmoothL1(centerX,centerY,radius) weights1,1,4; select minimum monitor loss.',
        gate='Only proceed to recognition validation if selected locator beats exact existing concentric baseline on mean monitor loss; no rerun/parameter search if gate fails.',
        recognition_plan='Change ONLY fallback pupil circle, retain ordinary holes, segmentation, RGB/native crops, outer ellipse, all identity weights and fusion weights. Evaluate original control,new fixed calibration,new CLEAN-only recalibration, all482 queries with16 supplied-side candidates. Same clean parameters/threshold upper/lower10. No test inference, filtering or automatic promotion.',
        fit_people=fit,monitor_people=monitor,manifest_sha256=sha(manifest_file),unet_sha256=sha(unet_file),script_sha256=sha(Path(__file__)),locator_source_sha256=sha(ROOT/'localizador_pupila.py'),
        source_context='Pupil localization literature includes PuRe (Santini et al.,2018),https://doi.org/10.1016/j.cviu.2018.02.002. This experiment is a custom supervised circle CNN, NOT PuRe or a reproduction of its reported results.')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());(out/'localizador_source.py').write_bytes((ROOT/'localizador_pupila.py').read_bytes())
    random.seed(57);np.random.seed(57);torch.manual_seed(57);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');started=time.monotonic()
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    prepared={name:dict(images=[],targets=[],baseline=[],records=[]) for name in ['fit','monitor']};excluded={}
    for start in range(0,len(rows),32):
        batch=[]
        for row in rows[start:start+32]:
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['image']).name) as im:batch.append(im.convert('RGB'))
        x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in batch]).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():predictions=unet(x).argmax(1).cpu().numpy()==1
        for offset,(im,small) in enumerate(zip(batch,predictions)):
            row=rows[start+offset];group='monitor' if row['subject'] in monitor else 'fit'
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['mask']).name) as annotation:reference=decode_mask(annotation)==1
            target=pupil_target(reference);mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool)
            reason=None
            if target is None:reason='annotation_has_no_plausible_closed_hole'
            elif not mask.any():reason='no_predicted_iris'
            if reason:excluded[group+':'+reason]=excluded.get(group+':'+reason,0)+1;continue
            encoded,bounds=encode_roi(np.asarray(im),mask);x0,y0,x1,y1=bounds;w=x1-x0;h=y1-y0
            value=np.array([(target[0]-x0)/w,(target[1]-y0)/h,target[2]/min(w,h)],np.float32)
            if not (0<value[0]<1 and 0<value[1]<1 and 0<value[2]<.4):excluded[group+':target_outside_roi']=excluded.get(group+':target_outside_roi',0)+1;continue
            y,x=np.where(mask);baseline=np.array([((x.min()+x.max())/2-x0)/w,((y.min()+y.max())/2-y0)/h,max(1,min(x.max()-x.min()+1,y.max()-y.min()+1)/8)/min(w,h)],np.float32)
            data=prepared[group];data['images'].append(encoded);data['targets'].append(value);data['baseline'].append(baseline);data['records'].append(dict(image=Path(row['image']).name,subject=row['subject']))
        if start%640==0:print(json.dumps(dict(phase='prepare',images=min(start+32,len(rows)),total=len(rows))),flush=True)
    del unet
    for group,data in prepared.items():
        for name in ['images','targets','baseline']:data[name]=np.stack(data[name])
        with (out/f'inputs_{group}.npz').open('wb') as stream:np.savez_compressed(stream,**{name:data[name] for name in ['images','targets','baseline']})
        (out/f'rows_{group}.json').write_text(json.dumps(data['records'],indent=2),encoding='utf-8')
    audit=dict(excluded=excluded,prepared={group:len(data['images']) for group,data in prepared.items()},fit_people=fit,monitor_people=monitor)
    (out/'AUDITORIA_DADOS.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    train=DataLoader(PupilInputs(prepared['fit']['images'],prepared['fit']['targets'],True),batch_size=64,shuffle=True,num_workers=0)
    valid=DataLoader(PupilInputs(prepared['monitor']['images'],prepared['monitor']['targets']),batch_size=128,shuffle=False,num_workers=0)
    weight=torch.tensor([1.,1.,4.],device=device)
    def loss_fn(pred,target):return (nn.functional.smooth_l1_loss(pred,target,reduction='none')*weight).mean()
    target=torch.from_numpy(prepared['monitor']['targets']).to(device);base=torch.from_numpy(prepared['monitor']['baseline']).to(device);baseline_loss=float(loss_fn(base,target));model=PupilLocator().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=1e-3,weight_decay=1e-4)
    history=[];best=float('inf');stale=0;best_epoch=None
    for epoch in range(1,16):
        model.train();losses=[]
        for images,targets in train:
            optimizer.zero_grad();loss=loss_fn(model(images.to(device)),targets.to(device));loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();losses.append(float(loss.detach()))
        model.eval();predictions=[]
        with torch.inference_mode():
            for images,_ in valid:predictions.append(model(images.to(device)).cpu())
        predictions=torch.cat(predictions).to(device);value=float(loss_fn(predictions,target));row=dict(epoch=epoch,train_loss=float(np.mean(losses)),monitor_loss=value,concentric_baseline_monitor_loss=baseline_loss)
        history.append(row)
        with (out/'historico.csv').open('w',encoding='utf-8',newline='') as stream:writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerows(history)
        if value<best:
            best=value;best_epoch=epoch;stale=0;temporary=out/'melhor_modelo.pt.part';torch.save(dict(model=model.state_dict(),epoch=epoch,configuration=protocol,monitor_loss=value),temporary);temporary.replace(out/'melhor_modelo.pt')
        else:stale+=1
        print(json.dumps(row|dict(seconds=time.monotonic()-started)),flush=True)
        if epoch>=5 and stale>=4:break
    final=dict(status='pupil_locator_training_completed',best_epoch=best_epoch,epochs_trained=epoch,best_monitor_loss=best,baseline_monitor_loss=baseline_loss,recognition_validation_gate_passed=best<baseline_loss,checkpoint_sha256=sha(out/'melhor_modelo.pt'),data_audit=audit,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)


if __name__=='__main__':main()
