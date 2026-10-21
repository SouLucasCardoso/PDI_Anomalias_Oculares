"""Reduz variacao intraolho por metrica linear treinada; validacao somente."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch

ROOT=Path(__file__).resolve().parent

def extract(model,images,device):
    features=[];mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None]
    std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    model.eval()
    for start in range(0,len(images),64):
        x=torch.from_numpy(np.asarray(images[start:start+64]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):
            f=model((x-mean)/std)
        features.append(torch.nn.functional.normalize(f.float(),dim=1).cpu().numpy())
    return np.concatenate(features)

def score(features,valid,rows):
    from avaliar_robustez_reconhecimento import identity
    from comparador_hdbif_lote import aggregate
    ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name))
    qi=[i for i,r in enumerate(rows) if r.session==2];labels=np.array([ids.index(identity(rows[i])) for i in qi])
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids]
    raw=features[qi]@features[gi].T;raw[:,~valid[gi]]=-2
    scores=aggregate(raw,groups,'top3');qvalid=valid[qi]&(scores>-2).any(1)
    return dict(scores=scores,labels=labels,valid=qvalid)

def measure(data):
    from avaliar_robustez_reconhecimento import metrics,operating_threshold
    scores=data['scores'];labels=data['labels'];valid=data['valid'];imp=np.ones_like(scores,dtype=bool)
    imp[np.arange(len(labels)),labels]=False;usable=imp&valid[:,None]&(scores>-2)
    threshold=operating_threshold(scores[usable]);result,correct,accepted=metrics(scores,labels,threshold,valid)
    result['threshold']=threshold;data.update(correct=correct,accepted=accepted)
    return result

def main():
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import Sample
    from avaliar_robustez_reconhecimento import identity,load_splits
    from metrica_intra_classe import fit,transform
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'metrica_intra_val_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_path.read_text())
    train=[Sample(**r) for r in manifest['train']];val=load_splits(manifest)['val']
    assert not {r.subject for r in train}&{r.subject for r in val}
    checkpoints=[ROOT/'outputs'/p/'melhor_modelo.pt' for p in ['identidade_automatica_2026-10-20','encoder_polar_2026-10-20']]
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'UBIPr development validation only, one query image; no test or occlusion scores',
        'method':'Fixed frozen embeddings; training-only global mean and within-eye covariance, shrinkage0.1 towards trace/dimension identity; inverse-square-root transform then L2',
        'variants':'RGB top3, polar top3, equal thirds fusion of transformed RGB/polar and previous spatial scores',
        'calibration':'Validation impostor z-score for fixed fusion; threshold validation empirical FMR<=1%; repeated validation not independent',
        'failure_handling':'Exclude empty training extractions only, retain all482 validation queries',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['metrica_intra_classe.py','comparador_hdbif_lote.py','treinar_identidade_iris.py']},
        'inputs_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checkpoints+[manifest_path]}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    results=[];components=[]
    for name,checkpoint in zip(['rgb','polar'],checkpoints):
        cache=ROOT/'data'/('cache_identidade_automatica_2026-10-20' if name=='rgb' else 'cache_encoder_polar_2026-10-20')
        suffix='crops' if name=='rgb' else 'polar'
        tx=np.load(cache/f'train_{suffix}.npy',mmap_mode='r');tv=np.load(cache/'train_valid.npy')
        vx=np.load(cache/f'val_{suffix}.npy',mmap_mode='r');vv=np.load(cache/'val_valid.npy')
        assert len(tx)==len(train) and len(vx)==len(val)
        model=IdentityEncoder().to(device);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
        tf=extract(model,tx,device);vf=extract(model,vx,device);del model
        mean,matrix=fit(tf[tv],np.array([identity(r) for r in train])[tv],.1)
        np.savez_compressed(out/f'metrica_{name}.npz',mean=mean,matrix=matrix)
        data=score(transform(vf,mean,matrix),vv,val);measured=measure(data);measured['variant']=name;results.append(measured);components.append(data)
        np.savez_compressed(out/f'scores_{name}.npz',**data);print(json.dumps(measured),flush=True)
    with np.load(ROOT/'outputs/espacial_polar_val_2026-10-20/scores_shift0.npz') as z:components.append({k:z[k] for k in z.files})
    labels=components[0]['labels'];available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels)
        usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        parameters.append({'mean':mu,'std':sd});standardized.append((c['scores']-mu)/sd)
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=valid&available.any(1));measured=measure(data);measured.update(variant='fixed_three_way',normalization=parameters);results.append(measured)
    np.savez_compressed(out/'scores_fusao.npz',**data)
    final={'status':'training_only_linear_metric_validation_completed','results':results,'test_inference':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
