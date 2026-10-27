"""Estabilidade externa com encoder U-Net congelado, ajuste só no treino original."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,random,time
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader,TensorDataset
from contorno_externo import outer_ellipse,ellipse_vector,segmentation_features,OuterCorrection
ROOT=Path(__file__).resolve().parent
CONDITIONS=[('clean','original',0),('upper10','oclusao_superior',10),('lower10','oclusao_inferior',10)]
WEIGHT=np.array([1.,1.,.04,.04,.04],np.float32)

def main():
    from avaliar_candidato_congelado import digest
    from avaliar_robustez_reconhecimento import perturb
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'contorno_externo_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());rows=manifest['train']
    old=json.loads((ROOT/'outputs/localizador_pupila_2026-10-22/protocolo.json').read_text());monitor=set(old['monitor_people']);fit=set(old['fit_people'])
    assert not monitor&fit and monitor|fit=={r['subject'] for r in rows}
    unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert digest(unet_file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Fit/monitor subsets of original TRAIN only. Same167fit/16monitor people as pupil work; monitor already used and seen by frozen U-Net. No recognition validation or test in fitting.',
        architecture='Frozen original U-Net enc3 adaptive8x8 gives2048 features of whole320x240 photo. Add5 baseline ellipse parameters in UNIT-IMAGE coordinates ->Linear2053x128/ReLU/Linear128x5; bounded residual [.25,.25,.7,.75,.75]tanh. Zero residual epoch0 reproduces baseline. Only head trained.',
        target='Largest outer ellipse fitted to original TRAIN iris annotation, affine-transformed into unit-image coordinates; center2,log-equivalent-radius,trace-free log-axis shape2. Annotation-derived visible-region proxy, NOT independently measured anatomical limbus.',
        preprocessing='Native RGB photograph, native exact gray128 upper/lower10% annotated-iris occlusion, then ordinary bilinear320x240 segmentation input. Same original target across3conditions. No crop or predicted bbox defines feature coordinates. Baseline outer ellipse from native nearest-upsampled predicted iris mask.',
        eligibility='Geometry-loss eligibility requires valid reference ellipse and predicted outer contour in ALL3conditions, before scoring. Exclusions only from geometry fitting/monitor; identity evaluation must retain all482queries including extraction failures.',
        training='Seed61,FP32,AdamW3e-4 wd1e-4,B128,max12epochs,patience3 after4. Weighted SmoothL1 [1,1,.04,.04,.04] on5params plus0.5 weighted clean/occluded paired MSE for consistency; equal3condition weights; no identity losses or labels. Features standardized by FIT clean mean/std only, baseline5 unstandardized.',
        selection='Epoch0 baseline. Select minimum WORST upper/lower monitor SmoothL1 subject clean<=1.05*epoch0 clean and both clean-to-occluded parameter drift<=epoch0 drift. Recognition gate requires nonzero selected epoch and strictly smaller worst occlusion monitor loss than epoch0. No architecture/loss/parameter search if fails.',
        inference_plan='Only outer ellipse of polar normalization changes; segmentation/support,RGB/native crops,inner ellipse,identity weights/fusion groups remain. Decode in whole-photo coordinates then translate to legacy ROI. Fixed guards: center in photo,axes>=2 and<2maxdim,pupil512samplescontained,nonempty polar support; else original outer, no query exclusion.',
        recognition_plan='If geometry gate passes, evaluate all482validation queries clean/upper10/lower10,one photo,side supplied,16same-side candidates. Primary candidate recalibrated CLEAN-only; old fixed calibration diagnostic. Clean Rank1/TAR>=90,FMR<=1 plus improved Rank1/TAR and FMR<=1 in BOTH occlusions for promotion eligibility. Never auto-promote or infer test.',
        fit_people=sorted(fit),monitor_people=sorted(monitor),conditions=CONDITIONS,manifest_sha256=digest(manifest_file),unet_sha256=digest(unet_file),script_sha256=digest(Path(__file__)),module_sha256=digest(ROOT/'contorno_externo.py'))
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());(out/'contorno_source.py').write_bytes((ROOT/'contorno_externo.py').read_bytes())
    torch.manual_seed(61);np.random.seed(61);random.seed(61);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    prepared={g:dict(features=[],baseline=[],target=[],records=[]) for g in ['fit','monitor']};exclusions={};started=time.monotonic()
    for start in range(0,len(rows),16):
        batchrows=rows[start:start+16];photos=[];references=[];targets=[]
        for row in batchrows:
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['image']).name) as im:photos.append(im.convert('RGB'))
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['mask']).name) as im:references.append(decode_mask(im)==1)
            try:
                target=ellipse_vector(outer_ellipse(references[-1]),*photos[-1].size)
                if not (0<target[0]<1 and 0<target[1]<1):raise ValueError('target_center_outside')
            except ValueError:target=None
            targets.append(target)
        batchfeatures=[];batchbaseline=[]
        for tag,kind,level in CONDITIONS:
            changed=[perturb(im,ref,kind,level)[0] for im,ref in zip(photos,references)]
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in changed]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():logits,features=segmentation_features(unet,x)
            masks=logits.argmax(1).cpu().numpy()==1;batchfeatures.append(features.cpu().numpy());bases=[]
            for im,small in zip(changed,masks):
                mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool)
                try:base=ellipse_vector(outer_ellipse(mask),*im.size)
                except ValueError:base=None
                bases.append(base)
            batchbaseline.append(bases)
        for i,row in enumerate(batchrows):
            group='monitor' if row['subject'] in monitor else 'fit'
            reason='invalid_reference_outer' if targets[i] is None else 'invalid_predicted_outer' if any(c[i] is None for c in batchbaseline) else None
            if reason:exclusions[group+':'+reason]=exclusions.get(group+':'+reason,0)+1;continue
            data=prepared[group];data['features'].append(np.stack([c[i] for c in batchfeatures]));data['baseline'].append(np.stack([c[i] for c in batchbaseline]));data['target'].append(targets[i]);data['records'].append(dict(image=Path(row['image']).name,subject=row['subject']))
        if start%320==0:print(json.dumps(dict(phase='prepare',images=min(start+16,len(rows)),total=len(rows),seconds=time.monotonic()-started)),flush=True)
    del unet
    for group,data in prepared.items():
        for key in ['features','baseline','target']:data[key]=np.stack(data[key])
        np.savez_compressed(out/f'inputs_{group}.npz',**{k:data[k] for k in ['features','baseline','target']})
        (out/f'rows_{group}.json').write_text(json.dumps(data['records'],indent=2),encoding='utf-8')
    audit=dict(exclusions=exclusions,fit_images=len(prepared['fit']['records']),monitor_images=len(prepared['monitor']['records']),fit_people=len(fit),monitor_people=len(monitor),all_original_train_images=len(rows))
    (out/'AUDITORIA_DADOS.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    mean=prepared['fit']['features'][:,0].mean(0);std=prepared['fit']['features'][:,0].std(0).clip(1e-5)
    for data in prepared.values():data['standardized']=(data['features']-mean)/std
    loader=DataLoader(TensorDataset(*[torch.from_numpy(prepared['fit'][k]) for k in ['standardized','baseline','target']]),batch_size=128,shuffle=True)
    monitor_x=torch.from_numpy(prepared['monitor']['standardized']).to(device);monitor_b=torch.from_numpy(prepared['monitor']['baseline']).to(device);monitor_t=torch.from_numpy(prepared['monitor']['target']).to(device)
    model=OuterCorrection().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);weight=torch.tensor(WEIGHT,device=device)
    def losses(pred,target):return (nn.functional.smooth_l1_loss(pred,target,reduction='none')*weight).mean(-1)
    def predict(x,b):return model(x.flatten(0,1),b.flatten(0,1)).reshape(len(x),3,5)
    baseline_losses=losses(monitor_b,monitor_t[:,None].expand_as(monitor_b)).mean(0).cpu().numpy()
    baseline_drift=(((monitor_b[:,1:]-monitor_b[:,:1])**2)*weight).mean((0,2)).cpu().numpy()
    best=float(max(baseline_losses[1:]));best_epoch=0;history=[];stale=0;selected_predictions=None
    for epoch in range(13):
        train_losses=[];model.train()
        if epoch:
            for x,b,t in loader:
                x=x.to(device);b=b.to(device);t=t.to(device);optimizer.zero_grad();pred=predict(x,b)
                fit_loss=losses(pred,t[:,None].expand_as(pred)).mean();consistent=(((pred[:,1:]-pred[:,:1])**2)*weight).mean();loss=fit_loss+.5*consistent
                if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();train_losses.append(float(loss.detach()))
        model.eval()
        with torch.inference_mode():
            pred=predict(monitor_x,monitor_b);values=losses(pred,monitor_t[:,None].expand_as(pred)).mean(0).cpu().numpy();drift=(((pred[:,1:]-pred[:,:1])**2)*weight).mean((0,2)).cpu().numpy()
        eligible=values[0]<=1.05*baseline_losses[0] and bool(np.all(drift<=baseline_drift+1e-12));worst=float(max(values[1:]))
        row=dict(epoch=epoch,train_loss=float(np.mean(train_losses)) if train_losses else None,clean_loss=float(values[0]),upper10_loss=float(values[1]),lower10_loss=float(values[2]),upper_drift=float(drift[0]),lower_drift=float(drift[1]),eligible=bool(eligible));history.append(row)
        if epoch==0 or (eligible and worst<best):
            best=worst;best_epoch=epoch;stale=0;selected_predictions=pred.cpu().numpy()
            torch.save(dict(model=model.state_dict(),feature_mean=torch.from_numpy(mean),feature_std=torch.from_numpy(std),epoch=epoch,configuration=protocol,monitor=row),out/'melhor_modelo.pt')
        elif epoch:stale+=1
        with (out/'historico.csv').open('w',newline='',encoding='utf-8') as f:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerows(history)
        print(json.dumps(row|dict(seconds=time.monotonic()-started)),flush=True)
        if epoch>=4 and stale>=3:break
    np.savez_compressed(out/'predicoes_monitor.npz',predictions=selected_predictions,baseline=prepared['monitor']['baseline'],target=prepared['monitor']['target'])
    final=dict(status='outer_contour_geometry_training_completed',best_epoch=best_epoch,epochs_trained=epoch,best_worst_occlusion_loss=best,baseline_losses=baseline_losses.tolist(),baseline_drift=baseline_drift.tolist(),recognition_validation_gate_passed=bool(best_epoch>0 and best<max(baseline_losses[1:])),checkpoint_sha256=digest(out/'melhor_modelo.pt'),data_audit=audit,test_inference=False,identity_validation_in_training=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()
