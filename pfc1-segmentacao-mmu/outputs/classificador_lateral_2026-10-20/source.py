"""Classificadores por lado ajustados somente nas fotos de cadastro."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def rbf(a,b,gamma):
    distance=np.maximum((a*a).sum(1)[:,None]+(b*b).sum(1)[None,:]-2*a@b.T,0)
    return np.exp(-gamma*distance)

def main():
    from avaliar_robustez_reconhecimento import load_splits
    from classificador_cadastro import fit,predict
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    source=ROOT/'outputs/classificador_cadastro_2026-10-20/features.npz'
    out=args.output_root/'classificador_lateral_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed single query, UBIPr development validation only',
        'features':'Previous frozen RGB256/polar256/ResNet50RGB256 concatenation, same as previous enrollment classifier',
        'fitting':'Separate L/R enrollment-only classifiers, same16 subject candidates per query; query images/labels excluded from fitting',
        'variants':'Linear ridge alpha1 fixed; RBF kernel ridge alpha0.01 fixed, gamma reciprocal median admissible enrollment different-eye squared distance; both with/without predefined query normalization',
        'calibration':'Threshold validation empirical FMR<=1% using15 same-side impostors per query; no hyperparameter search or query filtering',
        'limitations':'Repeated development; side supplied correctly; enrollment-trained classifier, not an independently frozen metric',
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['classificador_cadastro.py','normalizar_consulta.py','validar_metrica_intra_classe.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    with np.load(source) as z:features=z['features'];valid=z['valid']
    subjects=sorted({r.subject for r in rows});all_labels=np.array([subjects.index(r.subject) for r in rows]);qi=np.array([i for i,r in enumerate(rows) if r.session==2]);labels=all_labels[qi]
    raw_linear=np.full((len(qi),len(subjects)),-2.);raw_kernel=raw_linear.copy();audits=[]
    for side in ('L','R'):
        gi=np.array([i for i,r in enumerate(rows) if r.session==1 and r.side==side and valid[i]])
        qpositions=np.array([j for j,i in enumerate(qi) if rows[i].side==side]);x=features[gi];y=all_labels[gi]
        assert len(np.unique(y))==len(subjects),'Retain all enrolled identities'
        state=fit(x,y,len(subjects),1.);raw_linear[qpositions]=predict(features[qi[qpositions]],state)
        distance=np.maximum((x*x).sum(1)[:,None]+(x*x).sum(1)[None,:]-2*x@x.T,0)
        impostor=y[:,None]!=y[None,:];gamma=1/float(np.median(distance[impostor]));prior=np.eye(len(subjects))[y].mean(0)
        coefficient=np.linalg.solve(rbf(x,x,gamma)+.01*np.eye(len(x)),np.eye(len(subjects))[y]-prior)
        raw_kernel[qpositions]=rbf(features[qi[qpositions]],x,gamma)@coefficient+prior
        np.savez_compressed(out/f'kernel_{side}.npz',gallery=x,coefficient=coefficient,gamma=gamma,prior=prior)
        np.savez_compressed(out/f'linear_{side}.npz',**state)
        audits.append({'side':side,'gallery_count':len(gi),'queries':len(qpositions),'gamma':gamma,'queries_used_for_fitting':0})
    results=[]
    for name,raw in [('linear_alpha1',raw_linear),('rbf_alpha001',raw_kernel)]:
        scores=1/(1+np.exp(-np.clip(raw,-30,30)));data=dict(scores=scores,labels=labels,valid=valid[qi]);result=measure(data);result['variant']=name;results.append(result);np.savez_compressed(out/f'scores_{name}.npz',**data)
        normalized,nvalid=normalize(scores,valid[qi]);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']=name+'_query_normalized';results.append(result);np.savez_compressed(out/f'scores_{name}_norm.npz',**ndata)
        np.testing.assert_array_equal(ndata['correct'],data['correct'])
    final={'status':'side_enrollment_classifiers_completed','results':results,'audit':audits,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
