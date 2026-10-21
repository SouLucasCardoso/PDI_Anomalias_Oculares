"""Representacoes congeladas; classificador supervisionado so no cadastro S1."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from treinar_identidade_iris import IdentityEncoder
    from reconhecedor_resnet50 import load
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_metrica_intra_classe import extract,measure
    from classificador_cadastro import fit,predict
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--trained-dir',type=Path,required=True);args=parser.parse_args()
    trained=args.trained_dir.resolve();assert (trained/'CONCLUIDO.json').exists()
    out=trained.parent/'classificador_cadastro_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    checkpoints=[ROOT/'outputs'/p/'melhor_modelo.pt' for p in ['identidade_automatica_2026-10-20','encoder_polar_2026-10-20']]+[trained/'melhor_modelo.pt']
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'UBIPr, one photo per query, learned enrollment classifier; repeated validation only',
        'features':'Frozen old RGB256 + old polar256 + new ResNet50RGB256, concatenated and L2; no query label used to learn features or classifier',
        'fitting':'Valid session1 enrollment captures only; centered features/one-hot targets, ridge alpha1 fixed, dual solution; session2 queries never fit the classifier',
        'variants':'Concatenated normalized class centroid cosine control; ridge classifier; ridge with predefined per-query normalization',
        'calibration':'Per-variant validation empirical FMR<=1%; validation repeatedly used, no independent confirmation',
        'failure_handling':'Require all image components valid, retain all482 queries and32eyes; no valid eye enrollment floor-2',
        'checkpoint_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checkpoints},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['classificador_cadastro.py','reconhecedor_resnet50.py','normalizar_consulta.py','validar_metrica_intra_classe.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    ids=sorted({identity(r) for r in rows});all_labels=np.array([ids.index(identity(r)) for r in rows]);qi=np.array([i for i,r in enumerate(rows) if r.session==2])
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');parts=[];valid_parts=[]
    for j,checkpoint in enumerate(checkpoints):
        cache=ROOT/'data'/('cache_encoder_polar_2026-10-20' if j==1 else 'cache_identidade_automatica_2026-10-20')
        images=np.load(cache/('val_polar.npy' if j==1 else 'val_crops.npy'),mmap_mode='r');valid_parts.append(np.load(cache/'val_valid.npy'))
        if j==2:model,_=load(checkpoint,device)
        else:
            model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
        parts.append(extract(model,images,device));del model
    features=np.concatenate(parts,axis=1).astype(np.float64);features/=np.maximum(np.linalg.norm(features,axis=1,keepdims=True),1e-12)
    valid=np.logical_and.reduce(valid_parts);gi=np.array([i for i,r in enumerate(rows) if r.session==1 and valid[i]])
    failed=[j for j in range(len(ids)) if not (all_labels[gi]==j).any()]
    np.savez_compressed(out/'features.npz',features=features,valid=valid,labels=all_labels,session=np.array([r.session for r in rows]))
    qvalid=valid[qi];labels=all_labels[qi];results=[]
    prototypes=np.stack([features[gi[all_labels[gi]==j]].mean(0) if j not in failed else np.zeros(features.shape[1]) for j in range(len(ids))])
    prototypes/=np.maximum(np.linalg.norm(prototypes,axis=1,keepdims=True),1e-12)
    control=features[qi]@prototypes.T;control[:,failed]=-2
    data=dict(scores=control,labels=labels,valid=qvalid);result=measure(data);result['variant']='concatenated_centroid_control';results.append(result);np.savez_compressed(out/'scores_centroide.npz',**data)
    state=fit(features[gi],all_labels[gi],len(ids),1.);np.savez_compressed(out/'classificador.npz',**state)
    raw=predict(features[qi],state);scores=1/(1+np.exp(-np.clip(raw,-30,30)));scores[:,failed]=-2
    data=dict(scores=scores,labels=labels,valid=qvalid);result=measure(data);result['variant']='enrollment_ridge_alpha1';results.append(result);np.savez_compressed(out/'scores_ridge.npz',**data)
    normalized,nvalid=normalize(scores,qvalid);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='ridge_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    np.testing.assert_array_equal(ndata['correct'],data['correct'])
    final={'status':'enrollment_only_ridge_classifier_completed','results':results,'test_inference':False,'minimum_area':None,'gallery_images_used':len(gi),'query_images_used_for_fitting':0}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
