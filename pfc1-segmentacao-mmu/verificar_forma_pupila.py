"""Recarga de forma e reproducao dos controles/fusao, sem nova inferencia de identidade."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from PIL import Image
import torch
from localizador_pupila import PupilLocator
from pupila_eliptica import EllipticShape,encode_shape
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_candidato_congelado import digest,fuse,WEIGHTS
    from avaliar_robustez_reconhecimento import metrics,operating_threshold,paired_ci
    from validar_fusao_identidade_adaptada import ORDER,calibrate
    from auditar_alvos_pupila import ellipse_geometry
    from treinar_segmentacao_ubipr import decode_mask
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    trained=a.output_root/'forma_pupila_2026-10-23';out=a.output_root/'forma_pupila_val_2026-10-23'
    training=json.loads((trained/'CONCLUIDO.json').read_text());protocol=json.loads((trained/'protocolo.json').read_text());result=json.loads((out/'CONCLUIDO.json').read_text())
    assert digest(trained/'melhor_forma.json')==training['shape_sha256']==result['shape_checkpoint_sha256']
    assert digest(trained/'source.py')==protocol['script_sha256'];assert digest(trained/'shape_source.py')==protocol['shape_source_sha256']
    assert not set(protocol['fit_people'])&set(protocol['monitor_people'])
    old_geometry=json.loads((ROOT/'outputs/pupila_aprendida_val_2026-10-22/CONCLUIDO.json').read_text())
    geometry_audit=[]
    for condition in result['changes']:
        old=next(r for r in old_geometry['changes'] if r['condition']==condition['condition'])
        mapping={r['image']:r['pupil_ellipse'] for r in old['details']};area_error=0.;anisotropic=0
        assert set(mapping)=={r['image'] for r in condition['details']}
        for row in condition['details']:
            circle=mapping[row['image']];ellipse=row['pupil_ellipse']
            np.testing.assert_array_equal(circle[0],ellipse[0])
            relative=abs(np.prod(circle[1])-np.prod(ellipse[1]))/np.prod(circle[1]);assert relative<1e-12
            area_error=max(area_error,float(relative));anisotropic+=int(abs(ellipse[1][0]-ellipse[1][1])>1e-6)
        geometry_audit.append(dict(condition=condition['condition'],fallback_images=len(mapping),noncircular_outputs=anisotropic,maximum_relative_area_difference=area_error,centers_exact=True))
    for file,expected in result['source_sha256'].items():assert digest(Path(file))==expected
    for _,(folder,expected) in WEIGHTS.items():assert digest(ROOT/'outputs'/folder/'melhor_modelo.pt')==expected
    previous=ROOT/'outputs/localizador_pupila_2026-10-22';assert digest(previous/'melhor_modelo.pt')==training['circle_checkpoint_sha256']
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu';circle=PupilLocator().to(device).eval();circle.load_state_dict(torch.load(previous/'melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    model=EllipticShape().to(device).eval();model.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in json.loads((trained/'melhor_forma.json').read_text())['state'].items()})
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());mapping={Path(r['image']).name:r for r in manifest['train']}
    monitor=json.loads((previous/'rows_monitor.json').read_text());targets=[]
    for row in monitor:
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(mapping[row['image']]['mask']).name) as im:mask=decode_mask(im)==1
        _,inner=ellipse_geometry(mask);targets.append(encode_shape(inner))
    with np.load(previous/'inputs_monitor.npz') as z:inputs=z['images']
    features=[]
    with torch.inference_mode():
        for start in range(0,len(inputs),128):
            x=torch.from_numpy(inputs[start:start+128].transpose(0,3,1,2).copy()).to(device).float()/255;features.append(circle.features(x).flatten(1))
        target=torch.from_numpy(np.stack(targets)).to(device);loss=float(torch.nn.functional.smooth_l1_loss(model(torch.cat(features)),target))
    assert abs(loss-training['best_monitor_loss'])<1e-9
    raw=manifest['val'];key=lambda r:f"{r['subject']}_{r['side']}";eligible={key(r) for r in raw if r['session']==1}&{key(r) for r in raw if r['session']==2}
    subjects=np.array([r['subject'] for r in raw if key(r) in eligible and r['session']==2]);assert len(subjects)==482
    def read(file):
        with np.load(file) as z:return {k:z[k] for k in z.files}
    loaded={};comparisons=[];maximum=0.
    for strategy,params in result['parameters'].items():
        loaded[strategy]={}
        for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
            original=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21'
            components=[]
            for name in ORDER:
                file=original/f'scores_{name}.npz'
                if name in ['polar','spatial','transformer','arc_clahe','arc_red']:
                    if strategy=='circle_fixed':file=ROOT/'outputs/pupila_aprendida_val_2026-10-22'/f'component_{name}_{condition}.npz'
                    elif strategy.startswith('ellipse_'):file=out/f'component_{name}_{condition}.npz'
                components.append(read(file))
            scores,valid=fuse(components,params['component_calibration']);stored=read(out/f'scores_{strategy}_{condition}.npz')
            np.testing.assert_array_equal(scores,stored['scores']);np.testing.assert_array_equal(valid,stored['valid']);maximum=max(maximum,float(np.max(abs(scores-stored['scores']))))
            calculated,correct,accepted=metrics(scores,stored['labels'],params['threshold'],valid)
            np.testing.assert_array_equal(correct,stored['correct']);np.testing.assert_array_equal(accepted,stored['accepted'])
            record=next(r for r in result['results'] if r['strategy']==strategy and r['condition']==condition)
            for k in ['rank1','tar','far','extraction_failures','queries']:assert calculated[k]==record[k]
            with (out/f'scores_{strategy}_{condition}.csv').open(encoding='utf-8',newline='') as f:csv_rows=list(csv.DictReader(f))
            np.testing.assert_array_equal(np.array([[float(r[f'score_{j}']) for j in range(16)] for r in csv_rows]),scores)
            if strategy=='circle_fixed':
                old=read(ROOT/'outputs/pupila_aprendida_val_2026-10-22'/f'scores_new_fixed_{condition}.npz');np.testing.assert_array_equal(scores,old['scores'])
            loaded[strategy][condition]=stored
        if strategy=='ellipse_clean_calibrated':
            components=[read(out/f'component_{n}_clean.npz') if n in ['polar','spatial','transformer','arc_clahe','arc_red'] else read(ROOT/'outputs/confirmacao_congelada_val_2026-10-21'/f'scores_{n}.npz') for n in ORDER]
            np.testing.assert_array_equal(np.array(calibrate(components)),np.array(params['component_calibration']))
            data=loaded[strategy]['clean'];impostor=np.ones_like(data['scores'],bool);impostor[np.arange(482),data['labels']]=False
            assert params['threshold']==operating_threshold(data['scores'][impostor&data['valid'][:,None]&(data['scores']>-2)])
    for condition in ['clean','upper10','lower10']:
        new=loaded['ellipse_fixed'][condition]
        for control in ['original_control','circle_fixed']:
            old=loaded[control][condition]
            comparisons.append(dict(condition=condition,control=control,rank1_gain_pp=float(100*(new['correct'].mean()-old['correct'].mean())),rank1_gain_ci95_pp=paired_ci(new['correct'],old['correct'],subjects),tar_gain_pp=float(100*(new['accepted'].mean()-old['accepted'].mean())),tar_gain_ci95_pp=paired_ci(new['accepted'],old['accepted'],subjects),lost_correct=int((old['correct']&~new['correct']).sum()),recovered=int((~old['correct']&new['correct']).sum())))
    final=dict(status='ellipse_shape_and_fusion_reload_verified',monitor_loss=loss,maximum_score_difference=maximum,circle_control_exact=True,identity_checkpoint_hashes_unchanged=True,all_csv_scores_match_npz=True,geometry=geometry_audit,comparisons=comparisons,test_inference=False,frozen_candidate_replaced=False,minimum_area=None,limits='Proxy labels; reused internal monitor/development validation.5000person-cluster pointwise bootstrap with fixed gallery/threshold; no model-selection correction.')
    (out/'VERIFICACAO_RELOAD.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
