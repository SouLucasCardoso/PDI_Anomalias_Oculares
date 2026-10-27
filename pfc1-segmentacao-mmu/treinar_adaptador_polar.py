"""Pareamento nativo treino-only: nova geometria -> descritor limpo original."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,random,time
import numpy as np
from PIL import Image
import torch
from torch.utils.data import DataLoader,TensorDataset
from adaptador_polar import PolarAdapter,pooled_features,apply_adapter
from contorno_externo import OuterCorrection,outer_ellipse,ellipse_vector,segmentation_features,refined_textures
ROOT=Path(__file__).resolve().parent
CONDITIONS=[('clean','original',0),('upper10','oclusao_superior',10),('lower10','oclusao_inferior',10)]

def monitor_scores(vectors,valid,rows):
    from avaliar_candidato_congelado import global_scores
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold
    from validar_lateralidade_informada import subset
    ids=sorted({identity(r) for r in rows});data={};results={}
    gallery=np.array([i for i,r in enumerate(rows) if r.session==1])
    for tag,_,_ in CONDITIONS:
        current=np.array(vectors[tag],copy=True);current_valid=np.array(valid[tag],copy=True)
        current[gallery]=vectors['clean'][gallery];current_valid[gallery]=valid['clean'][gallery]
        full,qvalid=global_scores(current,current_valid,rows);scores,labels,_=subset(full,rows,ids);data[tag]=dict(scores=scores,labels=labels,valid=qvalid)
    c=data['clean'];imp=np.ones_like(c['scores'],bool);imp[np.arange(len(c['labels'])),c['labels']]=False
    threshold=operating_threshold(c['scores'][imp&c['valid'][:,None]&(c['scores']>-2)])
    for tag,c in data.items():
        result,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);result.update(threshold=threshold,correct=int(correct.sum()),accepted=int(accepted.sum()))
        data[tag].update(correct=correct,accepted=accepted);results[tag]=result
    return results,data

def main():
    from avaliar_candidato_congelado import digest,WEIGHTS
    from avaliar_robustez_reconhecimento import perturb
    from treinar_segmentacao_ubipr import Sample,MulticlassUNet,decode_mask
    from treinar_identidade_iris import IdentityEncoder
    from textura_polar import prepare_texture
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--cache-from',type=Path);a=p.parse_args();out=a.output_root/'adaptador_polar_cadastro_fixo_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());rows=[Sample(**r) for r in manifest['train']];assert len(rows)==7716
    geometry_folder=a.output_root/'contorno_consistente_2026-10-23';geometry_done=json.loads((geometry_folder/'CONCLUIDO.json').read_text());geometry_file=geometry_folder/'melhor_modelo.pt';assert digest(geometry_file)==geometry_done['checkpoint_sha256']
    gs=torch.load(geometry_file,map_location='cpu',weights_only=True);fit=set(gs['configuration']['fit_people']);monitor=set(gs['configuration']['monitor_people']);assert not fit&monitor and fit|monitor=={r.subject for r in rows}
    assert not (fit|monitor)&{r['subject'] for r in manifest['val']}
    polar_file=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt';assert digest(polar_file)==WEIGHTS['polar'][1]
    unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert digest(unet_file)==gs['configuration']['unet_sha256']
    old_cache=ROOT/'data/cache_encoder_polar_2026-10-20';audit=json.loads((old_cache/'train_auditoria.json').read_text());assert all(Path(r.image).name==v['image'] for r,v in zip(rows,audit)) and len(audit)==len(rows)
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Original TRAIN only:167fit/16reused internal monitor people. Frozen polar encoder and U-Net saw monitor in prior training; geometry selected on same monitor. Not independent generalization. No validation/test fitting.',
        architecture='Frozen polar ResNet18 pooled512 and existing projected256; FIT-clean standardized pooled512 ->Linear512x128/ReLU/Linear128x256 ->0.05tanh residual; add to original projected vector then L2. Last layer initialized zero. Only residual adapter trained.',
        target='Original automatic-geometry CLEAN polar descriptor of SAME TRAIN photo, FP32. Candidate inputs clean/native upper10/lower10 with previously selected consistent outer correction. Clean counterpart is teacher ONLY in training; inference uses one photo. No RGB generation or restoration.',
        training='Seed63,AdamW3e-4 wd1e-4,B128photos with all3views,max12epochs,patience4 after5. Mean same-photo cosine loss weights[4,1,1]/6 plus0.01mean(residual squared). No identity-label loss or parameter/weight search.',
        precision='Frozen backbone/projection FP32batch32maximum; adapter FP32batch512maximum. Explicit FP32 unadapted control needed in validation, original benchmark used BF16. Same precision in teacher/candidate/monitor/validation.',
        eligibility='Fit pairs require teacher AND all3candidate polar extractions valid, before descriptor scoring. Monitor retains ALL960photos/480S2queries and own per-condition validity, failures reject. No score filtering. Cosine diagnostics use paired-valid photos only.',
        calibration='Each monitor method gets ONE empirical FMR<=1% threshold on CLEAN only, unchanged for upper/lower10. Same-side16candidate eyes. In EVERY condition S1 descriptors and validity are explicitly copied from CLEAN; ONLY S2 queries use their condition. No combined query images.',
        selection='Include zero-adapter epoch0. Eligible epoch must have clean Rank1/TAR >= BOTH original-clean teacher and unadapted-new-geometry control, and clean teacher cosine >= unadapted. Among eligible maximize worst occluded TAR then worst occluded Rank1 then mean occluded teacher cosine. Stop as registered.',
        recognition_gate='Selected epoch>0 AND eligibility AND Rank1/TAR strictly better than unadapted-new-geometry control in BOTH occlusions AND paired teacher cosine improves in BOTH occlusions. If fails no validation inference. No automatic promotion or test evaluation.',
        validation_plan='If monitor passes: all482validationqueries/480S1photos; modify only polar GLOBAL score component of prior outer-geometry fusion; other8components unchanged. Original frozen control, outer-FP32-unadapted control, outer-adapted. Each candidate calibrated CLEAN-only; equal8group weights fixed. Need clean Rank1/TAR>=90,FMR<=1 and both occluded Rank1/TAR improvements with FMR<=1 to advance; separate all3conditions90% flag.',
        cache_from=str(a.cache_from) if a.cache_from else None,technical_correction='Earlier preparation run used correct images/features but monitor incorrectly occluded enrollment. Its recognition results are INVALID and never used for validation or hyperparameter choice. Reuse ONLY its feature cache after provenance checks. Head seed reset63 immediately before construction so preparation/cache mode cannot change initialization.',
        fit_people=sorted(fit),monitor_people=sorted(monitor),conditions=CONDITIONS,manifest_sha256=digest(manifest_file),geometry_checkpoint_sha256=digest(geometry_file),polar_encoder_sha256=digest(polar_file),unet_sha256=digest(unet_file),teacher_audit_sha256=digest(old_cache/'train_auditoria.json'),script_sha256=digest(Path(__file__)),dependencies_sha256={n:digest(ROOT/n) for n in ['adaptador_polar.py','contorno_externo.py','textura_polar.py','avaliar_candidato_congelado.py','normalizacao_eliptica.py','validar_lateralidade_informada.py']})
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());(out/'adapter_source.py').write_bytes((ROOT/'adaptador_polar.py').read_bytes())
    torch.manual_seed(63);np.random.seed(63);random.seed(63);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');started=time.monotonic()
    if a.cache_from:
        cached_protocol=json.loads((a.cache_from/'protocolo.json').read_text())
        for key in ['manifest_sha256','geometry_checkpoint_sha256','polar_encoder_sha256','unet_sha256','teacher_audit_sha256']:
            assert cached_protocol[key]==protocol[key]
        cached_rows=json.loads((a.cache_from/'rows.json').read_text())
        assert all(v['image']==Path(r.image).name and v['subject']==r.subject and v['side']==r.side and v['session']==r.session for r,v in zip(rows,cached_rows)) and len(cached_rows)==len(rows)
        with np.load(a.cache_from/'cache_features.npz') as z:
            raw=z['raw'];base=z['base'];teacher=z['teacher'];valid=z['valid'];teacher_valid=z['teacher_valid']
        cached_audit=json.loads((a.cache_from/'AUDITORIA_DADOS.json').read_text());assert cached_audit['clean_original_polar_inputs_exact']
        guards=cached_audit['guards']
        (out/'PROVENIENCIA_CACHE.json').write_text(json.dumps(dict(source=str(a.cache_from),cache_sha256=digest(a.cache_from/'cache_features.npz'),source_protocol_sha256=digest(a.cache_from/'protocolo.json'),source_code_sha256=digest(a.cache_from/'source.py'),recognition_results_reused=False),indent=2),encoding='utf-8')
        print('Features reutilizadas; resultados do monitor anterior descartados.',flush=True)
    else:
        geometry=OuterCorrection().to(device).eval();geometry.load_state_dict(gs['model']);gm=gs['feature_mean'].to(device);gst=gs['feature_std'].to(device)
        unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
        encoder=IdentityEncoder().to(device).eval();encoder.load_state_dict(torch.load(polar_file,map_location='cpu',weights_only=True)['model'])
        teacher_images=np.load(old_cache/'train_polar.npy',mmap_mode='r');teacher_valid=np.load(old_cache/'train_valid.npy');np.testing.assert_array_equal(teacher_valid,np.array([r['valid'] for r in audit]))
        raw=np.zeros((len(rows),3,512),np.float32);base=np.zeros((len(rows),3,256),np.float32);teacher=np.zeros((len(rows),256),np.float32);valid=np.zeros((len(rows),3),bool);guards={}
        for start in range(0,len(rows),32):
            batch=rows[start:start+32];photos=[];references=[]
            for row in batch:
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(row.image).name) as im:photos.append(im.convert('RGB'))
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(row.mask).name) as im:references.append(decode_mask(im)==1)
            _,teacher[start:start+len(batch)]=pooled_features(encoder,teacher_images[start:start+len(batch)],device)
            for view,(tag,kind,level) in enumerate(CONDITIONS):
                changed=[perturb(im,mask,kind,level)[0] for im,mask in zip(photos,references)]
                x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in changed]).transpose(0,3,1,2).copy()).to(device)
                with torch.inference_mode():logits,features=segmentation_features(unet,x)
                masks=[];baseline=[]
                for im,small in zip(changed,logits.argmax(1).cpu().numpy()==1):
                    mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool);masks.append(mask)
                    try:b=ellipse_vector(outer_ellipse(mask),*im.size)
                    except ValueError:b=np.zeros(5,np.float32)
                    baseline.append(b)
                with torch.inference_mode():pred=geometry((features-gm)/gst,torch.from_numpy(np.stack(baseline)).to(device)).cpu().numpy()
                textures=[]
                for offset,(im,mask,value) in enumerate(zip(changed,masks,pred)):
                    i=start+offset
                    try:
                        if view==0:
                            old,_=prepare_texture(np.asarray(im),mask);assert teacher_valid[i];np.testing.assert_array_equal(old,teacher_images[i])
                        polar,_,_,_,reason=refined_textures(np.asarray(im),mask,value);valid[i,view]=True
                    except ValueError:
                        if view==0:assert not teacher_valid[i]
                        polar=np.full((64,512,3),127,np.uint8);reason='invalid_polar'
                    guards[tag+':'+reason]=guards.get(tag+':'+reason,0)+1;textures.append(polar)
                raw[start:start+len(batch),view],base[start:start+len(batch),view]=pooled_features(encoder,np.stack(textures),device)
            if start%320==0:print(json.dumps(dict(phase='prepare',images=min(start+32,len(rows)),total=len(rows),seconds=time.monotonic()-started)),flush=True)
        del unet,geometry,encoder
    fit_indices=np.array([i for i,r in enumerate(rows) if r.subject in fit and teacher_valid[i] and valid[i].all()]);monitor_indices=np.array([i for i,r in enumerate(rows) if r.subject in monitor]);monitor_rows=[rows[i] for i in monitor_indices]
    assert len(monitor_indices)==960 and sum(r.session==2 for r in monitor_rows)==480
    assert not set(fit_indices)&set(monitor_indices)
    mean=raw[fit_indices,0].mean(0);std=raw[fit_indices,0].std(0).clip(1e-5)
    np.savez_compressed(out/'cache_features.npz',raw=raw,base=base,teacher=teacher,valid=valid,teacher_valid=teacher_valid,fit_indices=fit_indices,monitor_indices=monitor_indices)
    records=[dict(image=Path(r.image).name,subject=r.subject,side=r.side,session=r.session) for r in rows];(out/'rows.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    data_audit=dict(fit_valid_paired_images=len(fit_indices),fit_people=len(fit),monitor_images=len(monitor_indices),monitor_people=len(monitor),monitor_queries=480,fit_excluded_images=sum(r.subject in fit for r in rows)-len(fit_indices),guards=guards,clean_original_polar_inputs_exact=True)
    (out/'AUDITORIA_DADOS.json').write_text(json.dumps(data_audit,indent=2),encoding='utf-8')
    loader=DataLoader(TensorDataset(torch.from_numpy((raw[fit_indices]-mean)/std),torch.from_numpy(base[fit_indices]),torch.from_numpy(teacher[fit_indices])),batch_size=128,shuffle=True)
    monitor_raw=raw[monitor_indices];monitor_base=base[monitor_indices];monitor_teacher=teacher[monitor_indices];monitor_valid={tag:valid[monitor_indices,j] for j,(tag,_,_) in enumerate(CONDITIONS)}
    original,original_data=monitor_scores({tag:monitor_teacher for tag,_,_ in CONDITIONS},{tag:teacher_valid[monitor_indices] for tag,_,_ in CONDITIONS},monitor_rows)
    torch.manual_seed(63)
    model=PolarAdapter().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    baseline=None;cosine0=None;best=None;best_epoch=0;stale=0;history=[];selected_vectors=None;selected_metrics=None
    for epoch in range(13):
        losses=[];model.train()
        if epoch:
            for x,b,t in loader:
                x=x.to(device);b=b.to(device);t=t.to(device);optimizer.zero_grad();pred,delta=model(x.flatten(0,1),b.flatten(0,1));pred=pred.reshape(len(x),3,256)
                alignment=1-(pred*t[:,None]).sum(-1);loss=(alignment*alignment.new_tensor([4.,1.,1.])).sum(1).mean()/6+.01*delta.square().mean()
                if not torch.isfinite(loss):raise ValueError('Nonfinite adapter loss')
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();losses.append(float(loss.detach()))
        model.eval();vectors={tag:apply_adapter(model,monitor_raw[:,j],monitor_base[:,j],mean,std,device) for j,(tag,_,_) in enumerate(CONDITIONS)}
        measured,scores=monitor_scores(vectors,monitor_valid,monitor_rows);cosines={}
        for j,(tag,_,_) in enumerate(CONDITIONS):
            paired=monitor_valid[tag]&teacher_valid[monitor_indices];cosines[tag]=float(np.sum(vectors[tag][paired].astype(np.float64)*monitor_teacher[paired].astype(np.float64),1).mean())
        if baseline is None:baseline=measured;cosine0=cosines
        eligible=all(measured['clean'][k]>=control['clean'][k] for k in ['rank1','tar'] for control in [original,baseline]) and cosines['clean']>=cosine0['clean']
        key=(min(measured[c]['tar'] for c in ['upper10','lower10']),min(measured[c]['rank1'] for c in ['upper10','lower10']),float(np.mean([cosines[c] for c in ['upper10','lower10']])))
        row=dict(epoch=epoch,train_loss=float(np.mean(losses)) if losses else None,eligible=bool(eligible))
        for tag in measured:
            for k in ['rank1','tar','far']:row[tag+'_'+k]=measured[tag][k]
            row[tag+'_teacher_cosine']=cosines[tag]
        history.append(row)
        if epoch==0 or (eligible and (best is None or key>best)):
            if eligible:best=key
            best_epoch=epoch;stale=0;selected_vectors={k:v.copy() for k,v in vectors.items()};selected_metrics=measured
            torch.save(dict(model=model.state_dict(),raw_mean=torch.from_numpy(mean),raw_std=torch.from_numpy(std),epoch=epoch,configuration=protocol,monitor=measured,monitor_cosines=cosines,eligible=bool(eligible)),out/'melhor_modelo.pt')
            for tag,c in scores.items():np.savez_compressed(out/f'scores_selected_{tag}.npz',**c)
        elif epoch:stale+=1
        if epoch==0:
            for tag,c in scores.items():np.savez_compressed(out/f'scores_baseline_{tag}.npz',**c)
            np.savez_compressed(out/'scores_original_clean.npz',**original_data['clean'])
        with (out/'historico.csv').open('w',newline='',encoding='utf-8') as f:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerows(history)
        print(json.dumps(row),flush=True)
        if epoch>=5 and stale>=4:break
    chosen=torch.load(out/'melhor_modelo.pt',map_location='cpu',weights_only=True);cosines=chosen['monitor_cosines']
    gate=best_epoch>0 and chosen['eligible'] and all(selected_metrics[c][m]>baseline[c][m] for c in ['upper10','lower10'] for m in ['rank1','tar']) and all(cosines[c]>cosine0[c] for c in ['upper10','lower10'])
    before=np.stack([np.sum(monitor_base[:,j].astype(np.float64)*monitor_teacher.astype(np.float64),1) for j in range(3)],1)
    after=np.stack([np.sum(selected_vectors[tag].astype(np.float64)*monitor_teacher.astype(np.float64),1) for tag,_,_ in CONDITIONS],1)
    np.savez_compressed(out/'alinhamento_monitor.npz',before=before,after=after,valid=valid[monitor_indices],teacher_valid=teacher_valid[monitor_indices])
    final=dict(status='train_only_polar_adapter_completed',best_epoch=best_epoch,epochs_trained=epoch,original_monitor=original['clean'],baseline_monitor=baseline,selected_monitor=selected_metrics,baseline_cosines=cosine0,selected_cosines=cosines,recognition_validation_gate_passed=bool(gate),checkpoint_sha256=digest(out/'melhor_modelo.pt'),data_audit=data_audit,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()
