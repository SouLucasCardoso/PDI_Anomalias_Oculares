"""Fusao com calibracao de componentes restrita ao lado informado."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_lateralidade_informada import subset
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--convnext-dir',type=Path);args=parser.parse_args()
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz','resnet50_sessoes_2026-10-20/scores_melhor.npz']]
    if args.convnext_dir:
        assert (args.convnext_dir/'CONCLUIDO.json').exists();paths.append(args.convnext_dir/'scores_melhor.npz')
    out=args.output_root/f'fusao_lateral_{len(paths)}_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Explicitly authorized side-informed capture; UBIPr primary and one query; repeated development validation only',
        'method':'Restrict each component to16 candidate eyes of informed side BEFORE computing component impostor means/stds. Equal component weights, logistic, optional predefined per-query normalization over16 candidates.',
        'calibration':'Each variant threshold empirical validation FMR<=1%,15 admissible impostor comparisons per query; removed opposite-side eyes NOT counted as rejections',
        'variants':'One fixed equal-weight fusion and its predefined per-query normalization; no weights or parameter search',
        'failure_handling':'All482 queries and4 extraction failures retained, require every component valid',
        'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['validar_lateralidade_informada.py','normalizar_consulta.py','validar_metrica_intra_classe.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows});components=[]
    for p in paths:
        with np.load(p) as z:
            scores,labels,columns=subset(z['scores'],rows,ids);components.append(dict(scores=scores,labels=labels,valid=z['valid']))
    labels=components[0]['labels'];valid=np.logical_and.reduce([c['valid'] for c in components]);available=np.logical_and.reduce([c['scores']>-2 for c in components])
    assert available.shape==(482,16)
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2)
        mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=valid&available.any(1));result=measure(data);result.update(variant='side_conditioned_equal_fusion',normalization=parameters);results=[result];np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,data['valid']);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='side_conditioned_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    np.testing.assert_array_equal(ndata['correct'],data['correct'])
    final={'status':'side_conditioned_component_fusion_completed','components':len(paths),'results':results,'candidate_eyes_per_query':16,'impostor_comparisons_per_query':15,'test_inference':False,'minimum_area':None,
        'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
