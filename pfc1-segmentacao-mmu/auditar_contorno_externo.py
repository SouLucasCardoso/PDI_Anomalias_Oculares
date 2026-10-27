"""Reproduz seleção geométrica e, quando disponível, a validação biométrica."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import torch
from torch import nn
from contorno_externo import OuterCorrection
from treinar_contorno_externo import WEIGHT
from avaliar_candidato_congelado import digest,fuse,WEIGHTS

ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
CONDITIONS={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--training-name',default='contorno_externo_2026-10-23');p.add_argument('--experiment-name',default='contorno_externo_val_2026-10-23');a=p.parse_args()
    folder=a.output_root/a.training_name;validation=a.output_root/a.experiment_name
    final=json.loads((folder/'CONCLUIDO.json').read_text());protocol=json.loads((folder/'protocolo.json').read_text());state=torch.load(folder/'melhor_modelo.pt',map_location='cpu',weights_only=True)
    assert digest(ROOT/'contorno_externo.py')==protocol['module_sha256']==digest(folder/'contorno_source.py')
    consistent=final['status']=='clean_teacher_outer_geometry_training_completed'
    script='treinar_contorno_consistente.py' if consistent else 'treinar_contorno_externo.py'
    assert digest(ROOT/script)==protocol['script_sha256']==digest(folder/'source.py')
    inputs=a.output_root/'contorno_externo_2026-10-23' if consistent else folder
    if consistent:
        for group,value in protocol['source_cache_sha256'].items():assert digest(inputs/f'inputs_{group}.npz')==value
    assert digest(folder/'melhor_modelo.pt')==final['checkpoint_sha256']
    fit=set(protocol['fit_people']);monitor=set(protocol['monitor_people']);assert not fit&monitor
    seen=0
    for name,people in [('fit',fit),('monitor',monitor)]:
        rows=json.loads((inputs/f'rows_{name}.json').read_text());assert set(r['subject'] for r in rows)<=people;seen+=len(rows)
    assert seen+sum(final['data_audit']['exclusions'].values())==final['data_audit']['all_original_train_images']==7716
    with np.load(inputs/'inputs_fit.npz') as z:
        mean=z['features'][:,0].mean(0);std=z['features'][:,0].std(0).clip(1e-5)
    np.testing.assert_array_equal(state['feature_mean'].numpy(),mean);np.testing.assert_array_equal(state['feature_std'].numpy(),std)
    with np.load(inputs/'inputs_monitor.npz') as z:features=z['features'];base=z['baseline'];target=z['target']
    with np.load(folder/'predicoes_monitor.npz') as z:saved=z['predictions'];np.testing.assert_array_equal(z['baseline'],base);np.testing.assert_array_equal(z['target'],target)
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu';model=OuterCorrection().to(device).eval();model.load_state_dict(state['model'])
    x=torch.from_numpy((features-mean)/std).to(device);b=torch.from_numpy(base).to(device)
    with torch.inference_mode():actual=model(x.flatten(0,1),b.flatten(0,1)).reshape(len(x),3,5).cpu().numpy()
    np.testing.assert_allclose(actual,saved,rtol=1e-5,atol=1e-6)
    weight=torch.tensor(WEIGHT);pred=torch.from_numpy(saved);truth=torch.from_numpy(target)[:,None].expand_as(pred)
    values=((nn.functional.smooth_l1_loss(pred,truth,reduction='none')*weight).mean(-1)).mean(0).numpy()
    baseline=((nn.functional.smooth_l1_loss(torch.from_numpy(base),truth,reduction='none')*weight).mean(-1)).mean(0).numpy()
    drift=(((pred[:,1:]-pred[:,:1])**2)*weight).mean((0,2)).numpy()
    base_drift=(((torch.from_numpy(base)[:,1:]-torch.from_numpy(base)[:,:1])**2)*weight).mean((0,2)).numpy()
    np.testing.assert_allclose(baseline,final['baseline_losses'],rtol=1e-5,atol=1e-10);np.testing.assert_allclose(base_drift,final['baseline_drift'],rtol=1e-5,atol=1e-10)
    with (folder/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    best=history[0];best_value=max(float(best['upper10_loss']),float(best['lower10_loss']))
    for row in history[1:]:
        value=max(float(row['upper10_loss']),float(row['lower10_loss']))
        if row['eligible']=='True' and value<best_value:best=row;best_value=value
    assert int(best['epoch'])==final['best_epoch']==state['epoch']
    np.testing.assert_allclose(values,[float(best[k]) for k in ['clean_loss','upper10_loss','lower10_loss']],rtol=1e-5,atol=1e-10)
    if final['best_epoch']:
        assert values[0]<=1.05*baseline[0]+1e-10 and np.all(drift<=base_drift+1e-9)
    gate=final['best_epoch']>0 and best_value<max(final['baseline_losses'][1:]);assert gate==final['recognition_validation_gate_passed']
    for name,(directory,expected) in WEIGHTS.items():assert digest(ROOT/'outputs'/directory/'melhor_modelo.pt')==expected
    report=dict(status='outer_training_selection_and_geometry_audited',geometry_gate_reproduced=bool(gate),fit_and_monitor_disjoint=True,standardization_fit_clean_only_verified=True,selected_predictions_max_difference=float(np.abs(actual-saved).max()),selected_losses=values.tolist(),selected_drift=drift.tolist(),identity_weights_unchanged=True)
    if (validation/'CONCLUIDO.json').exists():
        vf=json.loads((validation/'CONCLUIDO.json').read_text())
        assert not vf['test_inference'] and not vf['frozen_candidate_replaced']
        if not gate:assert vf['status']=='outer_geometry_gate_failed_no_identity_inference';report['recognition_inference_skipped']=True
        else:
            from avaliar_robustez_reconhecimento import metrics,operating_threshold
            from validar_fusao_identidade_adaptada import calibrate
            grouped={}
            for tag,suffix in CONDITIONS.items():
                grouped[tag]={}
                for name in ORDER:
                    file=validation/tag/f'scores_{name}.npz' if name in ['polar','spatial','transformer','arc_clahe','arc_red'] else ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21'/f'scores_{name}.npz'
                    with np.load(file) as z:grouped[tag][name]={k:z[k] for k in ['scores','labels','valid']}
                    assert grouped[tag][name]['scores'].shape==(482,16)
            assert calibrate([grouped['clean'][n] for n in ORDER])==vf['parameters']['outer_clean_calibrated']['calibration']
            records=[]
            for row in vf['results']:
                tag=row['condition'];strategy=row['strategy'];params=vf['parameters'][strategy];labels=grouped[tag]['rgb']['labels']
                scores,valid=fuse([grouped[tag][n] for n in ORDER],params['calibration'])
                with np.load(validation/f'{strategy}_{tag}.npz') as z:
                    np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(valid,z['valid']);np.testing.assert_array_equal(labels,z['labels'])
                    measured,correct,accepted=metrics(scores,labels,params['threshold'],valid);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
                for k in ['rank1','tar','far','queries','extraction_failures']:assert measured[k]==row[k]
                if strategy=='outer_clean_calibrated' and tag=='clean':
                    imp=np.ones_like(scores,bool);imp[np.arange(482),labels]=False
                    assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==params['threshold']
                with (validation/f'{strategy}_{tag}.csv').open(encoding='utf-8',newline='') as f:csvrows=list(csv.DictReader(f))
                assert len(csvrows)==482
                np.testing.assert_array_equal(np.array([[float(r[f'score_{j}']) for j in range(16)] for r in csvrows]),scores)
                records.append(dict(strategy=strategy,condition=tag,correct=int(correct.sum()),accepted=int(accepted.sum()),false_accepts=int(round(measured['far']*7230))))
            primary={r['condition']:r for r in vf['results'] if r['strategy']=='outer_clean_calibrated'};c=primary['clean']
            advancement=c['rank1']>=.9 and c['tar']>=.9 and c['far']<=.01 and all(primary[tag][m]>vf['baseline'][tag][m] for tag in ['upper10','lower10'] for m in ['rank1','tar']) and all(primary[tag]['far']<=.01 for tag in ['upper10','lower10'])
            absolute=all(r['rank1']>=.9 and r['tar']>=.9 and r['far']<=.01 for r in primary.values())
            assert bool(advancement)==vf['promotion_gate_passed'] and bool(absolute)==vf['absolute_all_conditions_target_reached']
            report['recognition_audit']=dict(records=records,fusion_and_csv_exact=True,advancement_gate_reproduced=bool(advancement),absolute_target_reproduced=bool(absolute))
    (folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
