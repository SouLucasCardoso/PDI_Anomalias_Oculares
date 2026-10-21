"""Tres grupos de escala por olho, todas as referencias validas preservadas."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def partition(positions,widths,valid):
    ordered=sorted([i for i in positions if valid[i]],key=lambda i:(widths[i],i))
    return [part.tolist() for part in np.array_split(np.array(ordered,dtype=int),3) if len(part)]

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_lateralidade_informada import subset
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    source=args.output_root/'selecao_cadastro_2026-10-21';assert (source/'CONCLUIDO.json').exists()
    out=args.output_root/'prototipos_escala_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    audit_source=ROOT/'data/cache_encoder_polar_2026-10-20/val_auditoria.json';paths=[source/f'scores_capturas_{j}.npz' for j in range(4)]
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed UBIPr, single query, development validation only',
        'method':'For each eye sort valid S1 enrollment captures by native predicted iris width, split into3equal-size groups, no reference discarded. For each CNN score use max of the3 group mean cosine scores. This changes aggregation only; previous raw capture scores reused exactly.',
        'fusion':'Same5 frozen components RGB/polar/ResNet50/ConvNeXt and previous spatial, equal weights, same-side impostor z-score, logistic; with/without predefined query normalization',
        'calibration':'15same-side impostors/query, empirical validation FMR<=1%; all482 queries and extraction failures retained; no query-dependent group fitting or parameter search',
        'limitations':'Native width is a scale proxy, not controlled physical distance; repeated validation not independent confirmation',
        'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[audit_source]},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));audit=json.loads(audit_source.read_text())
    widths=np.array([audit[i]['geometry']['native_iris_width'] if audit[i]['geometry'] else 128 for i in gi])
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids];components=[];group_audit=[]
    with np.load(source/'scores_all_top3.npz') as z:qvalid=z['valid']
    for j,p in enumerate(paths):
        with np.load(p) as z:raw=z['scores']
        gvalid=(raw>-2).any(0);scores=np.full((len(raw),len(ids)),-2.,dtype=np.float64)
        for k,positions in enumerate(groups):
            divided=partition(positions,widths,gvalid)
            if divided:scores[:,k]=np.stack([raw[:,part].mean(1) for part in divided]).max(0)
            if j==0:group_audit.append({'eye':ids[k],'groups':[[{'image':Path(rows[gi[i]].image).name,'native_width':float(widths[i])} for i in part] for part in divided],'retained_valid_references':sum(map(len,divided))})
        sided,labels,_=subset(scores,rows,ids);components.append(dict(scores=sided,labels=labels,valid=qvalid))
    (out/'grupos_cadastro.json').write_text(json.dumps(group_audit,indent=2),encoding='utf-8')
    with np.load(ROOT/'outputs/espacial_polar_val_2026-10-20/scores_shift0.npz') as z:scores,labels,_=subset(z['scores'],rows,ids);components.append(dict(scores=scores,labels=labels,valid=z['valid']))
    available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=valid);result=measure(data);result.update(variant='scale_group_mean_max_fusion',normalization=parameters);results=[result];np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,valid);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='scale_group_fusion_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    np.testing.assert_array_equal(data['correct'],ndata['correct'])
    final={'status':'scale_group_prototypes_completed','results':results,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
