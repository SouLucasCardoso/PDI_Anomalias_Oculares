"""Reproduz fusao/decisoes, quantifica incerteza e fecha grade irregular predefinida."""
from pathlib import Path
import argparse,csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_candidato_congelado import digest,fuse
    from avaliar_robustez_reconhecimento import load_splits,metrics
    from incerteza_fronteira_area import clustered_draws
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'fronteira_meio_ponto_2026-10-23'
    completed=json.loads((out/'CONCLUIDO.json').read_text());protocol=json.loads((out/'protocolo.json').read_text());assert digest(out/'source.py')==protocol['script_sha256']
    frozen_path=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';assert digest(frozen_path)==protocol['frozen_sha256'];frozen=json.loads(frozen_path.read_text());threshold=frozen['frozen_threshold'];assert threshold==protocol['threshold']
    for name,expected in protocol['dependencies_sha256'].items():assert digest(ROOT/name)==expected
    old_protocol=json.loads((ROOT/'outputs/confirmacao_congelada_test_2026-10-21/protocolo.json').read_text())
    for name,expected in old_protocol['dependencies_sha256'].items():assert digest(ROOT/name)==expected
    assert protocol['unet_sha256']==old_protocol['unet_sha256']
    assert protocol['arc_weights_sha256']==old_protocol['external_arciris']['weights_sha256']
    for name,expected in protocol['weights_sha256'].items():
        from avaliar_candidato_congelado import WEIGHTS
        assert digest(ROOT/'outputs'/WEIGHTS[name][0]/'melhor_modelo.pt')==expected
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';assert digest(manifest_file)==protocol['manifest_sha256'];rows=load_splits(json.loads(manifest_file.read_text()))['test'];queries=[r for r in rows if r.session==2];subjects=np.array([r.subject for r in queries]);assert len(queries)==486
    def read(file):
        with np.load(file) as z:return {k:z[k] for k in z.files}
    original=read(ROOT/'outputs/confirmacao_congelada_test_2026-10-21/scores_finais.npz');vectors=[];records=[];hashes={};maximum=0.
    order=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
    for record in completed['records']:
        folder=out/record['tag'];components=[read(folder/f'scores_{name}.npz') for name in order];stored=read(folder/'scores_finais.npz');scores,valid=fuse(components,frozen['component_calibration_red_and_clahe'])
        np.testing.assert_array_equal(scores,stored['scores']);np.testing.assert_array_equal(valid,stored['valid']);np.testing.assert_array_equal(stored['labels'],original['labels']);maximum=max(maximum,float(abs(scores-stored['scores']).max()))
        measured,correct,accepted=metrics(scores,stored['labels'],threshold,valid);np.testing.assert_array_equal(correct,stored['correct']);np.testing.assert_array_equal(accepted,stored['accepted'])
        for key in ['rank1','tar','far','queries','extraction_failures']:assert measured[key]==record['result'][key]
        entries=json.loads((folder/'interventions.json').read_text());assert [e['image'] for e in entries]==[Path(r.image).name for r in queries]
        sizes=np.array([e['reference_pixels'] for e in entries]);defined=sizes>0;fractions=np.array([e['affected_fraction'] for e in entries]);zero=fractions==0
        assert defined.sum()==480 and (~defined).sum()==6
        for n,fraction in zip(sizes,fractions):assert fraction==(round(int(n)*record['occluded_percent']/100)/n if n else 0.)
        np.testing.assert_allclose(scores[zero],original['scores'][zero],atol=1e-12,rtol=0);np.testing.assert_array_equal(valid[zero],original['valid'][zero])
        # Native crop/support caches provide separate enrollment and empty-reference controls.
        old_cache=Path(__import__('tempfile').gettempdir())/'cache_confirmacao_test_2026-10-21';new_cache=a.output_root.parent/f"cache_fronteira_meio_ponto_{record['tag']}_2026-10-23"
        unchanged=np.array([r.session==1 or Path(r.image).name in {e['image'] for e in entries if not e['reference_pixels']} for r in rows])
        for name in ['rgb','native','polar','red']:np.testing.assert_array_equal(np.load(old_cache/(name+'.npy'),mmap_mode='r')[unchanged],np.load(new_cache/(name+'.npy'),mmap_mode='r')[unchanged])
        imp=np.ones_like(scores,bool);imp[np.arange(486),stored['labels']]=False;false_accepts=((scores>=threshold)&valid[:,None]&imp).sum(1);vectors.append(np.stack([correct,accepted,false_accepts],axis=1))
        measured.update(tag=record['tag'],occluded_percent=record['occluded_percent'],nominal_retained_percent=record['nominal_retained_percent'],rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),false_accepts=int(false_accepts.sum()),passed=record['passed'],defined_queries=480,empty_reference_queries=6,defined_zero_selected_queries=int((zero&defined).sum()),actual_loss_percent_mean=float(100*fractions[defined].mean()),actual_loss_percent_min=float(100*fractions[defined].min()),actual_loss_percent_max=float(100*fractions[defined].max()),unchanged_inputs_verified=True,zero_intervention_scores_equal_original=True)
        records.append(measured);hashes[record['tag']]={name:digest(folder/f'scores_{name}.npz') for name in order+['finais']}
        with (folder/'consultas.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(['image','subject','label','valid','correct','accepted','reference_pixels','affected_fraction']+[f'score_{i}' for i in range(16)])
            for i,row in enumerate(queries):writer.writerow([Path(row.image).name,row.subject,int(stored['labels'][i]),bool(valid[i]),bool(correct[i]),bool(accepted[i]),int(sizes[i]),float(fractions[i])]+scores[i].tolist())
    sampled,people,counts,sums=clustered_draws(np.stack(vectors),subjects);draws=np.random.default_rng(20261001).integers(0,len(people),(5000,len(people)));denominator=counts[draws].sum(1);fa=np.rint(sampled[:,:,2]*denominator[:,None]).astype(np.int64);sampled[:,:,2]=fa/(15*denominator[:,None])
    rank_counts=np.rint(sampled[:,:,0]*denominator[:,None]).astype(np.int64);tar_counts=np.rint(sampled[:,:,1]*denominator[:,None]).astype(np.int64);passing=(10*rank_counts>=9*denominator[:,None])&(10*tar_counts>=9*denominator[:,None])&(100*fa<=15*denominator[:,None])
    for i,record in enumerate(records):
        record['intervals95_percent']={name:[float(v) for v in np.quantile(100*sampled[:,i,j],[.025,.975])] for j,name in enumerate(['rank1','tar','fmr'])};record['joint_pass_fraction_of_resamples']=float(passing[:,i].mean())
    baseline=json.loads((ROOT/'outputs/confirmacao_congelada_test_2026-10-21/CONCLUIDO.json').read_text());assert baseline['target_reached'];boundaries={}
    for orientation,tag,levels in [('superior','superior_0p5',[.5,1,10]),('inferior','inferior_1p5',[1,1.5,2,10])]:
        sequence=[]
        for loss in levels:
            if loss in [.5,1.5]:passed=next(r['passed'] for r in records if r['tag']==tag)
            else:passed=json.loads((ROOT/'outputs'/f'confirmacao_congelada_test_oclusao_{orientation}_{loss}_2026-10-21/CONCLUIDO.json').read_text())['target_reached']
            sequence.append(dict(loss=loss,retained=100-loss,passed=passed))
        minimum=100;first_failure=None
        for r in sequence:
            if not r['passed']:first_failure=r['retained'];break
            minimum=r['retained']
        boundaries[orientation]=dict(smallest_passing_retained_percent_on_tested_prefix=minimum,first_failing_retained_percent=first_failure,loss_grid=[0]+levels,records=sequence)
    common_losses=sorted(set(boundaries['superior']['loss_grid'])&set(boundaries['inferior']['loss_grid']))
    common_minimum=100
    for loss in common_losses[1:]:
        both=all(next(r['passed'] for r in boundaries[side]['records'] if r['loss']==loss) for side in ['superior','inferior'])
        if not both:break
        common_minimum=100-loss
    boundaries['common']=dict(smallest_passing_retained_percent_on_common_tested_prefix=common_minimum,loss_grid=common_losses,note='Use only levels evaluated in BOTH orientations. Do not infer lower0.5% or take maximum of orientation minima as a common certified fraction.')
    grouped=[]
    for i,person in enumerate(people):
        for j,record in enumerate(records):grouped.append(dict(subject=int(person),condition=record['tag'],queries=int(counts[i]),correct=int(sums[i,j,0]),accepted=int(sums[i,j,1]),false_accepts=int(sums[i,j,2])))
    with (out/'estatisticas_por_pessoa.csv').open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=list(grouped[0]));writer.writeheader();writer.writerows(grouped)
    final=dict(status='midpoint_scores_inputs_and_boundary_audited',records=records,boundaries=boundaries,maximum_fusion_score_difference=maximum,threshold_unchanged=threshold,source_hashes=hashes,bootstrap_repetitions=5000,bootstrap_seed=20261001,audit_source_sha256=digest(Path(__file__)),training=False,threshold_recalibrated=False,anatomical_minimum=None,clinical_minimum=None,limits='Two prespecified exploratory additions on exposed test. Irregular tested grid,lower0.5% absent; no continuous/uniform0.5pp claim. Fixed gallery/threshold,16people,pointwise95% intervals,unknown pretraining overlap. Bootstrap pass frequencies NOT posterior population success probabilities.')
    (out/'AUDITORIA_FRONTEIRA.json').write_text(json.dumps(final,indent=2),encoding='utf-8');(out/'audit_source.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
