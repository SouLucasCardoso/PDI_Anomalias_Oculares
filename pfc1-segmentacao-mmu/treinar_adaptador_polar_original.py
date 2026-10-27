"""Adaptacao treino-only a oclusoes nativas, SEM trocar a normalizacao original."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,time
import numpy as np
from PIL import Image
import torch
from torch.utils.data import DataLoader,TensorDataset
from adaptador_polar import PolarAdapter,pooled_features,apply_adapter
from treinar_adaptador_polar import monitor_scores,CONDITIONS
ROOT=Path(__file__).resolve().parent
NAME='adaptador_polar_original_2026-10-23'

def eligible_clean(candidate,baseline):
    return all(candidate['clean'][k]>=baseline['clean'][k] for k in ['rank1','tar']) and candidate['clean']['far']<=.01

def advancement(candidate,baseline,epoch):
    return epoch>0 and eligible_clean(candidate,baseline) and all(candidate[t][k]>baseline[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']) and all(candidate[t]['far']<=.01 for t in ['upper10','lower10'])

def main():
    from avaliar_candidato_congelado import digest,WEIGHTS
    from avaliar_robustez_reconhecimento import perturb
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import Sample,MulticlassUNet,decode_mask
    from textura_polar import prepare_texture
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.output_root/NAME
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());rows=[Sample(**r) for r in manifest['train']]
    prior=a.output_root/'adaptador_polar_cadastro_fixo_2026-10-23';split=json.loads((prior/'protocolo.json').read_text());fit=set(split['fit_people']);monitor=set(split['monitor_people']);assert not fit&monitor and fit|monitor=={r.subject for r in rows}
    polar_file=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt';unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';cache=ROOT/'data/cache_encoder_polar_2026-10-20'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Original TRAIN7716photos only,167fit/16reused monitor people. Frozen encoders saw monitor historically, monitor previously reused, not independent generalization. No validation/test inference or fitting.',
            difference='Original automatic polar normalization in ALLconditions. No outer correction, learned geometry, secondary branch or SAM. Native gray128 upper/lower10% within annotated reference; annotation ONLYdefines synthetic intervention, not inference mask. Teacher is same-photo CLEAN original descriptor ONLYduringtraining; inference uses one observed photo.',
            architecture='Frozen U-Net and polar ResNet18/projection; same zero-initialized PolarAdapter512x128x256,0.05tanh residual+L2. FP32batch32features/512adapter. FIT-clean standardization only.',
            training='Seed63,AdamW3e-4 wd1e-4,B128photos,all3views;cosine same-photo teacher loss weights4/1/1 +.01residual-square;max12epochs,patience4after5. No identity-label loss, weight search or reusing rejected parameters.',
            monitor='ALL960photos/480S2queries,16same-side candidate eyes. All failures retained. Gallery in EVERYcondition explicitly replaced by clean S1 descriptors and validity. One clean FMR<=1% threshold per epoch, unchanged for both occlusions.',
            selection='Include epoch0; eligible CLEAN Rank1/TAR >= original epoch0 and FMR<=1%. Among eligible maximize worst-occluded TAR,then worstRank1,then mean teacher cosine occluded. Clean cosine diagnostic ONLY: originalclean teacher cosine already~1, no demand to improve alignment of identicalinputs. Save last epoch even if rejected.',
            gate='Selectedepoch>0,eligibleclean;Rank1 AND TAR strictly improve vs original in BOTH occlusions; FMR<=1% in both. Failure stops before validation. No automatic test/promotion/new minimum. A passing monitor only permits separately registered validation of polar component with other components original and fixed.',
            fit_pair_filter='Fit requires teacher plus ALL3native extractions valid before scoring. No query/monitor filtering. No cleancounterpartatoccludedinference.',
            fit_people=sorted(fit),monitor_people=sorted(monitor),manifest_sha256=digest(manifest_file),polar_sha256=digest(polar_file),unet_sha256=digest(unet_file),prior_clean_features_sha256=digest(prior/'cache_features.npz'),clean_polar_cache_sha256=digest(cache/'train_polar.npy'),clean_audit_sha256=digest(cache/'train_auditoria.json'),script_sha256=digest(Path(__file__)),dependencies_sha256={n:digest(ROOT/n) for n in ['adaptador_polar.py','treinar_adaptador_polar.py','textura_polar.py','normalizacao_eliptica.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py']})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Protocolo registrado antes da extracao/ajuste.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert digest(Path(__file__))==protocol['script_sha256'] and not (out/'CONCLUIDO.json').exists()
    for file,key in [(manifest_file,'manifest_sha256'),(polar_file,'polar_sha256'),(unet_file,'unet_sha256'),(prior/'cache_features.npz','prior_clean_features_sha256'),(cache/'train_polar.npy','clean_polar_cache_sha256'),(cache/'train_auditoria.json','clean_audit_sha256')]:assert digest(file)==protocol[key]
    for n,h in protocol['dependencies_sha256'].items():assert digest(ROOT/n)==h
    assert digest(polar_file)==WEIGHTS['polar'][1]
    assert not (fit|monitor)&{r['subject'] for r in manifest['val']+manifest['test']}
    audit=json.loads((cache/'train_auditoria.json').read_text());assert len(audit)==len(rows)==7716
    for row,record in zip(rows,audit):assert Path(row.image).name==record['image']
    images=np.load(cache/'train_polar.npy',mmap_mode='r');teacher_valid=np.load(cache/'train_valid.npy');np.testing.assert_array_equal(teacher_valid,[r['valid'] for r in audit])
    with np.load(prior/'cache_features.npz') as z:teacher=z['teacher'].copy();np.testing.assert_array_equal(teacher_valid,z['teacher_valid'])
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.manual_seed(63);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');started=time.monotonic()
    encoder=IdentityEncoder().to(device).eval();encoder.load_state_dict(torch.load(polar_file,map_location='cpu',weights_only=True)['model']);unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    raw=np.zeros((len(rows),3,512),np.float32);base=np.zeros((len(rows),3,256),np.float32);valid=np.zeros((len(rows),3),bool);max_teacher_difference=0.
    for start in range(0,len(rows),32):
        batch=rows[start:start+32];stop=start+len(batch);raw[start:stop,0],base[start:stop,0]=pooled_features(encoder,images[start:stop],device);valid[start:stop,0]=teacher_valid[start:stop]
        max_teacher_difference=max(max_teacher_difference,float(np.max(np.abs(base[start:stop,0]-teacher[start:stop]))))
        photos=[];references=[]
        for row in batch:
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(row.image).name) as im:photos.append(im.convert('RGB'))
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(row.mask).name) as im:references.append(decode_mask(im)==1)
        for j,(tag,kind,level) in enumerate(CONDITIONS[1:],1):
            changed=[perturb(im,ref,kind,level)[0] for im,ref in zip(photos,references)]
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in changed]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            textures=[]
            for offset,(im,small) in enumerate(zip(changed,masks)):
                mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool)
                try:texture=prepare_texture(np.asarray(im),mask)[0];valid[start+offset,j]=True
                except ValueError:texture=np.full((64,512,3),127,np.uint8)
                textures.append(texture)
            raw[start:stop,j],base[start:stop,j]=pooled_features(encoder,np.stack(textures),device)
        if start%640==0:print(json.dumps(dict(phase='prepare_original_geometry',photos=stop,total=len(rows),seconds=time.monotonic()-started)),flush=True)
    np.testing.assert_allclose(base[:,0],teacher,rtol=0,atol=1e-6);del encoder,unet
    fi=np.array([i for i,r in enumerate(rows) if r.subject in fit and teacher_valid[i] and valid[i].all()]);mi=np.array([i for i,r in enumerate(rows) if r.subject in monitor]);mr=[rows[i] for i in mi];assert len(mi)==960 and sum(r.session==2 for r in mr)==480
    np.savez_compressed(out/'cache_features.npz',raw=raw,base=base,teacher=teacher,valid=valid,teacher_valid=teacher_valid,fit_indices=fi,monitor_indices=mi)
    (out/'rows.json').write_text(json.dumps([dict(image=Path(r.image).name,subject=r.subject,side=r.side,session=r.session) for r in rows],indent=2),encoding='utf-8')
    data=dict(fit_valid_paired_photos=len(fi),fit_people=len(fit),fit_excluded_photos=sum(r.subject in fit for r in rows)-len(fi),monitor_photos=len(mi),monitor_queries=480,monitor_people=len(monitor),maximum_clean_teacher_difference=max_teacher_difference,precision='FP32')
    (out/'AUDITORIA_DADOS.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    mean=raw[fi,0].mean(0);std=raw[fi,0].std(0).clip(1e-5);loader=DataLoader(TensorDataset(torch.from_numpy((raw[fi]-mean)/std),torch.from_numpy(base[fi]),torch.from_numpy(teacher[fi])),batch_size=128,shuffle=True)
    torch.manual_seed(63);model=PolarAdapter().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);baseline=None;best=None;stale=0;history=[];best_epoch=0
    for epoch in range(13):
        losses=[];model.train()
        if epoch:
            for x,b,t in loader:
                x=x.to(device);b=b.to(device);t=t.to(device);optimizer.zero_grad();pred,delta=model(x.flatten(0,1),b.flatten(0,1));pred=pred.reshape(len(x),3,256)
                loss=((1-(pred*t[:,None]).sum(-1))*pred.new_tensor([4.,1.,1.])).sum(1).mean()/6+.01*delta.square().mean();assert torch.isfinite(loss)
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();losses.append(float(loss.detach()))
        model.eval();vectors={tag:apply_adapter(model,raw[mi,j],base[mi,j],mean,std,device) for j,(tag,_,_) in enumerate(CONDITIONS)};availability={tag:valid[mi,j] for j,(tag,_,_) in enumerate(CONDITIONS)}
        measured,scores=monitor_scores(vectors,availability,mr);cosines={}
        for j,(tag,_,_) in enumerate(CONDITIONS):
            paired=availability[tag]&teacher_valid[mi];cosines[tag]=float(np.sum(vectors[tag][paired].astype(np.float64)*teacher[mi][paired].astype(np.float64),1).mean())
        if baseline is None:
            baseline=measured
            for tag,s in scores.items():np.savez_compressed(out/f'scores_baseline_{tag}.npz',**s)
        eligible=eligible_clean(measured,baseline);key=(min(measured[t]['tar'] for t in ['upper10','lower10']),min(measured[t]['rank1'] for t in ['upper10','lower10']),np.mean([cosines[t] for t in ['upper10','lower10']]))
        record=dict(epoch=epoch,train_loss=float(np.mean(losses)) if losses else None,eligible=bool(eligible))
        for tag in measured:
            for k in ['rank1','tar','far']:record[tag+'_'+k]=measured[tag][k]
            record[tag+'_teacher_cosine']=cosines[tag]
        history.append(record)
        state=dict(model=model.state_dict(),raw_mean=torch.from_numpy(mean),raw_std=torch.from_numpy(std),epoch=epoch,monitor=measured,cosines=cosines,eligible=bool(eligible),configuration=protocol)
        if epoch==0 or eligible and (best is None or key>best):
            if eligible:best=key
            best_epoch=epoch;stale=0;torch.save(state,out/'melhor_modelo.pt')
            for tag,s in scores.items():np.savez_compressed(out/f'scores_selected_{tag}.npz',**s)
        elif epoch:stale+=1
        torch.save(state,out/'ultima_epoca.pt')
        for tag,s in scores.items():np.savez_compressed(out/f'scores_last_{tag}.npz',**s)
        with (out/'historico.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(record));w.writeheader();w.writerows(history)
        print(json.dumps(record),flush=True)
        if epoch>=5 and stale>=4:break
    chosen=torch.load(out/'melhor_modelo.pt',map_location='cpu',weights_only=True);gate=advancement(chosen['monitor'],baseline,best_epoch)
    final=dict(status='original_geometry_polar_adapter_completed',selected_epoch=best_epoch,epochs_trained=epoch,baseline_monitor=baseline,selected_monitor=chosen['monitor'],last_monitor=measured,selected_cosines=chosen['cosines'],recognition_validation_gate_passed=bool(gate),checkpoint_sha256=digest(out/'melhor_modelo.pt'),last_checkpoint_sha256=digest(out/'ultima_epoca.pt'),data_audit=data,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()
