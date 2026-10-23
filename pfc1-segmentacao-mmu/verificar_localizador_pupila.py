"""Recarga da geometria e reproducao independente das metricas de validacao."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import torch
from localizador_pupila import PupilLocator
ROOT=Path(__file__).resolve().parent


def main():
    from avaliar_candidato_congelado import digest,fuse,WEIGHTS
    from avaliar_robustez_reconhecimento import metrics,operating_threshold,paired_ci
    from validar_fusao_identidade_adaptada import ORDER,calibrate
    from diagnosticar_erros_validacao import transitions
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'outputs');a=p.parse_args()
    trained=a.output_root/'localizador_pupila_2026-10-22';evaluated=a.output_root/'pupila_aprendida_val_2026-10-22'
    training=json.loads((trained/'CONCLUIDO.json').read_text());protocol=json.loads((trained/'protocolo.json').read_text());final=json.loads((evaluated/'CONCLUIDO.json').read_text())
    assert digest(trained/'melhor_modelo.pt')==training['checkpoint_sha256'];assert digest(trained/'source.py')==protocol['script_sha256'];assert digest(trained/'localizador_source.py')==protocol['locator_source_sha256']
    assert not set(protocol['fit_people'])&set(protocol['monitor_people'])
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';assert digest(manifest_file)==protocol['manifest_sha256'];manifest=json.loads(manifest_file.read_text())
    assert not (set(protocol['fit_people'])|set(protocol['monitor_people']))&{r['subject'] for r in manifest['val']}
    for group,people in [('fit',protocol['fit_people']),('monitor',protocol['monitor_people'])]:
        rows=json.loads((trained/f'rows_{group}.json').read_text());assert all(r['subject'] in people for r in rows);assert len(rows)==training['data_audit']['prepared'][group]
    assert sum(training['data_audit']['prepared'].values())+sum(training['data_audit']['excluded'].values())==len(manifest['train'])
    with (trained/'historico.csv').open(encoding='utf-8',newline='') as stream:history=list(csv.DictReader(stream))
    assert int(min(history,key=lambda r:float(r['monitor_loss']))['epoch'])==training['best_epoch']
    torch.set_num_threads(4);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=PupilLocator().to(device).eval();model.load_state_dict(torch.load(trained/'melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    with np.load(trained/'inputs_monitor.npz') as z:images=z['images'];target=torch.from_numpy(z['targets']).to(device);baseline=torch.from_numpy(z['baseline']).to(device)
    predictions=[]
    with torch.inference_mode():
        for start in range(0,len(images),128):predictions.append(model(torch.from_numpy(images[start:start+128].transpose(0,3,1,2).copy()).to(device).float()/255))
    weights=torch.tensor([1.,1.,4.],device=device);loss=float((torch.nn.functional.smooth_l1_loss(torch.cat(predictions),target,reduction='none')*weights).mean());baseline_loss=float((torch.nn.functional.smooth_l1_loss(baseline,target,reduction='none')*weights).mean())
    assert loss==training['best_monitor_loss'] and baseline_loss==training['baseline_monitor_loss']
    if not training['recognition_validation_gate_passed']:
        audit=dict(status='pupil_monitor_reload_verified_gate_failed',monitor_loss=loss,baseline_loss=baseline_loss,test_inference=False,identity_validation_not_run=True)
        (trained/'VERIFICACAO_RELOAD.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(audit));return
    assert final['locator_checkpoint_sha256']==training['checkpoint_sha256']
    for file,expected in final['source_sha256'].items():assert digest(Path(file))==expected
    for _,(folder,expected) in WEIGHTS.items():assert digest(ROOT/'outputs'/folder/'melhor_modelo.pt')==expected
    def read(file):
        with np.load(file) as z:return {k:z[k] for k in z.files}
    conditions=[('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')];original={};modified={}
    for condition,suffix in conditions:
        folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21';original[condition]=[read(folder/f'scores_{name}.npz') for name in ORDER];modified[condition]=[]
        for j,name in enumerate(ORDER):
            file=evaluated/f'component_{name}_{condition}.npz';modified[condition].append(read(file) if file.exists() else original[condition][j])
            np.testing.assert_array_equal(modified[condition][-1]['labels'],original[condition][0]['labels']);np.testing.assert_array_equal(modified[condition][-1]['valid'],original[condition][j]['valid'])
    np.testing.assert_equal(calibrate(modified['clean']),final['parameters']['new_clean_calibrated']['component_calibration'])
    key=lambda r:f"{r['subject']}_{r['side']}";raw=manifest['val'];eligible={key(r) for r in raw if r['session']==1}&{key(r) for r in raw if r['session']==2};queries=[r for r in raw if key(r) in eligible and r['session']==2];subjects=np.array([r['subject'] for r in queries]);assert len(queries)==482
    decisions={};maximum=0.
    for strategy,parameters in final['parameters'].items():
        data=original if strategy=='original_control' else modified;decisions[strategy]={};threshold=parameters['threshold']
        for condition,_ in conditions:
            scores,valid=fuse(data[condition],parameters['component_calibration']);saved=read(evaluated/f'scores_{strategy}_{condition}.npz');maximum=max(maximum,float(np.abs(scores-saved['scores']).max()));np.testing.assert_array_equal(scores,saved['scores']);np.testing.assert_array_equal(valid,saved['valid'])
            result,correct,accepted=metrics(scores,saved['labels'],threshold,valid);np.testing.assert_array_equal(correct,saved['correct']);np.testing.assert_array_equal(accepted,saved['accepted'])
            reported=next(r for r in final['results'] if r['strategy']==strategy and r['condition']==condition)
            for metric in ['rank1','tar','far','extraction_failures','queries']:assert result[metric]==reported[metric]
            assert reported['threshold']==threshold
            if strategy=='new_clean_calibrated' and condition=='clean':
                imp=np.ones_like(scores,bool);imp[np.arange(482),saved['labels']]=False;assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==threshold
            decisions[strategy][condition]=dict(correct=correct,accepted=accepted)
    comparisons=[]
    for strategy in ['new_fixed','new_clean_calibrated']:
        for condition,_ in conditions:
            baseline=decisions['original_control'][condition];new=decisions[strategy][condition]
            comparisons.append(dict(strategy=strategy,condition=condition,rank1_gain_pp=100*float((new['correct'].astype(float)-baseline['correct']).mean()),rank1_gain_ci95_pp=paired_ci(new['correct'],baseline['correct'],subjects),tar_gain_pp=100*float((new['accepted'].astype(float)-baseline['accepted']).mean()),tar_gain_ci95_pp=paired_ci(new['accepted'],baseline['accepted'],subjects),transitions=transitions(baseline['correct'],new['correct'])))
    audit=dict(status='pupil_locator_and_fusion_reload_verified',monitor_loss=loss,baseline_loss=baseline_loss,locator_person_split_verified=True,original_identity_checkpoint_hashes_unchanged=True,maximum_fusion_score_difference=maximum,comparisons=comparisons,test_inference=False,frozen_candidate_replaced=False,minimum_area=None,limits='Proxy pupil labels; repeated development validation;5000 person-cluster pointwise bootstrap with fixed gallery/threshold, no model-selection correction.')
    (evaluated/'VERIFICACAO_RELOAD.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
