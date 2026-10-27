"""Reproduz a decisão do pacote recuperado sem refazer os vetores das CNNs."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import torch
from avaliar_candidato_congelado import digest,fuse
from avaliar_robustez_reconhecimento import metrics
ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
SUFFIX={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--restored-root',type=Path,required=True);a=p.parse_args();out=a.restored_root;folder=out/'adaptador_polar_cadastro_fixo_2026-10-23'
    final=json.loads((folder/'CONCLUIDO.json').read_text());state=torch.load(folder/'melhor_modelo.pt',map_location='cpu',weights_only=True);assert digest(folder/'melhor_modelo.pt')==final['checkpoint_sha256'] and state['epoch']==final['best_epoch']
    assert state['raw_mean'].shape==state['raw_std'].shape==(512,) and bool(torch.all(state['raw_std']>0))
    checked=[]
    for prefix,record in [('original_clean',final['original_monitor'])]+[(f'{name}_{tag}',final[f'{name}_monitor'][tag]) for name in ['baseline','selected'] for tag in SUFFIX]:
        with np.load(folder/f'scores_{prefix}.npz') as z:
            measured,correct,accepted=metrics(z['scores'],z['labels'],record['threshold'],z['valid']);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
        for k in ['rank1','tar','far','queries','extraction_failures']:assert measured[k]==record[k]
        checked.append(dict(method=prefix,correct=int(correct.sum()),accepted=int(accepted.sum())))
    with np.load(folder/'alinhamento_monitor.npz') as z:
        for j,tag in enumerate(SUFFIX):
            paired=z['valid'][:,j]&z['teacher_valid'];np.testing.assert_allclose(z['after'][paired,j].mean(),final['selected_cosines'][tag],rtol=0,atol=1e-12)
            np.testing.assert_allclose(z['before'][paired,j].mean(),final['baseline_cosines'][tag],rtol=0,atol=1e-6)
    selected=final['selected_monitor'];baseline=final['baseline_monitor'];original=final['original_monitor'];cosines=final['selected_cosines']
    eligible=all(selected['clean'][k]>=control[k] for k in ['rank1','tar'] for control in [original,baseline['clean']]) and cosines['clean']>=final['baseline_cosines']['clean']
    gate=final['best_epoch']>0 and eligible and all(selected[t][m]>baseline[t][m] for t in ['upper10','lower10'] for m in ['rank1','tar']) and all(cosines[t]>final['baseline_cosines'][t] for t in ['upper10','lower10']);assert bool(gate)==final['recognition_validation_gate_passed']
    report=dict(status='restored_polar_adapter_verified',monitor_records=checked,monitor_gate_reproduced=bool(gate),checkpoint_hash_verified=True,alignment_statistics_reproduced=True,full_feature_or_image_forward_replayed=False)
    replay=folder/'REPRODUCAO_ULTIMA_EPOCA.json'
    if replay.exists():
        rejected=json.loads(replay.read_text());weights=torch.load(folder/'ultima_epoca_rejeitada.pt',map_location='cpu',weights_only=True)
        assert weights['rejected'] and weights['epoch']==rejected['epoch'] and not rejected['accepted']
        assert digest(folder/'ultima_epoca_rejeitada.pt')==rejected['checkpoint_sha256']
        for tag,record in rejected['metrics'].items():
            with np.load(folder/f'scores_rejected_last_{tag}.npz') as z:
                measured,correct,accepted=metrics(z['scores'],z['labels'],record['threshold'],z['valid'])
                np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            for k in ['rank1','tar','far','queries','extraction_failures']:assert measured[k]==record[k]
            assert int(correct.sum())==record['correct'] and int(accepted.sum())==record['accepted']
        report['rejected_last_checkpoint_hash_and_scores_verified']=True
        report['training_loss_replay_maximum_difference']=rejected['maximum_training_loss_difference']
    validation=out/'adaptador_polar_cadastro_fixo_val_2026-10-23';vf=json.loads((validation/'CONCLUIDO.json').read_text())
    if not gate:assert not vf['validation_identity_inference'];report['validation_skipped_by_gate']=True
    else:
        records=[]
        for record in vf['results']:
            tag=record['condition'];strategy=record['strategy'];components=[]
            for name in ORDER:
                if strategy!='original_control' and name=='polar':file=validation/tag/f'polar_{strategy}.npz'
                elif strategy!='original_control' and name in ['spatial','transformer','arc_clahe','arc_red']:file=out/'dependency_outer_components'/tag/f'scores_{name}.npz'
                else:file=ROOT/'outputs'/f'confirmacao_congelada_val{SUFFIX[tag]}_2026-10-21'/f'scores_{name}.npz'
                with np.load(file) as z:components.append({k:z[k] for k in ['scores','labels','valid']})
            params=vf['parameters'][strategy];scores,valid=fuse(components,params['calibration']);labels=components[0]['labels']
            with np.load(validation/f'{strategy}_{tag}.npz') as z:
                np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(valid,z['valid']);measured,correct,accepted=metrics(scores,labels,params['threshold'],valid);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            for k in ['rank1','tar','far','queries']:assert measured[k]==record[k]
            with (validation/f'{strategy}_{tag}.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
            assert len(rows)==482;np.testing.assert_array_equal(np.array([[float(r[f'score_{j}']) for j in range(16)] for r in rows]),scores)
            records.append(dict(strategy=strategy,condition=tag,correct=int(correct.sum()),accepted=int(accepted.sum())))
        report['validation_records']=records;report['validation_score_fusion_and_csv_exact']=True
    (out/'VERIFICACAO_RECUPERACAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
