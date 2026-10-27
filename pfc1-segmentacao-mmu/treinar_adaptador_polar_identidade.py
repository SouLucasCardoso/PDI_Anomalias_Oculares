"""Adaptador polar com perda de identidade S2->cadastro S1, treino-only."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,csv,json
import numpy as np
import torch
from torch.utils.data import DataLoader,TensorDataset
from adaptador_polar import PolarAdapter,apply_adapter
from treinar_adaptador_polar import monitor_scores,CONDITIONS
from treinar_adaptador_polar_original import eligible_clean,advancement
from perda_identidade_polar import session_identity_loss,selection_key
ROOT=Path(__file__).resolve().parent
NAME='adaptador_polar_identidade_v2_2026-10-23'

def main():
    from avaliar_candidato_congelado import digest
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.output_root/NAME;source=a.output_root/'adaptador_polar_original_2026-10-23'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        previous=json.loads((source/'protocolo.json').read_text())
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Original TRAIN only:6665pairedfitphotos/167people,960monitorphotos/16people/480queries. Frozen encoders saw monitor historically; monitor reused, not independent.',
            hypothesis='Keep original normalization, frozen U-Net/backbone/projection; NEWzeroinitialized adapter. Same-photo clean teacher alignment PLUS fixed0.1weight identitycrossentropy at temperature0.1. NO reuse of rejected adapterweights.',
            identity_loss='Frozen L2mean CLEAN S1teacher prototype per FIT eye, including all teacher-valid S1 photos from FIT people; no monitor prototypes/labels in fitting. CE onlyS2fit queries, all3conditions weighted4/1/1. Negatives restricted SAME SIDE. S1fit photos enter teacher alignment only. Prototype means fixed, no gradient.',
            training='Seed63,AdamW3e-4 wd1e-4,B128photos,max12epochs,patience4after5. Teacher cosine loss weights4/1/1 plus.01residual-square plus.1identityCE. FP32,sourcefeaturecache reusedbitexact; no newCNN/imageinference. FITcleanstandardization.',
            monitor='Same480queries,ALLfailures retained,onephoto,suppliedside,16eyes;S1gallery explicitly CLEAN in ALLconditions. Each epoch one CLEANFMR<=1%threshold reused unchanged for both10%occlusions. No condition-specific threshold.',
            selection='Epoch0 included. EligiblecleanRank1/TAR>=epoch0,FMR<=1%. Amongeligible prioritize full monitor gate passed,then worstoccludedTAR,thenworstRank1,thennegativeworstFMR,thenmeanoccludedteachercosine. Monitor gate=epoch>0,cleanpreserved,BOTHocclusionsstrictRank1/TARgainvsbaseline,FMR<=1%. No weight/temperature search.',
            validation='Onlyifmonitorpasses,separately registered exploratoryVAL,replaceONLYpolarcomponent of ORIGINALfusion,8othercomponentsfixed,clean-onlycalibration,all482queries,noautomaticTEST/promotion/minimum.',
            technical_correction='v1 stopped at firstCE beforeANYoptimizerstep because WindowsNumPy labelsint32. Cast targets explicitlytorch.long; restartfromseed63zeroadapter,NOweight/loss search. v1epoch0notanexperimentaloutcome.',
            fit_people=previous['fit_people'],monitor_people=previous['monitor_people'],source_cache=str(source/'cache_features.npz'),source_cache_sha256=digest(source/'cache_features.npz'),source_rows_sha256=digest(source/'rows.json'),source_completion_sha256=digest(source/'CONCLUIDO.json'),script_sha256=digest(Path(__file__)),dependencies_sha256={n:digest(ROOT/n) for n in ['perda_identidade_polar.py','adaptador_polar.py','treinar_adaptador_polar.py','treinar_adaptador_polar_original.py']})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Perda de identidade registrada antes do ajuste.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert digest(Path(__file__))==protocol['script_sha256'] and not (out/'CONCLUIDO.json').exists()
    for file,key in [(source/'cache_features.npz','source_cache_sha256'),(source/'rows.json','source_rows_sha256'),(source/'CONCLUIDO.json','source_completion_sha256')]:assert digest(file)==protocol[key]
    for name,value in protocol['dependencies_sha256'].items():assert digest(ROOT/name)==value
    with np.load(source/'cache_features.npz') as z:c={k:z[k] for k in z.files}
    raw=c['raw'];base=c['base'];teacher=c['teacher'];valid=c['valid'];teacher_valid=c['teacher_valid'];fi=c['fit_indices'];mi=c['monitor_indices']
    rows=[SimpleNamespace(**r) for r in json.loads((source/'rows.json').read_text())];mr=[rows[i] for i in mi];fit=set(protocol['fit_people']);monitor=set(protocol['monitor_people'])
    assert not fit&monitor and {rows[i].subject for i in fi}<=fit and {rows[i].subject for i in mi}==monitor and len(mi)==960 and sum(r.session==2 for r in mr)==480
    eyes=sorted({(rows[i].subject,rows[i].side) for i in fi});eye_index={eye:j for j,eye in enumerate(eyes)};protos=[];gallery=[]
    for eye in eyes:
        indices=[i for i,r in enumerate(rows) if r.subject in fit and (r.subject,r.side)==eye and r.session==1 and teacher_valid[i]]
        assert indices;gallery.extend(indices);value=teacher[indices].mean(0);value/=max(float(np.linalg.norm(value)),1e-12);protos.append(value)
    protos=np.stack(protos);eye_labels=np.array([eye_index[(rows[i].subject,rows[i].side)] for i in fi]);query_flags=np.array([rows[i].session==2 for i in fi]);sides=np.array([0 if side=='L' else 1 for _,side in eyes])
    assert len(eyes)==334 and not set(gallery)&set(mi)
    np.savez_compressed(out/'prototipos_ajuste.npz',prototypes=protos,prototype_sides=sides,fit_indices=fi,fit_labels=eye_labels,fit_query_flags=query_flags,gallery_indices=np.array(gallery))
    (out/'rows.json').write_bytes((source/'rows.json').read_bytes())
    data=dict(fit_valid_paired_photos=len(fi),fit_people=len(fit),monitor_photos=len(mi),monitor_people=len(monitor),monitor_queries=480,prototype_eyes=len(eyes),prototype_clean_enrollment_photos=len(gallery),fit_S2_photos_with_identity_loss=int(query_flags.sum()),source_cache_sha256=protocol['source_cache_sha256'],new_cnn_inference=False)
    (out/'AUDITORIA_DADOS.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (out/'PROVENIENCIA_CACHE.json').write_text(json.dumps(dict(source=protocol['source_cache'],sha256=protocol['source_cache_sha256'],copied=False,rejected_weights_reused=False),indent=2),encoding='utf-8')
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    prototypes=torch.from_numpy(protos).to(device);prototype_sides=torch.from_numpy(sides).to(device)
    mean=raw[fi,0].mean(0);std=raw[fi,0].std(0).clip(1e-5);loader=DataLoader(TensorDataset(torch.from_numpy((raw[fi]-mean)/std),torch.from_numpy(base[fi]),torch.from_numpy(teacher[fi]),torch.from_numpy(eye_labels),torch.from_numpy(query_flags)),batch_size=128,shuffle=True)
    torch.manual_seed(63);model=PolarAdapter().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);baseline=None;best=None;stale=0;history=[];best_epoch=0
    for epoch in range(13):
        losses=[];model.train()
        if epoch:
            for x,b,t,eye,query in loader:
                x=x.to(device);b=b.to(device);t=t.to(device);optimizer.zero_grad();pred,delta=model(x.flatten(0,1),b.flatten(0,1));pred=pred.reshape(len(x),3,256)
                alignment=((1-(pred*t[:,None]).sum(-1))*pred.new_tensor([4.,1.,1.])).sum(1).mean()/6;metric=session_identity_loss(pred,eye.to(device),query.to(device),prototypes,prototype_sides);loss=alignment+.01*delta.square().mean()+.1*metric;assert torch.isfinite(loss)
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();losses.append(float(loss.detach()))
        model.eval();vectors={tag:apply_adapter(model,raw[mi,j],base[mi,j],mean,std,device) for j,(tag,_,_) in enumerate(CONDITIONS)};availability={tag:valid[mi,j] for j,(tag,_,_) in enumerate(CONDITIONS)}
        measured,scores=monitor_scores(vectors,availability,mr);cosines={}
        for j,(tag,_,_) in enumerate(CONDITIONS):
            paired=availability[tag]&teacher_valid[mi];cosines[tag]=float(np.sum(vectors[tag][paired].astype(np.float64)*teacher[mi][paired].astype(np.float64),1).mean())
        if baseline is None:
            baseline=measured
            for tag,s in scores.items():np.savez_compressed(out/f'scores_baseline_{tag}.npz',**s)
        eligible=eligible_clean(measured,baseline);key=selection_key(measured,cosines,baseline,epoch)
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
    final=dict(status='identity_loss_original_polar_adapter_completed',selected_epoch=best_epoch,epochs_trained=epoch,baseline_monitor=baseline,selected_monitor=chosen['monitor'],last_monitor=measured,selected_cosines=chosen['cosines'],recognition_validation_gate_passed=bool(gate),checkpoint_sha256=digest(out/'melhor_modelo.pt'),last_checkpoint_sha256=digest(out/'ultima_epoca.pt'),data_audit=data,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()

