"""Correspondencia local em camada2 e todas as capturas de cadastro."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch
from torch import nn

ROOT=Path(__file__).resolve().parent

def main():
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_correspondencia_espacial import spatial_scores
    from comparador_hdbif_lote import aggregate
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'espacial_capturas_val_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    checkpoint=ROOT/'outputs/encoder_polar_2026-10-20/melhor_modelo.pt'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'UBIPr, single query image, validation development only; no test or occlusion inference',
        'representation':'Frozen previous polar ResNet18 through layer2,128x8x64; subtract constant127 response; L2 channels per location',
        'matching':'Every valid session1 capture, mean local cosine best angular shifts -2..2, top3 mean per eye; no radial shifts, no query fusion',
        'variants':'Spatial top3; equal thirds previous RGB/previous polar/new spatial; same fusion with predefined per-query normalization',
        'failure_handling':'All482 queries retained, all32 eyes retained, missing galleries floor-2',
        'calibration':'Each threshold empirical validation FMR<=1%; fixed fusion weights, validation impostor z-score; repeated development not independent',
        'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['validar_correspondencia_espacial.py','comparador_hdbif_lote.py','normalizar_consulta.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    cache=ROOT/'data/cache_encoder_polar_2026-10-20';images=np.load(cache/'val_polar.npy',mmap_mode='r');valid=np.load(cache/'val_valid.npy')
    encoder=IdentityEncoder();encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model']);extractor=nn.Sequential(*list(encoder.backbone.children())[:6]).to(device).eval();del encoder
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    with torch.inference_mode():background=extractor((torch.full((1,3,64,512),127/255,device=device)-mean)/std)
    features=[]
    for start in range(0,len(images),32):
        x=torch.from_numpy(np.asarray(images[start:start+32]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode():f=nn.functional.normalize(extractor((x-mean)/std)-background,dim=1)
        features.append(f.cpu())
    features=torch.cat(features);del extractor
    ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2]
    labels=np.array([ids.index(identity(rows[i])) for i in qi]);groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids]
    gallery=features[gi].to(device);raw=[]
    for start in range(0,len(qi),16):
        with torch.inference_mode():scores=spatial_scores(features[qi[start:start+16]].to(device),gallery,2)
        raw.append(scores.cpu().numpy())
    raw=np.concatenate(raw).astype(np.float64);raw[:,~valid[gi]]=-2;scores=aggregate(raw,groups,'top3')
    data=dict(scores=scores,labels=labels,valid=valid[qi]&(scores>-2).any(1));results=[];result=measure(data);result['variant']='layer2_spatial_top3';results.append(result)
    np.savez_compressed(out/'scores_espacial.npz',**data);print(json.dumps(result),flush=True)
    components=[]
    for p in [ROOT/'outputs/identidade_automatica_2026-10-20/scores_baseline.npz',ROOT/'outputs/encoder_polar_2026-10-20/scores_melhor.npz']:
        with np.load(p) as z:components.append({k:z[k] for k in z.files})
    components.append(data);available=np.logical_and.reduce([c['scores']>-2 for c in components]);qvalid=np.logical_and.reduce([c['valid'] for c in components])
    imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels)
        usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        parameters.append({'mean':mu,'std':sd});standardized.append((c['scores']-mu)/sd)
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=qvalid&available.any(1));result=measure(data);result.update(variant='fixed_three_way',normalization=parameters);results.append(result);np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,data['valid']);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='fixed_three_way_query_normalized';results.append(result)
    np.testing.assert_array_equal(ndata['correct'],data['correct']);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    final={'status':'spatial_layer2_all_enrollment_completed','results':results,'test_inference':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
