"""Controle exploratorio ArcIris: geometria propria, nao pipeline IREX integral."""
from pathlib import Path
import argparse, hashlib, importlib.util, json
from datetime import datetime, timezone
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity
    from comparador_hdbif_lote import aggregate
    from validar_lateralidade_informada import subset
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--transformer-dir',type=Path,required=True);p.add_argument('--red',action='store_true');a=p.parse_args()
    out=a.output_root/('arciris_red_2026-10-21' if a.red else 'arciris_polar_2026-10-21');out.mkdir(parents=True,exist_ok=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous run')
    base=ROOT/'data/modelos/cvrl_arciris';source=base/'modules/network.py';weights=base/'models/ResNet100_154000.pt'
    if not weights.exists():
        matches=list(base.rglob('ResNet100_154000.pt'));assert len(matches)==1;weights=matches[0]
    digest=hashlib.sha256(weights.read_bytes()).hexdigest();assert digest=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory UBIPr validation, supplied side, one query photo, all482 queries',
      'method':'Pinned ArcIris iresnet100, FP32, author range[-1,1],512D unit vectors, angular similarity1-acos(cosine)/pi, top3 S1 mean. Existing automatic grayscale CLAHE polar64x512 with invalid support127; own geometry/preprocessing, NOT full original IREX pipeline.',
      'variants':'Standalone, and fixed equal1/8 fusion with previous7 components, with/without predefined per-query normalization. No weight search.',
      'limitations':'External pretraining population undocumented; overlap cannot be excluded; repeatedly reused development validation; no independent confirmation or minimum area claim',
      'calibration':'Validation same-side15 impostors/query, empirical FMR<=1%; failed queries retained',
      'weights_sha256':digest,'network_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if a.red:
        protocol['input_variant']='Raw red channel, same automatic ellipse geometry and mask support, no CLAHE; author input channel/range but own geometry, NOT full original pipeline'
        protocol['red_preprocessor_sha256']=hashlib.sha256((ROOT/'preparar_polar_vermelho.py').read_bytes()).hexdigest()
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    spec=importlib.util.spec_from_file_location('arciris_pinned_network',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    torch.set_num_threads(4);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=module.iresnet100();model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True));model.to(device).eval()
    cache=ROOT/'data/cache_encoder_polar_2026-10-20';images=np.load(cache/'val_polar.npy',mmap_mode='r');valid=np.load(cache/'val_valid.npy');vectors=[]
    if a.red:
        from preparar_polar_vermelho import prepare
        rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
        images,red_valid=prepare(rows,device,a.output_root.parent/'cache_arciris_red');np.testing.assert_array_equal(red_valid,valid)
    for start in range(0,len(images),8):
        x=torch.from_numpy(np.asarray(images[start:start+8]).transpose(0,3,1,2).copy()).to(device).float()/127.5-1
        with torch.inference_mode():f=model(x)
        vectors.append(f.cpu().numpy())
    features=np.concatenate(vectors).astype(np.float64);features/=np.maximum(np.linalg.norm(features,axis=1,keepdims=True),1e-12)
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2]
    raw=1-np.arccos(np.clip(features[qi]@features[gi].T,-1,1))/np.pi;raw[:,~valid[gi]]=-2
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids];full=aggregate(raw,groups,'top3');qvalid=valid[qi]&(full>-2).any(1)
    np.savez_compressed(out/'scores_full32.npz',scores=full,valid=qvalid,labels=np.array([ids.index(identity(rows[i])) for i in qi]))
    scores,labels,_=subset(full,rows,ids);component=dict(scores=scores,labels=labels,valid=qvalid);r=measure(component);r['variant']='arciris_own_red_geometry' if a.red else 'arciris_own_clahe_geometry';results=[r];np.savez_compressed(out/'scores_arciris.npz',**component)
    paths=[ROOT/'outputs'/s for s in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz','resnet50_sessoes_2026-10-20/scores_melhor.npz','convnext_contraste_2026-10-20/scores_melhor.npz','resnet50_nativo224_2026-10-21/scores_melhor.npz']]+[a.transformer_dir/'scores_melhor.npz']
    components=[]
    for file in paths:
        with np.load(file) as z:
            s,l,_=subset(z['scores'],rows,ids);np.testing.assert_array_equal(l,labels);components.append(dict(scores=s,valid=z['valid']))
    components.append(component);available=np.logical_and.reduce([c['scores']>-2 for c in components]);v=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;zs=[];parameters=[]
    for c in components:
        usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std());assert sd>0;zs.append((c['scores']-mu)/sd);parameters.append(dict(mean=mu,std=sd))
    fused=1/(1+np.exp(-np.clip(np.mean(zs,axis=0),-30,30)));fused[~available]=-2
    for name,s,ok in [('fusion8',fused,v),('fusion8_normalized',*normalize(fused,v))]:
        data=dict(scores=s,labels=labels,valid=ok);r=measure(data);r['variant']=name;results.append(r);np.savez_compressed(out/f'scores_{name}.npz',**data)
    final=dict(status='exploratory_external_arciris_completed',results=results,normalization=parameters,test_inference=False,minimum_area=None,external_pretraining_overlap_unknown=True,development_90_reached=any(r['rank1']>=.9 and r['tar']>=.9 for r in results))
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
