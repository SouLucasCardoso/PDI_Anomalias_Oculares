"""Reproduz ajuste elegível, métricas e decisão sem novo treino ou inferência CNN."""
from pathlib import Path
from types import SimpleNamespace
import argparse,csv,json
import numpy as np
import torch
from adaptador_polar import PolarAdapter,apply_adapter
from treinar_adaptador_polar import monitor_scores,CONDITIONS
from avaliar_candidato_congelado import digest,fuse
from avaliar_robustez_reconhecimento import metrics,operating_threshold
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'adaptador_polar_cadastro_fixo_2026-10-23'
    final=json.loads((out/'CONCLUIDO.json').read_text());protocol=json.loads((out/'protocolo.json').read_text())
    assert digest(ROOT/'treinar_adaptador_polar.py')==protocol['script_sha256']==digest(out/'source.py')
    assert digest(ROOT/'adaptador_polar.py')==protocol['dependencies_sha256']['adaptador_polar.py']==digest(out/'adapter_source.py')
    for name,value in protocol['dependencies_sha256'].items():assert digest(ROOT/name)==value
    assert digest(out/'melhor_modelo.pt')==final['checkpoint_sha256']
    state=torch.load(out/'melhor_modelo.pt',map_location='cpu',weights_only=True)
    with np.load(out/'cache_features.npz') as z:c={k:z[k] for k in z.files}
    rows=[SimpleNamespace(**r) for r in json.loads((out/'rows.json').read_text())];fit=set(protocol['fit_people']);monitor=set(protocol['monitor_people']);assert not fit&monitor
    expected_fit=np.array([i for i,r in enumerate(rows) if r.subject in fit and c['teacher_valid'][i] and c['valid'][i].all()]);expected_monitor=np.array([i for i,r in enumerate(rows) if r.subject in monitor])
    np.testing.assert_array_equal(expected_fit,c['fit_indices']);np.testing.assert_array_equal(expected_monitor,c['monitor_indices']);assert len(rows)==7716 and len(expected_monitor)==960
    mean=c['raw'][expected_fit,0].mean(0);std=c['raw'][expected_fit,0].std(0).clip(1e-5)
    np.testing.assert_array_equal(mean,state['raw_mean'].numpy());np.testing.assert_array_equal(std,state['raw_std'].numpy())
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu';model=PolarAdapter().to(device).eval();model.load_state_dict(state['model']);zero=PolarAdapter().to(device).eval()
    mi=expected_monitor;mr=[rows[i] for i in mi];valid={tag:c['valid'][mi,j] for j,(tag,_,_) in enumerate(CONDITIONS)};teacher=c['teacher'][mi]
    selected={tag:apply_adapter(model,c['raw'][mi,j],c['base'][mi,j],mean,std,device) for j,(tag,_,_) in enumerate(CONDITIONS)}
    baseline={tag:apply_adapter(zero,c['raw'][mi,j],c['base'][mi,j],mean,std,device) for j,(tag,_,_) in enumerate(CONDITIONS)}
    sm,sd=monitor_scores(selected,valid,mr);bm,bd=monitor_scores(baseline,valid,mr)
    original,od=monitor_scores({tag:teacher for tag,_,_ in CONDITIONS},{tag:c['teacher_valid'][mi] for tag,_,_ in CONDITIONS},mr)
    cosines={}
    for j,(tag,_,_) in enumerate(CONDITIONS):
        paired=valid[tag]&c['teacher_valid'][mi];cosines[tag]=float(np.sum(selected[tag][paired].astype(np.float64)*teacher[paired].astype(np.float64),1).mean())
        assert sm[tag]==final['selected_monitor'][tag] and bm[tag]==final['baseline_monitor'][tag]
        np.testing.assert_allclose(cosines[tag],final['selected_cosines'][tag],rtol=0,atol=1e-12)
        for prefix,data in [('selected',sd),('baseline',bd)]:
            with np.load(out/f'scores_{prefix}_{tag}.npz') as z:
                for key in ['scores','labels','valid','correct','accepted']:np.testing.assert_array_equal(z[key],data[tag][key])
    assert original['clean']==final['original_monitor']
    with np.load(out/'scores_original_clean.npz') as z:
        for key in ['scores','labels','valid','correct','accepted']:np.testing.assert_array_equal(z[key],od['clean'][key])
    with (out/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    best=None;selected_epoch=0
    for row in history:
        eligible=all(float(row['clean_'+k])>=control['clean'][k] for k in ['rank1','tar'] for control in [original,bm]) and float(row['clean_teacher_cosine'])>=final['baseline_cosines']['clean']
        assert eligible==(row['eligible']=='True')
        key=(min(float(row[t+'_tar']) for t in ['upper10','lower10']),min(float(row[t+'_rank1']) for t in ['upper10','lower10']),float(np.mean([float(row[t+'_teacher_cosine']) for t in ['upper10','lower10']])))
        if int(row['epoch'])==0 or (eligible and (best is None or key>best)):
            selected_epoch=int(row['epoch'])
            if eligible:best=key
    assert selected_epoch==final['best_epoch']==state['epoch']
    eligible=all(sm['clean'][k]>=control['clean'][k] for k in ['rank1','tar'] for control in [original,bm]) and cosines['clean']>=final['baseline_cosines']['clean']
    gate=selected_epoch>0 and eligible and all(sm[t][m]>bm[t][m] for t in ['upper10','lower10'] for m in ['rank1','tar']) and all(cosines[t]>final['baseline_cosines'][t] for t in ['upper10','lower10'])
    assert bool(gate)==final['recognition_validation_gate_passed']
    with np.load(out/'alinhamento_monitor.npz') as z:
        actual=np.stack([np.sum(selected[tag].astype(np.float64)*teacher.astype(np.float64),1) for tag,_,_ in CONDITIONS],1);np.testing.assert_array_equal(actual,z['after']);np.testing.assert_array_equal(z['valid'],c['valid'][mi])
    report=dict(status='polar_adapter_selection_and_monitor_audited',selected_epoch=selected_epoch,recognition_gate_reproduced=bool(gate),fit_and_monitor_people_disjoint=True,fit_clean_standardization_exact=True,selected_score_arrays_exact=True,selected_alignment_arrays_exact=True,monitor_queries=480)
    validation=a.output_root/'adaptador_polar_cadastro_fixo_val_2026-10-23'
    if (validation/'CONCLUIDO.json').exists():
        vf=json.loads((validation/'CONCLUIDO.json').read_text());assert not vf['test_inference'] and not vf['frozen_candidate_replaced']
        if not gate:assert not vf['validation_identity_inference'];report['validation_skipped_by_gate']=True
        else:
            from validar_adaptador_polar import ORDER,SUFFIX
            from validar_fusao_identidade_adaptada import calibrate
            outer=a.output_root/'contorno_consistente_val_2026-10-23';records=[]
            for record in vf['results']:
                tag=record['condition'];strategy=record['strategy'];components=[]
                for name in ORDER:
                    if strategy!='original_control' and name=='polar':file=validation/tag/f'polar_{strategy}.npz'
                    elif strategy!='original_control' and name in ['spatial','transformer','arc_clahe','arc_red']:file=outer/tag/f'scores_{name}.npz'
                    else:file=ROOT/'outputs'/f'confirmacao_congelada_val{SUFFIX[tag]}_2026-10-21'/f'scores_{name}.npz'
                    with np.load(file) as z:components.append({k:z[k] for k in ['scores','labels','valid']})
                params=vf['parameters'][strategy];labels=components[0]['labels'];scores,validity=fuse(components,params['calibration'])
                if tag=='clean' and strategy!='original_control':
                    assert calibrate(components)==params['calibration'];imp=np.ones_like(scores,bool);imp[np.arange(482),labels]=False
                    assert operating_threshold(scores[imp&validity[:,None]&(scores>-2)])==params['threshold']
                with np.load(validation/f'{strategy}_{tag}.npz') as z:
                    np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(validity,z['valid']);measured,correct,accepted=metrics(scores,labels,params['threshold'],validity);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
                for k in ['rank1','tar','far','queries','extraction_failures']:assert measured[k]==record[k]
                with (validation/f'{strategy}_{tag}.csv').open(encoding='utf-8',newline='') as f:csvrows=list(csv.DictReader(f))
                assert len(csvrows)==482;np.testing.assert_array_equal(np.array([[float(row[f'score_{j}']) for j in range(16)] for row in csvrows]),scores)
                records.append(dict(strategy=strategy,condition=tag,correct=int(correct.sum()),accepted=int(accepted.sum())))
            baseline={r['condition']:r for r in vf['results'] if r['strategy']=='original_control'};primary={r['condition']:r for r in vf['results'] if r['strategy']=='outer_adapted'};clean=primary['clean']
            advance=clean['rank1']>=.9 and clean['tar']>=.9 and clean['far']<=.01 and all(primary[t][m]>baseline[t][m] for t in ['upper10','lower10'] for m in ['rank1','tar']) and all(primary[t]['far']<=.01 for t in ['upper10','lower10'])
            absolute=all(r['rank1']>=.9 and r['tar']>=.9 and r['far']<=.01 for r in primary.values());assert bool(advance)==vf['promotion_gate_passed'] and bool(absolute)==vf['absolute_target_reached']
            report['validation_audit']=dict(records=records,fusion_and_csv_exact=True,advancement_gate_reproduced=bool(advance),absolute_target_reproduced=bool(absolute))
    (out/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
