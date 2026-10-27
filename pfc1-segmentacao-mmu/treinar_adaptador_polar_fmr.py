"""Adaptador polar com perda de identidade S2->cadastro S1, treino-only."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,csv,json,hashlib
import numpy as np
import torch
from torch.utils.data import DataLoader,TensorDataset
from adaptador_polar import PolarAdapter,apply_adapter
from treinar_adaptador_polar import monitor_scores,CONDITIONS
from treinar_adaptador_polar_original import eligible_clean,advancement
from perda_identidade_polar import selection_key
from perda_top3_polar import top3_hard_negative_loss
from perda_fmr_polar import fit_impostor_reference,top3_absolute_loss
ROOT=Path(__file__).resolve().parent
NAME='adaptador_polar_fmr_2026-10-23'

def main():
    from avaliar_candidato_congelado import digest,global_scores
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.output_root/NAME;source=a.output_root/'adaptador_polar_original_2026-10-23'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        previous=json.loads((source/'protocolo.json').read_text())
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Original TRAIN only:6665pairedfitphotos/167people,960monitorphotos/16people/480queries. Frozen encoders saw monitor historically; monitor reused, not independent.',
            hypothesis='Keep original normalization, frozen U-Net/backbone/projection; NEWzeroinitialized adapter. Same-photo clean teacher alignment PLUS fixed0.1weight hardnegativeTOP3marginsoftplus at temperature0.1,margin0.1 PLUS fixed0.1weight absolute-score penalty using ORIGINALFITclean1%FMRreference. NO reuse of rejected adapterweights.',
            identity_loss='ALLteacher-valid CLEAN S1FITphotos as enrollment, grouped by physicaleye. AtSTART ofEACHepoch refresh enrollment descriptors with currentadapter withoutgradient; freeze detachedgallery WITHINepoch. Loss ONLYS2fitqueries;genuine=meanbestmin(3,count)enrollmentcosines;negative=maxsame-sideOTHEReyeTOP3score. softplus((negative+0.1-genuine)/0.1),conditionsweighted4/1/1. Not exact joint gradient through enrollment: epoch-frozen approximation; monitor refreshes BOTHqueryandgallery at epochend. No monitor enrollment/labels in loss.',
            absolute_loss='BeforeANYoptimizerstep compute ONEfixedreference from ORIGINALcleanFIT S2->S1same-side comparisons, ALL6756FITphotos including failedqueries; validimpostorcomparisons only define quantile1% via existing operating_threshold. NEVERmonitor/VAL/test labels. For EACH S2FITquerycondition, average squaredrelu((impostor-reference)/0.1) overworstceil1%other-same-sideEYEscores (2of166),plus squaredrelu((reference+0.05-genuine)/0.1);conditionsweighted4/1/1. Fixedthroughoutepochs; reference is traininglossparameter,NOT evaluationthreshold.',
            training='Seed63,AdamW3e-4 wd1e-4,B128photos,max12epochs,patience4after5. Teacher cosine loss weights4/1/1 plus.01residual-square plus.1top3hardnegativesoftplus plus.1absolute-score-loss. FP32,sourcefeaturecache reusedbitexact; no newCNN/imageinference. FITcleanstandardization.',
            monitor='Same480queries,ALLfailures retained,onephoto,suppliedside,16eyes;S1gallery explicitly CLEAN in ALLconditions. Each epoch one CLEANFMR<=1%threshold reused unchanged for both10%occlusions. No condition-specific threshold.',
            selection='Epoch0 included. EligiblecleanRank1/TAR>=epoch0,FMR<=1%. Amongeligible prioritize full monitor gate passed,then worstoccludedTAR,thenworstRank1,thennegativeworstFMR,thenmeanoccludedteachercosine. Monitor gate=epoch>0,cleanpreserved,BOTHocclusionsstrictRank1/TARgainvsbaseline,FMR<=1%. No weight/margin/temperature search.',
            validation='Onlyifmonitorpasses,separately registered exploratoryVAL,replaceONLYpolarcomponent of ORIGINALfusion,8othercomponentsfixed,clean-onlycalibration,all482queries,noautomaticTEST/promotion/minimum.',
            fit_people=previous['fit_people'],monitor_people=previous['monitor_people'],source_cache=str(source/'cache_features.npz'),source_cache_sha256=digest(source/'cache_features.npz'),source_rows_sha256=digest(source/'rows.json'),source_completion_sha256=digest(source/'CONCLUIDO.json'),script_sha256=digest(Path(__file__)),dependencies_sha256={n:digest(ROOT/n) for n in ['perda_fmr_polar.py','perda_top3_polar.py','perda_identidade_polar.py','adaptador_polar.py','treinar_adaptador_polar.py','treinar_adaptador_polar_original.py']})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Perda de identidade registrada antes do ajuste.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert digest(Path(__file__))==protocol['script_sha256'] and not (out/'CONCLUIDO.json').exists()
    for file,key in [(source/'cache_features.npz','source_cache_sha256'),(source/'rows.json','source_rows_sha256'),(source/'CONCLUIDO.json','source_completion_sha256')]:assert digest(file)==protocol[key]
    for name,value in protocol['dependencies_sha256'].items():assert digest(ROOT/name)==value
    with np.load(source/'cache_features.npz') as z:c={k:z[k] for k in z.files}
    raw=c['raw'];base=c['base'];teacher=c['teacher'];valid=c['valid'];teacher_valid=c['teacher_valid'];fi=c['fit_indices'];mi=c['monitor_indices']
    rows=[SimpleNamespace(**r) for r in json.loads((source/'rows.json').read_text())];mr=[rows[i] for i in mi];fit=set(protocol['fit_people']);monitor=set(protocol['monitor_people'])
    assert not fit&monitor and {rows[i].subject for i in fi}<=fit and {rows[i].subject for i in mi}==monitor and len(mi)==960 and sum(r.session==2 for r in mr)==480
    eyes=sorted({(rows[i].subject,rows[i].side) for i in fi});eye_index={eye:j for j,eye in enumerate(eyes)};groups=[];gallery=[]
    for eye in eyes:
        indices=[i for i,r in enumerate(rows) if r.subject in fit and (r.subject,r.side)==eye and r.session==1 and teacher_valid[i]]
        assert indices;groups.append(indices);gallery.extend(indices)
    eye_labels=np.array([eye_index[(rows[i].subject,rows[i].side)] for i in fi]);query_flags=np.array([rows[i].session==2 for i in fi]);sides=np.array([0 if side=='L' else 1 for _,side in eyes])
    assert len(eyes)==334 and not set(gallery)&set(mi)
    padded=np.full((len(eyes),max(map(len,groups))),-1,np.int64)
    for j,indices in enumerate(groups):padded[j,:len(indices)]=indices
    present=padded>=0;local={global_index:i for i,global_index in enumerate(gallery)};positions=np.zeros_like(padded)
    for j,k in zip(*np.where(present)):positions[j,k]=local[padded[j,k]]
    np.savez_compressed(out/'cadastros_ajuste.npz',padded_indices=padded,eye_sides=sides,fit_indices=fi,fit_labels=eye_labels,fit_query_flags=query_flags,gallery_indices=np.array(gallery))
    (out/'rows.json').write_bytes((source/'rows.json').read_bytes())
    data=dict(fit_valid_paired_photos=len(fi),fit_people=len(fit),monitor_photos=len(mi),monitor_people=len(monitor),monitor_queries=480,enrollment_eyes=len(eyes),clean_enrollment_photos=len(gallery),maximum_enrollment_per_eye=padded.shape[1],fit_S2_photos_with_identity_loss=int(query_flags.sum()),source_cache_sha256=protocol['source_cache_sha256'],new_cnn_inference=False)
    (out/'AUDITORIA_DADOS.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (out/'PROVENIENCIA_CACHE.json').write_text(json.dumps(dict(source=protocol['source_cache'],sha256=protocol['source_cache_sha256'],copied=False,rejected_weights_reused=False),indent=2),encoding='utf-8')
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    gallery_present=torch.from_numpy(present).to(device);eye_sides=torch.from_numpy(sides).to(device)
    from avaliar_robustez_reconhecimento import identity
    from validar_lateralidade_informada import subset
    fit_all=np.array([i for i,r in enumerate(rows) if r.subject in fit]);fit_rows=[rows[i] for i in fit_all]
    assert len(fit_all)==6756 and not set(fit_all)&set(mi)
    reference_full,reference_valid=global_scores(base[fit_all,0],valid[fit_all,0],fit_rows);reference_scores,reference_labels,_=subset(reference_full,fit_rows,sorted({identity(r) for r in fit_rows}))
    fit_reference,reference_impostors=fit_impostor_reference(reference_scores,reference_labels,reference_valid)
    reference_record=dict(reference=fit_reference,method='OriginalFITcleanFP32top3same-side1%impostorquantile; fixedbeforeANYoptimizerstep',fit_people=len(fit),fit_photos=len(fit_all),queries=len(reference_labels),valid_queries=int(reference_valid.sum()),usable_impostor_comparisons=reference_impostors,same_side_candidate_eyes=reference_scores.shape[1],monitor_labels_used=False,evaluation_threshold_changed=False)
    np.savez_compressed(out/'referencia_ajuste.npz',scores=reference_scores,labels=reference_labels,valid=reference_valid,fit_global_indices=fit_all)
    (out/'REFERENCIA_AJUSTE.json').write_text(json.dumps(reference_record,indent=2),encoding='utf-8');print(json.dumps(reference_record),flush=True)
    mean=raw[fi,0].mean(0);std=raw[fi,0].std(0).clip(1e-5);loader=DataLoader(TensorDataset(torch.from_numpy((raw[fi]-mean)/std),torch.from_numpy(base[fi]),torch.from_numpy(teacher[fi]),torch.from_numpy(eye_labels),torch.from_numpy(query_flags)),batch_size=128,shuffle=True)
    torch.manual_seed(63);model=PolarAdapter().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);baseline=None;best=None;stale=0;history=[];best_epoch=0
    for epoch in range(13):
        model.eval();gallery_vectors=apply_adapter(model,raw[gallery,0],base[gallery,0],mean,std,device);gallery_hash=hashlib.sha256(gallery_vectors.tobytes()).hexdigest();gallery_features=torch.from_numpy(gallery_vectors[positions]).to(device)
        losses=[];model.train()
        if epoch:
            for x,b,t,eye,query in loader:
                x=x.to(device);b=b.to(device);t=t.to(device);optimizer.zero_grad();pred,delta=model(x.flatten(0,1),b.flatten(0,1));pred=pred.reshape(len(x),3,256)
                alignment=((1-(pred*t[:,None]).sum(-1))*pred.new_tensor([4.,1.,1.])).sum(1).mean()/6;metric=top3_hard_negative_loss(pred,eye.to(device),query.to(device),gallery_features,gallery_present,eye_sides);absolute=top3_absolute_loss(pred,eye.to(device),query.to(device),gallery_features,gallery_present,eye_sides,fit_reference);loss=alignment+.01*delta.square().mean()+.1*metric+.1*absolute;assert torch.isfinite(loss)
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();losses.append(float(loss.detach()))
        model.eval();vectors={tag:apply_adapter(model,raw[mi,j],base[mi,j],mean,std,device) for j,(tag,_,_) in enumerate(CONDITIONS)};availability={tag:valid[mi,j] for j,(tag,_,_) in enumerate(CONDITIONS)}
        measured,scores=monitor_scores(vectors,availability,mr);cosines={}
        for j,(tag,_,_) in enumerate(CONDITIONS):
            paired=availability[tag]&teacher_valid[mi];cosines[tag]=float(np.sum(vectors[tag][paired].astype(np.float64)*teacher[mi][paired].astype(np.float64),1).mean())
        if baseline is None:
            baseline=measured
            for tag,s in scores.items():np.savez_compressed(out/f'scores_baseline_{tag}.npz',**s)
        eligible=eligible_clean(measured,baseline);key=selection_key(measured,cosines,baseline,epoch)
        record=dict(epoch=epoch,gallery_sha256=gallery_hash,train_loss=float(np.mean(losses)) if losses else None,eligible=bool(eligible))
        for tag in measured:
            for k in ['rank1','tar','far']:record[tag+'_'+k]=measured[tag][k]
            record[tag+'_teacher_cosine']=cosines[tag]
        history.append(record)
        state=dict(model=model.state_dict(),raw_mean=torch.from_numpy(mean),raw_std=torch.from_numpy(std),epoch=epoch,monitor=measured,cosines=cosines,eligible=bool(eligible),configuration=protocol,fit_reference=fit_reference)
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
    final=dict(status='absolute_fmr_polar_adapter_completed',selected_epoch=best_epoch,epochs_trained=epoch,baseline_monitor=baseline,selected_monitor=chosen['monitor'],last_monitor=measured,selected_cosines=chosen['cosines'],recognition_validation_gate_passed=bool(gate),checkpoint_sha256=digest(out/'melhor_modelo.pt'),last_checkpoint_sha256=digest(out/'ultima_epoca.pt'),data_audit=data,fit_reference=reference_record,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()



