"""Fusao fixa registrada: RGB + polar + espacial + novo polar denso."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json
import numpy as np

ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import metrics, operating_threshold, load_splits, paired_ci
    parser=argparse.ArgumentParser();parser.add_argument('--trained-dir',type=Path,required=True);args=parser.parse_args()
    trained=args.trained_dir.resolve()
    completion=json.loads((trained/'CONCLUIDO.json').read_text())
    protocol=json.loads((trained/'protocolo.json').read_text())
    assert completion['technical_smoke'] is False and protocol['dense_texture'] is True
    out=trained.parent/'fusao_densa_val_2026-10-20';out.mkdir(exist_ok=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve existing experiment')
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz',
        'encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz']]+[trained/'scores_melhor.npz']
    registered={'registered_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'UBIPr development validation, one query photo, multiple enrollment images; no test or occlusion scoring',
        'fusion':'Four components equal 1/4 weight; per-component validation impostor z-score then logistic',
        'failure_handling':'Require every query and pair valid; all482 queries retained',
        'calibration':'Empirical validation FMR<=1%; repeatedly examined development set, not independent confirmation',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'inputs_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (out/'protocolo.json').write_text(json.dumps(registered,indent=2),encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    components=[]
    for p in paths:
        with np.load(p) as z:components.append({k:z[k] for k in z.files})
    labels=components[0]['labels'];valid=np.logical_and.reduce([c['valid'] for c in components])
    available=np.logical_and.reduce([c['scores']>-2 for c in components]);imp=np.ones_like(available)
    imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels)
        assert c['scores'].shape==(482,32) and np.isfinite(c['scores']).all()
        selected=imp&c['valid'][:,None]&(c['scores']>-2)
        mu=float(c['scores'][selected].mean());sd=float(c['scores'][selected].std())
        if sd<=0:raise ValueError('Constant impostor scores')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    score=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)))
    score[~available]=-2;valid &= available.any(1)
    threshold=operating_threshold(score[imp&valid[:,None]&available])
    result,correct,accepted=metrics(score,labels,threshold,valid)
    assert not accepted[~valid].any()
    result.update(threshold=threshold,joint_success=float((correct&accepted).mean()),normalization=parameters)
    np.savez_compressed(out/'scores.npz',scores=score,labels=labels,valid=valid,correct=correct,accepted=accepted)
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    subjects=np.array([r.subject for r in rows if r.session==2])
    with np.load(ROOT/'outputs/fusao_espacial_val_2026-10-20/scores.npz') as z:previous={k:z[k] for k in z.files}
    comparison={}
    for key,new in [('correct',correct),('accepted',accepted)]:
        comparison[key]={'gain_pp':float(100*(new.mean()-previous[key].mean())),
                         'paired_person_ci95_pp':paired_ci(new,previous[key],subjects)}
    final={'status':'fixed_four_way_fusion_development_completed','metrics':result,'test_inference':False,
        'previous_three_way_comparison':comparison,'interval_caveat':'Pointwise, fixed gallery/thresholds; not corrected for checkpoint selection or repeated development',
        'minimum_area':None,'required_count_90':434,'correct_count':int(correct.sum()),'genuine_accept_count':int(accepted.sum())}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
    print(json.dumps(final,indent=2))

if __name__=='__main__':main()
