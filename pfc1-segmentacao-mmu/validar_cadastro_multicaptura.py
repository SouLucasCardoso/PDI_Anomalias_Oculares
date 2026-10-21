"""Validacao apenas: cadastro multicaptura e mascara automatica, pesos congelados."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
import numpy as np
from PIL import Image
import torch
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/cadastro_multicaptura_val_v2_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    from avaliar_dinov3_ubipr import masked_crop
    from treinar_segmentacao_ubipr import decode_mask,MulticlassUNet
    from treinar_identidade_iris import IdentityEncoder
    from validar_melhoria_normalizacao import iso_pair
    from matcher_hdbif_fft import prepare
    from comparador_hdbif_lote import gallery_batch,scores_batch,aggregate
    torch.set_num_threads(4)
    manifest=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    rows=load_splits(json.loads(manifest.read_text()))['val']
    ids=sorted({identity(r) for r in rows})
    gallery=sorted([r for r in rows if r.session==1],key=lambda r:(identity(r),Path(r.image).name))
    queries=[r for r in rows if r.session==2]; chosen=gallery+queries; ng=len(gallery)
    groups=[[i for i,r in enumerate(gallery) if identity(r)==eye] for eye in ids]
    labels=np.array([ids.index(identity(r)) for r in queries])
    neural=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20/melhor_modelo.pt'
    unet=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    dependencies=['comparador_hdbif_lote.py','matcher_hdbif_fft.py','validar_melhoria_normalizacao.py','avaliar_robustez_reconhecimento.py','avaliar_dinov3_ubipr.py','treinar_segmentacao_ubipr.py','treinar_identidade_iris.py']
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Development validation only; no new test or occlusion scores',
        'variants':'Neural128 reference/automatic masks x first/max/top3/centroid; HDBIF reference ROI x first/max/top3',
        'selection':'All session1 images in each eye, sorted lexicographically; all session2 queries; no query-based enrollment selection',
        'aggregates':'First includes failed first enrollment; max uses best valid comparison; top3 mean up to3 valid comparisons; neural centroid normalizes mean of valid vectors',
        'mask_automatic':'Frozen retrained U-Net 320x240 RGB/255, nearest resize original, iris class1; reference never replaces predicted mask',
        'calibration':'Separate validation threshold each variant; empirical impostor FMR<=1%; repeated development comparisons, no independent evidence',
        'failures':'Retain all eye identities/queries; no-overlap and empty masks reject; no valid gallery for an eye gets score -2',
        'counts':{'images':len(chosen),'gallery_images':ng,'queries':len(queries),'eyes':len(ids),'people':len({r.subject for r in chosen})},
        'checkpoint_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (neural,unet)},
        'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in dependencies},
        'limitations':'Same validation used for checkpoint selection and development; HDBIF reference assisted; public pretraining overlap unknown; full test still required'}
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'protocolo.json').exists(): raise ValueError('Experiment already registered; preserve it')
    (OUT/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    results=[]; started=time.monotonic()
    def record(name,scores,valid):
        valid=np.asarray(valid,dtype=bool)&(scores>-2).any(1)
        imp=np.ones_like(scores,dtype=bool); imp[np.arange(len(labels)),labels]=False
        usable=imp&valid[:,None]&(scores>-2)
        threshold=operating_threshold(scores[usable]) if usable.any() else 2.
        result,correct,accepted=metrics(scores,labels,threshold,valid)
        result.update(variant=name,threshold=threshold,joint_success=float((correct&accepted).mean()))
        results.append(result)
        np.savez_compressed(OUT/(name+'.npz'),scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
        (OUT/'resultados_parciais.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    encoder=IdentityEncoder().to(device).eval(); encoder.load_state_dict(torch.load(neural,map_location='cpu',weights_only=True)['model'])
    segmenter=MulticlassUNet(8).to(device).eval(); segmenter.load_state_dict(torch.load(unet,map_location='cpu',weights_only=True)['model'])
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None]; std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    for mask_kind in ('reference','automatic'):
        crops=[]; valid=[]
        for row in chosen:
            with Image.open(row.image) as im: image=im.convert('RGB')
            if mask_kind=='reference':
                with Image.open(row.mask) as im: mask=decode_mask(im)==1
            else:
                small=np.asarray(image.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255
                with torch.inference_mode(): mask=segmenter(torch.from_numpy(small.transpose(2,0,1).copy())[None].to(device)).argmax(1)[0].cpu().numpy()==1
                mask=np.asarray(Image.fromarray(mask).resize(image.size,Image.Resampling.NEAREST),dtype=bool)
            valid.append(bool(mask.any())); crops.append(np.asarray(masked_crop(image,mask).resize((128,128),Image.Resampling.BILINEAR)))
        vectors=[]; valid=np.array(valid)
        for start in range(0,len(crops),64):
            tensor=torch.from_numpy(np.stack(crops[start:start+64]).transpose(0,3,1,2).copy()).to(device).float()/255
            with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'): value=encoder((tensor-mean)/std)
            vectors.append(torch.nn.functional.normalize(value.float(),dim=1).cpu().numpy())
        vectors=np.concatenate(vectors)
        if not np.isfinite(vectors).all(): raise ValueError('Nonfinite embeddings')
        raw=(vectors[ng:]@vectors[:ng].T).astype(np.float64); raw[:,~valid[:ng]]=-2
        for mode in ('first','max','top3'): record('neural_'+mask_kind+'_'+mode,aggregate(raw,groups,mode),valid[ng:])
        centroids=np.zeros((len(ids),vectors.shape[1]),np.float32); failed=[]
        for eye,positions in enumerate(groups):
            positions=[p for p in positions if valid[p]]
            if positions:
                center=vectors[positions].mean(0); norm=np.linalg.norm(center)
                if norm>0: centroids[eye]=center/norm
                else: failed.append(eye)
            else: failed.append(eye)
        scores=(vectors[ng:]@centroids.T).astype(np.float64); scores[:,failed]=-2
        record('neural_'+mask_kind+'_centroid',scores,valid[ng:])
        np.savez_compressed(OUT/('features_'+mask_kind+'.npz'),features=vectors,valid=valid)
    del encoder,segmenter,crops,vectors
    if device.type=='cuda': torch.cuda.empty_cache()
    source=ROOT/'data/modelos/cvrl_hdbif'; sys.path.insert(0,str(source))
    from modules.irisRecognition import irisRecognition
    old=ROOT/'outputs/melhoria_normalizacao_val_gpu_2026-10-20'
    config=json.loads((old/'protocolo.json').read_text())['config']; config['cuda']=device.type=='cuda'
    for metadata in ('fontes.json','pesos.json'):
        for item in json.loads((source/metadata).read_text())['files']:
            if hashlib.sha256((source/item['path']).read_bytes()).hexdigest()!=item['sha256']: raise ValueError('CVRL checksum mismatch')
    model=irisRecognition(config); templates=[]; audits=[]
    cache=OUT/'templates'; cache.mkdir(exist_ok=True)
    for i,row in enumerate(chosen):
        target=old/'roi_reference'/(Path(row.image).stem+'.npz')
        if not target.exists(): target=cache/(Path(row.image).stem+'.npz')
        if target.exists():
            with np.load(target) as z:
                audit=json.loads(str(z['audit'])); template=prepare(z['code'],z['mask']) if audit['valid'] else None
        else:
            with Image.open(row.image) as im: original=im.convert('L')
            with Image.open(row.mask) as im: ref=decode_mask(im)==1
            image,mask=iso_pair(original,Image.fromarray(ref.astype(np.uint8)*255),True)
            pupil,iris=model.circApprox(image)
            ok=bool(ref.any() and np.isfinite(pupil).all() and np.isfinite(iris).all() and 0<pupil[2]<iris[2])
            pm=np.zeros((64,512),np.uint8); code=np.zeros((5,48,512),bool)
            if ok:
                polar,pm=model.cartToPol_torch(image,mask,pupil,iris); ok=bool((pm[8:-8]>0).any())
                if ok: code=model.extractCode(polar)[0]
            audit={'image':Path(row.image).name,'valid':ok,'polar_valid_fraction':float((pm>0).mean()),'pupil_circle':pupil.tolist(),'iris_circle':iris.tolist()}
            np.savez_compressed(target,code=code,mask=pm,audit=json.dumps(audit))
            template=prepare(code,pm) if ok else None
        templates.append(template); audits.append(audit)
        if (i+1)%100==0: print(f'HDBIF templates {i+1}/{len(chosen)}',flush=True)
    (OUT/'auditoria_hdbif.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
    available=[i for i,t in enumerate(templates[:ng]) if t is not None]
    blocks=[(positions,gallery_batch([templates[p] for p in positions])) for start in range(0,len(available),16) if (positions:=available[start:start+16])]
    raw=np.full((len(queries),ng),-2.,np.float64)
    for qi,t in enumerate(templates[ng:]):
        if t is not None:
            for positions,batch in blocks: raw[qi,positions]=scores_batch(t,batch)
        if (qi+1)%25==0: print(f'HDBIF multicapture scores {qi+1}/{len(queries)}; {time.monotonic()-started:.0f}s',flush=True)
    np.savez_compressed(OUT/'scores_hdbif_capturas.npz',scores=raw)
    for mode in ('first','max','top3'): record('hdbif_reference_'+mode,aggregate(raw,groups,mode),[t is not None for t in templates[ng:]])
    (OUT/'CONCLUIDO.json').write_text(json.dumps({'status':'development_validation_completed','scientific_final_result':False,'counts':protocol['counts'],'results':results,'elapsed_seconds':time.monotonic()-started},indent=2),encoding='utf-8')

if __name__=='__main__': main()
