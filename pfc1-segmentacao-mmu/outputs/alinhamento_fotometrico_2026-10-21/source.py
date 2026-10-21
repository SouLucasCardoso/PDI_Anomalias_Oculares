"""Busca gamma fixa em uma foto, sem selecionar vistas pelo rotulo da consulta."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch
from torchvision.transforms import functional as F
ROOT=Path(__file__).resolve().parent

def aggregate_views(raw_views,groups):
    from comparador_hdbif_lote import aggregate
    return np.max([aggregate(raw,groups,'top3') for raw in raw_views],axis=0)

def encode(model,images,positions,device,gamma):
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None];vectors=[]
    for start in range(0,len(positions),16):
        selected=positions[start:start+16];x=torch.from_numpy(np.stack([images[i] for i in selected]).transpose(0,3,1,2).copy()).to(device).float()/255
        x=F.adjust_gamma(x,gamma)
        with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):f=model((x-mean)/std)
        vectors.append(torch.nn.functional.normalize(f.float(),dim=1).cpu().numpy())
    return np.concatenate(vectors)

def main():
    from treinar_identidade_iris import IdentityEncoder
    from reconhecedor_resnet50 import load as load_resnet
    from reconhecedor_convnext import load as load_convnext,contrast
    from avaliar_robustez_reconhecimento import load_splits,identity
    from comparador_hdbif_lote import aggregate
    from validar_lateralidade_informada import subset
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--transformer-dir',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'alinhamento_fotometrico_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    names=['identidade_automatica_2026-10-20','resnet50_sessoes_2026-10-20','convnext_contraste_2026-10-20','resnet50_nativo224_2026-10-21'];checkpoints=[ROOT/'outputs'/name/'melhor_modelo.pt' for name in names]
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed UBIPr, one original query photo, exploratory validation only',
        'method':'Freeze four RGB encoders. Original gallery preprocessing, no gallery gamma augmentation. Each individual query receives fixed gamma0.75,1,1.33 AFTER its fixed base preprocessing, BEFORE ImageNet normalization. Per candidate eye: top3 gallery similarity per gamma, then max across3query views, no query label used to select view.',
        'variants':'Own-extraction gamma1 control versus gamma-max, each fused with unchanged polar/spatial/Transformer, equal1/7, with/without predefined query normalization. No gamma/weight search.',
        'calibration':'All15same-side impostors receive same gamma maximization; threshold recalibrated empirical validation FMR<=1%; all482 queries and failures retained',
        'limitations':'Computational photometric alignment, not multiple query photos or generative restoration; repeated validation not independent confirmation',
        'checkpoint_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checkpoints},'transformer_scores_sha256':hashlib.sha256((args.transformer_dir/'scores_melhor.npz').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['reconhecedor_resnet50.py','reconhecedor_convnext.py','comparador_hdbif_lote.py','normalizar_consulta.py','validar_lateralidade_informada.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2];groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids]
    base=ROOT/'data/cache_identidade_automatica_2026-10-20';images128=np.load(base/'val_crops.npy',mmap_mode='r');valid=np.load(base/'val_valid.npy')
    native=args.output_root/'cache_resnet50_nativo224';images224=np.load(native/'val_crops.npy',mmap_mode='r');np.testing.assert_array_equal(valid,np.load(native/'val_valid.npy'))
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');modes={'gamma1_control':[],'gamma_max':[]}
    for j,checkpoint in enumerate(checkpoints):
        if j==0:
            model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model']);images=images128
        elif j==2:model,_=load_convnext(checkpoint,device);images=np.stack([contrast(im) for im in images128])
        else:model,_=load_resnet(checkpoint,device);images=images224 if j==3 else images128
        gallery=encode(model,images,gi,device,1.);views=[];control=None
        for gamma in [.75,1.,1.33]:
            q=encode(model,images,qi,device,gamma);raw=(q@gallery.T).astype(np.float64);raw[:,~valid[gi]]=-2;views.append(raw)
            if gamma==1:control=aggregate(raw,groups,'top3')
        aligned=aggregate_views(views,groups);assert np.all(aligned>=control-1e-12)
        for mode,scores in [('gamma1_control',control),('gamma_max',aligned)]:
            sided,labels,_=subset(scores,rows,ids);modes[mode].append(dict(scores=sided,labels=labels,valid=valid[qi]));np.savez_compressed(out/f'raw_{j}_{mode}.npz',scores=scores,valid=valid[qi])
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
        print(f'Photometric alignment encoder{j+1}/4 completed',flush=True)
    fixed_paths=[ROOT/'outputs/encoder_polar_2026-10-20/scores_melhor.npz',ROOT/'outputs/espacial_polar_val_2026-10-20/scores_shift0.npz',args.transformer_dir/'scores_melhor.npz'];fixed=[]
    for p in fixed_paths:
        with np.load(p) as z:scores,labels,_=subset(z['scores'],rows,ids);fixed.append(dict(scores=scores,labels=labels,valid=z['valid']))
    results=[]
    for mode,current in modes.items():
        components=current+fixed;available=np.logical_and.reduce([c['scores']>-2 for c in components]);qvalid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
        imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
        for c in components:
            np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
            if sd<=0:raise ValueError('Constant impostors')
            standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
        scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
        data=dict(scores=scores,labels=labels,valid=qvalid);result=measure(data);result.update(variant=mode+'_fusion',normalization=parameters);results.append(result);np.savez_compressed(out/f'scores_{mode}.npz',**data)
        normalized,nvalid=normalize(scores,qvalid);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']=mode+'_fusion_normalized';results.append(result);np.savez_compressed(out/f'scores_{mode}_norm.npz',**ndata)
        np.testing.assert_array_equal(data['correct'],ndata['correct'])
    final={'status':'single_photo_gamma_alignment_completed','results':results,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
