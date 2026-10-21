"""Selecao de3 referencias por qualidade; consultas preservadas integralmente."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_metrica_intra_classe import extract,measure
    from comparador_hdbif_lote import aggregate
    from reconhecedor_convnext import load,contrast
    from validar_lateralidade_informada import subset
    from normalizar_consulta import normalize
    from qualidade_cadastro import quality
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'selecao_cadastro_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    feature_source=ROOT/'outputs/classificador_cadastro_2026-10-20/features.npz';checkpoint=ROOT/'outputs/convnext_contraste_2026-10-20/melhor_modelo.pt';audit_source=ROOT/'data/cache_encoder_polar_2026-10-20/val_auditoria.json'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed UBIPr, single query; development validation only',
        'features':'Frozen oldRGB/polar/ResNet50 features from existing concatenated cache, split and L2 per component; ConvNeXt independently re-extracted with same preprocessing; previous spatial scores unchanged',
        'quality':'Enrollment only: variance of grayscale Laplacian divided by grayscale variance+1, excluding black exterior, saturated>=245 and dark<5, eroded3x3; multiply native-width/(native-width+128). Own heuristic, not ISO iris quality.',
        'selection':'Per eye choose3 highest-score valid S1 photos, deterministic filename tie; use fewer if fewer valid, retain eye. No query image used to select references or tune quality parameters.',
        'variants':'Own-extraction all-enrollment top3 fusion control; quality-selected3 mean fusion; both with/without predefined per-query normalization. Equal5 components; no weights/quality parameter search.',
        'calibration':'Only15same-side impostors per query, empirical validation FMR<=1%; all482 queries retained, no quality filtering of queries',
        'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [feature_source,checkpoint,audit_source]},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['qualidade_cadastro.py','reconhecedor_convnext.py','normalizar_consulta.py','validar_metrica_intra_classe.py','comparador_hdbif_lote.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2]
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids]
    cache=ROOT/'data/cache_identidade_automatica_2026-10-20';images=np.load(cache/'val_crops.npy',mmap_mode='r');audit=json.loads(audit_source.read_text())
    assert all(r['image']==Path(row.image).name for r,row in zip(audit,rows))
    with np.load(feature_source) as z:concatenated=z['features'];valid=z['valid']
    parts=[]
    for j in range(3):
        part=concatenated[:,256*j:256*(j+1)];part=part/np.maximum(np.linalg.norm(part,axis=1,keepdims=True),1e-12);parts.append(part)
    torch.set_num_threads(4);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model,_=load(checkpoint,device)
    corrected=np.stack([contrast(im) for im in images]);parts.append(extract(model,corrected,device));del model,corrected
    qualities=[]
    for i in gi:
        geometry=audit[i]['geometry'];width=geometry['native_iris_width'] if geometry else 128
        qualities.append(quality(images[i],width) if valid[i] else {'score':-1.,'invalid':True})
    selected=[];selection_audit=[]
    for eye,positions in zip(ids,groups):
        choices=sorted([j for j in positions if valid[gi[j]]],key=lambda j:(-qualities[j]['score'],Path(rows[gi[j]].image).name))[:3]
        selected.append(choices);selection_audit.append({'eye':eye,'selected':[{'image':Path(rows[gi[j]].image).name,**qualities[j]} for j in choices],'available_valid':sum(bool(valid[gi[j]]) for j in positions)})
    (out/'cadastros_escolhidos.json').write_text(json.dumps(selection_audit,indent=2),encoding='utf-8')
    scores_by_mode={'all_top3':[],'quality3':[]}
    for j,features in enumerate(parts):
        raw=features[qi]@features[gi].T;raw[:,~valid[gi]]=-2
        for mode in scores_by_mode:
            scores=aggregate(raw,groups if mode=='all_top3' else selected,'top3')
            sided,labels,_=subset(scores,rows,ids);scores_by_mode[mode].append(dict(scores=sided,labels=labels,valid=valid[qi]))
        np.savez_compressed(out/f'scores_capturas_{j}.npz',scores=raw)
    with np.load(ROOT/'outputs/espacial_polar_val_2026-10-20/scores_shift0.npz') as z:spatial,labels,_=subset(z['scores'],rows,ids);spatial_data=dict(scores=spatial,labels=labels,valid=z['valid'])
    results=[]
    for mode,components in scores_by_mode.items():
        components.append(spatial_data);available=np.logical_and.reduce([c['scores']>-2 for c in components]);qvalid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
        imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
        for c in components:
            np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
            if sd<=0:raise ValueError('Constant impostors')
            standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
        scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
        data=dict(scores=scores,labels=labels,valid=qvalid);result=measure(data);result.update(variant=mode,normalization=parameters);results.append(result);np.savez_compressed(out/f'scores_{mode}.npz',**data)
        normalized,nvalid=normalize(scores,qvalid);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']=mode+'_query_normalized';results.append(result);np.savez_compressed(out/f'scores_{mode}_norm.npz',**ndata)
        np.testing.assert_array_equal(data['correct'],ndata['correct'])
    final={'status':'enrollment_quality_selection_completed','results':results,'queries_filtered_by_quality':0,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
