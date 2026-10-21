"""Comparacao de desenvolvimento HDBIF UBIPr: imagem inteira vs ROI, somente val."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import sys
import time
import numpy as np
from PIL import Image, ImageDraw
import torch

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/melhoria_normalizacao_val_2026-10-20'

def iso_pair(image, mask, crop):
    """Mesma geometria para imagem e mascara; padding da mascara sempre zero."""
    if crop:
        yy,xx=np.where(np.asarray(mask)>0)
        if len(xx):
            px=max(2,round((xx.max()-xx.min()+1)*.5)); py=max(2,round((yy.max()-yy.min()+1)*.5))
            box=(max(0,int(xx.min())-px),max(0,int(yy.min())-py),min(image.width,int(xx.max())+px+1),min(image.height,int(yy.max())+py+1))
            image=image.crop(box); mask=mask.crop(box)
    w,h=image.size
    nw=max(w,int(np.ceil(h*4/3))); nh=max(h,int(np.ceil(w*3/4)))
    offset=((nw-w)//2,(nh-h)//2)
    padded=Image.new('L',(nw,nh),127); padded.paste(image,offset)
    padded_mask=Image.new('L',(nw,nh),0); padded_mask.paste(mask,offset)
    return padded.resize((640,480),Image.Resampling.BILINEAR),padded_mask.resize((640,480),Image.Resampling.NEAREST)

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    from treinar_segmentacao_ubipr import decode_mask
    from matcher_hdbif_fft import prepare,distances,best_score
    torch.set_num_threads(4)
    source=ROOT/'data/modelos/cvrl_hdbif'; sys.path.insert(0,str(source))
    from modules.irisRecognition import irisRecognition
    pilot=json.loads((ROOT/'outputs/hdbif_validacao_piloto_2026-10-20/protocolo.json').read_text(encoding='utf-8'))
    manifest=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    rows=load_splits(json.loads(manifest.read_text(encoding='utf-8')))['val']
    ids=sorted({identity(r) for r in rows})
    gallery=[sorted([r for r in rows if identity(r)==eye and r.session==1],key=lambda r:Path(r.image).name)[0] for eye in ids]
    queries=[r for r in rows if r.session==2]; chosen=gallery+queries
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Development validation only; no test scores or minimum-area claim',
        'variants':['full_reference','roi_reference'],'crop':'Reference bbox with 50% margin per axis, grayscale, aspect preserving ISO640x480; reference mask geometry identical with zero padding',
        'gallery':'One first lexicographic session1 image per eye; all eligible session2 queries; no score selection',
        'matcher':'HDBIF 17x17 five filters, +/-16 columns, raw masked Hamming; no score normalization',
        'calibration':'Each variant validation FMR<=1%; development estimates, not independent evaluation',
        'failures':'Keep every eye and query; invalid templates/pairs reject; no post-score exclusions',
        'limitations':'Reference mask assisted ROI, pretrained circle027 differs source config; training population independence unknown; gallery differs neural centroid protocol',
        'config':pilot['config'],'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'people':len({r.subject for r in rows}),'eyes':len(ids),'queries':len(queries),'images':len(chosen)}
    OUT.mkdir(exist_ok=True,parents=True)
    signature=hashlib.sha256(json.dumps({k:v for k,v in protocol.items() if k!='registered_utc'},sort_keys=True).encode()).hexdigest()
    registration=OUT/'protocolo.json'
    if registration.exists():
        if json.loads(registration.read_text())['signature']!=signature: raise ValueError('Changed protocol; preserve previous folder')
    else: registration.write_text(json.dumps(dict(protocol,signature=signature),indent=2),encoding='utf-8')
    (OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    model=irisRecognition(pilot['config']); summaries=[]; started=time.monotonic()
    qa=[]; audits=[]
    for variant in protocol['variants']:
        cache=OUT/variant; cache.mkdir(exist_ok=True); templates=[]
        for i,row in enumerate(chosen):
            target=cache/(Path(row.image).stem+'.npz')
            if target.exists():
                with np.load(target) as z:
                    audit=json.loads(str(z['audit'])); template=prepare(z['code'],z['mask']) if audit['valid'] else None
            else:
                original=Image.open(row.image).convert('L'); ref=decode_mask(Image.open(row.mask))==1
                image,mask=iso_pair(original,Image.fromarray(ref.astype(np.uint8)*255),variant=='roi_reference')
                pupil,iris=model.circApprox(image)
                ok=bool(ref.any() and np.isfinite(pupil).all() and np.isfinite(iris).all() and 0<pupil[2]<iris[2])
                polar=np.zeros((64,512),np.uint8); pm=np.zeros_like(polar); code=np.zeros((5,48,512),bool)
                if ok:
                    polar,pm=model.cartToPol_torch(image,mask,pupil,iris)
                    ok=bool((pm[8:-8]>0).any())
                    if ok: code=model.extractCode(polar)[0]
                yy,xx=np.where(ref)
                audit={'variant':variant,'image':Path(row.image).name,'valid':ok,'iris_width_pixels':int(xx.max()-xx.min()+1) if len(xx) else 0,
                    'iris_height_pixels':int(yy.max()-yy.min()+1) if len(yy) else 0,'polar_valid_fraction':float((pm>0).mean()),'pupil_circle':pupil.tolist(),'iris_circle':iris.tolist()}
                temporary=target.with_suffix('.part.npz'); np.savez_compressed(temporary,code=code,mask=pm,audit=json.dumps(audit)); temporary.replace(target)
                template=prepare(code,pm) if ok else None
                if i in (0,1,2,3):
                    visual=image.convert('RGB'); draw=ImageDraw.Draw(visual)
                    for circle,color in [(pupil,'red'),(iris,'lime')]:
                        x,y,r=map(float,circle)
                        if np.isfinite(circle).all() and r>0: draw.ellipse((x-r,y-r,x+r,y+r),outline=color,width=2)
                    qa.append((variant,Path(row.image).stem,visual,polar,pm))
            templates.append(template); audits.append(audit)
            if (i+1)%50==0: print(f'{variant} templates {i+1}/{len(chosen)} {time.monotonic()-started:.0f}s',flush=True)
        scores=np.full((len(queries),len(ids)),-2.,np.float64)
        for qi in range(len(queries)):
            query=templates[len(ids)+qi]
            for gi in range(len(ids)):
                if query is not None and templates[gi] is not None:
                    raw,_,_=distances(query,templates[gi]); scores[qi,gi]=best_score(raw,16)
            if (qi+1)%100==0: print(f'{variant} scores {qi+1}/{len(queries)}',flush=True)
        labels=np.array([ids.index(identity(r)) for r in queries]); valid=np.array([t is not None for t in templates[len(ids):]])&(scores>=0).any(1)
        imp=np.ones_like(scores,dtype=bool); imp[np.arange(len(labels)),labels]=False
        threshold=operating_threshold(scores[imp&(scores>=0)])
        result,correct,accepted=metrics(scores,labels,threshold,valid)
        summary={'variant':variant,'threshold':threshold,**result,'joint_success':float((correct&accepted).mean()),'failed_gallery':sum(t is None for t in templates[:len(ids)]),'failed_images':sum(t is None for t in templates)}
        summaries.append(summary)
        np.savez_compressed(cache/'scores.npz',scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
        (OUT/'resultados_parciais.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
        print(json.dumps(summary),flush=True)
    if qa:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(len(qa),3,figsize=(12,2.5*len(qa)))
        for i,(variant,name,image,polar,mask) in enumerate(qa):
            for ax,value,title in zip(axes[i],(image,polar,mask),(variant+' '+name,'Textura polar','Mascara polar valida')):
                ax.imshow(value,cmap='gray'); ax.set_title(title,fontsize=9); ax.axis('off')
        fig.tight_layout(); fig.savefig(OUT/'qa_normalizacao.png',dpi=130); plt.close(fig)
    (OUT/'auditoria.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
    widths=np.array([r['iris_width_pixels'] for r in audits if r['variant']=='full_reference' and r['iris_width_pixels']])
    result={'status':'validation_completed','scientific_final_result':False,'results':summaries,'iris_native_width_percentiles':dict(zip(['p10','median','p90'],np.percentile(widths,[10,50,90]).tolist())),'elapsed_seconds':time.monotonic()-started}
    (OUT/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()
