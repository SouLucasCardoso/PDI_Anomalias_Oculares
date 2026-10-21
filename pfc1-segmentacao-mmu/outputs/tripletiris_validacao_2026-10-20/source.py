"""CVRL TripletIris polar: desenvolvimento somente na validacao UBIPr."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,sys,time
import numpy as np
from PIL import Image,ImageDraw
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    from treinar_segmentacao_ubipr import decode_mask,MulticlassUNet
    from validar_melhoria_normalizacao import iso_pair
    from comparador_hdbif_lote import aggregate
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    torch.set_num_threads(4)
    source=ROOT/'data/modelos/cvrl_tripletiris';metadata={}
    for name in ('fontes.json','pesos.json'):
        metadata[name]=json.loads((source/name).read_text())
        for item in metadata[name]['files']:
            if hashlib.sha256((source/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('CVRL source/weight checksum mismatch')
    manifest=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    rows=load_splits(json.loads(manifest.read_text()))['val']
    if args.smoke:
        eyes=sorted({identity(r) for r in rows})[:4]
        rows=[next(r for r in rows if identity(r)==eye and r.session==session) for eye in eyes for session in (1,2)]
    ids=sorted({identity(r) for r in rows});gallery=sorted([r for r in rows if r.session==1],key=lambda r:(identity(r),Path(r.image).name));queries=[r for r in rows if r.session==2];chosen=gallery+queries;ng=len(gallery)
    groups=[[i for i,r in enumerate(gallery) if identity(r)==eye] for eye in ids];labels=np.array([ids.index(identity(r)) for r in queries])
    out=ROOT/'outputs'/('tripletiris_piloto_2026-10-20' if args.smoke else 'tripletiris_validacao_2026-10-20');out.mkdir(exist_ok=True)
    config={'cuda':torch.cuda.is_available(),'polar_height':64,'polar_width':512,'circle_model_path':str(source/'models/resnet18-1543-0.047488-maskIoU-0.934494.pth'),'nn_model_path':str(source/'models/convnext_tiny-znorm-best.pth')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'technical_smoke':args.smoke,
        'scope':'Development validation only; public pretrained TripletIris, no identity retraining or test/occlusion inference',
        'variants':['full_author','roi_reference','roi_automatic'],'config':config,'provenance':metadata,
        'preprocessing':'Red channel as authors demo; full uses author fix_image; ROI reference/automatic bbox50% margin then our aspect-preserving bilinear ISO640x480; no iris mask applied to polar texture',
        'encoder':'Official extractVector, per-image z-normalization clipped[-4,4], ConvNeXt-tiny2048, no embedding L2 normalization',
        'comparison':'Official Euclidean distance mapped monotonically to1/(1+distance), then first/max/top3 gallery aggregation; these gallery rules are our extension',
        'failure_handling':'Retain all eyes/queries; empty ROI masks or nonfinite/nonpositive circles with pupil>=iris reject; zero/nonfinite polar variance rejects; invalid comparisons score-2',
        'calibration':'Each variant validation empirical FMR<=1%; rates are development not independent confirmation',
        'caveats':'Different pretrained model/normalizer/input, no isolated architecture effect; source training population overlap unknown; reference ROI assisted; automatic ROI may include context; no universal minimum claim',
        'counts':{'people':len({r.subject for r in chosen}),'eyes':len(ids),'gallery_images':ng,'queries':len(queries),'images':len(chosen)},
        'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'unet_sha256':hashlib.sha256((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt').read_bytes()).hexdigest(),
        'dependencies_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['validar_melhoria_normalizacao.py','comparador_hdbif_lote.py','avaliar_robustez_reconhecimento.py']}}
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous run')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    sys.path.insert(0,str(source));from modules.irisRecognition import irisRecognition
    model=irisRecognition(config);device=model.device
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    results=[];audits=[];qa=[];started=time.monotonic()
    for variant in protocol['variants']:
        vectors=[];valid=[]
        for i,row in enumerate(chosen):
            with Image.open(row.image) as im:rgb=im.convert('RGB')
            image=Image.fromarray(np.asarray(rgb)[:,:,0],'L');ok=True
            if variant=='full_author':image=model.fix_image(image)
            else:
                if variant=='roi_reference':
                    with Image.open(row.mask) as im:mask=decode_mask(im)==1
                else:
                    small=np.asarray(rgb.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255
                    with torch.inference_mode():mask=unet(torch.from_numpy(small.transpose(2,0,1).copy())[None].to(device)).argmax(1)[0].cpu().numpy()==1
                    mask=np.asarray(Image.fromarray(mask).resize(rgb.size,Image.Resampling.NEAREST),dtype=bool)
                ok=bool(mask.any());image,_=iso_pair(image,Image.fromarray(mask.astype(np.uint8)*255),True)
            pupil,iris=model.circApprox(image)
            ok=bool(ok and np.isfinite(pupil).all() and np.isfinite(iris).all() and 0<pupil[2]<iris[2])
            vector=np.zeros(2048,np.float32);polar=np.zeros((64,512),np.uint8)
            if ok:
                polar=model.cartToPol_torch(image,pupil,iris)
                ok=bool(np.isfinite(polar).all() and np.std(polar)>0)
                if ok:
                    vector=model.extractVector(polar);ok=bool(np.isfinite(vector).all())
            vectors.append(vector);valid.append(ok)
            audits.append({'variant':variant,'image':Path(row.image).name,'valid':ok,'pupil_circle':pupil.tolist(),'iris_circle':iris.tolist()})
            if i<2:
                visual=image.convert('RGB');draw=ImageDraw.Draw(visual)
                for circle,color in [(pupil,'red'),(iris,'lime')]:
                    if np.isfinite(circle).all() and circle[2]>0:
                        x,y,r=map(float,circle);draw.ellipse((x-r,y-r,x+r,y+r),outline=color,width=2)
                qa.append((variant,Path(row.image).stem,visual,polar))
            if (i+1)%100==0:print(f'{variant} {i+1}/{len(chosen)} {time.monotonic()-started:.0f}s',flush=True)
        vectors=np.asarray(vectors);valid=np.asarray(valid)
        np.savez_compressed(out/('features_'+variant+'.npz'),features=vectors,valid=valid)
        # Float64 prevents cancellation for very similar high-dimensional vectors.
        a=vectors[ng:].astype(np.float64);b=vectors[:ng].astype(np.float64)
        d=np.sqrt(np.maximum(0,(a*a).sum(1)[:,None]+(b*b).sum(1)[None,:]-2*a@b.T))
        raw=1/(1+d);raw[:,~valid[:ng]]=-2
        for mode in ('first','max','top3'):
            name=variant+'_'+mode;scores=aggregate(raw,groups,mode);qvalid=valid[ng:]&(scores>-2).any(1)
            imp=np.ones_like(scores,dtype=bool);imp[np.arange(len(labels)),labels]=False;usable=imp&qvalid[:,None]&(scores>-2)
            threshold=operating_threshold(scores[usable]) if usable.any() else 2.
            measured,correct,accepted=metrics(scores,labels,threshold,qvalid)
            measured.update(variant=name,threshold=threshold,joint_success=float((correct&accepted).mean()),failed_images=int((~valid).sum()))
            results.append(measured);np.savez_compressed(out/(name+'.npz'),scores=scores,labels=labels,valid=qvalid,correct=correct,accepted=accepted)
            print(json.dumps(measured),flush=True)
        (out/'resultados_parciais.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(len(qa),2,figsize=(11,2.6*len(qa)))
    for i,(variant,name,image,polar) in enumerate(qa):
        for ax,value,title in [(axes[i,0],image,variant+' '+name),(axes[i,1],polar,'Faixa polar usada no encoder')]:ax.imshow(value,cmap='gray');ax.set_title(title,fontsize=10);ax.axis('off')
    fig.tight_layout();fig.savefig(out/'qa_polar_tripletiris.png',dpi=140);plt.close(fig)
    (out/'auditoria.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
    (out/'CONCLUIDO.json').write_text(json.dumps({'status':'validation_completed','scientific_final_result':False,'technical_smoke':args.smoke,'counts':protocol['counts'],'results':results,'elapsed_seconds':time.monotonic()-started},indent=2),encoding='utf-8')

if __name__=='__main__':main()
