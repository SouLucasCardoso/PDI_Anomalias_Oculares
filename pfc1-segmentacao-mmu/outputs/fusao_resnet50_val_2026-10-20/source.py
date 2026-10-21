"""Fusao fixa de quatro componentes e normalizacao de uma consulta."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--trained-dir',type=Path,required=True);args=parser.parse_args()
    trained=args.trained_dir.resolve();assert (trained/'CONCLUIDO.json').exists()
    out=trained.parent/'fusao_resnet50_val_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz']]+[trained/'scores_melhor.npz']
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'UBIPr primary, single query photo; repeated development validation only; no test or occlusion',
        'fusion':'Four fixed equal1/4 components RGB/polar/spatial/ResNet50; validation impostor z-score then logistic',
        'variants':'Fixed fusion; same fusion with previously defined per-query normalization; no weights or temperature search',
        'calibration':'Per-variant empirical validation FMR<=1%; all482 queries retained, require all components valid',
        'inputs_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'normalization_module_sha256':hashlib.sha256((ROOT/'normalizar_consulta.py').read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    components=[]
    for p in paths:
        with np.load(p) as z:components.append({k:z[k] for k in z.files})
    labels=components[0]['labels'];valid=np.logical_and.reduce([c['valid'] for c in components]);available=np.logical_and.reduce([c['scores']>-2 for c in components])
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels)
        assert c['scores'].shape==(482,32) and np.isfinite(c['scores']).all()
        selected=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][selected].mean());sd=float(c['scores'][selected].std())
        if sd<=0:raise ValueError('Constant impostors')
        parameters.append({'mean':mu,'std':sd});standardized.append((c['scores']-mu)/sd)
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=valid&available.any(1));result=measure(data);result.update(variant='fixed_four_way',normalization=parameters);results=[result];np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,data['valid']);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='fixed_four_way_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    np.testing.assert_array_equal(ndata['correct'],data['correct'])
    final={'status':'fixed_resnet50_fusion_completed','results':results,'test_inference':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
