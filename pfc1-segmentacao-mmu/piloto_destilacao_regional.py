"""Piloto estrutural: aprender descritores locais antes de compara-los."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import argparse,hashlib,json
import numpy as np
from threadpoolctl import threadpool_limits
from descritor_regional_aprendido import sectors,fit_ridge,transform,eye_scores

ROOT=Path(__file__).resolve().parent
NAME='destilacao_regional_treino_2026-10-27'
METHODS=['global','regional6','fusion6','fusion8']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def compute_scores(x,v,rows,indices,base,state,condition):
    rr=[rows[i] for i in indices];eyes=sorted({(r.subject,r.side) for r in rr})
    qi=np.array([i for i in indices if rows[i].session==2]);gi=np.array([i for i in indices if rows[i].session==1 and v[i,0]])
    groups=[[k for k,i in enumerate(gi) if (rows[i].subject,rows[i].side)==eye] for eye in eyes]
    assert all(groups)
    gallery=transform(x[gi,0],state);query=transform(x[qi,condition],state)
    local={k:eye_scores(query,gallery,groups,k) for k in [6,8]}
    pair=base[qi,condition]@base[gi,0].T
    full=np.stack([np.sort(pair[:,g],axis=1)[:,-min(3,len(g)):].mean(1) for g in groups],axis=1)
    select=np.array([[j for j,e in enumerate(eyes) if e[1]==rows[i].side] for i in qi])
    labels=np.array([[e for e in eyes if e[1]==rows[i].side].index((rows[i].subject,rows[i].side)) for i in qi])
    values=dict(global_=full,regional6=local[6],fusion6=.75*full+.25*local[6],fusion8=.75*full+.25*local[8])
    values['global']=values.pop('global_')
    return {m:dict(scores=np.take_along_axis(values[m],select,axis=1).astype(np.float64),labels=labels,valid=v[qi,condition],query_indices=qi) for m in METHODS}

def measure(data,tau):
    from avaliar_robustez_reconhecimento import metrics
    m,c,g=metrics(data['scores'],data['labels'],tau,data['valid']);m.update(threshold=tau,correct=int(c.sum()),accepted=int(g.sum()))
    return m,dict(**data,correct=c,accepted=g)

def threshold(data):
    from avaliar_robustez_reconhecimento import operating_threshold
    mask=np.ones_like(data['scores'],bool);mask[np.arange(len(mask)),data['labels']]=False
    return operating_threshold(data['scores'][mask&data['valid'][:,None]],target=.005)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args()
    out=a.root/NAME;source=a.root/'adaptador_polar_original_2026-10-23';cache=a.root/'encoder_polar_espacial_2026-10-23';div=a.root/'diversidade_oclusao_treino_2026-10-24';split=a.root/'bloco_fmr_separado_2026-10-23'
    if a.registrar:
        out.mkdir(exist_ok=False);prior=json.loads((div/'protocolo.json').read_text())
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),hypothesis='Learn8regional identity descriptors from original layer3;prior frozenregional failed clean. Weighted ridge .01 into original clean global teacher;NOgeneratedpixels. Separate regressor per angularsector,radialmean,4angularcolumns. Fixed8sectors,broadreceptivefields,NOT8isolatedpixelregions.',fit='151FITpeople only,all6067eligiblephotos threeviews (S1samecleanmap;S2same3222diverseviews from prior).Teacher samephoto clean used ONLYinFIT. viewweights4/1/1;invalidviews zero. Weighted inputcentering/scaling and ridge withunpenalizedintercept,lambda.01fixed;NOhyperparametersearch.',primary='fusion6: .75originalglobalcosine+.25regionalcosine;mean6highestcorrespondingregionalcosines per query/galleryPHOTO,thenmean3highestphotos per eye. Pairdependentdiscardcanfavorimpostors,FMRmustpass. No normalizationfittedonmonitor. No querylabels/GTmask/cleanquerycounterpart in inference.',controls='globaloriginal,regional6alone,fusion8allsectors. Reportall,NOposthocchoiceofcontrols. CleanS1gallery andsame-side16candidates;onequeryphoto.',selection='One closedformfit,noepochselection. CalibrateeachmethodONCE on16internalCLEANpeople atFMR.5%;freeze. PRIMARYcleanmonitor mustpreserveglobalRank1/TAR andFMR<=1%BEFOREopeninganymonitorocclusion. Ifcleanfails,STOPNOocclusioninference. Ifpasses,openupper/lower10both;requirestrictgainR/TvsoriginalglobalandFMR<=1%,absolute90%goalreportedseparately. NoVAL/test/promotion.',limitations='Encoderspreviouslysawinternalandmonitorpeople;reuseddevelopment,NOTindependentgeneralization. Novelengineeringpilot,NOTreproductionofpublishedpatchmatcher.',fit_people=prior['fit_people'],internal_people=prior['internal_people'],monitor_people=prior['monitor_people'],augmentation_plan=prior['augmentation_plan'],dependencies={n:sha(ROOT/n) for n in ['descritor_regional_aprendido.py','piloto_destilacao_regional.py']},inputs={str(f):sha(f) for f in [source/'cache_features.npz',source/'rows.json',cache/'cache_layer3.npy',cache/'cache_indices.npz',div/'cache_diverso.npy',div/'cache_diverso_valid.npz',split/'indices_ajuste.npz']},reference='https://openaccess.thecvf.com/content/WACV2023W/XAI4B/html/Boyd_Human_Saliency-Driven_Patch-Based_Matching_for_Interpretable_Post-Mortem_Iris_Recognition_WACVW_2023_paper.html')
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Protocolo estrutural registrado.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists()
    for n,h in protocol['dependencies'].items():assert sha(ROOT/n)==h
    for f,h in protocol['inputs'].items():assert sha(f)==h
    rows=[SimpleNamespace(**r) for r in json.loads((source/'rows.json').read_text())]
    fit=set(protocol['fit_people']);internal=set(protocol['internal_people']);monitor=set(protocol['monitor_people'])
    assert len(fit)==151 and len(internal)==len(monitor)==16 and not fit&internal and not (fit|internal)&monitor
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());assert not (fit|internal|monitor)&{r['subject'] for r in manifest['val']+manifest['test']}
    maps=np.load(cache/'cache_layer3.npy',mmap_mode='r');extra=np.load(div/'cache_diverso.npy',mmap_mode='r')
    with np.load(cache/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
    with np.load(div/'cache_diverso_valid.npz') as z:ev=z['valid']
    with np.load(source/'cache_features.npz') as z:teacher=z['teacher'];base=z['base'];teacher_valid=z['teacher_valid']
    with np.load(split/'indices_ajuste.npz') as z:fi=z['fit'];ci=z['internal'];mi=z['monitor']
    assert all(rows[i].subject in fit and teacher_valid[i] for i in fi)
    x=np.empty((len(rows),3,8,256),np.float32)
    for start in range(0,len(rows),64):
        ii=np.arange(start,min(start+64,len(rows)))
        for j in range(3):x[ii,j]=sectors(maps[mapping[ii,j]])
    train=x[fi].copy();vv=valid[fi].copy();lookup={int(i):k for k,i in enumerate(fi)}
    for j,item in enumerate(protocol['augmentation_plan']):
        i=item['index'];k=lookup[i];view=1 if item['kind']=='upper' else 2
        train[k,view]=sectors(extra[j:j+1])[0];vv[k,view]=ev[j]
    weights=(vv*np.array([4.,1.,1.])).reshape(-1);target=np.repeat(teacher[fi],3,axis=0)
    with threadpool_limits(limits=4):
        state=fit_ridge(train.reshape(-1,8,256),target,weights)
        np.savez_compressed(out/'model.npz',**state)
        np.savez_compressed(out/'fit_evidence.npz',sectors=train,teacher=teacher[fi],valid=vv,fit_indices=fi)
        thresholds={};results={};occlusions=False
        for group,indices in [('internal',ci),('monitor',mi)]:
            data=compute_scores(x,valid,rows,indices,base,state,0)
            for method in METHODS:
                if group=='internal':thresholds[method]=threshold(data[method])
                m,d=measure(data[method],thresholds[method]);results.setdefault(group,{}).setdefault(method,{})['clean']=m
                np.savez_compressed(out/f'scores_{group}_{method}_clean.npz',**d)
        r=results['monitor'];clean_gate=all(r['fusion6']['clean'][k]>=r['global']['clean'][k] for k in ['rank1','tar']) and r['fusion6']['clean']['far']<=.01
        if clean_gate:
            occlusions=True
            for tag,j in [('upper10',1),('lower10',2)]:
                data=compute_scores(x,valid,rows,mi,base,state,j)
                for method in METHODS:
                    m,d=measure(data[method],thresholds[method]);results['monitor'][method][tag]=m;np.savez_compressed(out/f'scores_monitor_{method}_{tag}.npz',**d)
        gate=clean_gate and all(r['fusion6'][tag]['far']<=.01 and all(r['fusion6'][tag][k]>r['global'][tag][k] for k in ['rank1','tar']) for tag in ['upper10','lower10'])
    final=dict(status='regional_distillation_closed_form_completed',results=results,thresholds=thresholds,primary='fusion6',clean_gate_passed=bool(clean_gate),occlusions_evaluated=occlusions,monitor_gate_passed=bool(gate),fit_photos=len(fi),fit_invalid_views=int((~vv).sum()),validation_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None,model_sha256=sha(out/'model.npz'))
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()
