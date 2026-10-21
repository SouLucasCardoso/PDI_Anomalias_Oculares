"""Fusao fixa de representacoes complementares, apenas desenvolvimento val."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import operating_threshold,metrics
    rgb=ROOT/'outputs/identidade_automatica_2026-10-20/scores_baseline.npz';polar=ROOT/'outputs/encoder_polar_2026-10-20/scores_melhor.npz'
    assert (polar.parent/'CONCLUIDO.json').exists(),'Wait for completed selection'
    out=ROOT/'outputs/fusao_polar_rgb_val_2026-10-20';out.mkdir(exist_ok=True)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Fixed equal-weight RGB/polar fusion on repeated development validation; no test or occlusion inference',
        'rule':'Each score standardized by its own usable validation impostor mean/std; average with fixed0.5+0.5 weights, then logistic mapping; no learned weights or weight search',
        'failure_handling':'Require both query extractions and both pair scores available; all queries/eyes retained, invalid pair floor-2',
        'calibration':'Standardization and FMR<=1% threshold on same validation, development only; not independent confirmation',
        'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb,polar)},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    with np.load(rgb) as z:a={k:z[k] for k in z.files}
    with np.load(polar) as z:b={k:z[k] for k in z.files}
    np.testing.assert_array_equal(a['labels'],b['labels']);labels=a['labels'];valid=a['valid']&b['valid']
    imp=np.ones_like(a['scores'],dtype=bool);imp[np.arange(len(labels)),labels]=False
    zscores=[];parameters=[]
    for value in (a,b):
        selected=imp&value['valid'][:,None]&(value['scores']>-2)
        mu=float(value['scores'][selected].mean());sd=float(value['scores'][selected].std())
        if sd<=0:raise ValueError('Constant impostor scores')
        zscores.append((value['scores']-mu)/sd);parameters.append({'impostor_mean':mu,'impostor_std':sd})
    score=1/(1+np.exp(-np.clip(.5*zscores[0]+.5*zscores[1],-30,30)))
    usable=(a['scores']>-2)&(b['scores']>-2);score[~usable]=-2
    valid &= usable.any(1)
    threshold=operating_threshold(score[imp&valid[:,None]&usable]);result,correct,accepted=metrics(score,labels,threshold,valid)
    result.update(threshold=threshold,joint_success=float((correct&accepted).mean()),normalization=parameters)
    np.savez_compressed(out/'scores.npz',scores=score,labels=labels,valid=valid,correct=correct,accepted=accepted)
    (out/'CONCLUIDO.json').write_text(json.dumps({'status':'fixed_fusion_development_completed','metrics':result,'test_inference':False},indent=2),encoding='utf-8');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
