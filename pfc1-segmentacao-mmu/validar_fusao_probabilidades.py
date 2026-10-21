"""Media de probabilidades por componente, com uma unica foto de consulta."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def mean_probabilities(standardized,available,valid):
    components=[]
    for z in standardized:
        probability=np.zeros_like(z,dtype=np.float64)
        for i in np.flatnonzero(valid):
            selected=available[i];values=z[i,selected];weights=np.exp(values-values.max());probability[i,selected]=weights/weights.sum()
        components.append(probability)
    scores=np.mean(components,axis=0);scores[~available]=-2;scores[~valid]=-2
    return scores

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_lateralidade_informada import subset
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--native-dir',type=Path);args=parser.parse_args()
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz','resnet50_sessoes_2026-10-20/scores_melhor.npz','convnext_contraste_2026-10-20/scores_melhor.npz']]
    if args.native_dir:
        assert (args.native_dir/'CONCLUIDO.json').exists();paths.append(args.native_dir/'scores_melhor.npz')
    out=args.output_root/f'fusao_probabilidades_{len(paths)}_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve existing experiment')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed UBIPr, one query; development validation only',
        'method':'Per-component same-side validation impostor z-score; softmax over16 enrolled eyes for that single query, fixed temperature1; arithmetic mean of probabilities with equal model weights; no weight/temperature search',
        'variants':'Equal probability fusion, same with predefined per-query logit normalization; five components, six when native224 completed',
        'failure_handling':'All482 queries retained, common available candidate comparisons only; require every component query valid',
        'calibration':'Each threshold empirical validation FMR<=1%,15 admissible same-side impostors per query; repeated development not independent confirmation',
        'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['normalizar_consulta.py','validar_lateralidade_informada.py','validar_metrica_intra_classe.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows});components=[]
    for p in paths:
        with np.load(p) as z:scores,labels,_=subset(z['scores'],rows,ids);components.append(dict(scores=scores,labels=labels,valid=z['valid']))
    valid=np.logical_and.reduce([c['valid'] for c in components]);available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid &= available.any(1)
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    scores=mean_probabilities(standardized,available,valid)
    np.testing.assert_allclose(np.where(available,scores,0)[valid].sum(1),1,rtol=0,atol=1e-12)
    data=dict(scores=scores,labels=labels,valid=valid);result=measure(data);result.update(variant='mean_model_probabilities',normalization=parameters);results=[result];np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,valid);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='mean_probabilities_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    np.testing.assert_array_equal(data['correct'],ndata['correct'])
    final={'status':'fixed_mean_probability_fusion_completed','components':len(paths),'results':results,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
