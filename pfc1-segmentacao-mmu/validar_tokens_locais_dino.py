"""Controle DINOv3 intermediario local, distinto do antigo CLS global."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parent

def main():
    from huggingface_hub import hf_hub_download
    from transformers import AutoModel
    from avaliar_robustez_reconhecimento import load_splits,identity,MODEL_REVISION
    from avaliar_dinov3_ubipr import MODEL_ID
    from validar_correspondencia_espacial import spatial_scores
    from comparador_hdbif_lote import aggregate
    from validar_metrica_intra_classe import measure
    from validar_lateralidade_informada import subset
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'dino_local6_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    folder=Path(hf_hub_download(MODEL_ID,'config.json',revision=MODEL_REVISION,local_files_only=True)).parent
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Authorized side-informed UBIPr, one query; exploratory validation only',
        'model':MODEL_ID,'revision':MODEL_REVISION,
        'representation':'Custom frozen FIRST6 of24 ViT-L layers, final LayerNorm replaced Identity; not official final DINOv3 output. Exclude CLS and4registers. Input native polar cache64x512, ImageNet normalization without square resize. Subtract constant127 response; L2 channels per patch.',
        'matching':'All valid enrollment captures, mean aligned local cosine best angular shifts -2..2 patch columns, top3 mean per eye',
        'variants':'Local patches alone with side restriction; equal5 fusion oldRGB/polar/newDINOlocal/ResNet50/ConvNeXt with/without predefined query normalization',
        'calibration':'Only15 same-side impostors/query; component z-score on those validation impostors, equal weights; per-variant FMR<=1%; no weight/layer search',
        'failures':'All482 queries retained; no valid gallery floor-2',
        'limitations':'Intermediate layer and polar preprocessing are own hypothesis; large web pretraining population not individually audited; repeated development not independent confirmation',
        'model_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['validar_correspondencia_espacial.py','normalizar_consulta.py','validar_lateralidade_informada.py','comparador_hdbif_lote.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model=AutoModel.from_pretrained(folder,dtype=torch.bfloat16 if device.type=='cuda' else torch.float32,local_files_only=True)
    assert len(model.model.layer)==24 and model.config.num_register_tokens==4
    model.model.layer=nn.ModuleList(list(model.model.layer)[:6]);model.norm=nn.Identity();model.to(device).eval()
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows})
    cache=ROOT/'data/cache_encoder_polar_2026-10-20';images=np.load(cache/'val_polar.npy',mmap_mode='r');valid=np.load(cache/'val_valid.npy')
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    def patches(x):
        result=model(pixel_values=(x-mean)/std).last_hidden_state[:,5:]
        assert result.shape[1:]==(128,1024)
        return result.transpose(1,2).reshape(-1,1024,4,32).float()
    with torch.inference_mode():background=patches(torch.full((1,3,64,512),127/255,device=device))
    features=[]
    for start in range(0,len(images),4):
        x=torch.from_numpy(np.asarray(images[start:start+4]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode():f=nn.functional.normalize(patches(x)-background,dim=1)
        features.append(f.cpu())
        if start%128==0:print(f'DINO6 patches {min(start+4,len(images))}/{len(images)}',flush=True)
    features=torch.cat(features);del model,background
    if device.type=='cuda':torch.cuda.empty_cache()
    gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2]
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids];gallery=features[gi].to(device);raw=[]
    for start in range(0,len(qi),8):
        with torch.inference_mode():value=spatial_scores(features[qi[start:start+8]].to(device),gallery,2)
        raw.append(value.cpu().numpy())
    raw=np.concatenate(raw).astype(np.float64);raw[:,~valid[gi]]=-2;full_scores=aggregate(raw,groups,'top3');full_valid=valid[qi]&(full_scores>-2).any(1)
    labels_full=np.array([ids.index(identity(rows[i])) for i in qi]);np.savez_compressed(out/'scores_full32.npz',scores=full_scores,labels=labels_full,valid=full_valid)
    scores,labels,_=subset(full_scores,rows,ids);data=dict(scores=scores,labels=labels,valid=full_valid);result=measure(data);result['variant']='DINO6_local_side';results=[result];np.savez_compressed(out/'scores_local.npz',**data)
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','resnet50_sessoes_2026-10-20/scores_melhor.npz','convnext_contraste_2026-10-20/scores_melhor.npz']]
    components=[]
    for p in paths:
        with np.load(p) as z:scores,labels,_=subset(z['scores'],rows,ids);components.append(dict(scores=scores,labels=labels,valid=z['valid']))
    components.append(data);available=np.logical_and.reduce([c['scores']>-2 for c in components]);qvalid=np.logical_and.reduce([c['valid'] for c in components]);imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=qvalid&available.any(1));result=measure(data);result.update(variant='DINO6_equal_fusion',normalization=parameters);results.append(result);np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,data['valid']);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='DINO6_fusion_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    final={'status':'DINO6_custom_local_validation_completed','results':results,'test_inference':False,'minimum_area':None,'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()
