"""Condicao autorizada: lado informado na captura, candidatos do mesmo lado."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def subset(scores,rows,ids):
    from avaliar_robustez_reconhecimento import identity
    subjects=sorted({r.subject for r in rows});queries=[r for r in rows if r.session==2]
    columns=np.array([[ids.index(f'{subject}_{r.side}') for subject in subjects] for r in queries])
    labels=np.array([subjects.index(r.subject) for r in queries])
    # Every retained genuine score must refer to the same physical eye as before.
    for i,r in enumerate(queries):assert ids[columns[i,labels[i]]]==identity(r)
    return np.take_along_axis(scores,columns,axis=1),labels,columns

def main():
    from avaliar_robustez_reconhecimento import load_splits
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    from avaliar_robustez_reconhecimento import identity
    ids=sorted({identity(r) for r in rows})
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'authorization':'User explicitly permits requiring left/right side at capture; UBIPr primary and one query photo unchanged',
        'scope':'Development validation, side-informed capture condition; separate from previous32-eye gallery protocol',
        'method':'Keep source fixed fusion scores, restrict each query to enrolled eyes of informed side; genuine physical eye unchanged. Candidates16 per query; all482 queries retained.',
        'variants':'Side-conditioned fixed fusion; same with predefined per-query score normalization over16 candidates',
        'calibration':'Recalibrate each threshold using only same-side impostor comparisons:15 per query, NOT31 with masked comparisons counted as rejections. Empirical validation FMR<=1%.',
        'limitations':'Side must be supplied correctly; no automatic side prediction assumed. Repeated development validation, not independent confirmation or anatomical minimum.',
        'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['normalizar_consulta.py','validar_metrica_intra_classe.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    with np.load(args.source) as z:original={k:z[k] for k in z.files}
    scores,labels,columns=subset(original['scores'],rows,ids);valid=original['valid']&(scores>-2).any(1)
    assert scores.shape==(482,16)
    data=dict(scores=scores,labels=labels,valid=valid);results=[];result=measure(data);result['variant']='side_informed_fixed_fusion';results.append(result);np.savez_compressed(out/'scores_fusao.npz',**data,source_columns=columns)
    normalized,nvalid=normalize(scores,valid);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='side_informed_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata,source_columns=columns)
    np.testing.assert_array_equal(ndata['correct'],data['correct'])
    final={'status':'side_informed_validation_completed','results':results,'query_count':482,'candidate_eyes_per_query':16,'impostor_comparisons_per_query':15,'test_inference':False,'minimum_area':None,
        'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
