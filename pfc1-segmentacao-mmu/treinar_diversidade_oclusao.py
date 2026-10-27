"""Ajuste com penalizacao impostora; selecao sem consultar o monitor antigo."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,csv,json
import numpy as np
import torch
from torch.utils.data import DataLoader
from ajuste_bloco_polar import FullTail
from oclusao_diversa_polar import prepare_diverse
from encoder_polar_espacial import tail_vectors
from treinar_encoder_polar_espacial import FeaturePairs
from preparar_encoder_espacial import file_hash
from perda_top3_polar import top3_hard_negative_loss
from perda_fmr_polar import top3_absolute_loss,fit_impostor_reference
from avaliar_candidato_congelado import global_scores,WEIGHTS
from avaliar_robustez_reconhecimento import metrics,operating_threshold,identity
from validar_lateralidade_informada import subset
ROOT=Path(__file__).resolve().parent
NAME='diversidade_oclusao_treino_2026-10-24'
CONDITIONS=['clean','upper10','lower10']

def score(vectors,valid,rows):
    full,available=global_scores(vectors,valid,rows);values,labels,_=subset(full,rows,sorted({identity(r) for r in rows}))
    return dict(scores=values,labels=labels,valid=available)

def calibrate(data,target=.005):
    scores=data['scores'];mask=np.ones_like(scores,bool);mask[np.arange(len(scores)),data['labels']]=False
    return operating_threshold(scores[mask&data['valid'][:,None]&(scores>-2)],target=target)

def measured(data,threshold):
    m,c,g=metrics(data['scores'],data['labels'],threshold,data['valid']);m.update(threshold=threshold,correct=int(c.sum()),accepted=int(g.sum()))
    return m,dict(**data,correct=c,accepted=g)

def clean_eligible(candidate,baseline):
    return all(candidate[k]>=baseline[k] for k in ['rank1','tar']) and candidate['far']<=.005

def main():
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'adaptador_polar_original_2026-10-23';cache=a.root/'encoder_polar_espacial_2026-10-23';old=json.loads((source/'protocolo.json').read_text());metadata=json.loads((cache/'CACHE_CONCLUIDO.json').read_text());encoder_file=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt'
    if a.registrar:
        out.mkdir(exist_ok=False);rng=np.random.default_rng(20261023);internal=sorted(int(x) for x in rng.choice(sorted(old['fit_people']),16,replace=False));fit=sorted(set(old['fit_people'])-set(internal))
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='OriginalTRAIN only.151gradient-fitpeople,16internal-clean-calibrationpeople splitfromold167fit,16OLDmonitorpeople evaluatedONLYafterweightsfrozen. Encoders previously saw all; repeated development,NOTunseen generalization. No VAL/test.',
            model='OriginalFullTail:5Convkernels8388608weights trainable;prefix/projection/ALLBN frozen. Start ORIGINALcheckpoint,NOrejectedweights. FITqueries receive nativeUPPER/LOWER1..20% with randomgray32/64/128/192/224; INTERNAL/OLDmonitor remainfixed10%;S1alwaysclean. No annotation in recognizer.',
            training='Same architecture/loss/splits/optimizer/8epochs as fixed10 control; Seed63,AdamW1e-5 wd1e-4,B16;FP32. ONLYtraininginterventiondiversitychanged: fixedseed20261024 oneUPPERandoneLOWERdrawperFITeligibleS2,levels1..20 inclusive uniform,grayfrom32/64/128/192/224. Nativeimage intervention BEFOREautomaticsegmentation/polar. AlloriginalFITsamples retained inclnewextractionfailures. teacher alignment4/1/1 +.1top3hardnegative +.5absolute-tail-score-loss +1e-4originalkernelanchor. Absolute loss reference ORIGINALCLEAN151FIT same-side1%FMR quantile,computedbeforeANYstep, fixed. Hardnegativesandabsolute use FITS2ONLY;galleryFITcleanS1 refreshedonce/epoch,no-gradient.',
            selection='Epoch0fallback;amongepochs1..8 preserving INTERNALCLEAN Rank1/TAR>=epoch0 select smallestmeanFITtrainingloss. NOinternalocclusionorOLDmonitor scores during epochs. Internalclean threshold calibratedto0.5%FMR as predefined buffer,ONEthreshold frozen atselection,appliedunchanged tobothocclusionsandOLDmonitorinclclean. No sweep/earlystop/threshold fitting on occluded data.',
            final='AfterselectionONLY: evaluate3conditions of internalpeople andOLDmonitor. Recordbaseline underitsINTERNALclean threshold,notOLDmonitorclean. Primary OLDmonitor gate:cleancounts>=originalbaseline,FMR<=1%,BOTHoccludedRank1/TARstrictgain,FMR<=1%. Absolute90%goalreportedseparately. No automaticVAL/test/promotion.',
            fit_people=fit,internal_people=internal,monitor_people=old['monitor_people'],source_cache=str(source/'cache_features.npz'),source_cache_sha256=file_hash(source/'cache_features.npz'),rows_sha256=file_hash(source/'rows.json'),cache_sha256=metadata['sha256'],indices_sha256=metadata['indices_sha256'],encoder_relative_path=encoder_file.relative_to(ROOT).as_posix(),encoder_sha256=file_hash(encoder_file),manifest_sha256=file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'),script_sha256=file_hash(Path(__file__)),dependencies_sha256={n:file_hash(ROOT/n) for n in ['oclusao_diversa_polar.py','textura_polar.py','normalizacao_eliptica.py','treinar_segmentacao_ubipr.py','ajuste_bloco_polar.py','encoder_polar_espacial.py','treinar_encoder_polar_espacial.py','perda_top3_polar.py','perda_fmr_polar.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','validar_lateralidade_informada.py']})
        control=a.root/'bloco_fmr_separado_2026-10-23';control_protocol=json.loads((control/'protocolo.json').read_text());assert fit==control_protocol['fit_people'] and internal==control_protocol['internal_people'] and protocol['monitor_people']==control_protocol['monitor_people']
        with np.load(control/'indices_ajuste.npz') as z:eligible_indices=z['fit']
        source_rows=json.loads((source/'rows.json').read_text());queries=[int(i) for i in eligible_indices if source_rows[i]['session']==2];arng=np.random.default_rng(20261024);plan=[]
        for i in queries:
            for kind in ['upper','lower']:plan.append(dict(index=i,kind=kind,level=int(arng.integers(1,21)),value=int(arng.choice([32,64,128,192,224]))))
        assert len(plan)==3222 and all(source_rows[v['index']]['subject'] in fit for v in plan)
        protocol.update(augmentation_plan=plan,augmentation_seed=20261024,augmentation_maps=len(plan),unet_sha256=file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'),fixed10_control_result_sha256=file_hash(control/'CONCLUIDO.json'),fixed10_control_indices_sha256=file_hash(control/'indices_ajuste.npz'))
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Protocolo separado registrado antes do treino.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256']
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    for path,key in [(source/'cache_features.npz','source_cache_sha256'),(source/'rows.json','rows_sha256'),(cache/'cache_layer3.npy','cache_sha256'),(cache/'cache_indices.npz','indices_sha256'),(encoder_file,'encoder_sha256'),(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json','manifest_sha256')]:assert file_hash(path)==protocol[key]
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.manual_seed(63);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');rows=[SimpleNamespace(**r) for r in json.loads((source/'rows.json').read_text())];fit=set(protocol['fit_people']);internal=set(protocol['internal_people']);monitor=set(protocol['monitor_people']);assert len(fit)==151 and len(internal)==len(monitor)==16 and not fit&internal and not (fit|internal)&monitor
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());assert not (fit|internal|monitor)&{r['subject'] for r in manifest['val']+manifest['test']}
    features=np.load(cache/'cache_layer3.npy',mmap_mode='r')
    with np.load(cache/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
    with np.load(source/'cache_features.npz') as z:teacher=z['teacher'];tv=z['teacher_valid'];old_fi=z['fit_indices'];base=z['base']
    fi=np.array([i for i in old_fi if rows[i].subject in fit]);ci=np.array([i for i,r in enumerate(rows) if r.subject in internal]);mi=np.array([i for i,r in enumerate(rows) if r.subject in monitor]);cr=[rows[i] for i in ci]
    assert file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt')==protocol['unet_sha256']
    control=a.root/'bloco_fmr_separado_2026-10-23';assert file_hash(control/'CONCLUIDO.json')==protocol['fixed10_control_result_sha256'] and file_hash(control/'indices_ajuste.npz')==protocol['fixed10_control_indices_sha256']
    with np.load(control/'indices_ajuste.npz') as z:np.testing.assert_array_equal(fi,z['fit']);np.testing.assert_array_equal(ci,z['internal']);np.testing.assert_array_equal(mi,z['monitor'])
    features,mapping,valid=prepare_diverse(out,protocol,features,mapping,valid,rows,device)
    all_fit=np.array([i for i,r in enumerate(rows) if r.subject in fit]);reference_data=score(base[all_fit,0],valid[all_fit,0],[rows[i] for i in all_fit]);reference,count=fit_impostor_reference(**reference_data);np.savez_compressed(out/'referencia_ajuste.npz',**reference_data,fit_indices=all_fit)
    (out/'REFERENCIA_AJUSTE.json').write_text(json.dumps(dict(reference=reference,comparisons=count,people=151,monitor_used=False,internal_used=False),indent=2),encoding='utf-8')
    eyes=sorted({(rows[i].subject,rows[i].side) for i in fi});groups=[[i for i,r in enumerate(rows) if r.subject in fit and (r.subject,r.side)==eye and r.session==1 and tv[i]] for eye in eyes];assert len(eyes)==302 and all(groups)
    gallery=np.array([i for g in groups for i in g]);positions=np.zeros((len(eyes),max(map(len,groups))),int);present=np.zeros_like(positions,bool);lookup={i:j for j,i in enumerate(gallery)}
    for j,g in enumerate(groups):positions[j,:len(g)]=[lookup[i] for i in g];present[j,:len(g)]=True
    labels=np.array([eyes.index((rows[i].subject,rows[i].side)) for i in fi]);flags=np.array([rows[i].session==2 for i in fi]);sides=np.array([0 if s=='L' else 1 for _,s in eyes]);np.savez_compressed(out/'indices_ajuste.npz',fit=fi,internal=ci,monitor=mi,gallery=gallery,positions=positions,present=present,labels=labels,query_flags=flags,sides=sides)
    (out/'rows.json').write_bytes((source/'rows.json').read_bytes());encoder=IdentityEncoder();encoder.load_state_dict(torch.load(encoder_file,map_location='cpu',weights_only=True)['model']);torch.manual_seed(63);model=FullTail(encoder).to(device);del encoder;frozen=model.frozen_digest();parameters=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(parameters,lr=1e-5,weight_decay=1e-4)
    loader=DataLoader(FeaturePairs(features,mapping,teacher,fi,labels,flags),batch_size=16,shuffle=True,num_workers=0,pin_memory=device.type=='cuda');tp=torch.from_numpy(present).to(device);ts=torch.from_numpy(sides).to(device);history=[];best=None;selected_epoch=0;baseline_clean=None
    for epoch in range(9):
        model.eval();g=tail_vectors(model,features,mapping[gallery,0],device);tg=torch.from_numpy(g[positions]).to(device);losses=[];model.train()
        if epoch:
            for x,t,eye,query in loader:
                x=x.to(device);t=t.to(device);eye=eye.to(device);query=query.to(device);optimizer.zero_grad();pred=model(x.flatten(0,1)).reshape(len(x),3,256)
                alignment=((1-(pred*t[:,None]).sum(-1))*pred.new_tensor([4.,1.,1.])).sum(1).mean()/6;relative=top3_hard_negative_loss(pred,eye,query,tg,tp,ts);absolute=top3_absolute_loss(pred,eye,query,tg,tp,ts,reference);loss=alignment+.1*relative+.5*absolute+1e-4*model.anchor_loss();assert torch.isfinite(loss);loss.backward();torch.nn.utils.clip_grad_norm_(parameters,5);optimizer.step();losses.append(float(loss.detach()))
        model.eval();v=tail_vectors(model,features,mapping[ci,0],device);clean=score(v,valid[ci,0],cr);threshold=calibrate(clean);cm,cd=measured(clean,threshold)
        if epoch==0:baseline_clean=cm
        eligible=clean_eligible(cm,baseline_clean);average=float(np.mean(losses)) if losses else None
        state=dict(adapters=model.adapters(),rank=0,epoch=epoch,internal_clean=cm,configuration=protocol,frozen_sha256=frozen)
        if epoch==0 or eligible and (best is None or average<best):
            if epoch:best=average
            selected_epoch=epoch;torch.save(state,out/'melhor_modelo.pt');np.savez_compressed(out/'scores_internal_clean_selected.npz',**cd)
        torch.save(state,out/'ultima_epoca.pt');record=dict(epoch=epoch,fit_loss=average,eligible=bool(eligible),**{k:cm[k] for k in ['rank1','tar','far','threshold']});history.append(record)
        with (out/'historico.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(record));w.writeheader();w.writerows(history)
        print(json.dumps(record),flush=True)
    assert model.frozen_digest()==frozen;chosen=torch.load(out/'melhor_modelo.pt',map_location='cpu',weights_only=True);model.load_adapters(chosen['adapters']);selected_threshold=chosen['internal_clean']['threshold'];results={};baseline={}
    for split,indices in [('internal',ci),('monitor',mi)]:
        selected_vectors={tag:tail_vectors(model,features,mapping[indices,j],device) for j,tag in enumerate(CONDITIONS)};clean_gallery=np.array([r.session==1 for r in np.array(rows,dtype=object)[indices]])
        for tag in CONDITIONS:selected_vectors[tag][clean_gallery]=selected_vectors['clean'][clean_gallery]
        for tag,j in zip(CONDITIONS,range(3)):
            data=score(selected_vectors[tag],valid[indices,j],[rows[i] for i in indices]);m,d=measured(data,selected_threshold);results.setdefault(split,{})[tag]=m;np.savez_compressed(out/f'scores_selected_{split}_{tag}.npz',**d)
            data=score(base[indices,j],valid[indices,j],[rows[i] for i in indices])
            # Baseline S1 in older cache may have altered auxiliary vectors: explicitly restore clean enrollment.
            original=base[indices,j].copy();original[clean_gallery]=base[indices[clean_gallery],0];data=score(original,valid[indices,j],[rows[i] for i in indices]);m,d=measured(data,baseline_clean['threshold']);baseline.setdefault(split,{})[tag]=m;np.savez_compressed(out/f'scores_baseline_{split}_{tag}.npz',**d)
    r=results['monitor'];b=baseline['monitor'];gate=selected_epoch>0 and all(r['clean'][k]>=b['clean'][k] for k in ['rank1','tar']) and all(r[t]['far']<=.01 for t in CONDITIONS) and all(r[t][k]>b[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t in CONDITIONS)
    final=dict(status='diverse_native_occlusion_fulltail_completed',selected_epoch=selected_epoch,epochs=8,results=results,baseline=baseline,baseline_internal_clean=baseline_clean,selected_threshold=selected_threshold,monitor_gate_passed=bool(gate),absolute_target_reached=bool(absolute),fit_photos=len(fi),fit_people=151,internal_people=16,monitor_people=16,old_monitor_used_for_selection=False,occluded_internal_used_for_selection=False,frozen_sha256=frozen,checkpoint_sha256=file_hash(out/'melhor_modelo.pt'),last_checkpoint_sha256=file_hash(out/'ultima_epoca.pt'),validation_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None)
    final['augmentation_cache']=json.loads((out/'CACHE_DIVERSO_CONCLUIDO.json').read_text());final['fixed10_control_result_sha256']=protocol['fixed10_control_result_sha256']
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()
