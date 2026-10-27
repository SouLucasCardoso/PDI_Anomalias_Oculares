"""Incerteza da fronteira existente, sem novas inferencias ou calibracao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def prefix_outcomes(approved):
    """-1=original reprovada; depois retorna menor area do prefixo da grade1pp."""
    approved=np.asarray(approved,dtype=bool)
    if approved.ndim!=2 or approved.shape[1]<1:raise ValueError('Expected draws x consecutive levels including0')
    result=np.full(len(approved),-1,dtype=int);alive=approved[:,0].copy();result[alive]=100
    for loss in range(1,approved.shape[1]):
        alive &= approved[:,loss];result[alive]=100-loss
    return result

def clustered_draws(values,subjects,reps=5000,seed=20261001):
    """Mesmos sorteios de participantes para todas as condicoes e metricas."""
    values=np.asarray(values,dtype=np.float64);subjects=np.asarray(subjects)
    if values.ndim!=3 or values.shape[1]!=len(subjects):raise ValueError('Expected condition x query x metric')
    people=np.unique(subjects);counts=np.array([(subjects==p).sum() for p in people])
    sums=np.stack([values[:,subjects==p,:].sum(1) for p in people])
    draws=np.random.default_rng(seed).integers(0,len(people),(reps,len(people)))
    return sums[draws].sum(1)/counts[draws].sum(1)[:,None,None],people,counts,sums

def prefix_distribution(approved):
    outcome=prefix_outcomes(approved);levels=[-1]+list(range(100,100-np.asarray(approved).shape[1],-1))
    result={('original_fails_no_approved_prefix' if level==-1 else f'{level}_percent_on_available_grid'):dict(draws=int((outcome==level).sum()),fraction=float((outcome==level).mean())) for level in levels}
    assert sum(r['draws'] for r in result.values())==len(outcome)
    return result

def main():
    from avaliar_candidato_congelado import digest
    from avaliar_robustez_reconhecimento import load_splits,metrics
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'incerteza_fronteira_area_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_file.read_text());threshold=frozen['frozen_threshold']
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Reuse ONLY previously evaluated original,upper1,lower1,lower2,upper10,lower10 test scores. No training,inference,recalibration,new loss condition or model selection. Previously exposed test,exploratory descriptive analysis.',
        uncertainty='5000paired participant-cluster bootstrap draws with replacement,seed20261001. Same draws for all conditions/metrics. Gallery,threshold and models fixed. All486query failures retained;15impostors per query. Pointwise percentile95% intervals,not simultaneous coverage; does not correct repeated test/model selection or unknown external pretraining overlap.',
        criterion='Existing point estimate Rank1>=.9,TAR>=.9,FMR<=.01 unchanged. Bootstrap joint-pass frequencies are resampling stability,NOT posterior probabilities or proof of population performance.',
        prefixes='Upper grid[0,1]pp loss,lower[0,1,2]pp loss. Require baseline and all consecutive larger-area conditions to pass; original failure gives undefined prefix,never100%. No interpolation,monotonicity assertion or anatomical minimum.',
        pixel_diagnostic='Describe selected reference-pixel fractions for hypothetical0.5% and1.5% losses using existing480reference sizes; no inference/performance estimate at these levels. Keep6empty references in main metrics.',
        technical_note='Supersedes a temporary technical run whose prefix summary omitted the terminal category. Integer-count comparisons preserve exact boundary criteria. No observation or model changed.',
        frozen_sha256=digest(frozen_file),script_sha256=digest(Path(__file__)),threshold=threshold)
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';rows=load_splits(json.loads(manifest_file.read_text()))['test'];queries=[r for r in rows if r.session==2];subjects=np.array([r.subject for r in queries]);assert len(queries)==486
    specifications=[('original',''),('upper1','_oclusao_superior_1'),('lower1','_oclusao_inferior_1'),('lower2','_oclusao_inferior_2'),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]
    source_hashes={};vectors=[];records=[]
    for name,suffix in specifications:
        folder=ROOT/'outputs'/f'confirmacao_congelada_test{suffix}_2026-10-21';file=folder/'scores_finais.npz';source_hashes[name]=dict(scores_sha256=digest(file),completion_sha256=digest(folder/'CONCLUIDO.json'))
        saved=json.loads((folder/'CONCLUIDO.json').read_text());assert saved['result']['threshold']==threshold
        with np.load(file) as z:
            scores=z['scores'];labels=z['labels'];valid=z['valid'];measured,correct,accepted=metrics(scores,labels,threshold,valid)
            np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
        assert scores.shape==(486,16)
        for key in ['rank1','tar','far','queries','extraction_failures']:assert measured[key]==saved['result'][key]
        impostor=np.ones_like(scores,bool);impostor[np.arange(486),labels]=False
        false_accepts=((scores>=threshold)&valid[:,None]&impostor).sum(1);fmr=false_accepts/15
        assert abs(float(fmr.mean())-measured['far'])<1e-14
        vectors.append(np.stack([correct,accepted,false_accepts],axis=1))
        records.append(dict(condition=name,rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),false_accepts=int(false_accepts.sum()),queries=486,impostor_comparisons=7290,extraction_failures=measured['extraction_failures'],point_passed=bool(measured['rank1']>=.9 and measured['tar']>=.9 and measured['far']<=.01),rank1_percent=100*measured['rank1'],tar_percent=100*measured['tar'],fmr_percent=100*measured['far']))
    values=np.stack(vectors);sampled,people,counts,sums=clustered_draws(values,subjects)
    draw_indices=np.random.default_rng(20261001).integers(0,len(people),(5000,len(people)));denominators=counts[draw_indices].sum(1)
    correct_counts=np.rint(sampled[:,:,0]*denominators[:,None]).astype(np.int64);accepted_counts=np.rint(sampled[:,:,1]*denominators[:,None]).astype(np.int64);false_counts=np.rint(sampled[:,:,2]*denominators[:,None]).astype(np.int64)
    approved=(10*correct_counts>=9*denominators[:,None])&(10*accepted_counts>=9*denominators[:,None])&(100*false_counts<=15*denominators[:,None])
    sampled[:,:,2]=false_counts/(15*denominators[:,None])
    for i,record in enumerate(records):
        record['intervals95_percent']={key:[float(v) for v in np.quantile(100*sampled[:,i,j],[.025,.975])] for j,key in enumerate(['rank1','tar','fmr'])}
        record['joint_pass_fraction_of_resamples']=float(approved[:,i].mean())
        record['paired_rank1_loss_pp_ci95']=[float(v) for v in np.quantile(100*(sampled[:,0,0]-sampled[:,i,0]),[.025,.975])]
        record['paired_tar_loss_pp_ci95']=[float(v) for v in np.quantile(100*(sampled[:,0,1]-sampled[:,i,1]),[.025,.975])]
    distributions={}
    for name,indices in [('upper_grid_0_1',[0,1]),('lower_grid_0_1_2',[0,2,3]),('common_grid_0_1',[0,1])]:
        passing=approved[:,indices].copy()
        if name=='common_grid_0_1':passing[:,1]=approved[:,1]&approved[:,2]
        distributions[name]=prefix_distribution(passing)
    interventions=ROOT/'outputs/confirmacao_congelada_test_oclusao_superior_1_2026-10-21/interventions.json';entries=json.loads(interventions.read_text());assert [r['image'] for r in entries]==[Path(r.image).name for r in queries]
    reference_pixels=np.array([r['reference_pixels'] for r in entries]);assert (reference_pixels>0).sum()==480 and (reference_pixels==0).sum()==6
    pixel_diagnostics=[]
    for level in [.5,1.5]:
        size=reference_pixels[reference_pixels>0];selected=np.array([round(int(n)*level/100) for n in size]);actual=selected/size*100
        pixel_diagnostics.append(dict(hypothetical_nominal_loss_percent=level,defined_queries=480,selected_zero_pixels_queries=int((selected==0).sum()),actual_loss_percent_mean=float(actual.mean()),actual_loss_percent_min=float(actual.min()),actual_loss_percent_max=float(actual.max()),recognition_evaluated=False))
    grouped=[]
    for person_index,person in enumerate(people):
        for condition_index,(name,_) in enumerate(specifications):
            grouped.append(dict(subject=int(person),condition=name,queries=int(counts[person_index]),correct=int(round(sums[person_index,condition_index,0])),accepted=int(round(sums[person_index,condition_index,1])),false_accepts=int(round(sums[person_index,condition_index,2]))))
    with (out/'estatisticas_por_pessoa.csv').open('w',encoding='utf-8',newline='') as stream:writer=csv.DictWriter(stream,fieldnames=list(grouped[0]));writer.writeheader();writer.writerows(grouped)
    final=dict(status='frozen_boundary_uncertainty_completed',records=records,bootstrap_prefix_distributions=distributions,people=len(people),queries=486,repetitions=5000,threshold_unchanged=threshold,source_hashes=source_hashes,manifest_sha256=digest(manifest_file),interventions_sha256=digest(interventions),pixel_diagnostics=pixel_diagnostics,
        upper_minus_lower_rank1_at10pp=dict(point_difference_pp=float(100*(values[4,:,0].mean()-values[5,:,0].mean())),ci95_pp=[float(v) for v in np.quantile(100*(sampled[:,4,0]-sampled[:,5,0]),[.025,.975])]),
        point_estimate_prefix_minima_unchanged=dict(upper=100,lower=99,common=100),new_inference=False,threshold_recalibrated=False,frozen_candidate_replaced=False,anatomical_minimum=None,clinical_minimum=None,
        limits=protocol['uncertainty']+' Bootstrap prefix frequencies describe ONLY available consecutive grid, not a distribution of anatomical minimum. 0.5/1.5pixel diagnostics provide no recognition results.')
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
