"""Controle sem gargalo de projecao256, centro estimado so no cadastro."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_metrica_intra_classe import score,measure
    from validar_lateralidade_informada import subset
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--trained-dir',type=Path,required=True);parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--convnext',action='store_true');parser.add_argument('--previous-scores',type=Path);args=parser.parse_args()
    trained=args.trained_dir.resolve();assert (trained/'CONCLUIDO.json').exists();checkpoint=trained/'melhor_modelo.pt'
    name='backbone_convnext_2026-10-21' if args.convnext else 'backbone_resnet50_2026-10-21';out=args.output_root/name;out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz']]
    if args.convnext:
        if not args.previous_scores:raise ValueError('Need previously registered full ResNet50 backbone scores')
        paths.append(args.previous_scores)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed UBIPr, single query; repeated development validation only',
        'representation':'Frozen trained backbone before projection:2048 GeM ResNet50 or768 LayerNorm ConvNeXt. Raw vectors centered by mean valid session1 enrollment only, then L2. No query in center estimation. Same preprocessing as training.',
        'variants':'Backbone top3 conditional on side; equal-weight old RGB/polar/spatial plus ResNet50 backbone, plus ConvNeXt backbone when available; with/without predefined per-query normalization',
        'calibration':'Component normalization only same-side validation impostors,15 per query; FMR<=1% each variant; no weight or center parameter search',
        'failures':'All482 queries retained; every component must be valid',
        'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        'sources_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['reconhecedor_resnet50.py','reconhecedor_convnext.py','normalizar_consulta.py','validar_lateralidade_informada.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows})
    cache=ROOT/'data/cache_identidade_automatica_2026-10-20';images=np.load(cache/'val_crops.npy',mmap_mode='r');valid=np.load(cache/'val_valid.npy')
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if args.convnext:
        from reconhecedor_convnext import load,contrast
    else:
        from reconhecedor_resnet50 import load
    model,_=load(checkpoint,device);mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None];features=[]
    for start in range(0,len(images),64):
        batch=np.stack([contrast(x) for x in images[start:start+64]]) if args.convnext else np.asarray(images[start:start+64])
        x=torch.from_numpy(batch.transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):f=model.backbone((x-mean)/std)
        features.append(f.float().cpu().numpy())
    features=np.concatenate(features).astype(np.float64);gi=np.array([i for i,r in enumerate(rows) if r.session==1 and valid[i]])
    center=features[gi].mean(0);features-=center;norm=np.linalg.norm(features,axis=1,keepdims=True);valid=valid&(norm[:,0]>1e-12);features/=np.maximum(norm,1e-12)
    np.savez_compressed(out/'features.npz',features=features,valid=valid,enrollment_center=center)
    full=score(features,valid,rows);np.savez_compressed(out/'scores_full32.npz',**full)
    scores,labels,_=subset(full['scores'],rows,ids);data=dict(scores=scores,labels=labels,valid=full['valid']);result=measure(data);result['variant']='wide_backbone_top3_side';results=[result];np.savez_compressed(out/'scores_backbone.npz',**data)
    components=[]
    for p in paths:
        with np.load(p) as z:scores,labels,_=subset(z['scores'],rows,ids);components.append(dict(scores=scores,labels=labels,valid=z['valid']))
    components.append(data);available=np.logical_and.reduce([c['scores']>-2 for c in components]);qvalid=np.logical_and.reduce([c['valid'] for c in components]);imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=qvalid&available.any(1));result=measure(data);result.update(variant='wide_backbone_equal_fusion',normalization=parameters);results.append(result);np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,data['valid']);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='wide_fusion_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    np.testing.assert_array_equal(ndata['correct'],data['correct'])
    final={'status':'wide_backbone_side_validation_completed','results':results,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
