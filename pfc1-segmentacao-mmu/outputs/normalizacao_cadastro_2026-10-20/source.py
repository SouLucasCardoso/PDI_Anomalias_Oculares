"""Cohort por olho com fotos de cadastro; nenhuma identidade de consulta no ajuste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch

ROOT=Path(__file__).resolve().parent

def main():
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_metrica_intra_classe import extract,score,measure
    from comparador_hdbif_lote import aggregate
    from normalizacao_cadastro import fit,transform
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'normalizacao_cadastro_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    checkpoints=[ROOT/'outputs'/p/'melhor_modelo.pt' for p in ['identidade_automatica_2026-10-20','encoder_polar_2026-10-20']]
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'UBIPr, single query, development validation only',
        'method':'Frozen previous RGB/polar features. For each enrolled eye, mean/std of all other valid-eye enrollment captures scored against its top3 enrollment templates. No genuine cohort pairs and no query labels in normalization fitting.',
        'variants':'RGB enrollment-cohort normalization, polar enrollment-cohort normalization; equal thirds fusion with previous spatial, with/without predefined per-query normalization',
        'fusion':'Invert logistic cohort mapping; standardize each component by validation impostor mean/std; equal weights then logistic. No weight/parameter search.',
        'calibration':'Each threshold validation empirical FMR<=1%; repeatedly examined validation, no independent confirmation',
        'failure_handling':'All482 queries retained; no valid enrollment cohort raises error instead of removing eye',
        'checkpoint_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checkpoints},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['normalizacao_cadastro.py','normalizar_consulta.py','validar_metrica_intra_classe.py','comparador_hdbif_lote.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name))
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids];glabels=np.array([ids.index(identity(rows[i])) for i in gi])
    results=[];components=[]
    for name,checkpoint in zip(['rgb','polar'],checkpoints):
        cache=ROOT/'data'/('cache_identidade_automatica_2026-10-20' if name=='rgb' else 'cache_encoder_polar_2026-10-20')
        images=np.load(cache/('val_crops.npy' if name=='rgb' else 'val_polar.npy'),mmap_mode='r');valid=np.load(cache/'val_valid.npy')
        model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model']);features=extract(model,images,device);del model
        raw=features[gi]@features[gi].T;raw[:,~valid[gi]]=-2;cohort=aggregate(raw.astype(np.float64),groups,'top3')
        means,stds,counts=fit(cohort,glabels,valid[gi]);np.savez_compressed(out/f'cohort_{name}.npz',mean=means,std=stds,count=counts)
        data=score(features,valid,rows);control=measure(data);control['variant']=name+'_unmodified_replication';results.append(control)
        np.savez_compressed(out/f'scores_{name}_controle.npz',**data)
        data['scores']=transform(data['scores'],means,stds);result=measure(data);result['variant']=name+'_enrollment_normalized';results.append(result);components.append(data)
        np.savez_compressed(out/f'scores_{name}.npz',**data);print(json.dumps(result),flush=True)
    with np.load(ROOT/'outputs/espacial_polar_val_2026-10-20/scores_shift0.npz') as z:components.append({k:z[k] for k in z.files})
    labels=components[0]['labels'];available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for j,c in enumerate(components):
        np.testing.assert_array_equal(c['labels'],labels);raw=c['scores']
        if j<2:raw=np.log(np.clip(raw,1e-12,1-1e-12)/np.clip(1-raw,1e-12,1))
        usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(raw[usable].mean());sd=float(raw[usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        standardized.append((raw-mu)/sd);parameters.append({'mean':mu,'std':sd})
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=valid&available.any(1));result=measure(data);result.update(variant='fixed_three_way',normalization=parameters);results.append(result);np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,data['valid']);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='fixed_three_way_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    np.testing.assert_array_equal(ndata['correct'],data['correct'])
    final={'status':'enrollment_cohort_normalization_completed','results':results,'test_inference':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
