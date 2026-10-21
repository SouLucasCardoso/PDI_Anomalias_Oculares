"""Alinhamento angular de uma foto de consulta,templates de cadastro fixos."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent

def extract(model,images,device,shift):
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None];features=[]
    for start in range(0,len(images),64):
        x=torch.from_numpy(np.asarray(images[start:start+64]).transpose(0,3,1,2).copy()).to(device).float()/255
        x=torch.roll(x,shift,dims=-1)
        with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):f=model((x-mean)/std)
        features.append(torch.nn.functional.normalize(f.float(),dim=1).cpu().numpy())
    return np.concatenate(features)

def main():
    from reconhecedor_transformer_polar import load
    from avaliar_robustez_reconhecimento import load_splits,identity
    from comparador_hdbif_lote import aggregate
    from validar_lateralidade_informada import subset
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--trained-dir',type=Path,required=True);args=parser.parse_args()
    trained=args.trained_dir.resolve();assert (trained/'CONCLUIDO.json').exists();checkpoint=trained/'melhor_modelo.pt'
    out=args.output_root/'alinhamento_transformer_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed UBIPr, one original query photo; repeated development validation only',
        'method':'Frozen trained polar Transformer, enrollment original orientation only. Query circular rolls fixed -32,-16,0,+16,+32, same already used augmentation range. For each eye aggregate top3 enrollment similarities per query view, then max across5views, without true identity to select view.',
        'variants':'Own-extraction unshifted control and angular-max Transformer scores; each fused with6previous components equal1/7, with/without predefined query normalization. No angle/weight search.',
        'calibration':'15same-side impostors/query; separate component z-score and threshold empirical validation FMR<=1%; all482 queries retained',
        'limitations':'Several computational views of same image, not multiple query photos; validation repeatedly used, no independent confirmation',
        'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['reconhecedor_transformer_polar.py','normalizar_consulta.py','comparador_hdbif_lote.py','validar_lateralidade_informada.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2]
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids]
    cache=ROOT/'data/cache_encoder_polar_2026-10-20';images=np.load(cache/'val_polar.npy',mmap_mode='r');valid=np.load(cache/'val_valid.npy')
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model,_=load(checkpoint,device)
    gallery=extract(model,images[gi],device,0);view_scores=[];control=None
    for shift in [-32,-16,0,16,32]:
        vectors=extract(model,images[qi],device,shift);raw=(vectors@gallery.T).astype(np.float64);raw[:,~valid[gi]]=-2;scores=aggregate(raw,groups,'top3');view_scores.append(scores)
        if shift==0:control=scores
        print(f'Query angular shift{shift} completed',flush=True)
    aligned=np.max(view_scores,axis=0);qvalid=valid[qi]&(aligned>-2).any(1)
    full_labels=np.array([ids.index(identity(rows[i])) for i in qi]);np.savez_compressed(out/'scores_full32.npz',scores=aligned,labels=full_labels,valid=qvalid)
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz','resnet50_sessoes_2026-10-20/scores_melhor.npz','convnext_contraste_2026-10-20/scores_melhor.npz','resnet50_nativo224_2026-10-21/scores_melhor.npz']]
    fixed=[]
    for p in paths:
        with np.load(p) as z:scores,labels,_=subset(z['scores'],rows,ids);fixed.append(dict(scores=scores,labels=labels,valid=z['valid']))
    results=[]
    for name,current in [('unshifted_control',control),('aligned',aligned)]:
        scores,labels,_=subset(current,rows,ids);component=dict(scores=scores,labels=labels,valid=qvalid);result=measure(component);result['variant']=name+'_transformer';results.append(result);np.savez_compressed(out/f'scores_{name}_transformer.npz',**component)
        components=fixed+[component];available=np.logical_and.reduce([c['scores']>-2 for c in components]);usable_queries=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
        imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
        for c in components:
            np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
            if sd<=0:raise ValueError('Constant impostors')
            standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
        scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
        data=dict(scores=scores,labels=labels,valid=usable_queries);result=measure(data);result.update(variant=name+'_fusion',normalization=parameters);results.append(result);np.savez_compressed(out/f'scores_{name}_fusion.npz',**data)
        normalized,nvalid=normalize(scores,usable_queries);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']=name+'_fusion_normalized';results.append(result);np.savez_compressed(out/f'scores_{name}_norm.npz',**ndata)
        np.testing.assert_array_equal(data['correct'],ndata['correct'])
    final={'status':'single_photo_angular_alignment_completed','results':results,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
