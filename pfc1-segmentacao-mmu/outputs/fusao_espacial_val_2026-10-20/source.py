"""Controle de fusao fixa RGB/polar/espacial; nao otimiza pesos na validacao."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import metrics,operating_threshold
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz']]
    for p in paths:assert (p.parent/'CONCLUIDO.json').exists()
    out=ROOT/'outputs/fusao_espacial_val_2026-10-20';out.mkdir(exist_ok=True)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Development-only fixed equal three-way fusion; no weight search, test or occlusion scoring',
        'components':'RGB128 top3, polar64x512 top3, polar layer3 spatial prototype with zero angular shift',
        'normalization':'Per-component usable validation impostor mean/std, equal1/3 weights then logistic mapping; threshold empirical validation FMR<=1%',
        'failures':'Require every component query and pair valid, retain all482 queries/32eyes; invalid pairs floor-2',
        'caveat':'Components correlated; validation already examined, not independent confirmation',
        'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    components=[]
    for p in paths:
        with np.load(p) as z:components.append({k:z[k] for k in z.files})
    labels=components[0]['labels'];valid=np.logical_and.reduce([c['valid'] for c in components]);available=np.logical_and.reduce([c['scores']>-2 for c in components])
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels)
        selected=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][selected].mean());sd=float(c['scores'][selected].std())
        if sd<=0:raise ValueError('Constant impostor scores')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    score=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));score[~available]=-2;valid &= available.any(1)
    threshold=operating_threshold(score[imp&valid[:,None]&available]);result,correct,accepted=metrics(score,labels,threshold,valid)
    result.update(threshold=threshold,joint_success=float((correct&accepted).mean()),normalization=parameters)
    np.savez_compressed(out/'scores.npz',scores=score,labels=labels,valid=valid,correct=correct,accepted=accepted)
    (out/'CONCLUIDO.json').write_text(json.dumps({'status':'fixed_three_way_fusion_development_completed','metrics':result,'test_inference':False},indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
